# Dashboard Command Center Full Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Build the complete Sift dashboard command center: real backend card endpoints, prioritization controls, feed-health summary, saved follow-up, monitoring signals, discovery candidates, trends, frontend card UI, refresh behavior, tests, and docs.

**Architecture:** Add a dashboard service layer under `src/sift/services/` that computes each card from existing Sift domain tables and services. Keep `/api/v1/dashboard/summary` as the lightweight availability/metadata endpoint and add dedicated `/api/v1/dashboard/cards/*` endpoints for card data. The frontend should keep the existing `/app/dashboard` workspace shell, replace placeholder cards with real card components, and fetch each card independently with manual refresh plus light summary polling.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, Alembic, Pydantic, pytest; React, TypeScript, MUI, TanStack Query, Zod, Vitest.

**Decisions captured:**
- Dashboard scope: implement all planned v1 dashboard card surfaces from `docs/specs/dashboard-command-center-v1.md` — prioritized queue, feed health, saved follow-up, high-value monitoring, trends, discovery candidates.
- Layout: responsive dashboard grid with priority/signal cards first, feed-health/saved/discovery/trends after *(judgement; based on command-center triage intent in `docs/specs/dashboard-command-center-v1.md:45-59`)*.
- Card fetching: independent card endpoints and queries, not one huge payload *(judgement; aligns with manual per-card refresh in `docs/specs/dashboard-command-center-v1.md:90-96`)*.
- Trends implementation: implement deterministic local trend snapshots using term/keyphrase scoring; no external NLP service and no temporary dashboard-only hack *(judgement; follows `docs/specs/trends-detection-dashboard-v1.md:20-24` and `:53-66`)*.
- Discovery candidates: combine implemented feed recommendation summary with monitoring-first article candidates *(judgement; follows `docs/specs/dashboard-command-center-v1.md:57-59` and `docs/specs/monitoring-signal-scoring-v1.md:54-73`)*.
- Prioritization controls: implement user profile API and defaults before the prioritized queue card, using explicit heuristic math *(judgement; follows `docs/specs/stream-ranking-prioritization-controls-v1.md:57-82`)*.

**Assumptions:**
- `/api/v1/dashboard/summary` exists but is availability-only and stale for discovery candidates (`src/sift/api/routes/dashboard.py:12-58`).
- Dashboard frontend shell already exists at `frontend/src/features/dashboard/components/DashboardHost.tsx:147-184`; it renders ready cards from a registry and unavailable cards from summary metadata.
- `/app/dashboard` already preserves workspace chrome (`frontend/src/features/workspace/routes/WorkspacePage.tsx:418-423`) and the rail action navigates to `/app/dashboard` (`WorkspacePage.tsx:370-374`).
- Dashboard card availability schemas are currently minimal (`src/sift/domain/schemas.py:585-595`), so card-specific response models need to be added.
- Feed-health list/summary service already computes user-scoped feed counts, stale counts, and error counts (`src/sift/services/feed_health_service.py:52-161`); the dashboard card can reuse/extract this logic.
- Article listing already supports unread/saved state and exposes stream match evidence (`src/sift/services/article_service.py:146-260`). Dashboard services can query directly rather than forcing card use through the reader API.
- Discovery recommendation summary already exists (`src/sift/services/discovery_service.py:753-772`).
- Existing models provide feed/article/state/stream/recommendation data (`src/sift/db/models.py:30-101`, `:188-309`), but prioritization profile and trends snapshot/topic tables do not exist yet.
- Backend canonical gates require running Docker app container; current plan mode did not start containers because the Docker stack was not already running.

**Baseline:**

| Gate | Command | Result |
| --- | --- | --- |
| Backend containers running | `docker compose -f .devcontainer/docker-compose.yml ps --services --filter status=running` | PASS command, no services running |
| Backend ruff/mypy/pytest | canonical Docker commands from `sift-project` skill | NOT RUN — plan mode, stack down, do not start containers |
| Frontend typecheck | `cd frontend && npx tsc --noEmit` | PASS |
| Frontend lint | `cd frontend && npx eslint .` | PASS |
| Dashboard/workspace tests | `cd frontend && npx vitest run src/features/dashboard/components/DashboardHost.test.tsx src/features/workspace/routes/WorkspacePage.test.tsx` | PASS — 8 tests |
| Frontend build | `cd frontend && npm run build` | PASS, existing >500k chunk warning |

---

## Current Dashboard State Summary

Implemented:
- Backend route: `GET /api/v1/dashboard/summary`.
- Frontend route: `/app/dashboard`.
- Frontend shell: `DashboardHost` grid with availability fallback and one placeholder `saved_followup` card registration.
- Tests: `tests/test_dashboard_api.py`, `DashboardHost.test.tsx`, workspace route dashboard test.

Stale or incomplete:
- `discovery_candidates` card in `src/sift/api/routes/dashboard.py:50-56` says discovery is not implemented and points at `docs/specs/feed-recommendations-v1.md`, but discovery is implemented and archived under `docs/specs/done/feed-recommendations-v1.md`.
- No card data endpoints exist yet.
- No prioritization profile table/API exists yet.
- No dashboard card frontend API/hooks/components exist yet beyond summary/host.
- No trend snapshot/topic tables or trend computation service exist yet.

---

## Files likely to change

Backend:
- `src/sift/db/models.py`
- `src/sift/domain/schemas.py`
- `src/sift/api/routes/dashboard.py`
- `src/sift/api/router.py` if new router split is chosen, otherwise unchanged
- `src/sift/services/dashboard_service.py` (new)
- `src/sift/services/dashboard_scoring.py` (new, optional helper)
- `src/sift/services/trends_service.py` (new)
- `src/sift/services/feed_health_service.py` (small extraction if needed)
- `alembic/versions/<revision>_dashboard_prioritization_and_trends.py` (new)
- `tests/test_dashboard_api.py`
- `tests/test_dashboard_service.py` (new)
- `tests/test_trends_service.py` (new)

