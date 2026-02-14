from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.core.runtime import get_plugin_manager
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import FeedCreate, FeedIngestResult, FeedOut
from sift.services.feed_service import FeedAlreadyExistsError, feed_service
from sift.services.ingestion_service import FeedNotFoundError, ingestion_service

router = APIRouter()


@router.get("", response_model=list[FeedOut])
async def list_feeds(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[FeedOut]:
    feeds = await feed_service.list_feeds(session=session, user_id=current_user.id)
    return [FeedOut.model_validate(feed) for feed in feeds]


@router.post("", response_model=FeedOut, status_code=status.HTTP_201_CREATED)
async def create_feed(
    payload: FeedCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedOut:
    try:
        feed = await feed_service.create_feed(session=session, data=payload, user_id=current_user.id)
    except FeedAlreadyExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FeedOut.model_validate(feed)


@router.post("/{feed_id}/ingest", response_model=FeedIngestResult, status_code=status.HTTP_202_ACCEPTED)
async def ingest_feed(
    feed_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedIngestResult:
    feed = await feed_service.get_feed(session=session, feed_id=feed_id, user_id=current_user.id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Feed {feed_id} not found")

    try:
        return await ingestion_service.ingest_feed(session=session, feed_id=feed.id, plugin_manager=get_plugin_manager())
    except FeedNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

