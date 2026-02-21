from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, ArticleState, Feed, FeedFolder
from sift.domain.schemas import FeedCreate, FeedLifecycleUpdate, FeedSettingsUpdate


class FeedService:
    async def list_feeds(self, session: AsyncSession, user_id: UUID, include_archived: bool = False) -> Sequence[Feed]:
        query = select(Feed).where(Feed.owner_id == user_id)
        if not include_archived:
            query = query.where(Feed.is_archived.is_(False))
        query = query.order_by(Feed.created_at.desc())
        result = await session.execute(query)
        return result.scalars().all()

    async def get_feed(self, session: AsyncSession, feed_id: UUID, user_id: UUID) -> Feed | None:
        query = select(Feed).where(Feed.id == feed_id, Feed.owner_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_feed(self, session: AsyncSession, data: FeedCreate, user_id: UUID) -> Feed:
        if data.folder_id is not None:
            folder_query = select(FeedFolder.id).where(FeedFolder.id == data.folder_id, FeedFolder.user_id == user_id)
            folder_result = await session.execute(folder_query)
            if folder_result.scalar_one_or_none() is None:
                raise FeedFolderNotFoundError(f"Folder {data.folder_id} not found")

        feed = Feed(
            owner_id=user_id,
            folder_id=data.folder_id,
            title=data.title.strip(),
            url=str(data.url),
            site_url=str(data.site_url) if data.site_url else None,
        )
        session.add(feed)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise FeedAlreadyExistsError("Feed already exists") from exc
        await session.refresh(feed)
        return feed

    async def list_active_feeds(self, session: AsyncSession, limit: int = 500) -> Sequence[Feed]:
        query = (
            select(Feed)
            .where(
                Feed.is_active.is_(True),
                Feed.is_archived.is_(False),
                Feed.owner_id.is_not(None),
            )
            # Scheduler fairness: prioritize never-fetched feeds, then oldest fetch first.
            .order_by(Feed.last_fetched_at.asc().nullsfirst(), Feed.created_at.asc())
            .limit(limit)
        )
        result = await session.execute(query)
        return result.scalars().all()

    async def update_feed_settings(
        self,
        session: AsyncSession,
        *,
        feed: Feed,
        payload: FeedSettingsUpdate,
    ) -> Feed:
        if payload.fetch_interval_minutes < 1 or payload.fetch_interval_minutes > 10080:
            raise FeedValidationError("fetch_interval_minutes must be between 1 and 10080")
        feed.fetch_interval_minutes = payload.fetch_interval_minutes
        await session.commit()
        await session.refresh(feed)
        return feed

    async def transition_lifecycle(
        self,
        session: AsyncSession,
        *,
        feed: Feed,
        user_id: UUID,
        payload: FeedLifecycleUpdate,
    ) -> tuple[Feed, int]:
        action = payload.action
        marked_read_count = 0
        now = datetime.now(UTC)

        if action == "pause":
            if feed.is_archived:
                raise FeedLifecycleError("Cannot pause an archived feed")
            feed.is_active = False
        elif action == "resume":
            if feed.is_archived:
                raise FeedLifecycleError("Cannot resume an archived feed")
            feed.is_active = True
        elif action == "archive":
            if not feed.is_archived:
                feed.is_archived = True
                feed.is_active = False
                feed.archived_at = now
                marked_read_count = await self._mark_feed_unread_as_read(
                    session=session,
                    user_id=user_id,
                    feed_id=feed.id,
                )
        elif action == "unarchive":
            if feed.is_archived:
                feed.is_archived = False
                feed.archived_at = None
                feed.is_active = True
        else:
            raise FeedLifecycleError(f"Unsupported lifecycle action: {action}")

        await session.commit()
        await session.refresh(feed)
        return feed, marked_read_count

    async def assign_folder(
        self,
        session: AsyncSession,
        *,
        feed: Feed,
        user_id: UUID,
        folder_id: UUID | None,
    ) -> Feed:
        if folder_id is None:
            feed.folder_id = None
            await session.commit()
            await session.refresh(feed)
            return feed

        folder_query = select(FeedFolder.id).where(FeedFolder.id == folder_id, FeedFolder.user_id == user_id)
        folder_result = await session.execute(folder_query)
        if folder_result.scalar_one_or_none() is None:
            raise FeedFolderNotFoundError(f"Folder {folder_id} not found")

        feed.folder_id = folder_id
        await session.commit()
        await session.refresh(feed)
        return feed

    async def _mark_feed_unread_as_read(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        feed_id: UUID,
    ) -> int:
        unread_query = (
            select(Article.id)
            .where(Article.feed_id == feed_id)
            .outerjoin(
                ArticleState,
                and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
            )
            .where(
                func.coalesce(ArticleState.is_read, False).is_(False),
                func.coalesce(ArticleState.is_archived, False).is_(False),
            )
        )
        unread_rows = await session.execute(unread_query)
        unread_article_ids = list(unread_rows.scalars().all())
        if not unread_article_ids:
            return 0

        states_query = select(ArticleState).where(
            ArticleState.user_id == str(user_id),
            ArticleState.article_id.in_(unread_article_ids),
        )
        existing_states_result = await session.execute(states_query)
        state_by_article_id = {state.article_id: state for state in existing_states_result.scalars().all()}

        for article_id in unread_article_ids:
            state = state_by_article_id.get(article_id)
            if state is None:
                session.add(
                    ArticleState(
                        user_id=str(user_id),
                        article_id=article_id,
                        is_read=True,
                        is_starred=False,
                        is_archived=False,
                    )
                )
                continue
            state.is_read = True

        return len(unread_article_ids)


feed_service = FeedService()


class FeedAlreadyExistsError(Exception):
    pass


class FeedFolderNotFoundError(Exception):
    pass


class FeedLifecycleError(Exception):
    pass


class FeedValidationError(Exception):
    pass
