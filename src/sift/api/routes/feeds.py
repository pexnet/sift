from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.core.runtime import get_plugin_manager
from sift.db.session import get_db_session
from sift.domain.schemas import FeedCreate, FeedIngestResult, FeedOut
from sift.services.feed_service import feed_service
from sift.services.ingestion_service import FeedNotFoundError, ingestion_service

router = APIRouter()


@router.get("", response_model=list[FeedOut])
async def list_feeds(session: AsyncSession = Depends(get_db_session)) -> list[FeedOut]:
    feeds = await feed_service.list_feeds(session)
    return [FeedOut.model_validate(feed) for feed in feeds]


@router.post("", response_model=FeedOut, status_code=status.HTTP_201_CREATED)
async def create_feed(payload: FeedCreate, session: AsyncSession = Depends(get_db_session)) -> FeedOut:
    feed = await feed_service.create_feed(session, payload)
    return FeedOut.model_validate(feed)


@router.post("/{feed_id}/ingest", response_model=FeedIngestResult, status_code=status.HTTP_202_ACCEPTED)
async def ingest_feed(feed_id: UUID, session: AsyncSession = Depends(get_db_session)) -> FeedIngestResult:
    try:
        return await ingestion_service.ingest_feed(session, feed_id=feed_id, plugin_manager=get_plugin_manager())
    except FeedNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

