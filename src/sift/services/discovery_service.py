import json
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse, urlunparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.models import DiscoveryStream
from sift.domain.schemas import DiscoveryStreamCreate, DiscoveryStreamOut, DiscoveryStreamUpdate
from sift.plugins.base import SearchFeedCandidate
from sift.plugins.registry import PluginRegistryEntry, load_plugin_registry
from sift.search.query_language import SearchQuerySyntaxError, parse_search_query
from sift.services.search_service import SearchProviderBudget, SearchWarning, search_provider_service

_SUPPORTED_SCHEMES = frozenset({"http", "https"})


class DiscoveryStreamConflictError(Exception):
    pass


class DiscoveryStreamValidationError(Exception):
    pass


class DiscoveryStreamNotFoundError(Exception):
    pass


class DiscoveryGenerationUnavailableError(Exception):
    pass


@dataclass(slots=True)
class SearchProviderRuntimeConfig:
    plugin_id: str
    provider_chain: list[str]
    provider_budgets: dict[str, SearchProviderBudget]
    provider_settings: dict[str, dict[str, Any]]


@dataclass(slots=True)
class DiscoveryGenerationResult:
    stream_id: UUID
    provider_chain: list[str]
    query_variants: list[str]
    candidates: list[SearchFeedCandidate]
    warnings: list[str]
    warning_details: list[SearchWarning]


def _normalize_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        item = keyword.strip().lower()
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def _keywords_to_json(keywords: list[str]) -> str:
    return json.dumps(_normalize_keywords(keywords))


def _keywords_from_json(raw: str) -> list[str]:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_keywords([str(item) for item in loaded])


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_candidate_url(url: str) -> str | None:
    normalized = _normalize_optional_text(url)
    if normalized is None:
        return None
    parsed = urlparse(normalized)
    if parsed.scheme.lower() not in _SUPPORTED_SCHEMES:
        return None
    if not parsed.netloc:
        return None
    return urlunparse(parsed._replace(fragment=""))


def _resolve_search_provider_entry(manager: Any) -> tuple[PluginRegistryEntry, dict[str, Any]]:
    entries: list[PluginRegistryEntry]
    get_registry_entries = getattr(manager, "get_registry_entries", None)
    if callable(get_registry_entries):
        entries = get_registry_entries()
    else:
        settings = get_settings()
        registry = load_plugin_registry(settings.plugin_registry_path)
        entries = registry.plugins

    for entry in entries:
        if not entry.enabled:
            continue
        if "search_provider" not in entry.capabilities:
            continue
        raw_settings = entry.settings.get("search_provider")
        if not isinstance(raw_settings, dict):
            continue
        return entry, raw_settings
    raise DiscoveryGenerationUnavailableError("No enabled search provider plugin configured")


def _require_loaded_search_provider(manager: Any, plugin_id: str) -> None:
    snapshots = {snapshot.plugin_id: snapshot for snapshot in manager.get_status_snapshots()}
    snapshot = snapshots.get(plugin_id)
    if snapshot is None or not snapshot.loaded:
        raise DiscoveryGenerationUnavailableError("Search provider plugin unavailable")


def _build_runtime_config(manager: Any) -> SearchProviderRuntimeConfig:
    entry, search_settings = _resolve_search_provider_entry(manager)
    _require_loaded_search_provider(manager, entry.id)

    provider_chain = [str(item).strip() for item in search_settings.get("provider_chain", []) if str(item).strip()]
    if not provider_chain:
        raise DiscoveryGenerationUnavailableError("Search provider chain is empty")

    raw_budgets = search_settings.get("provider_budgets")
    provider_budgets = search_provider_service.parse_provider_budgets(raw_budgets) if isinstance(raw_budgets, dict) else {}
    if not provider_budgets:
        raise DiscoveryGenerationUnavailableError("Search provider budgets are not configured")

    raw_providers = search_settings.get("providers")
    provider_settings: dict[str, dict[str, Any]] = {}
    if isinstance(raw_providers, dict):
        for provider, provider_cfg in raw_providers.items():
            if isinstance(provider, str) and isinstance(provider_cfg, dict):
                provider_settings[provider] = provider_cfg

    return SearchProviderRuntimeConfig(
        plugin_id=entry.id,
        provider_chain=provider_chain,
        provider_budgets=provider_budgets,
        provider_settings=provider_settings,
    )


