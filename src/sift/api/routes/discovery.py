from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import (
    DiscoveryStreamCreate,
    DiscoveryStreamGenerateOut,
    DiscoveryStreamGenerateRequestIn,
    DiscoveryStreamOut,
    DiscoveryStreamUpdate,
    SearchFeedCandidateOut,
    SearchWarningOut,
)
from sift.services.discovery_service import (
    DiscoveryGenerationUnavailableError,
    DiscoveryStreamConflictError,
    DiscoveryStreamNotFoundError,
    DiscoveryStreamValidationError,
    discovery_service,
)

router = APIRouter()


@router.get("/streams", response_model=list[DiscoveryStreamOut])
async def list_discovery_streams(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[DiscoveryStreamOut]:
    streams = await discovery_service.list_streams(session=session, user_id=current_user.id)
    return [discovery_service.to_out(stream) for stream in streams]


@router.post("/streams", response_model=DiscoveryStreamOut, status_code=status.HTTP_201_CREATED)
async def create_discovery_stream(
    payload: DiscoveryStreamCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryStreamOut:
    try:
        stream = await discovery_service.create_stream(session=session, user_id=current_user.id, payload=payload)
    except DiscoveryStreamConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DiscoveryStreamValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return discovery_service.to_out(stream)


@router.patch("/streams/{stream_id}", response_model=DiscoveryStreamOut)
async def update_discovery_stream(
    stream_id: UUID,
    payload: DiscoveryStreamUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryStreamOut:
    try:
        stream = await discovery_service.update_stream(
            session=session,
            user_id=current_user.id,
            stream_id=stream_id,
            payload=payload,
        )
    except DiscoveryStreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DiscoveryStreamConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DiscoveryStreamValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return discovery_service.to_out(stream)


@router.delete("/streams/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_discovery_stream(
    stream_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await discovery_service.delete_stream(session=session, user_id=current_user.id, stream_id=stream_id)
    except DiscoveryStreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/streams/{stream_id}/generate", response_model=DiscoveryStreamGenerateOut)
async def generate_discovery_stream_candidates(
    stream_id: UUID,
    payload: DiscoveryStreamGenerateRequestIn = Body(default_factory=DiscoveryStreamGenerateRequestIn),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DiscoveryStreamGenerateOut:
    try:
        result = await discovery_service.generate_for_stream(
            session=session,
            user_id=current_user.id,
            stream_id=stream_id,
            max_results_per_query=payload.max_results_per_query,
            max_candidates=payload.max_candidates,
        )
    except DiscoveryStreamNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DiscoveryStreamValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DiscoveryGenerationUnavailableError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return DiscoveryStreamGenerateOut(
        stream_id=result.stream_id,
        provider_chain=result.provider_chain,
        query_variants=result.query_variants,
        attempted_queries=len(result.query_variants),
        candidate_count=len(result.candidates),
        candidates=[
            SearchFeedCandidateOut(
                title=item.title,
                url=item.url,
                site_url=item.site_url,
                description=item.description,
                provider=item.provider,
            )
            for item in result.candidates
        ],
        warnings=result.warnings,
        warning_details=[
            SearchWarningOut(code=detail.code, provider=detail.provider, message=detail.message)
            for detail in result.warning_details
        ],
    )
