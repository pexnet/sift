import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sift.core.runtime import get_plugin_manager
from sift.plugins.base import SearchFeedsRequest, SearchFeedsResult


@dataclass(slots=True)
class SearchProviderBudget:
    max_requests_per_run: int
    max_requests_per_day: int
    min_interval_ms: int
    max_query_variants_per_stream: int
    max_results_per_query: int


@dataclass(slots=True)
class _ProviderBudgetState:
    requests_today: int = 0
    day_utc: datetime | None = None
    last_request_at: datetime | None = None


class SearchProviderService:
    def __init__(self) -> None:
        self._budget_state: dict[str, _ProviderBudgetState] = {}
        self._lock = asyncio.Lock()

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
        self._budget_state = {}

    async def search_with_fallback(
        self,
        *,
        plugin_name: str,
        query: str,
        max_results: int,
        provider_chain: list[str],
        provider_budgets: dict[str, SearchProviderBudget],
        provider_settings: dict[str, dict[str, Any]],
        metadata: dict[str, str],
    ) -> SearchFeedsResult | None:
        warnings: list[str] = []
        run_counts: dict[str, int] = {}
        manager = get_plugin_manager()

        for provider in provider_chain:
            budget = provider_budgets.get(provider)
            if budget is None:
                warnings.append(f"{provider}: missing provider budget configuration")
                continue

            allowed, reason = await self._try_reserve_budget_slot(provider=provider, budget=budget, run_counts=run_counts)
            if not allowed:
                warnings.append(f"{provider}: {reason}")
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
                warnings.append(f"{provider}: invocation failed or timed out")
                continue

            provider_warnings = [f"{provider}: {item}" for item in result.warnings]
            if result.candidates:
                return SearchFeedsResult(
                    provider=result.provider,
                    candidates=result.candidates,
                    warnings=warnings + provider_warnings,
                )

            warnings.extend(provider_warnings)
            warnings.append(f"{provider}: no candidates returned")

        if not warnings:
            return None
        return SearchFeedsResult(provider=provider_chain[0] if provider_chain else "unconfigured", candidates=[], warnings=warnings)

    async def _try_reserve_budget_slot(
        self,
        *,
        provider: str,
        budget: SearchProviderBudget,
        run_counts: dict[str, int],
    ) -> tuple[bool, str | None]:
        now = datetime.now(UTC)
        async with self._lock:
            run_count = run_counts.get(provider, 0)
            if run_count >= budget.max_requests_per_run:
                return False, "max_requests_per_run exhausted"

            state = self._budget_state.setdefault(provider, _ProviderBudgetState())
            if state.day_utc is None or state.day_utc.date() != now.date():
                state.day_utc = now
                state.requests_today = 0
                state.last_request_at = None

            if state.requests_today >= budget.max_requests_per_day:
                return False, "max_requests_per_day exhausted"

            if state.last_request_at is not None:
                elapsed_ms = int((now - state.last_request_at).total_seconds() * 1000)
                if elapsed_ms < budget.min_interval_ms:
                    return False, f"min_interval_ms not satisfied ({elapsed_ms}ms < {budget.min_interval_ms}ms)"

            state.requests_today += 1
            state.last_request_at = now
            run_counts[provider] = run_count + 1
            return True, None


search_provider_service = SearchProviderService()