Frontend:
- `frontend/src/shared/types/contracts.ts`
- `frontend/src/shared/types/generated.ts` (manual update or regenerate OpenAPI)
- `frontend/src/entities/navigation/dashboard.ts`
- `frontend/src/shared/api/queryKeys.ts`
- `frontend/src/shared/api/workspaceApi.ts` or new `frontend/src/shared/api/dashboardApi.ts`
- `frontend/src/features/workspace/api/workspaceHooks.ts`
- `frontend/src/features/dashboard/api/dashboardHooks.ts` (new)
- `frontend/src/features/dashboard/components/DashboardHost.tsx`
- new card components under `frontend/src/features/dashboard/components/`
- `frontend/src/features/dashboard/components/DashboardHost.test.tsx`
- new card tests under `frontend/src/features/dashboard/components/*.test.tsx`
- `frontend/src/app/styles.css`

Docs:
- `docs/current-state.md`
- `docs/backlog.md`
- `docs/backlog-history.md`
- `docs/specs/dashboard-command-center-v1.md`
- related dashboard specs under `docs/specs/`
- `docs/session-notes.md`

---

## Backend Response Model Sketch

Add these Pydantic models to `src/sift/domain/schemas.py` near `DashboardCardAvailabilityOut`:

```python
class DashboardCardBaseOut(BaseModel):
    status: Literal["ready", "unavailable", "degraded"] = "ready"
    reason: str | None = None
    dependency_spec: str | None = None
    last_updated_at: datetime


class DashboardPriorityProfileOut(BaseModel):
    source_weights: dict[str, int]
    recency_horizon_hours: int


class DashboardPriorityProfileUpdate(BaseModel):
    source_weights: dict[str, int] | None = None
    recency_horizon_hours: int | None = Field(default=None, ge=1, le=720)


class DashboardPrioritizedArticleOut(BaseModel):
    article_id: UUID
    title: str
    feed_title: str
    canonical_url: str | None
    published_at: datetime | None
    created_at: datetime
    is_read: bool
    is_starred: bool
    priority_score: float
    score_breakdown: dict[str, float]
    why_prioritized: list[str]


class DashboardPrioritizedQueueOut(DashboardCardBaseOut):
    profile: DashboardPriorityProfileOut
    items: list[DashboardPrioritizedArticleOut]


class DashboardFeedHealthQueueLagOut(BaseModel):
    queue_length: int | None = None
    oldest_job_age_seconds: float | None = None
    failed_jobs_24h: int | None = None
    unavailable_reason: str | None = None


class DashboardFeedHealthCardOut(DashboardCardBaseOut):
    stale_feed_count: int
    error_feed_count: int
    oldest_success_age_hours: float | None
    queue_lag: DashboardFeedHealthQueueLagOut


class DashboardSavedFollowupItemOut(BaseModel):
    article_id: UUID
    title: str
    feed_title: str
    canonical_url: str | None
    published_at: datetime | None
    saved_at: datetime | None


class DashboardSavedFollowupOut(DashboardCardBaseOut):
    saved_count: int
    latest_items: list[DashboardSavedFollowupItemOut]


class DashboardMonitoringSignalStreamOut(BaseModel):
    stream_id: UUID
    stream_name: str
    signal_score: float
    matched_count_window: int
    unread_count_window: int
    confidence_summary: dict[str, float | int | None]
    latest_match_at: datetime | None
    score_breakdown: dict[str, float]


class DashboardMonitoringSignalsOut(DashboardCardBaseOut):
    window_hours: int
    streams: list[DashboardMonitoringSignalStreamOut]


class DashboardDiscoveryCandidateOut(BaseModel):
    article_id: UUID | None = None
    recommendation_id: UUID | None = None
    title: str
    canonical_url: str | None
    source_kind: Literal["feed_recommendation", "monitoring_article"]
    candidate_score: float
    why_candidate: list[str]


class DashboardDiscoveryCandidatesOut(DashboardCardBaseOut):
    pending_recommendation_count: int
    monitoring_candidate_count: int
    candidates: list[DashboardDiscoveryCandidateOut]


class DashboardTrendTopicOut(BaseModel):
    topic: str
    momentum_score: float
    short_window_count: int
    baseline_count: int
    source_diversity_count: int
    representative_article_ids: list[UUID]


class DashboardTrendsOut(DashboardCardBaseOut):
    window_hours: int
    baseline_days: int
    topics: list[DashboardTrendTopicOut]
```

Use these names unless implementation finds a strong existing naming convention conflict.

---

## Task 1: Fix stale dashboard summary contract for discovery candidates

**Objective:** Make the existing summary accurately reflect implemented discovery feeds before adding new card endpoints.

**Files:**
- Modify: `src/sift/api/routes/dashboard.py:50-56`
- Test: `tests/test_dashboard_api.py`

**Step 1: Write/adjust failing test**

In `tests/test_dashboard_api.py`, extend `test_dashboard_summary_returns_card_availability_for_authenticated_user`:

```python
assert by_id["discovery_candidates"]["status"] in {"ready", "degraded"}
assert by_id["discovery_candidates"].get("dependency_spec") != "docs/specs/feed-recommendations-v1.md"
```

**Step 2: Run test to verify failure**

Run:

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_api.py -q
```

Expected: FAIL because the card is currently `unavailable` and points to the stale active spec path.

**Step 3: Implement minimal fix**

Update `discovery_candidates` in `src/sift/api/routes/dashboard.py` to either:

```python
DashboardCardAvailabilityOut(
    id="discovery_candidates",
    title="Discovery candidates",
    status="ready",
)
```

or `degraded` if the data card endpoint is not yet available in that task. Prefer `ready` once Task 12 exists; for this initial consistency task use `degraded` with reason `Discovery workflow is implemented; dashboard data card endpoint pending.` if implemented before Task 12.

**Step 4: Run test to verify pass**

Run:

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_api.py -q
```

Expected: PASS in isolation. If `event loop closed` appears, rerun once and compare with known pre-existing flakiness in `sift-project` skill.

**Step 5: Commit**

Only commit if the user explicitly authorizes commits:

```bash
git add src/sift/api/routes/dashboard.py tests/test_dashboard_api.py
git commit -m "fix: align dashboard discovery availability"
```

---

## Task 2: Add dashboard prioritization and trends tables

**Objective:** Add durable storage for user prioritization profiles and trend snapshots/topics.

