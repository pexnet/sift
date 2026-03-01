import json
from dataclasses import dataclass
from datetime import UTC, datetime
from html.parser import HTMLParser
from typing import Any, Literal, cast
from urllib.parse import urljoin, urlparse, urlunparse
from uuid import UUID

import feedparser
import httpx
from pydantic import ValidationError
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.core.runtime import get_plugin_manager
from sift.db.models import DiscoveryStream, Feed, FeedRecommendation, FeedRecommendationSource
from sift.domain.schemas import (
    DiscoveryStreamCreate,
    DiscoveryStreamOut,
    DiscoveryStreamUpdate,
    FeedCreate,
    FeedRecommendationOut,
    FeedRecommendationSourceOut,
)
from sift.plugins.base import SearchFeedCandidate
from sift.plugins.registry import PluginRegistryEntry, load_plugin_registry
from sift.search.query_language import SearchQuerySyntaxError, parse_search_query
from sift.services.dedup_service import normalize_canonical_url
from sift.services.feed_service import FeedAlreadyExistsError, feed_service
from sift.services.search_service import SearchProviderBudget, SearchWarning, search_provider_service

_SUPPORTED_SCHEMES = frozenset({"http", "https"})
_RECOMMENDATION_STATUS_VALUES = frozenset({"pending", "accepted", "denied", "resolved_existing"})
_CANDIDATE_FEED_FALLBACK_PATHS = ("/feed", "/rss", "/atom.xml", "/feed.xml")
_MAX_VALIDATION_CANDIDATES = 40


class DiscoveryStreamConflictError(Exception):
    pass


class DiscoveryStreamValidationError(Exception):
    pass


class DiscoveryStreamNotFoundError(Exception):
    pass


class DiscoveryGenerationUnavailableError(Exception):
    pass


class DiscoveryRecommendationNotFoundError(Exception):
    pass


class DiscoveryRecommendationValidationError(Exception):
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
    persisted_count: int
    pending_count: int
    resolved_existing_count: int


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


def _normalize_candidate_url(url: str | None) -> str | None:
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


def _normalize_recommendation_url(url: str) -> str:
    normalized = normalize_canonical_url(url)
    if normalized:
        return normalized
    return url.strip().lower()


