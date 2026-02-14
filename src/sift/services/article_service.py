from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import Select, and_, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, ArticleState, Feed, KeywordStream, KeywordStreamMatch
from sift.domain.schemas import ArticleDetailOut, ArticleListItemOut, ArticleListResponse, ArticleStateOut

ScopeType = Literal["system", "folder", "feed", "stream"]
StateFilter = Literal["all", "unread", "saved", "archived", "fresh", "recent"]
SortMode = Literal["newest", "oldest", "unread_first"]


class ArticleNotFoundError(Exception):
    pass


class ArticleStateValidationError(Exception):
    pass


@dataclass(slots=True)
class _ListContext:
    read_expr: Any
    starred_expr: Any
    archived_expr: Any


def _scope_filter(
    *,
    user_id: UUID,
    scope_type: ScopeType,
    scope_id: UUID | None,
) -> Any | None:
    if scope_type == "system":
        return None
    if scope_id is None:
        raise ArticleStateValidationError("scope_id is required for non-system scopes")

    if scope_type == "folder":
        return Feed.folder_id == scope_id
    if scope_type == "feed":
        return Article.feed_id == scope_id
    if scope_type == "stream":
        return exists(
            select(KeywordStreamMatch.id)
            .join(KeywordStream, KeywordStream.id == KeywordStreamMatch.stream_id)
            .where(
                KeywordStreamMatch.article_id == Article.id,
                KeywordStream.id == scope_id,
                KeywordStream.user_id == user_id,
            )
        )
    raise ArticleStateValidationError(f"Unsupported scope_type: {scope_type}")


def _state_filter(
    *,
    state: StateFilter,
    read_expr: Any,
    starred_expr: Any,
    archived_expr: Any,
    state_updated_at_expr: Any,
) -> Any:
    now = datetime.now(UTC)
    if state == "all":
        return archived_expr.is_(False)
    if state == "unread":
        return and_(read_expr.is_(False), archived_expr.is_(False))
    if state == "saved":
        return and_(starred_expr.is_(True), archived_expr.is_(False))
    if state == "archived":
        return archived_expr.is_(True)
    if state == "fresh":
        threshold = now - timedelta(days=3)
        return and_(
            read_expr.is_(False),
            archived_expr.is_(False),
            func.coalesce(Article.published_at, Article.created_at) >= threshold,
        )
    if state == "recent":
        threshold = now - timedelta(days=7)
        return and_(read_expr.is_(True), state_updated_at_expr >= threshold)
    raise ArticleStateValidationError(f"Unsupported state filter: {state}")


def _sorting_clause(*, sort: SortMode, read_expr: Any) -> tuple[Any, ...]:
    timestamp = func.coalesce(Article.published_at, Article.created_at)
    if sort == "newest":
        return (timestamp.desc(), Article.created_at.desc())
    if sort == "oldest":
        return (timestamp.asc(), Article.created_at.asc())
    if sort == "unread_first":
        return (read_expr.asc(), timestamp.desc(), Article.created_at.desc())
    raise ArticleStateValidationError(f"Unsupported sort mode: {sort}")