**Files:**
- Modify: `src/sift/db/models.py`
- Create: `alembic/versions/<revision>_dashboard_prioritization_and_trends.py`
- Test: migration smoke via Alembic in container

**Step 1: Add SQLAlchemy models**

Add near other user-scoped models in `src/sift/db/models.py`:

```python
class UserPrioritizationProfile(TimestampMixin, Base):
    __tablename__ = "user_prioritization_profiles"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    source_weights_json: Mapped[str] = mapped_column(Text, default='{"feed": 40, "monitoring_stream": 60}')
    recency_horizon_hours: Mapped[int] = mapped_column(Integer, default=24)


class TrendSnapshot(TimestampMixin, Base):
    __tablename__ = "trend_snapshots"
    __table_args__ = (Index("ix_trend_snapshots_user_scope_created", "user_id", "scope_type", "created_at"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    scope_type: Mapped[str] = mapped_column(String(32), default="system", index=True)
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), index=True)
    short_window_hours: Mapped[int] = mapped_column(Integer, default=24)
    baseline_days: Mapped[int] = mapped_column(Integer, default=14)
    status: Mapped[str] = mapped_column(String(32), default="ready", index=True)


class TrendTopic(TimestampMixin, Base):
    __tablename__ = "trend_topics"
    __table_args__ = (Index("ix_trend_topics_snapshot_score", "snapshot_id", "momentum_score"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    snapshot_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("trend_snapshots.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    momentum_score: Mapped[float] = mapped_column(Float, default=0.0)
    short_window_count: Mapped[int] = mapped_column(Integer, default=0)
    baseline_count: Mapped[int] = mapped_column(Integer, default=0)
    source_diversity_count: Mapped[int] = mapped_column(Integer, default=0)
    representative_article_ids_json: Mapped[str] = mapped_column(Text, default="[]")
```

**Step 2: Create Alembic migration**

Run:

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run alembic revision -m "dashboard prioritization and trends"
```

Then edit the generated migration to create the three tables and indexes exactly matching the model fields.

**Step 3: Verify migration**

Run:

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run alembic upgrade head
```

Expected: migration applies cleanly.

**Step 4: Commit**

Only if authorized:

```bash
git add src/sift/db/models.py alembic/versions/*dashboard_prioritization_and_trends*.py
git commit -m "feat: add dashboard prioritization and trend tables"
```

---

## Task 3: Add dashboard Pydantic contracts

**Objective:** Add response/request schemas for every dashboard endpoint.

**Files:**
- Modify: `src/sift/domain/schemas.py:585-595`
- Test: downstream API tests in later tasks

**Step 1: Add contracts**

Use the model sketch from “Backend Response Model Sketch”. Keep all new classes near `DashboardCardAvailabilityOut`.

**Step 2: Run static checks**

Run:

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run ruff check src/sift/domain/schemas.py
cd /home/pex/code/sift && docker compose exec -T app uv run mypy src/sift/domain/schemas.py
```

Expected: PASS.

**Step 3: Commit**

Only if authorized:

```bash
git add src/sift/domain/schemas.py
git commit -m "feat: add dashboard card schemas"
```

---

## Task 4: Implement prioritization profile service methods

**Objective:** Provide default/create/update behavior for per-user prioritization profiles.

**Files:**
- Create: `src/sift/services/dashboard_service.py`
- Test: `tests/test_dashboard_service.py`

**Step 1: Write failing tests**

Create `tests/test_dashboard_service.py` using the existing in-memory SQLite pattern from `sift-project`.

Test cases:

```python
async def test_get_prioritization_profile_returns_defaults_for_new_user(): ...
async def test_update_prioritization_profile_validates_weight_range(): ...
async def test_update_prioritization_profile_persists_user_scoped_values(): ...
```

Assert defaults:

```python
assert profile.source_weights == {"feed": 40, "monitoring_stream": 60}
assert profile.recency_horizon_hours == 24
```

**Step 2: Run tests to verify failure**

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_service.py -q
```

Expected: FAIL because service does not exist.

**Step 3: Implement service skeleton**

In `src/sift/services/dashboard_service.py`:

```python
DEFAULT_SOURCE_WEIGHTS = {"feed": 40, "monitoring_stream": 60}
DEFAULT_RECENCY_HORIZON_HOURS = 24

class DashboardValidationError(Exception):
    pass

class DashboardService:
    async def get_prioritization_profile(self, *, session: AsyncSession, user_id: UUID) -> DashboardPriorityProfileOut:
        ...

    async def update_prioritization_profile(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        payload: DashboardPriorityProfileUpdate,
    ) -> DashboardPriorityProfileOut:
        ...

dashboard_service = DashboardService()
```

Validation:
- allowed keys: `feed`, `monitoring_stream`
- values: integer `0..100`
- `recency_horizon_hours`: `1..720`

**Step 4: Run tests**

Expected: PASS.

**Step 5: Commit**

Only if authorized:

```bash
git add src/sift/services/dashboard_service.py tests/test_dashboard_service.py
git commit -m "feat: add dashboard prioritization profile service"
```

---

## Task 5: Add prioritization profile API endpoints

**Objective:** Expose profile read/update endpoints.

**Files:**
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_api.py`

**Step 1: Write failing API tests**

Add tests:

```python
def test_dashboard_prioritization_profile_requires_auth(): ...
def test_dashboard_prioritization_profile_returns_defaults_for_user(): ...
def test_dashboard_prioritization_profile_update_persists_values(): ...
def test_dashboard_prioritization_profile_update_rejects_bad_weight(): ...
```

**Step 2: Add routes**

Add to `dashboard.py`:

```python
@router.get("/prioritization-profile", response_model=DashboardPriorityProfileOut)
async def get_prioritization_profile(...): ...

@router.patch("/prioritization-profile", response_model=DashboardPriorityProfileOut)
async def update_prioritization_profile(...): ...
```

Return `400` on `DashboardValidationError`.

**Step 3: Verify**

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_api.py -q
```

Expected: PASS in isolation.

**Step 4: Commit**

Only if authorized:

```bash
git add src/sift/api/routes/dashboard.py tests/test_dashboard_api.py
git commit -m "feat: add dashboard prioritization profile api"
```

