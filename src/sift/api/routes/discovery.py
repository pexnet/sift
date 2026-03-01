from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
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
    FeedRecommendationDecisionIn,
    FeedRecommendationListOut,
    FeedRecommendationOut,
    FeedRecommendationSummaryOut,
    SearchFeedCandidateOut,
    SearchWarningOut,
)
from sift.services.discovery_service import (
    DiscoveryGenerationUnavailableError,
    DiscoveryRecommendationNotFoundError,
    DiscoveryRecommendationValidationError,
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
        persisted_count=result.persisted_count,
        pending_count=result.pending_count,
        resolved_existing_count=result.resolved_existing_count,
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


@router.get("/recommendations", response_model=FeedRecommendationListOut)
async def list_feed_recommendations(
    status_filter: Literal["pending", "accepted", "denied", "resolved_existing"] | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedRecommendationListOut:
    recommendations, total, sources_by_recommendation = await discovery_service.list_recommendations(
        session=session,
        user_id=current_user.id,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )
    return FeedRecommendationListOut(
        items=[
            discovery_service.recommendation_to_out(
                recommendation,
                sources=sources_by_recommendation.get(recommendation.id, []),
            )
            for recommendation in recommendations
        ],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/recommendations/summary", response_model=FeedRecommendationSummaryOut)
async def recommendation_summary(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedRecommendationSummaryOut:
    summary = await discovery_service.recommendation_summary(session=session, user_id=current_user.id)
    return FeedRecommendationSummaryOut(**summary)


@router.patch("/recommendations/{recommendation_id}", response_model=FeedRecommendationOut)
async def decide_recommendation(
    recommendation_id: UUID,
    payload: FeedRecommendationDecisionIn,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedRecommendationOut:
    try:
        recommendation = await discovery_service.decide_recommendation(
            session=session,
            user_id=current_user.id,
            recommendation_id=recommendation_id,
            decision=payload.decision,
        )
    except DiscoveryRecommendationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DiscoveryRecommendationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sources_by_recommendation = await discovery_service.load_sources_by_recommendation(
        session=session,
        recommendation_ids=[recommendation.id],
    )
    return discovery_service.recommendation_to_out(
        recommendation,
        sources=sources_by_recommendation.get(recommendation.id, []),
    )


@router.post("/recommendations/{recommendation_id}/reset", response_model=FeedRecommendationOut)
async def reset_recommendation(
    recommendation_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedRecommendationOut:
    try:
        recommendation = await discovery_service.reset_recommendation(
            session=session,
            user_id=current_user.id,
            recommendation_id=recommendation_id,
        )
    except DiscoveryRecommendationNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DiscoveryRecommendationValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    sources_by_recommendation = await discovery_service.load_sources_by_recommendation(
        session=session,
        recommendation_ids=[recommendation.id],
    )
    return discovery_service.recommendation_to_out(
        recommendation,
        sources=sources_by_recommendation.get(recommendation.id, []),
    )