def _validate_criteria(*, match_query: str | None, include_keywords: list[str]) -> None:
    if match_query:
        return
    if include_keywords:
        return
    raise DiscoveryStreamValidationError("A discovery stream needs match_query or include_keywords")


def _resolve_max_query_variants(
    *,
    provider_chain: list[str],
    provider_budgets: dict[str, SearchProviderBudget],
) -> int:
    variant_limits = [
        budget.max_query_variants_per_stream
        for provider in provider_chain
        if (budget := provider_budgets.get(provider)) is not None
    ]
    if not variant_limits:
        return 1
    return max(1, min(variant_limits))


def _build_query_variants(*, stream: DiscoveryStream, max_query_variants: int) -> list[str]:
    variants: list[str] = []
    seen: set[str] = set()
    include_keywords = _keywords_from_json(stream.include_keywords_json)
    exclude_keywords = _keywords_from_json(stream.exclude_keywords_json)
    match_query = _normalize_optional_text(stream.match_query)
    exclude_suffix = " ".join(f"-{keyword}" for keyword in exclude_keywords[:5])

    def append_variant(raw_value: str) -> None:
        normalized = raw_value.strip()
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        variants.append(normalized)

    if match_query:
        append_variant(match_query)

    if include_keywords:
        include_variants = [" ".join(include_keywords[:6]), *include_keywords]
        for include_variant in include_variants:
            if exclude_suffix:
                append_variant(f"{include_variant} {exclude_suffix}")
            else:
                append_variant(include_variant)

    if not variants:
        append_variant(stream.name)

    return variants[: max(1, max_query_variants)]


def _dedupe_candidates(candidates: list[SearchFeedCandidate], max_candidates: int) -> list[SearchFeedCandidate]:
    deduped: list[SearchFeedCandidate] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        normalized_url = _normalize_candidate_url(candidate.url)
        if normalized_url is None or normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        site_url = _normalize_candidate_url(candidate.site_url) if candidate.site_url else None
        deduped.append(
            SearchFeedCandidate(
                title=candidate.title,
                url=normalized_url,
                site_url=site_url,
                description=candidate.description,
                provider=candidate.provider,
            )
        )
        if len(deduped) >= max_candidates:
            break
    return deduped