---

## Task 6: Implement prioritized queue scoring service

**Objective:** Compute deterministic prioritized unread queue with score breakdown.

**Files:**
- Modify: `src/sift/services/dashboard_service.py`
- Test: `tests/test_dashboard_service.py`

**Step 1: Write failing service tests**

Add tests:

```python
async def test_prioritized_queue_ranks_unread_recent_monitoring_matches_first(): ...
async def test_prioritized_queue_respects_profile_source_weights(): ...
async def test_prioritized_queue_is_user_scoped(): ...
async def test_prioritized_queue_tie_breaks_are_stable(): ...
```

Avoid date fixture drift: create test articles with explicit `datetime.now(UTC) - timedelta(...)` inside each test.

**Step 2: Implement score helper**

Use explicit formula from spec:

```python
def _recency_score(*, published_at: datetime | None, created_at: datetime, now: datetime, horizon_hours: int) -> float:
    timestamp = published_at or created_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    age_hours = max(0.0, (now - timestamp).total_seconds() / 3600)
    return round(max(0.0, 40.0 * (1.0 - min(age_hours, horizon_hours) / horizon_hours)), 2)
```

Score components:
- `source_weight`: profile `feed` default, plus `monitoring_stream` when article has match.
- `recency_score`: `0..40` decay.
- `unread_bonus`: `+20` for unread.
- `saved_bonus`: `+15` for starred.
- `monitoring_signal_bonus`: initial normalized `0..40` from matched stream priority/count; refine after monitoring signal service exists.
- `confidence_bonus`: `0..15` when classifier run confidence exists.

Tie-breaks:
1. score desc
2. publish/create timestamp desc
3. monitoring bonus desc
4. article id asc

**Step 3: Implement method**

```python
async def get_prioritized_queue(
    self,
    *,
    session: AsyncSession,
    user_id: UUID,
    limit: int = 10,
) -> DashboardPrioritizedQueueOut:
    ...
```

Use SQLAlchemy label objects for ordering; do not use `.order_by("d desc")`.

**Step 4: Run tests**

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_service.py -q
```

Expected: PASS.

**Step 5: Commit**

Only if authorized.

---

## Task 7: Add prioritized queue API endpoint

**Objective:** Expose `GET /api/v1/dashboard/cards/prioritized-queue`.

**Files:**
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_api.py`

**Step 1: Write failing API test**

Add:

```python
def test_dashboard_prioritized_queue_requires_auth(): ...
def test_dashboard_prioritized_queue_returns_items_for_authenticated_user(): ...
```

**Step 2: Implement route**

```python
@router.get("/cards/prioritized-queue", response_model=DashboardPrioritizedQueueOut)
async def get_prioritized_queue(
    limit: int = Query(default=10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> DashboardPrioritizedQueueOut:
    return await dashboard_service.get_prioritized_queue(session=session, user_id=current_user.id, limit=limit)
```

**Step 3: Update summary readiness**

Set `prioritized_queue` status to `ready` once endpoint exists.

**Step 4: Verify**

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_api.py tests/test_dashboard_service.py -q
```

Expected: PASS.

---

## Task 8: Implement dashboard feed-health card service

**Objective:** Produce dashboard aggregate feed-health payload using existing feed-health logic.

**Files:**
- Modify: `src/sift/services/dashboard_service.py`
- Optionally modify: `src/sift/services/feed_health_service.py`
- Test: `tests/test_dashboard_service.py`

**Step 1: Write failing tests**

Add:

```python
async def test_feed_health_card_counts_stale_and_error_feeds(): ...
async def test_feed_health_card_oldest_success_age_hours(): ...
async def test_feed_health_card_degrades_queue_lag_when_unavailable(): ...
```

**Step 2: Implement service method**

```python
async def get_feed_health_card(self, *, session: AsyncSession, user_id: UUID) -> DashboardFeedHealthCardOut:
    now = datetime.now(UTC)
    # Reuse FeedHealthService._summary or extract public summary helper.
    # oldest_success_age_hours = max(now - last_fetch_success_at) over active feeds with success.
    # queue_lag unavailable for v1 unless RQ inspection is already safely configured.
```

Set `status="degraded"` if queue lag is unavailable but feed aggregates are ready. Set `queue_lag.unavailable_reason="Queue telemetry is not available in dashboard card yet."`.

**Step 3: Verify tests**

Expected: PASS.

---

## Task 9: Add feed-health card API endpoint

**Objective:** Expose `GET /api/v1/dashboard/cards/feed-health`.

**Files:**
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_api.py`

**Step 1: Write failing API test**

Assert authenticated response contains:

```python
assert payload["stale_feed_count"] == expected
assert "queue_lag" in payload
assert payload["status"] in {"ready", "degraded"}
```

**Step 2: Implement route and update summary**

Add route and change `feed_health` summary status from `unavailable` to `degraded` until queue lag is real, or `ready` if queue lag adapter ships in this task.

**Step 3: Verify**

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_api.py tests/test_dashboard_service.py -q
```

Expected: PASS.

---

## Task 10: Implement saved follow-up card service and endpoint

**Objective:** Replace placeholder saved-followup frontend copy with real saved article counts and latest saved items.

**Files:**
- Modify: `src/sift/services/dashboard_service.py`
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_service.py`, `tests/test_dashboard_api.py`

**Step 1: Write failing service tests**

```python
async def test_saved_followup_counts_starred_unarchived_articles(): ...
async def test_saved_followup_orders_latest_saved_first(): ...
```

Use `ArticleState.updated_at` as `saved_at`; if unavailable, fall back to `Article.created_at`.

**Step 2: Implement service method**

```python
async def get_saved_followup(self, *, session: AsyncSession, user_id: UUID, limit: int = 5) -> DashboardSavedFollowupOut:
    ...
```

Query `ArticleState.is_starred == True` and `is_archived == False`, join `Article` and `Feed`, user-scope through `Feed.owner_id` and `ArticleState.user_id == str(user_id)`.

**Step 3: Add API route**

```python
@router.get("/cards/saved-followup", response_model=DashboardSavedFollowupOut)
async def get_saved_followup(...): ...
```

**Step 4: Verify**

Expected: API/service tests pass.

