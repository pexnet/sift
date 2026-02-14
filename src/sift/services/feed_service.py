from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Feed
from sift.domain.schemas import FeedCreate


class FeedService:
    async def list_feeds(self, session: AsyncSession, user_id: UUID) -> Sequence[Feed]:
        query = select(Feed).where(Feed.owner_id == user_id).order_by(Feed.created_at.desc())
        result = await session.execute(query)
        return result.scalars().all()

    async def get_feed(self, session: AsyncSession, feed_id: UUID, user_id: UUID) -> Feed | None:
        query = select(Feed).where(Feed.id == feed_id, Feed.owner_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_feed(self, session: AsyncSession, data: FeedCreate, user_id: UUID) -> Feed:
        feed = Feed(
            owner_id=user_id,
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
            .where(Feed.is_active.is_(True), Feed.owner_id.is_not(None))
            .order_by(Feed.updated_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return result.scalars().all()


feed_service = FeedService()


class FeedAlreadyExistsError(Exception):
    pass

