import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from sift.core.runtime import get_plugin_manager
from sift.db.models import SearchProviderBudgetDaily
from sift.plugins.base import SearchFeedCandidate, SearchFeedsRequest

_PROVIDER_WARNING_PATTERN = re.compile(r"^\s*([a-z0-9_]+)\s*:\s*(.+?)\s*$")


@dataclass(slots=True)
class SearchProviderBudget:
    max_requests_per_run: int
    max_requests_per_day: int
    min_interval_ms: int
    max_query_variants_per_stream: int
    max_results_per_query: int


@dataclass(slots=True)
class SearchWarning:
    code: str
    provider: str | None
    message: str


@dataclass(slots=True)
class SearchExecutionResult:
    provider: str
    candidates: list[SearchFeedCandidate]
    warnings: list[str]
    warning_details: list[SearchWarning]


class SearchProviderService:
    @staticmethod
    def parse_provider_budgets(raw_budgets: dict[str, Any]) -> dict[str, SearchProviderBudget]:
        parsed: dict[str, SearchProviderBudget] = {}
        for provider, raw_value in raw_budgets.items():
            if not isinstance(provider, str) or not isinstance(raw_value, dict):
                continue
            parsed[provider] = SearchProviderBudget(
                max_requests_per_run=int(raw_value["max_requests_per_run"]),
                max_requests_per_day=int(raw_value["max_requests_per_day"]),
                min_interval_ms=int(raw_value["min_interval_ms"]),
                max_query_variants_per_stream=int(raw_value["max_query_variants_per_stream"]),
                max_results_per_query=int(raw_value["max_results_per_query"]),
            )
        return parsed

    def reset_budget_state(self) -> None:
        # Legacy test helper: budget state is now persisted in DB; there is no in-memory cache to clear.
        return None

    async def search_with_fallback(
        self,
        *,
        plugin_name: str,
        session: AsyncSession,
        query: str,
        max_results: int,
        provider_chain: list[str],
        provider_budgets: dict[str, SearchProviderBudget],
        provider_settings: dict[str, dict[str, Any]],
        metadata: dict[str, str],
    ) -> SearchExecutionResult | None:
        warnings: list[str] = []
        warning_details: list[SearchWarning] = []
        run_counts: dict[str, int] = {}
        manager = get_plugin_manager()

        for provider in provider_chain:
            budget = provider_budgets.get(provider)
            if budget is None:
                self._append_warning(
                    warnings=warnings,
                    warning_details=warning_details,
                    provider=provider,
                    code="missing_provider_budget_config",
                    message="missing provider budget configuration",
                )
                continue

            allowed, code, reason = await self._try_reserve_budget_slot(
                session=session,
                provider=provider,
                budget=budget,
                run_counts=run_counts,
            )
            if not allowed:
                self._append_warning(
                    warnings=warnings,
                    warning_details=warning_details,
                    provider=provider,
                    code=code or "budget_slot_unavailable",
                    message=reason or "provider budget slot unavailable",
                )
                continue

            request = SearchFeedsRequest(
                query=query,
                provider_chain=[provider],
                max_results=min(max_results, budget.max_results_per_query),
                provider_settings=provider_settings.get(provider, {}),
                metadata=metadata,
            )
            result = await manager.search_feeds(plugin_name=plugin_name, request=request)
            if result is None:
                self._append_warning(
                    warnings=warnings,
                    warning_details=warning_details,
                    provider=provider,
                    code="provider_invocation_failed",
                    message="invocation failed or timed out",
                )
                continue

            for provider_warning in result.warnings:
                warning_code, warning_message = self._parse_provider_warning(provider_warning)
                self._append_warning(
                    warnings=warnings,
                    warning_details=warning_details,
                    provider=provider,
                    code=warning_code,
                    message=warning_message,
                )
            if result.candidates:
                return SearchExecutionResult(
                    provider=result.provider,
                    candidates=result.candidates,
                    warnings=warnings,
                    warning_details=warning_details,
                )

            self._append_warning(
                warnings=warnings,
                warning_details=warning_details,
                provider=provider,
                code="provider_no_candidates",
                message="no candidates returned",
            )

        if not warnings:
            return None
        return SearchExecutionResult(
            provider=provider_chain[0] if provider_chain else "unconfigured",
            candidates=[],
            warnings=warnings,
            warning_details=warning_details,
        )

    async def _try_reserve_budget_slot(
        self,
        *,
        session: AsyncSession,
        provider: str,
        budget: SearchProviderBudget,
        run_counts: dict[str, int],
    ) -> tuple[bool, str | None, str | None]:
        now = datetime.now(UTC)
        run_count = run_counts.get(provider, 0)
        if run_count >= budget.max_requests_per_run:
            return False, "max_requests_per_run_exhausted", "max_requests_per_run exhausted"

        day_utc = now.date()
        await self._ensure_daily_budget_row(session=session, provider=provider, day_utc=day_utc, now=now)

        cutoff = now - timedelta(milliseconds=budget.min_interval_ms)
        update_result = await session.execute(
            update(SearchProviderBudgetDaily)
            .where(
                SearchProviderBudgetDaily.provider_id == provider,
                SearchProviderBudgetDaily.day_utc == day_utc,
                SearchProviderBudgetDaily.requests_count < budget.max_requests_per_day,
                or_(
                    SearchProviderBudgetDaily.last_request_at.is_(None),
                    SearchProviderBudgetDaily.last_request_at <= cutoff,
                ),
            )
            .values(
                requests_count=SearchProviderBudgetDaily.requests_count + 1,
                last_request_at=now,
                updated_at=now,
            )
        )
        rowcount = int(getattr(update_result, "rowcount", 0) or 0)
        if rowcount > 0:
            await session.commit()
            run_counts[provider] = run_count + 1
            return True, None, None

        state_result = await session.execute(
            select(SearchProviderBudgetDaily.requests_count, SearchProviderBudgetDaily.last_request_at).where(
                SearchProviderBudgetDaily.provider_id == provider,
                SearchProviderBudgetDaily.day_utc == day_utc,
            )
        )
        state_row = state_result.one_or_none()
        if state_row is None:
            return False, "budget_state_unavailable", "provider budget state unavailable"

        requests_count, last_request_at = state_row
        if requests_count >= budget.max_requests_per_day:
            return False, "max_requests_per_day_exhausted", "max_requests_per_day exhausted"

        normalized_last_request_at = self._normalize_timestamp(last_request_at)
        if normalized_last_request_at is not None:
            elapsed_ms = int((now - normalized_last_request_at).total_seconds() * 1000)
            if elapsed_ms < budget.min_interval_ms:
                return (
                    False,
                    "min_interval_ms_not_satisfied",
                    f"min_interval_ms not satisfied ({elapsed_ms}ms < {budget.min_interval_ms}ms)",
                )

        return False, "budget_slot_unavailable", "provider budget slot unavailable"

    async def _ensure_daily_budget_row(
        self,
        *,
        session: AsyncSession,
        provider: str,
        day_utc: date,
        now: datetime,
    ) -> None:
        values = {
            "provider_id": provider,
            "day_utc": day_utc,
            "requests_count": 0,
            "last_request_at": None,
            "created_at": now,
            "updated_at": now,
        }

        dialect_name = session.get_bind().dialect.name
        if dialect_name == "sqlite":
            await session.execute(
                sqlite_insert(SearchProviderBudgetDaily)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=[SearchProviderBudgetDaily.provider_id, SearchProviderBudgetDaily.day_utc]
                )
            )
            return
        if dialect_name == "postgresql":
            await session.execute(
                postgresql_insert(SearchProviderBudgetDaily)
                .values(**values)
                .on_conflict_do_nothing(
                    index_elements=[SearchProviderBudgetDaily.provider_id, SearchProviderBudgetDaily.day_utc]
                )
            )
            return

        existing = await session.execute(
            select(SearchProviderBudgetDaily.id).where(
                SearchProviderBudgetDaily.provider_id == provider,
                SearchProviderBudgetDaily.day_utc == day_utc,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return
        session.add(
            SearchProviderBudgetDaily(
                provider_id=provider,
                day_utc=day_utc,
                requests_count=0,
                last_request_at=None,
            )
        )
        await session.flush()

    @staticmethod
    def _normalize_timestamp(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value

    @staticmethod
    def _append_warning(
        *,
        warnings: list[str],
        warning_details: list[SearchWarning],
        provider: str | None,
        code: str,
        message: str,
    ) -> None:
        prefix = f"{provider}: " if provider else ""
        warnings.append(f"{prefix}{message}")
        warning_details.append(SearchWarning(code=code, provider=provider, message=message))

    @staticmethod
    def _parse_provider_warning(raw_warning: str) -> tuple[str, str]:
        match = _PROVIDER_WARNING_PATTERN.match(raw_warning)
        if match is None:
            return "provider_warning", raw_warning
        code = match.group(1).strip()
        message = match.group(2).strip() or raw_warning
        return code, message


search_provider_service = SearchProviderService()
