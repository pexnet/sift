from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from sift.api.deps.auth import get_current_user
from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.models import User
from sift.domain.schemas import (
    SearchFeedCandidateOut,
    SearchFeedsOut,
    SearchFeedsRequestIn,
    SearchProviderBudgetOut,
    SearchProvidersOut,
)
from sift.plugins.registry import PluginRegistryEntry, load_plugin_registry
from sift.services.search_service import search_provider_service

router = APIRouter()


def _resolve_search_provider_entry() -> tuple[PluginRegistryEntry, dict[str, Any]]:
    settings = get_settings()
    registry = load_plugin_registry(settings.plugin_registry_path)
    for entry in registry.plugins:
        if not entry.enabled:
            continue
        if "search_provider" not in entry.capabilities:
            continue
        raw_settings = entry.settings.get("search_provider")
        if not isinstance(raw_settings, dict):
            continue
        return entry, raw_settings
    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="No enabled search provider plugin configured",
    )


def _require_loaded_search_provider(plugin_id: str) -> None:
    manager = get_plugin_manager()
    snapshots = {snapshot.plugin_id: snapshot for snapshot in manager.get_status_snapshots()}
    snapshot = snapshots.get(plugin_id)
    if snapshot is None or not snapshot.loaded:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Search provider plugin unavailable",
        )


@router.get("/providers", response_model=SearchProvidersOut)
async def get_search_providers(current_user: User = Depends(get_current_user)) -> SearchProvidersOut:
    del current_user

    entry, search_settings = _resolve_search_provider_entry()
    _require_loaded_search_provider(entry.id)
    settings = get_settings()

    provider_chain = [str(item) for item in search_settings.get("provider_chain", [])]
    raw_budgets = search_settings.get("provider_budgets", {})
    budgets: dict[str, SearchProviderBudgetOut] = {}
    if isinstance(raw_budgets, dict):
        for provider, budget in raw_budgets.items():
            if not isinstance(provider, str) or not isinstance(budget, dict):
                continue
            budgets[provider] = SearchProviderBudgetOut(**budget)

    return SearchProvidersOut(
        plugin_id=entry.id,
        provider_chain=provider_chain,
        provider_budgets=budgets,
        timeout_ms=settings.plugin_timeout_search_provider_ms,
        loaded=True,
    )


@router.post("/feeds", response_model=SearchFeedsOut)
async def search_feeds(
    payload: SearchFeedsRequestIn,
    current_user: User = Depends(get_current_user),
) -> SearchFeedsOut:
    entry, search_settings = _resolve_search_provider_entry()
    _require_loaded_search_provider(entry.id)
    provider_chain = [str(item).strip() for item in search_settings.get("provider_chain", []) if str(item).strip()]
    raw_budgets = search_settings.get("provider_budgets")
    raw_providers = search_settings.get("providers")
    provider_budgets = (
        search_provider_service.parse_provider_budgets(raw_budgets)
        if isinstance(raw_budgets, dict)
        else {}
    )
    provider_settings: dict[str, dict[str, Any]] = {}
    if isinstance(raw_providers, dict):
        for provider, provider_cfg in raw_providers.items():
            if isinstance(provider, str) and isinstance(provider_cfg, dict):
                provider_settings[provider] = provider_cfg

    result = await search_provider_service.search_with_fallback(
        plugin_name=entry.id,
        query=payload.query.strip(),
        max_results=payload.max_results,
        provider_chain=provider_chain,
        provider_budgets=provider_budgets,
        provider_settings=provider_settings,
        metadata={"user_id": str(current_user.id)},
    )
    if result is None:
        return SearchFeedsOut(
            query=payload.query,
            provider=None,
            provider_chain=provider_chain,
            candidates=[],
            warnings=["search provider returned no result"],
        )

    return SearchFeedsOut(
        query=payload.query,
        provider=result.provider,
        provider_chain=provider_chain,
        candidates=[
            SearchFeedCandidateOut(
                title=item.title,
                url=item.url,
                site_url=item.site_url,
                description=item.description,
                provider=item.provider,
            )
            for item in result.candidates[: payload.max_results]
        ],
        warnings=list(result.warnings),
    )
