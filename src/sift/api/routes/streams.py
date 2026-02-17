from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.core.runtime import get_plugin_manager
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import (
    KeywordStreamCreate,
    KeywordStreamOut,
    KeywordStreamUpdate,
    StreamArticleOut,
    StreamBackfillResultOut,
    StreamClassifierRunOut,
)
from sift.services.stream_service import StreamConflictError, StreamNotFoundError, StreamValidationError, stream_service

router = APIRouter()


@router.get("", response_model=list[KeywordStreamOut])
async def list_streams(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[KeywordStreamOut]:
    streams = await stream_service.list_streams(session=session, user_id=current_user.id)
    return [stream_service.to_out(stream) for stream in streams]


@router.post("", response_model=KeywordStreamOut, status_code=status.HTTP_201_CREATED)
async def create_stream(
    payload: KeywordStreamCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> KeywordStreamOut:
    try:
        stream = await stream_service.create_stream(session=session, user_id=current_user.id, payload=payload)
    except StreamConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except StreamValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return stream_service.to_out(stream)


@router.patch("/{stream_id}", response_model=KeywordStreamOut)
async def update_stream(
    stream_id: UUID,
    payload: KeywordStreamUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> KeywordStreamOut:
    try:
        stream = await stream_service.update_stream(
            session=session,
            user_id=current_user.id,
            stream_id=stream_id,
            payload=payload,
        )
    except StreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StreamConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except StreamValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return stream_service.to_out(stream)


@router.delete("/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_stream(
    stream_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await stream_service.delete_stream(session=session, user_id=current_user.id, stream_id=stream_id)
    except StreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{stream_id}/articles", response_model=list[StreamArticleOut])
async def list_stream_articles(
    stream_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[StreamArticleOut]:
    try:
        return await stream_service.list_stream_articles(
            session=session,
            user_id=current_user.id,
            stream_id=stream_id,
            limit=limit,
        )
    except StreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/{stream_id}/classifier-runs", response_model=list[StreamClassifierRunOut])
async def list_stream_classifier_runs(
    stream_id: UUID,
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[StreamClassifierRunOut]:
    try:
        return await stream_service.list_stream_classifier_runs(
            session=session,
            user_id=current_user.id,
            stream_id=stream_id,
            limit=limit,
        )
    except StreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{stream_id}/backfill", response_model=StreamBackfillResultOut)
async def run_stream_backfill(
    stream_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> StreamBackfillResultOut:
    try:
        return await stream_service.run_stream_backfill(
            session=session,
            user_id=current_user.id,
            stream_id=stream_id,
            plugin_manager=get_plugin_manager(),
        )
    except StreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except StreamValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
