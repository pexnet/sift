from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Feed
from sift.domain.schemas import FeedCreate


class FeedService:
    async def list_feeds(self, session: AsyncSession) -> Sequence[Feed]:
        query = select(Feed).order_by(Feed.created_at.desc())
        result = await session.execute(query)
        return result.scalars().all()

    async def create_feed(self, session: AsyncSession, data: FeedCreate) -> Feed:
        feed = Feed(title=data.title.strip(), url=str(data.url), site_url=str(data.site_url) if data.site_url else None)
        session.add(feed)
        await session.commit()
        await session.refresh(feed)
        return feed


feed_service = FeedService()

