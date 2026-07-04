from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import (
    DashboardCardAvailabilityOut,
    DashboardFeedHealthCardOut,
    DashboardMonitoringSignalsOut,
    DashboardPrioritizedQueueOut,
    DashboardPriorityProfileOut,
    DashboardPriorityProfileUpdate,
    DashboardSavedFollowupOut,
    DashboardSummaryOut,
)
from sift.services.dashboard_service import DashboardValidationError, dashboard_service

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryOut)
async def get_dashboard_summary(current_user: User = Depends(get_current_user)) -> DashboardSummaryOut:
    del current_user

    cards = [
        DashboardCardAvailabilityOut(
            id="prioritized_queue",
            title="Prioritized queue",
            status="ready",
        ),
        DashboardCardAvailabilityOut(
            id="feed_health",
            title="Feed ops health",
            status="ready",
        ),
        DashboardCardAvailabilityOut(
            id="saved_followup",
            title="Saved follow-up",
            status="ready",
        ),
        DashboardCardAvailabilityOut(
            id="monitoring_signals",
            title="Monitoring signal",
            status="ready",
        ),
        DashboardCardAvailabilityOut(
            id="trends",
            title="Trends",
            status="unavailable",
            reason="Trends detection pipeline is not implemented yet.",
            dependency_spec="docs/specs/trends-detection-dashboard-v1.md",
        ),
        DashboardCardAvailabilityOut(
            id="discovery_candidates",
            title="Discovery candidates",
            status="degraded",
            reason="Discovery workflow is implemented; dashboard data card endpoint pending.",
            dependency_spec="docs/specs/done/feed-recommendations-v1.md",
        ),
    ]
    return DashboardSummaryOut(cards=cards, last_updated_at=datetime.now(UTC))


@router.get("/prioritization-profile", response_model=DashboardPriorityProfileOut)
async def get_prioritization_profile(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DashboardPriorityProfileOut:
    return await dashboard_service.get_prioritization_profile(session=session, user_id=current_user.id)


@router.patch("/prioritization-profile", response_model=DashboardPriorityProfileOut)
async def update_prioritization_profile(
    payload: DashboardPriorityProfileUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DashboardPriorityProfileOut:
    try:
        return await dashboard_service.update_prioritization_profile(
            session=session,
            user_id=current_user.id,
            payload=payload,
        )
    except DashboardValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/cards/prioritized-queue", response_model=DashboardPrioritizedQueueOut)
async def get_prioritized_queue(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=10, ge=1, le=50),
) -> DashboardPrioritizedQueueOut:
    return await dashboard_service.get_prioritized_queue(session=session, user_id=current_user.id, limit=limit)


@router.get("/cards/feed-health", response_model=DashboardFeedHealthCardOut)
async def get_feed_health_card(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DashboardFeedHealthCardOut:
    return await dashboard_service.get_feed_health_card(session=session, user_id=current_user.id)


@router.get("/cards/saved-followup", response_model=DashboardSavedFollowupOut)
async def get_saved_followup_card(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=5, ge=1, le=25),
) -> DashboardSavedFollowupOut:
    return await dashboard_service.get_saved_followup_card(session=session, user_id=current_user.id, limit=limit)


@router.get("/cards/monitoring-signals", response_model=DashboardMonitoringSignalsOut)
async def get_monitoring_signals_card(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
    window_hours: int = Query(default=24, ge=1, le=168),
) -> DashboardMonitoringSignalsOut:
    return await dashboard_service.get_monitoring_signals_card(
        session=session,
        user_id=current_user.id,
        window_hours=window_hours,
    )
