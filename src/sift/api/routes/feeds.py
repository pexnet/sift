from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.core.runtime import get_plugin_manager
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import (
    FeedCreate,
    FeedFolderAssignmentUpdate,
    FeedHealthListResponse,
    FeedIngestResult,
    FeedLifecycleResultOut,
    FeedLifecycleUpdate,
    FeedOut,
    FeedSettingsUpdate,
)
from sift.services.feed_health_service import feed_health_service
from sift.services.feed_service import (
    FeedAlreadyExistsError,
    FeedFolderNotFoundError,
    FeedLifecycleError,
    FeedValidationError,
    feed_service,
)
from sift.services.ingestion_service import FeedNotFoundError, ingestion_service

router = APIRouter()


@router.get("", response_model=list[FeedOut])
async def list_feeds(
    include_archived: bool = Query(default=False),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[FeedOut]:
    feeds = await feed_service.list_feeds(
        session=session,
        user_id=current_user.id,
        include_archived=include_archived,
    )
    return [FeedOut.model_validate(feed) for feed in feeds]


@router.get("/health", response_model=FeedHealthListResponse)
async def list_feed_health(
    lifecycle: Literal["all", "active", "paused", "archived"] = Query(default="all"),
    q: str | None = Query(default=None),
    stale_only: bool = Query(default=False),
    error_only: bool = Query(default=False),
    all: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedHealthListResponse:
    return await feed_health_service.list_feed_health(
        session=session,
        user_id=current_user.id,
        lifecycle=lifecycle,
        q=q,
        stale_only=stale_only,
        error_only=error_only,
        include_all=all,
        limit=limit,
        offset=offset,
    )


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
    except FeedFolderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
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
        return await ingestion_service.ingest_feed(
            session=session, feed_id=feed.id, plugin_manager=get_plugin_manager()
        )
    except FeedNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{feed_id}/folder", response_model=FeedOut)
async def assign_feed_folder(
    feed_id: UUID,
    payload: FeedFolderAssignmentUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedOut:
    feed = await feed_service.get_feed(session=session, feed_id=feed_id, user_id=current_user.id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Feed {feed_id} not found")

    try:
        updated = await feed_service.assign_folder(
            session=session,
            feed=feed,
            user_id=current_user.id,
            folder_id=payload.folder_id,
        )
    except FeedFolderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FeedOut.model_validate(updated)


@router.patch("/{feed_id}/settings", response_model=FeedOut)
async def update_feed_settings(
    feed_id: UUID,
    payload: FeedSettingsUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedOut:
    feed = await feed_service.get_feed(session=session, feed_id=feed_id, user_id=current_user.id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Feed {feed_id} not found")
    try:
        updated = await feed_service.update_feed_settings(session=session, feed=feed, payload=payload)
    except FeedValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FeedOut.model_validate(updated)


@router.patch("/{feed_id}/lifecycle", response_model=FeedLifecycleResultOut)
async def update_feed_lifecycle(
    feed_id: UUID,
    payload: FeedLifecycleUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedLifecycleResultOut:
    feed = await feed_service.get_feed(session=session, feed_id=feed_id, user_id=current_user.id)
    if feed is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Feed {feed_id} not found")

    try:
        updated_feed, marked_read_count = await feed_service.transition_lifecycle(
            session=session,
            feed=feed,
            user_id=current_user.id,
            payload=payload,
        )
    except FeedLifecycleError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return FeedLifecycleResultOut(feed=FeedOut.model_validate(updated_feed), marked_read_count=marked_read_count)
