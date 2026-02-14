from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.session import get_db_session
from sift.domain.schemas import FeedCreate, FeedOut
from sift.services.feed_service import feed_service

router = APIRouter()


@router.get("", response_model=list[FeedOut])
async def list_feeds(session: AsyncSession = Depends(get_db_session)) -> list[FeedOut]:
    feeds = await feed_service.list_feeds(session)
    return [FeedOut.model_validate(feed) for feed in feeds]


@router.post("", response_model=FeedOut, status_code=status.HTTP_201_CREATED)
async def create_feed(payload: FeedCreate, session: AsyncSession = Depends(get_db_session)) -> FeedOut:
    feed = await feed_service.create_feed(session, payload)
    return FeedOut.model_validate(feed)