def _to_json_payload(payload: dict[str, Any] | None) -> str | None:
    if payload is None:
        return None
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def _from_json_payload(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _fallback_feed_title(feed_url: str) -> str:
    parsed = urlparse(feed_url)
    host = parsed.netloc.strip()
    if host:
        return host
    return "Discovered feed"


def _candidate_validation_urls(*, feed_url: str, site_url: str | None) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()

    def push(raw_value: str | None) -> None:
        normalized = _normalize_candidate_url(raw_value)
        if normalized is None or normalized in seen:
            return
        seen.add(normalized)
        urls.append(normalized)

    push(feed_url)
    base = _normalize_candidate_url(site_url)
    if base is not None:
        push(base)
        for path in _CANDIDATE_FEED_FALLBACK_PATHS:
            push(urljoin(base, path))
    return urls


class _FeedAutodiscoveryParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "link":
            return
        attrs_map = {key.lower(): value for key, value in attrs}
        rel_value = (attrs_map.get("rel") or "").lower()
        type_value = (attrs_map.get("type") or "").lower()
        href_value = attrs_map.get("href")
        if "alternate" not in rel_value:
            return
        if "rss" not in type_value and "atom" not in type_value and "xml" not in type_value:
            return
        if not href_value:
            return
        self.links.append(href_value.strip())


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
        validated_candidates, validation_warnings, validation_warning_details = await self._validate_candidates(
            candidates=candidates,
            max_candidates=max_candidates,
        )
        for warning in validation_warnings:
            if warning not in warnings:
                warnings.append(warning)
        for warning_detail in validation_warning_details:
            warning_key = (warning_detail.code, warning_detail.provider, warning_detail.message)
            if warning_key in warning_detail_keys:
                continue
            warning_detail_keys.add(warning_key)
            warning_details.append(warning_detail)

        persisted_count, pending_count, resolved_existing_count = await self._persist_generated_recommendations(
            session=session,
            user_id=user_id,
            stream=stream,
            candidates=validated_candidates,
            query_variants=query_variants,
        )
        return DiscoveryGenerationResult(
            stream_id=stream.id,
            provider_chain=runtime_config.provider_chain,
            query_variants=query_variants,
            candidates=validated_candidates,
            warnings=warnings,
            warning_details=warning_details,
            persisted_count=persisted_count,
            pending_count=pending_count,
            resolved_existing_count=resolved_existing_count,
        )

    async def list_recommendations(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        status_filter: Literal["pending", "accepted", "denied", "resolved_existing"] | None,
        q: str | None,
        sort_by: Literal["created_at", "updated_at", "last_seen_at", "decided_at", "confidence", "feed_title", "status"],
        sort_direction: Literal["asc", "desc"],
        limit: int,
        offset: int,
    ) -> tuple[list[FeedRecommendation], int, dict[UUID, list[FeedRecommendationSourceOut]]]:
        where_clauses = [FeedRecommendation.user_id == user_id]
        if status_filter is not None:
            where_clauses.append(FeedRecommendation.status == status_filter)
        normalized_q = (q or "").strip().lower()
        if normalized_q:
            pattern = f"%{normalized_q}%"
            where_clauses.append(
                or_(
                    func.lower(FeedRecommendation.feed_title).like(pattern),
                    func.lower(FeedRecommendation.feed_url).like(pattern),
                    func.lower(FeedRecommendation.site_url).like(pattern),
                )
            )

        total_query = select(func.count()).select_from(select(FeedRecommendation.id).where(*where_clauses).subquery())
        total = int((await session.execute(total_query)).scalar_one() or 0)

        sort_columns: dict[
            Literal["created_at", "updated_at", "last_seen_at", "decided_at", "confidence", "feed_title", "status"],
            Any,
        ] = {
            "created_at": FeedRecommendation.created_at,
            "updated_at": FeedRecommendation.updated_at,
            "last_seen_at": FeedRecommendation.last_seen_at,
            "decided_at": FeedRecommendation.decided_at,
            "confidence": FeedRecommendation.confidence,
            "feed_title": FeedRecommendation.feed_title,
            "status": FeedRecommendation.status,
        }
        sort_column = sort_columns[sort_by]
        primary_order = asc(sort_column) if sort_direction == "asc" else desc(sort_column)
        secondary_order = desc(FeedRecommendation.created_at)

        rows_query = (
            select(FeedRecommendation)
            .where(*where_clauses)
            .order_by(primary_order, secondary_order)
            .offset(offset)
            .limit(limit)
        )
        rows_result = await session.execute(rows_query)
        recommendations = list(rows_result.scalars().all())
        recommendation_ids = [recommendation.id for recommendation in recommendations]
        sources_by_recommendation = await self.load_sources_by_recommendation(
            session=session,
            recommendation_ids=recommendation_ids,
        )
        return recommendations, total, sources_by_recommendation

    async def decide_recommendation(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        recommendation_id: UUID,
        decision: Literal["accept", "deny"],
    ) -> FeedRecommendation:
        recommendation = await self.get_recommendation(
            session=session,
            user_id=user_id,
            recommendation_id=recommendation_id,
        )
        if recommendation is None:
            raise DiscoveryRecommendationNotFoundError(f"Recommendation {recommendation_id} not found")

        now = datetime.now(UTC)
        if decision == "deny":
            if recommendation.status != "pending":
                if recommendation.status == "denied":
                    raise DiscoveryRecommendationValidationError("Recommendation is already denied")
                raise DiscoveryRecommendationValidationError("Only pending recommendations can be denied")
            recommendation.status = "denied"
            recommendation.decided_at = now
            recommendation.accepted_feed_id = None
            recommendation.last_seen_at = now
            await session.commit()
            await session.refresh(recommendation)
            return recommendation

        if recommendation.status != "pending":
            if recommendation.status == "denied":
                raise DiscoveryRecommendationValidationError("Denied recommendation must be reset before accepting")
            if recommendation.status == "accepted":
                raise DiscoveryRecommendationValidationError("Recommendation is already accepted")
            if recommendation.status == "resolved_existing":
                raise DiscoveryRecommendationValidationError("Recommendation already resolved to an existing feed")
            raise DiscoveryRecommendationValidationError("Only pending recommendations can be accepted")

        existing_feed = await self._find_existing_user_feed_for_recommendation(
            session=session,
            user_id=user_id,
            recommendation=recommendation,
        )
        if existing_feed is not None:
            recommendation.status = "resolved_existing"
            recommendation.accepted_feed_id = existing_feed.id
            recommendation.decided_at = now
            recommendation.last_seen_at = now
            await session.commit()
            await session.refresh(recommendation)
            return recommendation

        try:
            payload = FeedCreate.model_validate(
                {
                    "title": (recommendation.feed_title or _fallback_feed_title(recommendation.feed_url)).strip(),
                    "url": recommendation.feed_url,
                    "site_url": recommendation.site_url,
                }
            )
        except ValidationError as exc:
            raise DiscoveryRecommendationValidationError("Recommendation URL is invalid and cannot be accepted") from exc

        try:
            created_feed = await feed_service.create_feed(session=session, data=payload, user_id=user_id)
        except FeedAlreadyExistsError as exc:
            existing_feed = await self._find_existing_user_feed_for_recommendation(
                session=session,
                user_id=user_id,
                recommendation=recommendation,
            )
            if existing_feed is None:
                raise DiscoveryRecommendationValidationError(
                    "Feed URL already exists globally and is unavailable for this user"
                ) from exc
            recommendation.status = "resolved_existing"
            recommendation.accepted_feed_id = existing_feed.id
            recommendation.decided_at = now
            recommendation.last_seen_at = now
            await session.commit()
            await session.refresh(recommendation)
            return recommendation

        recommendation.status = "accepted"
        recommendation.accepted_feed_id = created_feed.id
        recommendation.decided_at = now
        recommendation.last_seen_at = now
        await session.commit()
        await session.refresh(recommendation)
        return recommendation

    async def reset_recommendation(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> FeedRecommendation:
        recommendation = await self.get_recommendation(
            session=session,
            user_id=user_id,
            recommendation_id=recommendation_id,
        )
        if recommendation is None:
            raise DiscoveryRecommendationNotFoundError(f"Recommendation {recommendation_id} not found")
        if recommendation.status != "denied":
            raise DiscoveryRecommendationValidationError("Only denied recommendations can be reset")
        recommendation.status = "pending"
        recommendation.decided_at = None
        recommendation.accepted_feed_id = None
        recommendation.last_seen_at = datetime.now(UTC)
        await session.commit()
        await session.refresh(recommendation)
        return recommendation

    async def recommendation_summary(self, *, session: AsyncSession, user_id: UUID) -> dict[str, int]:
        query = (
            select(FeedRecommendation.status, func.count())
            .where(FeedRecommendation.user_id == user_id)
            .group_by(FeedRecommendation.status)
        )
        result = await session.execute(query)
        counts = {status: int(count) for status, count in result.all() if isinstance(status, str)}
        pending_count = counts.get("pending", 0)
        denied_count = counts.get("denied", 0)
        accepted_count = counts.get("accepted", 0)
        resolved_existing_count = counts.get("resolved_existing", 0)
        total_count = pending_count + denied_count + accepted_count + resolved_existing_count
        return {
            "pending_count": pending_count,
            "denied_count": denied_count,
            "accepted_count": accepted_count,
            "resolved_existing_count": resolved_existing_count,
            "total_count": total_count,
        }

    async def get_recommendation(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        recommendation_id: UUID,
    ) -> FeedRecommendation | None:
        query = select(FeedRecommendation).where(
            FeedRecommendation.id == recommendation_id,
            FeedRecommendation.user_id == user_id,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def _persist_generated_recommendations(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        stream: DiscoveryStream,
        candidates: list[SearchFeedCandidate],
        query_variants: list[str],
    ) -> tuple[int, int, int]:
        if not candidates:
            return 0, 0, 0

        now = datetime.now(UTC)
        user_feeds_by_normalized = await self._load_user_feed_map(session=session, user_id=user_id)

        candidate_by_normalized: dict[str, SearchFeedCandidate] = {}
        for candidate in candidates:
            normalized_url = _normalize_recommendation_url(candidate.url)
            candidate_by_normalized[normalized_url] = candidate

        normalized_urls = list(candidate_by_normalized.keys())
        existing_query = select(FeedRecommendation).where(
            FeedRecommendation.user_id == user_id,
            FeedRecommendation.feed_url_normalized.in_(normalized_urls),
        )
        existing_result = await session.execute(existing_query)
        existing_by_normalized = {
            recommendation.feed_url_normalized: recommendation for recommendation in existing_result.scalars().all()
        }

        touched_recommendations: list[FeedRecommendation] = []
        for normalized_url, candidate in candidate_by_normalized.items():
            existing_feed = user_feeds_by_normalized.get(normalized_url)
            recommendation = existing_by_normalized.get(normalized_url)
            recommendation_evidence = {
                "query_variants": query_variants,
                "description": candidate.description,
                "provider": candidate.provider,
            }

            if recommendation is None:
                status: Literal["pending", "resolved_existing"] = (
                    "resolved_existing" if existing_feed is not None else "pending"
                )
                recommendation = FeedRecommendation(
                    user_id=user_id,
                    status=status,
                    feed_url=candidate.url,
                    feed_url_normalized=normalized_url,
                    feed_title=_normalize_optional_text(candidate.title),
                    site_url=_normalize_optional_text(candidate.site_url),
                    confidence=None,
                    provider=candidate.provider,
                    evidence_json=_to_json_payload(recommendation_evidence),
                    accepted_feed_id=existing_feed.id if existing_feed is not None else None,
                    decided_at=now if existing_feed is not None else None,
                    last_seen_at=now,
                )
                session.add(recommendation)
                touched_recommendations.append(recommendation)
                continue

            recommendation.feed_url = candidate.url
            recommendation.feed_title = _normalize_optional_text(candidate.title) or recommendation.feed_title
            recommendation.site_url = _normalize_optional_text(candidate.site_url) or recommendation.site_url
            recommendation.provider = candidate.provider
            recommendation.evidence_json = _to_json_payload(recommendation_evidence)
            recommendation.last_seen_at = now
            if existing_feed is not None:
                recommendation.status = "resolved_existing"
                recommendation.accepted_feed_id = existing_feed.id
                recommendation.decided_at = now
            elif recommendation.status == "resolved_existing":
                recommendation.status = "pending"
                recommendation.accepted_feed_id = None
                recommendation.decided_at = None
            if recommendation.status not in _RECOMMENDATION_STATUS_VALUES:
                recommendation.status = "pending"
            touched_recommendations.append(recommendation)

        await session.flush()
        await self._upsert_generation_sources(
            session=session,
            stream=stream,
            recommendations=touched_recommendations,
            query_variants=query_variants,
        )
        await session.commit()

        persisted_count = len(touched_recommendations)
        pending_count = sum(1 for recommendation in touched_recommendations if recommendation.status == "pending")
        resolved_existing_count = sum(
            1 for recommendation in touched_recommendations if recommendation.status == "resolved_existing"
        )
        return persisted_count, pending_count, resolved_existing_count

    async def _upsert_generation_sources(
        self,
        *,
        session: AsyncSession,
        stream: DiscoveryStream,
        recommendations: list[FeedRecommendation],
        query_variants: list[str],
    ) -> None:
        if not recommendations:
            return

        recommendation_ids = [recommendation.id for recommendation in recommendations]
        existing_source_query = select(FeedRecommendationSource).where(
            FeedRecommendationSource.discovery_stream_id == stream.id,
            FeedRecommendationSource.recommendation_id.in_(recommendation_ids),
        )
        existing_source_result = await session.execute(existing_source_query)
        existing_sources = {source.recommendation_id: source for source in existing_source_result.scalars().all()}
        source_evidence = _to_json_payload({"query_variants": query_variants, "stream_name": stream.name})

        for recommendation in recommendations:
            source = existing_sources.get(recommendation.id)
            if source is None:
                session.add(
                    FeedRecommendationSource(
                        recommendation_id=recommendation.id,
                        discovery_stream_id=stream.id,
                        provider_confidence=recommendation.confidence,
                        evidence_json=source_evidence,
                    )
                )
                continue
            source.provider_confidence = recommendation.confidence
            source.evidence_json = source_evidence

        await session.flush()

    async def _load_user_feed_map(self, *, session: AsyncSession, user_id: UUID) -> dict[str, Feed]:
        query = select(Feed).where(Feed.owner_id == user_id)
        result = await session.execute(query)
        feeds = list(result.scalars().all())
        by_normalized_url: dict[str, Feed] = {}
        for feed in feeds:
            normalized_url = _normalize_recommendation_url(feed.url)
            if normalized_url not in by_normalized_url:
                by_normalized_url[normalized_url] = feed
        return by_normalized_url

    async def _find_existing_user_feed_for_recommendation(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        recommendation: FeedRecommendation,
    ) -> Feed | None:
        user_feeds_by_normalized = await self._load_user_feed_map(session=session, user_id=user_id)
        return user_feeds_by_normalized.get(recommendation.feed_url_normalized)

    async def load_sources_by_recommendation(
        self,
        *,
        session: AsyncSession,
        recommendation_ids: list[UUID],
    ) -> dict[UUID, list[FeedRecommendationSourceOut]]:
        if not recommendation_ids:
            return {}
        query = (
            select(FeedRecommendationSource, DiscoveryStream.name)
            .outerjoin(DiscoveryStream, DiscoveryStream.id == FeedRecommendationSource.discovery_stream_id)
            .where(FeedRecommendationSource.recommendation_id.in_(recommendation_ids))
            .order_by(FeedRecommendationSource.created_at.asc())
        )
        result = await session.execute(query)
        by_recommendation_id: dict[UUID, list[FeedRecommendationSourceOut]] = {}
        for source, stream_name in result.all():
            item = FeedRecommendationSourceOut(
                id=source.id,
                recommendation_id=source.recommendation_id,
                discovery_stream_id=source.discovery_stream_id,
                discovery_stream_name=str(stream_name) if isinstance(stream_name, str) else None,
                provider_confidence=source.provider_confidence,
                evidence=_from_json_payload(source.evidence_json),
                created_at=source.created_at,
            )
            by_recommendation_id.setdefault(source.recommendation_id, []).append(item)
        return by_recommendation_id

    async def _validate_candidates(
        self,
        *,
        candidates: list[SearchFeedCandidate],
        max_candidates: int,
    ) -> tuple[list[SearchFeedCandidate], list[str], list[SearchWarning]]:
        if not candidates:
            return [], [], []

        warnings: list[str] = []
        warning_details: list[SearchWarning] = []
        validated: list[SearchFeedCandidate] = []
        seen_urls: set[str] = set()
        validation_limit = min(max_candidates, _MAX_VALIDATION_CANDIDATES)
        targets = candidates[:validation_limit]

        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            for candidate in targets:
                resolved_feed_url = await self._resolve_feed_endpoint_for_candidate(client=client, candidate=candidate)
                if resolved_feed_url is None:
                    message = f"no valid feed endpoint found for {candidate.url}"
                    warnings.append(message)
                    warning_details.append(
                        SearchWarning(
                            code="invalid_candidate_feed_endpoint",
                            provider=candidate.provider,
                            message=message,
                        )
                    )
                    continue

                normalized_url = _normalize_candidate_url(resolved_feed_url)
                if normalized_url is None or normalized_url in seen_urls:
                    continue
                seen_urls.add(normalized_url)
                validated.append(
                    SearchFeedCandidate(
                        title=candidate.title,
                        url=normalized_url,
                        site_url=_normalize_candidate_url(candidate.site_url),
                        description=candidate.description,
                        provider=candidate.provider,
                    )
                )

        skipped_count = max(0, len(candidates) - len(targets))
        if skipped_count > 0:
            message = f"candidate validation skipped for {skipped_count} candidates due to validation cap"
            warnings.append(message)
            warning_details.append(
                SearchWarning(
                    code="candidate_validation_skipped",
                    provider=None,
                    message=message,
                )
            )

        return validated, warnings, warning_details

    async def _resolve_feed_endpoint_for_candidate(
        self,
        *,
        client: httpx.AsyncClient,
        candidate: SearchFeedCandidate,
    ) -> str | None:
        urls = _candidate_validation_urls(feed_url=candidate.url, site_url=candidate.site_url)
        for url in urls:
            if await self._is_valid_feed_endpoint(client=client, url=url):
                return url

            discovered_urls = await self._discover_feed_links_from_html(client=client, url=url)
            for discovered_url in discovered_urls:
                if await self._is_valid_feed_endpoint(client=client, url=discovered_url):
                    return discovered_url
        return None

    async def _is_valid_feed_endpoint(self, *, client: httpx.AsyncClient, url: str) -> bool:
        try:
            response = await client.get(url)
        except httpx.HTTPError:
            return False
        if response.status_code != 200:
            return False
        parsed = feedparser.parse(response.content)
        entries = getattr(parsed, "entries", [])
        if isinstance(entries, list) and len(entries) > 0:
            return True
        feed_meta = getattr(parsed, "feed", None)
        if isinstance(feed_meta, dict):
            title = str(feed_meta.get("title", "")).strip()
            if title and getattr(parsed, "version", ""):
                return True
        return False

    async def _discover_feed_links_from_html(self, *, client: httpx.AsyncClient, url: str) -> list[str]:
        try:
            response = await client.get(url)
        except httpx.HTTPError:
            return []
        if response.status_code != 200:
            return []

        content_type = (response.headers.get("content-type") or "").lower()
        is_html_like = "html" in content_type or response.text.lstrip().lower().startswith("<!doctype html")
        if not is_html_like:
            return []

        parser = _FeedAutodiscoveryParser()
        try:
            parser.feed(response.text)
        except Exception:  # noqa: BLE001
            return []

        links: list[str] = []
        seen: set[str] = set()
        for href in parser.links:
            normalized = _normalize_candidate_url(urljoin(url, href))
            if normalized is None or normalized in seen:
                continue
            seen.add(normalized)
            links.append(normalized)
        return links

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

    def recommendation_to_out(
        self,
        recommendation: FeedRecommendation,
        *,
        sources: list[FeedRecommendationSourceOut] | None = None,
    ) -> FeedRecommendationOut:
        status_value = recommendation.status if recommendation.status in _RECOMMENDATION_STATUS_VALUES else "pending"
        return FeedRecommendationOut(
            id=recommendation.id,
            user_id=recommendation.user_id,
            status=cast(Literal["pending", "accepted", "denied", "resolved_existing"], status_value),
            feed_url=recommendation.feed_url,
            feed_url_normalized=recommendation.feed_url_normalized,
            feed_title=recommendation.feed_title,
            site_url=recommendation.site_url,
            confidence=recommendation.confidence,
            provider=recommendation.provider,
            evidence=_from_json_payload(recommendation.evidence_json),
            accepted_feed_id=recommendation.accepted_feed_id,
            decided_at=recommendation.decided_at,
            last_seen_at=recommendation.last_seen_at,
            created_at=recommendation.created_at,
            updated_at=recommendation.updated_at,
            sources=sources or [],
        )


discovery_service = DiscoveryService()