---

## Task 11: Implement monitoring signal scoring service and endpoint

**Objective:** Rank streams by recent monitoring value with explicit score breakdown.

**Files:**
- Modify: `src/sift/services/dashboard_service.py`
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_service.py`, `tests/test_dashboard_api.py`

**Step 1: Write failing service tests**

```python
async def test_monitoring_signals_rank_by_volume_unread_confidence_and_recency(): ...
async def test_monitoring_signals_handles_rules_only_matches_without_classifier_runs(): ...
async def test_monitoring_signals_are_user_scoped(): ...
```

**Step 2: Implement scoring**

Follow `docs/specs/monitoring-signal-scoring-v1.md:30-52`:

```python
stream_signal_score = volume_component + confidence_component + unread_impact_component + recency_component
```

Normalize:
- `volume_component`: `min(40, matched_count_window * 4)` for initial v1.
- `confidence_component`: average classifier confidence `* 25`, or `0` when absent.
- `unread_impact_component`: `min(25, unread_count_window * 5)`.
- `recency_component`: `0..10` based on latest match age within the window.

**Step 3: Implement service method**

```python
async def get_monitoring_signals(
    self,
    *,
    session: AsyncSession,
    user_id: UUID,
    window_hours: int = 24,
    limit: int = 10,
) -> DashboardMonitoringSignalsOut:
    ...
```

Use label objects for SQLAlchemy ordering.

**Step 4: Add API endpoint**

```python
@router.get("/cards/monitoring-signals", response_model=DashboardMonitoringSignalsOut)
async def get_monitoring_signals(...): ...
```

**Step 5: Update summary readiness**

Set `monitoring_signals` to `ready` after endpoint passes tests.

---

## Task 12: Implement discovery candidates service and endpoint

**Objective:** Combine feed recommendation summary and monitoring-first article candidates.

**Files:**
- Modify: `src/sift/services/dashboard_service.py`
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_service.py`, `tests/test_dashboard_api.py`

**Step 1: Write failing tests**

```python
async def test_discovery_candidates_include_pending_feed_recommendations(): ...
async def test_discovery_candidates_include_monitoring_first_articles(): ...
async def test_discovery_candidates_exclude_archived_articles(): ...
```

**Step 2: Implement service method**

```python
async def get_discovery_candidates(
    self,
    *,
    session: AsyncSession,
    user_id: UUID,
    limit: int = 10,
) -> DashboardDiscoveryCandidatesOut:
    ...
```

Source 1: pending `FeedRecommendation` rows.
Source 2: recent `KeywordStreamMatch` + unread `Article` rows, scored with monitoring stream priority, recency, unread/saved state.

**Step 3: Add endpoint**

```python
@router.get("/cards/discovery-candidates", response_model=DashboardDiscoveryCandidatesOut)
async def get_discovery_candidates(...): ...
```

**Step 4: Update summary readiness**

Set `discovery_candidates` to `ready`.

---

## Task 13: Implement trend computation service

**Objective:** Create deterministic trend snapshots and topics from user-owned articles.

**Files:**
- Create: `src/sift/services/trends_service.py`
- Test: `tests/test_trends_service.py`

**Step 1: Write failing tests**

```python
async def test_trend_snapshot_detects_short_window_lift(): ...
async def test_trend_snapshot_counts_source_diversity(): ...
async def test_trend_snapshot_is_user_scoped(): ...
async def test_trend_snapshot_excludes_tiny_stopwords(): ...
```

**Step 2: Implement token extraction**

YAGNI: use local deterministic token/keyphrase extraction only.

```python
STOPWORDS = {"the", "and", "for", "with", "from", "that", "this", "are", "was", "were", "has", "have"}

def extract_trend_terms(text: str) -> list[str]:
    tokens = re.findall(r"[A-Za-zÅÄÖåäö0-9][A-Za-zÅÄÖåäö0-9-]{2,}", text.lower())
    return [token for token in tokens if token not in STOPWORDS]
```

**Step 3: Implement snapshot generation**

```python
async def generate_snapshot(
    self,
    *,
    session: AsyncSession,
    user_id: UUID,
    scope_type: str = "system",
    scope_id: UUID | None = None,
    short_window_hours: int = 24,
    baseline_days: int = 14,
    limit: int = 10,
) -> DashboardTrendsOut:
    ...
```

Momentum formula:

```python
short_rate = short_count / max(1, short_window_hours)
baseline_rate = baseline_count / max(1, baseline_days * 24)
momentum_score = round((short_rate + 0.1) / (baseline_rate + 0.1) * min(short_count, 10), 2)
```

Persist `TrendSnapshot` and `TrendTopic` rows.

**Step 4: Implement latest snapshot read**

```python
async def get_latest_trends_card(..., generate_if_missing: bool = True) -> DashboardTrendsOut:
    ...
```

If no articles exist, return `status="unavailable"`, reason `No article corpus available for trend detection yet.`

**Step 5: Verify tests**

Expected: PASS.

---

## Task 14: Add trends API endpoints

**Objective:** Expose dashboard trends card endpoint and optional manual refresh.

**Files:**
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_api.py`

**Step 1: Write failing tests**

```python
def test_dashboard_trends_requires_auth(): ...
def test_dashboard_trends_returns_unavailable_without_articles(): ...
def test_dashboard_trends_refresh_generates_snapshot(): ...
```

**Step 2: Add endpoints**

```python
@router.get("/cards/trends", response_model=DashboardTrendsOut)
async def get_trends(...): ...

@router.post("/cards/trends/refresh", response_model=DashboardTrendsOut)
async def refresh_trends(...): ...
```

**Step 3: Update summary readiness**

Set `trends` status based on latest snapshot/corpus state. The summary endpoint can remain simple but should not claim permanent implementation absence after this task.

---

## Task 15: Refactor dashboard summary to derive availability from service state

**Objective:** Stop hardcoding stale availability where service state can determine readiness.

**Files:**
- Modify: `src/sift/services/dashboard_service.py`
- Modify: `src/sift/api/routes/dashboard.py`
- Test: `tests/test_dashboard_api.py`

**Step 1: Write failing test**

Add a test that asserts summary cards include current readiness for all v1 cards:

```python
expected_ids = {
    "prioritized_queue",
    "feed_health",
    "saved_followup",
    "monitoring_signals",
    "trends",
    "discovery_candidates",
}
assert expected_ids <= set(by_id)
```

Assert no `dependency_spec` points to a missing active file.

**Step 2: Implement summary helper**

```python
async def get_dashboard_summary(self, *, session: AsyncSession, user_id: UUID) -> DashboardSummaryOut:
    ...
