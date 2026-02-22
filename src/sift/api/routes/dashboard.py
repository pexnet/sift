from datetime import UTC, datetime

from fastapi import APIRouter, Depends

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.domain.schemas import DashboardCardAvailabilityOut, DashboardSummaryOut

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryOut)
async def get_dashboard_summary(current_user: User = Depends(get_current_user)) -> DashboardSummaryOut:
    del current_user

    cards = [
        DashboardCardAvailabilityOut(
            id="prioritized_queue",
            title="Prioritized queue",
            status="unavailable",
            reason="Stream ranking controls are not implemented yet.",
            dependency_spec="docs/specs/stream-ranking-prioritization-controls-v1.md",
        ),
        DashboardCardAvailabilityOut(
            id="feed_health",
            title="Feed ops health",
            status="unavailable",
            reason="Dashboard feed-health panel endpoint is not implemented yet.",
            dependency_spec="docs/specs/feed-health-ops-panel-v1.md",
        ),
        DashboardCardAvailabilityOut(
            id="saved_followup",
            title="Saved follow-up",
            status="ready",
        ),
        DashboardCardAvailabilityOut(
            id="monitoring_signals",
            title="Monitoring signal",
            status="unavailable",
            reason="Monitoring signal scoring pipeline is not implemented yet.",
            dependency_spec="docs/specs/monitoring-signal-scoring-v1.md",
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
            status="unavailable",
            reason="Discover feeds workflow is not implemented yet.",
            dependency_spec="docs/specs/feed-recommendations-v1.md",
        ),
    ]
    return DashboardSummaryOut(cards=cards, last_updated_at=datetime.now(UTC))