class ArticleService:
    def _base_query(
        self,
        *,
        user_id: UUID,
    ) -> tuple[Select[tuple[Article, str, bool, bool, bool]], _ListContext]:
        state_user_key = str(user_id)
        read_expr = func.coalesce(ArticleState.is_read, False)
        starred_expr = func.coalesce(ArticleState.is_starred, False)
        archived_expr = func.coalesce(ArticleState.is_archived, False)
        query = (
            select(
                Article,
                Feed.title.label("feed_title"),
                read_expr.label("is_read"),
                starred_expr.label("is_starred"),
                archived_expr.label("is_archived"),
            )
            .join(Feed, Feed.id == Article.feed_id)
            .outerjoin(
                ArticleState,
                and_(ArticleState.article_id == Article.id, ArticleState.user_id == state_user_key),
            )
            .where(Feed.owner_id == user_id)
        )
        return query, _ListContext(read_expr=read_expr, starred_expr=starred_expr, archived_expr=archived_expr)

    async def list_articles(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        scope_type: ScopeType,
        scope_id: UUID | None,
        state: StateFilter,
        q: str | None,
        limit: int,
        offset: int,
        sort: SortMode,
    ) -> ArticleListResponse:
        base_query, context = self._base_query(user_id=user_id)

        filters: list[Any] = []
        scope_condition = _scope_filter(user_id=user_id, scope_type=scope_type, scope_id=scope_id)
        if scope_condition is not None:
            filters.append(scope_condition)

        state_condition = _state_filter(
            state=state,
            read_expr=context.read_expr,
            starred_expr=context.starred_expr,
            archived_expr=context.archived_expr,
            state_updated_at_expr=func.coalesce(ArticleState.updated_at, Article.created_at),
        )
        filters.append(state_condition)

        if q:
            like = f"%{q.strip().lower()}%"
            if like != "%%":
                filters.append(
                    or_(
                        func.lower(Article.title).like(like),
                        func.lower(Article.content_text).like(like),
                        func.lower(Feed.title).like(like),
                    )
                )

        count_query = (
            select(func.count())
            .select_from(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .outerjoin(
                ArticleState,
                and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
            )
            .where(Feed.owner_id == user_id, *filters)
        )
        total_result = await session.execute(count_query)
        total = int(total_result.scalar_one() or 0)

        rows_result = await session.execute(
            base_query.where(*filters).order_by(*_sorting_clause(sort=sort, read_expr=context.read_expr)).limit(limit).offset(offset)
        )
        rows = rows_result.all()
        article_ids = [row[0].id for row in rows]
        stream_map = await self._stream_map(session=session, user_id=user_id, article_ids=article_ids)

        items = [
            ArticleListItemOut(
                id=article.id,
                feed_id=article.feed_id,
                feed_title=feed_title,
                title=article.title,
                canonical_url=article.canonical_url,
                published_at=article.published_at,
                created_at=article.created_at,
                is_read=bool(is_read),
                is_starred=bool(is_starred),
                is_archived=bool(is_archived),
                stream_ids=stream_map.get(article.id, []),
            )
            for article, feed_title, is_read, is_starred, is_archived in rows
        ]
        return ArticleListResponse(items=items, total=total, limit=limit, offset=offset)

    async def get_article_detail(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_id: UUID,
    ) -> ArticleDetailOut:
        query, _ = self._base_query(user_id=user_id)
        result = await session.execute(query.where(Article.id == article_id))
        row = result.one_or_none()
        if row is None:
            raise ArticleNotFoundError(f"Article {article_id} not found")

        article, feed_title, is_read, is_starred, is_archived = row
        stream_map = await self._stream_map(session=session, user_id=user_id, article_ids=[article.id])
        return ArticleDetailOut(
            id=article.id,
            feed_id=article.feed_id,
            feed_title=feed_title,
            source_id=article.source_id,
            canonical_url=article.canonical_url,
            title=article.title,
            content_text=article.content_text,
            language=article.language,
            published_at=article.published_at,
            created_at=article.created_at,
            is_read=bool(is_read),
            is_starred=bool(is_starred),
            is_archived=bool(is_archived),
            stream_ids=stream_map.get(article.id, []),
        )

    async def patch_state(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_id: UUID,
        is_read: bool | None,
        is_starred: bool | None,
        is_archived: bool | None,
    ) -> ArticleStateOut:
        if is_read is None and is_starred is None and is_archived is None:
            raise ArticleStateValidationError("At least one state field must be provided")

        await self._assert_article_visible(session=session, user_id=user_id, article_id=article_id)
        state = await self._get_or_create_state(session=session, user_id=user_id, article_id=article_id)
        if is_read is not None:
            state.is_read = is_read
        if is_starred is not None:
            state.is_starred = is_starred
        if is_archived is not None:
            state.is_archived = is_archived
        await session.commit()
        await session.refresh(state)
        return ArticleStateOut(
            article_id=article_id,
            is_read=state.is_read,
            is_starred=state.is_starred,
            is_archived=state.is_archived,
        )

    async def bulk_patch_state(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_ids: list[UUID],
        is_read: bool | None,
        is_starred: bool | None,
        is_archived: bool | None,
    ) -> int:
        if is_read is None and is_starred is None and is_archived is None:
            raise ArticleStateValidationError("At least one state field must be provided")
        if not article_ids:
            return 0

        visible_query = (
            select(Article.id)
            .join(Feed, Feed.id == Article.feed_id)
            .where(Feed.owner_id == user_id, Article.id.in_(article_ids))
        )
        visible_rows = await session.execute(visible_query)
        visible_ids = list(visible_rows.scalars().all())
        if not visible_ids:
            return 0

        existing_query = select(ArticleState).where(
            ArticleState.user_id == str(user_id),
            ArticleState.article_id.in_(visible_ids),
        )
        existing_rows = await session.execute(existing_query)
        state_by_article_id = {state.article_id: state for state in existing_rows.scalars().all()}

        for article_id in visible_ids:
            state = state_by_article_id.get(article_id)
            if state is None:
                state = ArticleState(
                    user_id=str(user_id),
                    article_id=article_id,
                    is_read=False,
                    is_starred=False,
                    is_archived=False,
                )
                session.add(state)
                state_by_article_id[article_id] = state
            if is_read is not None:
                state.is_read = is_read
            if is_starred is not None:
                state.is_starred = is_starred
            if is_archived is not None:
                state.is_archived = is_archived

        await session.commit()
        return len(visible_ids)

    async def _stream_map(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_ids: list[UUID],
    ) -> dict[UUID, list[UUID]]:
        if not article_ids:
            return {}
        query = (
            select(KeywordStreamMatch.article_id, KeywordStreamMatch.stream_id)
            .join(KeywordStream, KeywordStream.id == KeywordStreamMatch.stream_id)
            .where(
                KeywordStream.user_id == user_id,
                KeywordStreamMatch.article_id.in_(article_ids),
            )
        )
        rows = await session.execute(query)
        mapping: dict[UUID, list[UUID]] = {article_id: [] for article_id in article_ids}
        for article_id, stream_id in rows.all():
            mapping.setdefault(article_id, []).append(stream_id)
        return mapping

    async def _assert_article_visible(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_id: UUID,
    ) -> None:
        query = (
            select(Article.id)
            .join(Feed, Feed.id == Article.feed_id)
            .where(Article.id == article_id, Feed.owner_id == user_id)
        )
        result = await session.execute(query)
        if result.scalar_one_or_none() is None:
            raise ArticleNotFoundError(f"Article {article_id} not found")

    async def _get_or_create_state(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_id: UUID,
    ) -> ArticleState:
        query = select(ArticleState).where(
            ArticleState.user_id == str(user_id),
            ArticleState.article_id == article_id,
        )
        result = await session.execute(query)
        state = result.scalar_one_or_none()
        if state is not None:
            return state

        state = ArticleState(
            user_id=str(user_id),
            article_id=article_id,
            is_read=False,
            is_starred=False,
            is_archived=False,
        )
        session.add(state)
        await session.flush()
        return state


article_service = ArticleService()