```

Keep this lightweight: do not execute heavy card queries. Use known implemented endpoint availability plus cheap corpus checks for trends if needed.

**Step 3: Route uses service**

Change `get_dashboard_summary` route to depend on `get_db_session` and call service.

**Step 4: Verify tests**

Expected: PASS.

---

## Task 16: Add frontend dashboard API types and parsers

**Objective:** Teach the frontend about all dashboard card payloads.

**Files:**
- Modify: `frontend/src/shared/types/contracts.ts`
- Modify: `frontend/src/entities/navigation/dashboard.ts`
- Create: `frontend/src/shared/api/dashboardApi.ts`
- Modify: `frontend/src/shared/api/queryKeys.ts`

**Step 1: Add TypeScript types**

Add explicit types to `contracts.ts` mirroring backend response models. Do not rely on stale generated OpenAPI unless regenerated.

**Step 2: Add Zod schemas**

In `frontend/src/entities/navigation/dashboard.ts`, extend existing summary schema and add parsers:

```ts
export function parseDashboardPrioritizedQueue(payload: unknown): DashboardPrioritizedQueue { ... }
export function parseDashboardFeedHealth(payload: unknown): DashboardFeedHealthCard { ... }
export function parseDashboardSavedFollowup(payload: unknown): DashboardSavedFollowup { ... }
export function parseDashboardMonitoringSignals(payload: unknown): DashboardMonitoringSignals { ... }
export function parseDashboardDiscoveryCandidates(payload: unknown): DashboardDiscoveryCandidates { ... }
export function parseDashboardTrends(payload: unknown): DashboardTrends { ... }
```

**Step 3: Add API functions**

Create `dashboardApi.ts`:

```ts
const DASHBOARD_ENDPOINT = "/api/v1/dashboard";

