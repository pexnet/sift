from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, ArticleState, Feed
from sift.domain.schemas import FeedHealthItemOut, FeedHealthListResponse, FeedHealthSummaryOut

FeedLifecycleFilter = Literal["all", "active", "paused", "archived"]


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _feed_lifecycle_status(feed: Feed) -> Literal["active", "paused", "archived"]:
    if feed.is_archived:
        return "archived"
    if feed.is_active:
        return "active"
    return "paused"


def _stale_threshold_seconds(feed: Feed) -> float:
    return float(max(6 * 3600, 4 * feed.fetch_interval_minutes * 60))


def _feed_staleness(feed: Feed, now: datetime) -> tuple[bool, float | None]:
    if feed.is_archived or not feed.is_active:
        return False, None

    last_success = _normalize_datetime(feed.last_fetch_success_at)
    if last_success is None:
        return True, None

    age_seconds = max(0.0, (now - last_success).total_seconds())
    is_stale = age_seconds > _stale_threshold_seconds(feed)
    stale_age_hours = round(age_seconds / 3600, 2) if is_stale else None
    return is_stale, stale_age_hours


def _has_error(feed: Feed) -> bool:
    return bool((feed.last_fetch_error or "").strip())


class FeedHealthService:
    async def list_feed_health(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        lifecycle: FeedLifecycleFilter,
        q: str | None,
        stale_only: bool,
        error_only: bool,
        limit: int,
        offset: int,
    ) -> FeedHealthListResponse:
        now = datetime.now(UTC)
        summary = await self._summary(session=session, user_id=user_id, now=now)

        feeds_query = select(Feed).where(Feed.owner_id == user_id)
        if lifecycle == "active":
            feeds_query = feeds_query.where(Feed.is_archived.is_(False), Feed.is_active.is_(True))
        elif lifecycle == "paused":
            feeds_query = feeds_query.where(Feed.is_archived.is_(False), Feed.is_active.is_(False))
        elif lifecycle == "archived":
            feeds_query = feeds_query.where(Feed.is_archived.is_(True))

        normalized_q = (q or "").strip().lower()
        if normalized_q:
            like = f"%{normalized_q}%"
            feeds_query = feeds_query.where(
                or_(
                    func.lower(Feed.title).like(like),
                    func.lower(Feed.url).like(like),
                    func.lower(func.coalesce(Feed.site_url, "")).like(like),
                )
            )

        feeds_result = await session.execute(feeds_query.order_by(Feed.title.asc(), Feed.created_at.asc()))
        feeds = feeds_result.scalars().all()
        feed_ids = [feed.id for feed in feeds]
        article_count_by_feed = await self._articles_last_7d(session=session, user_id=user_id, feed_ids=feed_ids, now=now)
        unread_count_by_feed = await self._unread_counts(session=session, user_id=user_id, feed_ids=feed_ids)

        items: list[FeedHealthItemOut] = []
        for feed in feeds:
            is_stale, stale_age_hours = _feed_staleness(feed, now)
            if stale_only and not is_stale:
                continue
            if error_only and not _has_error(feed):
                continue

            articles_last_7d = int(article_count_by_feed.get(feed.id, 0))
            items.append(
                FeedHealthItemOut(
                    feed_id=feed.id,
                    title=feed.title,
                    url=feed.url,
                    site_url=feed.site_url,
                    folder_id=feed.folder_id,
                    lifecycle_status=_feed_lifecycle_status(feed),
                    fetch_interval_minutes=feed.fetch_interval_minutes,
                    last_fetched_at=_normalize_datetime(feed.last_fetched_at),
                    last_fetch_success_at=_normalize_datetime(feed.last_fetch_success_at),
                    last_fetch_error=feed.last_fetch_error,
                    last_fetch_error_at=_normalize_datetime(feed.last_fetch_error_at),
                    is_stale=is_stale,
                    stale_age_hours=stale_age_hours,
                    articles_last_7d=articles_last_7d,
                    estimated_articles_per_day_7d=round(articles_last_7d / 7, 2),
                    unread_count=int(unread_count_by_feed.get(feed.id, 0)),
                )
            )

        total = len(items)
        paged_items = items[offset : offset + limit]
        return FeedHealthListResponse(
            items=paged_items,
            total=total,
            limit=limit,
            offset=offset,
            summary=summary,
            last_updated_at=now,
        )

    async def _summary(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        now: datetime,
    ) -> FeedHealthSummaryOut:
        feeds_result = await session.execute(select(Feed).where(Feed.owner_id == user_id))
        feeds = feeds_result.scalars().all()
        total_feed_count = len(feeds)
        active_feed_count = sum(1 for feed in feeds if not feed.is_archived and feed.is_active)
        paused_feed_count = sum(1 for feed in feeds if not feed.is_archived and not feed.is_active)
        archived_feed_count = sum(1 for feed in feeds if feed.is_archived)
        stale_feed_count = sum(1 for feed in feeds if _feed_staleness(feed, now)[0])
        error_feed_count = sum(1 for feed in feeds if _has_error(feed))
        return FeedHealthSummaryOut(
            total_feed_count=total_feed_count,
            active_feed_count=active_feed_count,
            paused_feed_count=paused_feed_count,
            archived_feed_count=archived_feed_count,
            stale_feed_count=stale_feed_count,
            error_feed_count=error_feed_count,
        )

    async def _articles_last_7d(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        feed_ids: list[UUID],
        now: datetime,
    ) -> dict[UUID, int]:
        if not feed_ids:
            return {}
        threshold = now - timedelta(days=7)
        rows = await session.execute(
            select(
                Article.feed_id,
                func.count(Article.id).label("article_count"),
            )
            .join(Feed, Feed.id == Article.feed_id)
            .where(
                Feed.owner_id == user_id,
                Article.feed_id.in_(feed_ids),
                func.coalesce(Article.published_at, Article.created_at) >= threshold,
            )
            .group_by(Article.feed_id)
        )
        return {feed_id: int(article_count or 0) for feed_id, article_count in rows.all() if feed_id is not None}

    async def _unread_counts(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        feed_ids: list[UUID],
    ) -> dict[UUID, int]:
        if not feed_ids:
            return {}
        unread_expr = and_(
            func.coalesce(ArticleState.is_read, False).is_(False),
            func.coalesce(ArticleState.is_archived, False).is_(False),
        )
        rows = await session.execute(
            select(
                Article.feed_id,
                func.sum(case((unread_expr, 1), else_=0)).label("unread_count"),
            )
            .select_from(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .outerjoin(
                ArticleState,
                and_(ArticleState.article_id == Article.id, ArticleState.user_id == str(user_id)),
            )
            .where(
                Feed.owner_id == user_id,
                Article.feed_id.in_(feed_ids),
            )
            .group_by(Article.feed_id)
        )
        return {feed_id: int(unread_count or 0) for feed_id, unread_count in rows.all() if feed_id is not None}


feed_health_service = FeedHealthService()