class DiscoveryService:
    async def list_streams(self, session: AsyncSession, user_id: UUID) -> list[DiscoveryStream]:
        query = (
            select(DiscoveryStream)
            .where(DiscoveryStream.user_id == user_id)
            .order_by(DiscoveryStream.priority.asc(), DiscoveryStream.name.asc())
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_stream(self, session: AsyncSession, user_id: UUID, stream_id: UUID) -> DiscoveryStream | None:
        query = select(DiscoveryStream).where(DiscoveryStream.id == stream_id, DiscoveryStream.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def create_stream(self, session: AsyncSession, user_id: UUID, payload: DiscoveryStreamCreate) -> DiscoveryStream:
        match_query = _normalize_optional_text(payload.match_query)
        include_keywords = _normalize_keywords(payload.include_keywords)
        exclude_keywords = _normalize_keywords(payload.exclude_keywords)
        _validate_criteria(match_query=match_query, include_keywords=include_keywords)

        if match_query:
            try:
                parse_search_query(match_query)
            except SearchQuerySyntaxError as exc:
                raise DiscoveryStreamValidationError(str(exc)) from exc

        stream = DiscoveryStream(
            user_id=user_id,
            name=payload.name.strip(),
            description=_normalize_optional_text(payload.description),
            is_active=payload.is_active,
            priority=payload.priority,
            match_query=match_query,
            include_keywords_json=_keywords_to_json(include_keywords),
            exclude_keywords_json=_keywords_to_json(exclude_keywords),
        )
        session.add(stream)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise DiscoveryStreamConflictError("Discovery stream with the same name already exists") from exc

        await session.refresh(stream)
        return stream

    async def update_stream(
        self,
        session: AsyncSession,
        user_id: UUID,
        stream_id: UUID,
        payload: DiscoveryStreamUpdate,
    ) -> DiscoveryStream:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise DiscoveryStreamNotFoundError(f"Discovery stream {stream_id} not found")

        if payload.name is not None:
            stream.name = payload.name.strip()
        if "description" in payload.model_fields_set:
            stream.description = _normalize_optional_text(payload.description)
        if payload.is_active is not None:
            stream.is_active = payload.is_active
        if payload.priority is not None:
            stream.priority = payload.priority
        if "match_query" in payload.model_fields_set:
            stream.match_query = _normalize_optional_text(payload.match_query)
        if payload.include_keywords is not None:
            stream.include_keywords_json = _keywords_to_json(payload.include_keywords)
        if payload.exclude_keywords is not None:
            stream.exclude_keywords_json = _keywords_to_json(payload.exclude_keywords)

        match_query = _normalize_optional_text(stream.match_query)
        include_keywords = _keywords_from_json(stream.include_keywords_json)
        _validate_criteria(match_query=match_query, include_keywords=include_keywords)
        if match_query:
            try:
                parse_search_query(match_query)
            except SearchQuerySyntaxError as exc:
                raise DiscoveryStreamValidationError(str(exc)) from exc

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise DiscoveryStreamConflictError("Discovery stream with the same name already exists") from exc

        await session.refresh(stream)
        return stream

    async def delete_stream(self, session: AsyncSession, user_id: UUID, stream_id: UUID) -> None:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise DiscoveryStreamNotFoundError(f"Discovery stream {stream_id} not found")
        await session.delete(stream)
        await session.commit()

    async def generate_for_stream(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        stream_id: UUID,
        max_results_per_query: int,
        max_candidates: int,
    ) -> DiscoveryGenerationResult:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise DiscoveryStreamNotFoundError(f"Discovery stream {stream_id} not found")
        if not stream.is_active:
            raise DiscoveryStreamValidationError("Discovery stream must be active to run generation")

        runtime_config = _build_runtime_config(get_plugin_manager())
        query_variants = _build_query_variants(
            stream=stream,
            max_query_variants=_resolve_max_query_variants(
                provider_chain=runtime_config.provider_chain,
                provider_budgets=runtime_config.provider_budgets,
            ),
        )

        warnings: list[str] = []
        warning_details: list[SearchWarning] = []
        warning_detail_keys: set[tuple[str, str | None, str]] = set()
        aggregated_candidates: list[SearchFeedCandidate] = []

        for query in query_variants:
            result = await search_provider_service.search_with_fallback(
                plugin_name=runtime_config.plugin_id,
                session=session,
                query=query,
                max_results=max_results_per_query,
                provider_chain=runtime_config.provider_chain,
                provider_budgets=runtime_config.provider_budgets,
                provider_settings=runtime_config.provider_settings,
                metadata={"user_id": str(user_id), "discovery_stream_id": str(stream_id)},
            )
            if result is None:
                continue

            for warning in result.warnings:
                if warning not in warnings:
                    warnings.append(warning)
            for warning_detail in result.warning_details:
                warning_key = (warning_detail.code, warning_detail.provider, warning_detail.message)
                if warning_key in warning_detail_keys:
                    continue
                warning_detail_keys.add(warning_key)
                warning_details.append(warning_detail)
            aggregated_candidates.extend(result.candidates)

        candidates = _dedupe_candidates(aggregated_candidates, max_candidates)

        return DiscoveryGenerationResult(
            stream_id=stream.id,
            provider_chain=runtime_config.provider_chain,
            query_variants=query_variants,
            candidates=candidates,
            warnings=warnings,
            warning_details=warning_details,
        )

    def to_out(self, stream: DiscoveryStream) -> DiscoveryStreamOut:
        return DiscoveryStreamOut(
            id=stream.id,
            user_id=stream.user_id,
            name=stream.name,
            description=stream.description,
            is_active=stream.is_active,
            priority=stream.priority,
            match_query=stream.match_query,
            include_keywords=_keywords_from_json(stream.include_keywords_json),
            exclude_keywords=_keywords_from_json(stream.exclude_keywords_json),
            created_at=stream.created_at,
            updated_at=stream.updated_at,
        )


discovery_service = DiscoveryService()