export async function getDashboardPrioritizedQueue() { ... }
export async function getDashboardFeedHealth() { ... }
export async function getDashboardSavedFollowup() { ... }
export async function getDashboardMonitoringSignals() { ... }
export async function getDashboardDiscoveryCandidates() { ... }
export async function getDashboardTrends() { ... }
export async function refreshDashboardTrends() { ... }
export async function getDashboardPrioritizationProfile() { ... }
export async function updateDashboardPrioritizationProfile(payload: DashboardPriorityProfileUpdate) { ... }
```

**Step 4: Add query keys**

```ts
dashboardCard: (cardId: string) => ["dashboard", "card", cardId] as const,
dashboardPrioritizationProfile: () => ["dashboard", "prioritization-profile"] as const,
```

**Step 5: Verify**

```bash
cd /home/pex/code/sift/frontend && npx tsc --noEmit
```

Expected: PASS.

---

## Task 17: Add dashboard hooks

**Objective:** Add TanStack Query hooks for every dashboard card and profile mutation.

**Files:**
- Create: `frontend/src/features/dashboard/api/dashboardHooks.ts`
- Test: covered through component tests later

**Step 1: Implement hooks**

```ts
export function useDashboardCardQuery<T>(cardId: string, queryFn: () => Promise<T>, enabled = true) { ... }
export function usePrioritizedQueueQuery(enabled = true) { ... }
export function useFeedHealthCardQuery(enabled = true) { ... }
export function useSavedFollowupQuery(enabled = true) { ... }
export function useMonitoringSignalsQuery(enabled = true) { ... }
export function useDiscoveryCandidatesQuery(enabled = true) { ... }
export function useTrendsQuery(enabled = true) { ... }
export function useRefreshTrendsMutation() { ... }
export function usePrioritizationProfileQuery(enabled = true) { ... }
export function useUpdatePrioritizationProfileMutation() { ... }
```

Use `staleTime` per card:
- summary/profile: 60s
- prioritized/saved/monitoring/discovery: 30s
- trends: 5m

**Step 2: Verify**

```bash
cd /home/pex/code/sift/frontend && npx tsc --noEmit
```

Expected: PASS.

---

## Task 18: Refactor DashboardHost to card layout orchestrator

**Objective:** Keep host layout/error boundaries but mount real card components instead of only summary availability copy.

**Files:**
- Modify: `frontend/src/features/dashboard/components/DashboardHost.tsx`
- Test: `frontend/src/features/dashboard/components/DashboardHost.test.tsx`

**Step 1: Write failing tests**

Update tests to assert:
- card grid renders in summary order
- manual refresh buttons are visible for ready cards
- unavailable/degraded fallback remains deterministic
- card-level render errors are isolated

**Step 2: Introduce generic card shell**

Add reusable component inside `DashboardHost.tsx` or separate `DashboardCardShell.tsx`:

```tsx
function DashboardCardShell({ title, children, onRefresh, isRefreshing }: Props) {
  return (
    <Paper className="dashboard-card" elevation={0}>
      <Stack spacing={1}>
        <Stack direction="row" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" component="h2">{title}</Typography>
          {onRefresh ? <IconButton aria-label={`Refresh ${title}`} onClick={onRefresh} disabled={isRefreshing}>...</IconButton> : null}
        </Stack>
        {children}
      </Stack>
    </Paper>
  );
}
```

**Step 3: Verify**

```bash
cd /home/pex/code/sift/frontend && npx vitest run src/features/dashboard/components/DashboardHost.test.tsx
```

Expected: PASS.

---

## Task 19: Build PrioritizedQueueCard frontend

**Objective:** Render top ranked unread/saved articles and score reasons.

**Files:**
- Create: `frontend/src/features/dashboard/components/PrioritizedQueueCard.tsx`
- Create: `frontend/src/features/dashboard/components/PrioritizedQueueCard.test.tsx`
- Modify: `DashboardHost.tsx`

**Step 1: Write component test**

Test renders:
- title
- item title/feed
- score
- at least one `why_prioritized` reason
- empty state

**Step 2: Implement component**

Use dense list layout. Clicking article should be planned as future route integration unless `DashboardHost` receives navigation handlers; avoid premature coupling in v1.

**Step 3: Register card**

Register `prioritized_queue` in dashboard card registry.

**Step 4: Verify**

```bash
cd /home/pex/code/sift/frontend && npx vitest run src/features/dashboard/components/PrioritizedQueueCard.test.tsx src/features/dashboard/components/DashboardHost.test.tsx
```

Expected: PASS.

---

## Task 20: Build FeedHealthCard frontend

**Objective:** Render stale/error counts, oldest success age, and queue lag degradation.

**Files:**
- Create: `frontend/src/features/dashboard/components/FeedHealthCard.tsx`
- Create: `frontend/src/features/dashboard/components/FeedHealthCard.test.tsx`
- Modify: `DashboardHost.tsx`

**Step 1: Test card states**

Test ready/degraded payloads and queue lag unavailable message.

**Step 2: Implement component**

Use metric tiles:
- Stale feeds
- Error feeds
- Oldest success age
- Queue lag

**Step 3: Verify**

Expected: vitest card tests pass.

---

## Task 21: Build SavedFollowupCard frontend

**Objective:** Replace placeholder text with real saved count and latest saved items.

**Files:**
- Modify or replace current `SavedFollowupCard` in `DashboardHost.tsx`
- Prefer create: `frontend/src/features/dashboard/components/SavedFollowupCard.tsx`
- Test: `SavedFollowupCard.test.tsx`

**Step 1: Write tests**

Assert saved count and latest items render.

**Step 2: Implement component**

Render empty state: `No saved follow-up items yet.`

**Step 3: Verify**

Expected: tests pass and previous placeholder text no longer appears.

---

## Task 22: Build MonitoringSignalsCard frontend

**Objective:** Render high-value monitoring streams with score breakdown.

**Files:**
- Create: `frontend/src/features/dashboard/components/MonitoringSignalsCard.tsx`
- Test: `MonitoringSignalsCard.test.tsx`
- Modify: `DashboardHost.tsx`

**Step 1: Write tests**

Assert stream name, signal score, match/unread counts, latest match, and score breakdown are visible.

**Step 2: Implement component**

Use a compact ranked list. Show score breakdown in collapsible detail per stream or tooltip; default to collapsed to keep density high.

**Step 3: Verify**

Expected: tests pass.

---

## Task 23: Build DiscoveryCandidatesCard frontend

**Objective:** Render feed recommendations and monitoring-first article candidates in one card.

**Files:**
- Create: `frontend/src/features/dashboard/components/DiscoveryCandidatesCard.tsx`
- Test: `DiscoveryCandidatesCard.test.tsx`
- Modify: `DashboardHost.tsx`

**Step 1: Write tests**

Assert:
- pending recommendation count
- candidate source badges (`feed recommendation`, `monitoring article`)
- candidate reasons
- empty state

**Step 2: Implement component**

Use source-kind chip and compact list. Link actions can be deferred unless routing context is already available.

**Step 3: Verify**

Expected: tests pass.

---

## Task 24: Build TrendsCard frontend

**Objective:** Render trend topics with momentum, evidence counts, unavailable state, and manual refresh.

**Files:**
- Create: `frontend/src/features/dashboard/components/TrendsCard.tsx`
- Test: `TrendsCard.test.tsx`
- Modify: `DashboardHost.tsx`

**Step 1: Write tests**

Assert:
- unavailable reason renders
- ready topics render with momentum score
- refresh button calls mutation

**Step 2: Implement component**

Render topic rows with:
- topic label
- momentum score
- short/baseline count
- source diversity count

**Step 3: Verify**

Expected: tests pass.

---

## Task 25: Add prioritization controls UI

**Objective:** Let the user tune source weights and recency horizon from dashboard.

**Files:**
- Create: `frontend/src/features/dashboard/components/PrioritizationSettingsPanel.tsx`
- Test: `PrioritizationSettingsPanel.test.tsx`
- Modify: `DashboardHost.tsx` or dashboard header area

**Step 1: Write tests**

Assert:
- current profile values render
- invalid value disables save or shows validation
- save calls mutation payload
- reset-to-default applies `{ feed: 40, monitoring_stream: 60, recency_horizon_hours: 24 }`

**Step 2: Implement collapsible panel**

Default placement: dashboard header action `Prioritization settings`, opens a collapsible section above the grid. This is a UX judgement and should be easy to flip to dialog later.

**Step 3: Verify**

Expected: tests pass.

---

## Task 26: Add dashboard styling and responsive behavior

**Objective:** Polish responsive card layout and dense command-center presentation.

**Files:**
- Modify: `frontend/src/app/styles.css:775-805` and nearby dashboard classes
- Test: existing frontend build + component snapshots/DOM assertions

**Step 1: Add/adjust CSS**

Ensure:
- desktop: two-column responsive grid
- tablet: two-column where space allows
- mobile: single-column card stack
- cards have consistent min-height, spacing, and metric tile rhythm

**Step 2: Verify layout with tests/build**

```bash
cd /home/pex/code/sift/frontend && npx vitest run src/features/dashboard/components
cd /home/pex/code/sift/frontend && npm run build
```

Expected: PASS, no TS2307 import errors.

---

## Task 27: Update OpenAPI/generated frontend types

**Objective:** Keep generated contract file from drifting further.

**Files:**
- Modify: `frontend/src/shared/types/generated.ts`
- Maybe update OpenAPI generation command/docs if present

**Step 1: Prefer regeneration if project command exists**

Search package scripts first:

```bash
cd /home/pex/code/sift/frontend && npm run
```

If an OpenAPI generation script exists, run it against the dev app.

**Step 2: Otherwise manually update generated.ts**

Add schemas for new dashboard contracts. Keep manual `contracts.ts` wrappers as the stable frontend-facing types.

**Step 3: Verify**

```bash
cd /home/pex/code/sift/frontend && npx tsc --noEmit
```

Expected: PASS.

---

## Task 28: End-to-end backend verification

**Objective:** Run focused backend gates after all backend tasks.

**Files:**
- No source changes unless failures require fixes

**Step 1: Run backend quality gates**

```bash
cd /home/pex/code/sift && docker compose exec -T app uv run ruff check src/sift/
cd /home/pex/code/sift && docker compose exec -T app uv run ruff format --check src/sift/
cd /home/pex/code/sift && docker compose exec -T app uv run mypy src/sift/
cd /home/pex/code/sift && docker compose exec -T app uv run python -m pytest tests/test_dashboard_api.py tests/test_dashboard_service.py tests/test_trends_service.py -q
```

Expected: all pass.

**Step 2: If a known flaky API test fails**

Rerun the failing file in isolation. Do not chase known `event loop closed` failures unless the dashboard-specific files fail consistently.

---

## Task 29: End-to-end frontend verification

**Objective:** Run full frontend gates after all frontend tasks.

**Files:**
- No source changes unless failures require fixes

**Step 1: Run frontend gates**

```bash
cd /home/pex/code/sift/frontend && npx tsc --noEmit
cd /home/pex/code/sift/frontend && npx eslint .
cd /home/pex/code/sift/frontend && npx vitest run src/features/dashboard/components src/features/workspace/routes/WorkspacePage.test.tsx
cd /home/pex/code/sift/frontend && npm run build
```

Expected: all pass; existing chunk-size warning may remain.

---

## Task 30: Update dashboard docs and backlog lifecycle

**Objective:** Move implemented dashboard specs/history to the right docs locations.

**Files:**
- Modify: `docs/current-state.md`
- Modify: `docs/backlog.md`
- Modify: `docs/backlog-history.md`
- Modify: `docs/session-notes.md`
- Move completed specs from `docs/specs/` to `docs/specs/done/` when acceptance criteria are complete:
  - `dashboard-command-center-v1.md`
  - `stream-ranking-prioritization-controls-v1.md`
  - `feed-health-ops-panel-v1.md`
  - `monitoring-signal-scoring-v1.md`
  - `trends-detection-dashboard-v1.md`

**Step 1: Update docs after implementation, not before**

Only mark a spec complete after code + tests pass for its acceptance criteria.

**Step 2: Run Markdown link check**

Use the existing Python snippet from the docs cleanup session:

```bash
cd /home/pex/code/sift && python3 - <<'PY'
from pathlib import Path
import re
root = Path('.')
pat = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
broken=[]
for path in (root/'docs').rglob('*.md'):
    text=path.read_text(encoding='utf-8')
    for m in pat.finditer(text):
        target=m.group(1).split('#',1)[0]
        if not target or target.startswith(('http://','https://','mailto:')):
            continue
        if not (path.parent/target).resolve().exists():
            broken.append((str(path),m.group(1)))
print('broken links:', len(broken))
for p,t in broken[:50]: print(f'{p}: {t}')
PY
```

Expected: `broken links: 0`.

---

## Task 31: Final cumulative review

**Objective:** Run independent review against the full dashboard diff before declaring done.

**Files:**
- Full cumulative diff

**Step 1: Run final gates**

Run Tasks 28 and 29 again.

**Step 2: Request code review**

Use the `requesting-code-review` workflow against the cumulative diff. Review focus:
- dashboard endpoint auth/user scoping
- deterministic scoring and tie-breaks
- SQLAlchemy grouping/order_by correctness
- frontend query invalidation/manual refresh
- no placeholder copy left in ready cards
- no stale active spec links

**Step 3: Fix review findings**

Address only findings from the review. Re-run impacted gates.

**Step 4: Commit**

Only if explicitly authorized:

```bash
git add src/sift frontend/src tests docs alembic
 git commit -m "[verified] feat: implement dashboard command center v1"
```

---

## Risks, tradeoffs, and open questions

1. **Scope size:** This is a full dashboard program, not a single slice. Recommended execution should be split into backend-first slices: profile/queue, feed/saved, monitoring/discovery, trends, then frontend.
2. **Trend quality:** Deterministic local term extraction is explainable and dependency-free, but less semantically rich than embeddings/NLP. This matches v1 non-goals.
3. **Queue lag telemetry:** Feed-health card can ship degraded without queue lag if RQ inspection is not reliable in all environments. Add real queue lag as a follow-up if needed.
4. **Performance:** Dashboard cards query aggregate data. Keep default limits small (`10`) and avoid full article scans. If large data causes slow queries, add indexes in a follow-up migration.
5. **OpenAPI generation drift:** Current frontend has some manually patched types. Prefer regenerating if a stable command exists; otherwise keep dashboard contracts explicit in `contracts.ts` and Zod parsers.
6. **Routing from dashboard cards:** This plan renders cards first. Deep-linking card rows into reader/search scopes can be a follow-up unless the implementer wires existing workspace search state safely.

---

## Deferred items

- **D1: Full semantic/vector trend detection** — Deferred because `docs/specs/trends-detection-dashboard-v1.md` explicitly avoids external NLP/vector dependency for v1. Class of work: MLOps/vector plugin feature.
- **D2: Dashboard plugin-card extension API** — Deferred because v1 only needs builtin cards while preserving future compatibility. Class of work: plugin platform extension.
- **D3: Deep feed-health drilldown from dashboard card** — Deferred because `/account/feed-health` already exists and `feed-health-ops-panel-v1` card scope says no deep per-feed history UI in card v1. Class of work: UX/navigation integration.
- **D4: Mobile-specific dashboard redesign** — Deferred because backlog keeps mobile planning as a separate session. Class of work: mobile UX planning.
- **D5: Advanced search acceleration for dashboard candidate queries** — Deferred because dashboard cards should use bounded queries first. Class of work: database performance/indexing.

---

## Recommended execution sequence

1. Task 1 only: stale discovery summary fix.
2. Tasks 2-7: prioritization profile + prioritized queue backend.
3. Tasks 8-10: feed-health and saved follow-up backend.
4. Tasks 11-12: monitoring signals + discovery candidates backend.
5. Tasks 13-15: trends + summary derivation.
6. Tasks 16-27: frontend card implementation.
7. Tasks 28-31: verification, docs, review.

Plan complete. Ready for implementation with subagent-driven-development when the user says to proceed.
