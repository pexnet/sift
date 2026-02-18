import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Literal, cast
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, Feed, KeywordStream, KeywordStreamMatch, RawEntry, StreamClassifierRun
from sift.domain.schemas import (
    ArticleOut,
    KeywordStreamCreate,
    KeywordStreamOut,
    KeywordStreamUpdate,
    StreamArticleOut,
    StreamBackfillResultOut,
    StreamClassifierRunOut,
)
from sift.plugins.base import ArticleContext, StreamClassifierContext
from sift.plugins.manager import PluginManager
from sift.search.query_language import ParsedSearchQuery, SearchQueryHit, SearchQuerySyntaxError, parse_search_query


class StreamConflictError(Exception):
    pass


class StreamValidationError(Exception):
    pass


class StreamNotFoundError(Exception):
    pass


@dataclass(slots=True)
class CompiledKeywordStream:
    id: UUID
    name: str
    priority: int
    match_query: ParsedSearchQuery | None
    include_keywords: list[str]
    exclude_keywords: list[str]
    include_regex: list[re.Pattern[str]]
    exclude_regex: list[re.Pattern[str]]
    source_contains: str | None
    language_equals: str | None
    classifier_mode: Literal["rules_only", "classifier_only", "hybrid"]
    classifier_plugin: str | None
    classifier_config: dict[str, Any]
    classifier_min_confidence: float


@dataclass(slots=True)
class StreamMatchDecision:
    stream_id: UUID
    reason: str | None
    evidence: dict[str, Any] | None = None


@dataclass(slots=True)
class StreamClassifierRunDecision:
    stream_id: UUID
    classifier_mode: Literal["classifier_only", "hybrid"]
    plugin_name: str
    provider: str | None
    model_name: str | None
    model_version: str | None
    matched: bool
    confidence: float | None
    threshold: float
    reason: str | None
    run_status: Literal["ok", "no_decision"]
    error_message: str | None
    duration_ms: int | None


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


def _normalize_regex_patterns(patterns: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for pattern in patterns:
        item = pattern.strip()
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def _regex_to_json(patterns: list[str]) -> str:
    return json.dumps(_normalize_regex_patterns(patterns))


def _regex_from_json(raw: str) -> list[str]:
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return []
    if not isinstance(loaded, list):
        return []
    return _normalize_regex_patterns([str(item) for item in loaded])


def _compile_regex_patterns(patterns: list[str], *, field_label: str) -> list[re.Pattern[str]]:
    compiled: list[re.Pattern[str]] = []
    for pattern in patterns:
        try:
            compiled.append(re.compile(pattern, flags=re.IGNORECASE))
        except re.error as exc:
            raise StreamValidationError(f"Invalid {field_label} regex '{pattern}': {exc}") from exc
    return compiled


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_optional_lower(value: str | None) -> str | None:
    normalized = _normalize_optional_text(value)
    return normalized.lower() if normalized else None


def _classifier_config_to_json(value: dict[str, Any]) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _classifier_config_from_json(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StreamValidationError("Invalid persisted classifier_config payload") from exc
    if not isinstance(loaded, dict):
        raise StreamValidationError("Invalid persisted classifier_config payload")
    return loaded


def _normalize_classifier_config(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise StreamValidationError("classifier_config must be a JSON object")
    try:
        encoded = _classifier_config_to_json(value)
    except (TypeError, ValueError) as exc:
        raise StreamValidationError("classifier_config must be JSON serializable") from exc
    if len(encoded) > 5000:
        raise StreamValidationError("classifier_config is too large (max 5000 chars)")
    return value


def _match_evidence_to_json(value: dict[str, Any] | None) -> str | None:
    if value is None:
        return None
    return json.dumps(value, separators=(",", ":"), sort_keys=True)


def _match_evidence_from_json(raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(loaded, dict):
        return None
    return loaded


def _normalize_classifier_findings(findings: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not findings:
        return []
    normalized: list[dict[str, Any]] = []
    for raw_finding in findings:
        if not isinstance(raw_finding, dict):
            continue
        finding: dict[str, Any] = {}

        label = raw_finding.get("label")
        if isinstance(label, str) and label.strip():
            finding["label"] = label.strip()

        text = raw_finding.get("text")
        if isinstance(text, str) and text.strip():
            finding["text"] = text.strip()
        else:
            snippet = raw_finding.get("snippet")
            if isinstance(snippet, str) and snippet.strip():
                finding["text"] = snippet.strip()

        value = raw_finding.get("value")
        if isinstance(value, str) and value.strip():
            finding["value"] = value.strip()

        source = raw_finding.get("source")
        if isinstance(source, str) and source.strip():
            finding["source"] = source.strip()

        field = raw_finding.get("field")
        if isinstance(field, str) and field.strip():
            finding["field"] = field.strip()

        score_value = raw_finding.get("score")
        if isinstance(score_value, (int, float)) and not isinstance(score_value, bool):
            score = float(score_value)
            if math.isfinite(score):
                finding["score"] = round(score, 4)

        start_value = raw_finding.get("start")
        end_value = raw_finding.get("end")
        if isinstance(start_value, int) and isinstance(end_value, int) and end_value > start_value:
            finding["start"] = start_value
            finding["end"] = end_value
            offset_basis = raw_finding.get("offset_basis")
            if isinstance(offset_basis, str) and offset_basis.strip():
                finding["offset_basis"] = offset_basis.strip()
            else:
                finding["offset_basis"] = "field_text_v1"

        if finding:
            normalized.append(finding)
    return normalized


def _classifier_finding_reason(findings: list[dict[str, Any]]) -> str | None:
    if not findings:
        return None
    first = findings[0]
    label = first.get("label")
    text = first.get("text")
    value = first.get("value")
    score = first.get("score")
    if isinstance(label, str) and isinstance(text, str):
        return f"{label}: {text}"
    if isinstance(text, str):
        return text
    if isinstance(label, str) and isinstance(value, str):
        return f'{label}: "{value}"'
    if isinstance(value, str):
        return value
    if isinstance(label, str):
        return label
    if isinstance(score, (int, float)):
        return f"finding score {float(score):.2f}"
    return None


def _normalize_classifier_mode(value: str) -> Literal["rules_only", "classifier_only", "hybrid"]:
    mode = value.strip().lower()
    if mode in {"rules_only", "classifier_only", "hybrid"}:
        return cast(Literal["rules_only", "classifier_only", "hybrid"], mode)
    raise StreamValidationError("Invalid classifier mode")


def _validate_criteria(
    include_keywords: list[str],
    include_regex: list[str],
    match_query: str | None,
    source_contains: str | None,
    language_equals: str | None,
    *,
    classifier_mode: str,
    classifier_plugin: str | None,
) -> None:
    normalized_mode = _normalize_classifier_mode(classifier_mode)

    if normalized_mode in {"classifier_only", "hybrid"} and not classifier_plugin:
        raise StreamValidationError("classifier_plugin is required when classifier mode is enabled")

    if include_keywords:
        return
    if include_regex:
        return
    if match_query:
        return
    if source_contains:
        return
    if language_equals:
        return
    if normalized_mode in {"classifier_only", "hybrid"} and classifier_plugin:
        return
    raise StreamValidationError(
        "A stream needs at least one positive criterion (query, include keyword, include regex, source, or language)"
    )


def compile_stream(stream: KeywordStream) -> CompiledKeywordStream:
    compiled_query: ParsedSearchQuery | None = None
    if stream.match_query:
        compiled_query = parse_search_query(stream.match_query)
    include_regex = _compile_regex_patterns(_regex_from_json(stream.include_regex_json), field_label="include")
    exclude_regex = _compile_regex_patterns(_regex_from_json(stream.exclude_regex_json), field_label="exclude")
    return CompiledKeywordStream(
        id=stream.id,
        name=stream.name,
        priority=stream.priority,
        match_query=compiled_query,
        include_keywords=_keywords_from_json(stream.include_keywords_json),
        exclude_keywords=_keywords_from_json(stream.exclude_keywords_json),
        include_regex=include_regex,
        exclude_regex=exclude_regex,
        source_contains=_normalize_optional_lower(stream.source_contains),
        language_equals=_normalize_optional_lower(stream.language_equals),
        classifier_mode=_normalize_classifier_mode(stream.classifier_mode),
        classifier_plugin=stream.classifier_plugin,
        classifier_config=_classifier_config_from_json(stream.classifier_config_json),
        classifier_min_confidence=stream.classifier_min_confidence,
    )


def _build_snippet(text: str, *, start: int, end: int, radius: int = 48) -> str:
    snippet_start = max(0, start - radius)
    snippet_end = min(len(text), end + radius)
    snippet = text[snippet_start:snippet_end].strip()
    if snippet_start > 0:
        snippet = f"...{snippet}"
    if snippet_end < len(text):
        snippet = f"{snippet}..."
    return snippet


def _query_hit_to_evidence(hit: SearchQueryHit, *, title: str, content_text: str) -> dict[str, Any]:
    field_text = title if hit.field == "title" else content_text
    query_hit: dict[str, Any] = {
        "field": hit.field,
        "offset_basis": "field_text_v1",
        "token": hit.token,
        "start": hit.start,
        "end": hit.end,
        "snippet": _build_snippet(field_text, start=hit.start, end=hit.end),
    }
    if hit.operator_context:
        query_hit["operator_context"] = hit.operator_context
    return query_hit


def _find_keyword_hit(title: str, content_text: str, keyword: str) -> dict[str, Any] | None:
    keyword_lower = keyword.lower()

    title_index = title.lower().find(keyword_lower)
    if title_index >= 0:
        end = title_index + len(keyword)
        return {
            "field": "title",
            "offset_basis": "field_text_v1",
            "value": keyword,
            "start": title_index,
            "end": end,
            "snippet": _build_snippet(title, start=title_index, end=end),
        }

    content_index = content_text.lower().find(keyword_lower)
    if content_index >= 0:
        end = content_index + len(keyword)
        return {
            "field": "content_text",
            "offset_basis": "field_text_v1",
            "value": keyword,
            "start": content_index,
            "end": end,
            "snippet": _build_snippet(content_text, start=content_index, end=end),
        }

    return None


def _find_regex_hit(title: str, content_text: str, pattern: re.Pattern[str]) -> dict[str, Any] | None:
    title_match = pattern.search(title)
    if title_match:
        return {
            "field": "title",
            "offset_basis": "field_text_v1",
            "pattern": pattern.pattern,
            "value": title_match.group(0),
            "start": title_match.start(),
            "end": title_match.end(),
            "snippet": _build_snippet(title, start=title_match.start(), end=title_match.end()),
        }

    content_match = pattern.search(content_text)
    if content_match:
        return {
            "field": "content_text",
            "offset_basis": "field_text_v1",
            "pattern": pattern.pattern,
            "value": content_match.group(0),
            "start": content_match.start(),
            "end": content_match.end(),
            "snippet": _build_snippet(content_text, start=content_match.start(), end=content_match.end()),
        }

    return None


def stream_matches(
    stream: CompiledKeywordStream,
    *,
    title: str,
    content_text: str,
    source_url: str | None,
    language: str | None,
) -> bool:
    return stream_rule_match_outcome(
        stream,
        title=title,
        content_text=content_text,
        source_url=source_url,
        language=language,
    )[0] is not None


def stream_rule_match_outcome(
    stream: CompiledKeywordStream,
    *,
    title: str,
    content_text: str,
    source_url: str | None,
    language: str | None,
) -> tuple[str | None, dict[str, Any] | None]:
    payload_raw = f"{title}\n{content_text}"
    payload = payload_raw.lower()
    source = (source_url or "").lower()
    normalized_language = (language or "").lower()
    reason: str | None = None
    evidence: dict[str, Any] = {"matcher_type": "rules"}
    include_keyword_hits: list[dict[str, Any]] = []
    include_regex_hits: list[dict[str, Any]] = []
    query_hits: list[dict[str, Any]] = []

    if stream.match_query and not stream.match_query.matches(
        title=title,
        content_text=content_text,
        source_text=source_url,
    ):
        return None, None
    if stream.match_query:
        reason = "query matched"
        evidence["query"] = {"expression": True}
        query_hits = [
            _query_hit_to_evidence(hit, title=title, content_text=content_text)
            for hit in stream.match_query.matched_hits(
                title=title,
                content_text=content_text,
                source_text=source_url,
            )
        ]
        if query_hits:
            evidence["query_hits"] = query_hits

    for keyword in stream.include_keywords:
        if keyword in payload:
            hit = _find_keyword_hit(title, content_text, keyword)
            if hit:
                include_keyword_hits.append(hit)
    if stream.include_keywords and not include_keyword_hits:
        return None, None
    if include_keyword_hits:
        evidence["keyword_hits"] = include_keyword_hits
        if reason is None:
            reason = f"keyword: {include_keyword_hits[0]['value']}"

    for pattern in stream.include_regex:
        hit = _find_regex_hit(title, content_text, pattern)
        if hit:
            include_regex_hits.append(hit)
    if stream.include_regex and not include_regex_hits:
        return None, None
    if include_regex_hits:
        evidence["regex_hits"] = include_regex_hits
        if reason is None:
            reason = f"regex: {include_regex_hits[0]['pattern']}"

    blocked_keyword = next((keyword for keyword in stream.exclude_keywords if keyword in payload), None)
    if blocked_keyword is not None:
        return None, None

    blocked_regex = next((pattern for pattern in stream.exclude_regex if pattern.search(payload_raw)), None)
    if blocked_regex is not None:
        return None, None

    if stream.source_contains and stream.source_contains not in source:
        return None, None
    if stream.source_contains:
        evidence["source"] = {"contains": stream.source_contains}
        if reason is None:
            reason = f"source: {stream.source_contains}"

    if stream.language_equals and stream.language_equals != normalized_language:
        return None, None
    if stream.language_equals:
        evidence["language"] = {"equals": stream.language_equals}
        if reason is None:
            reason = f"language: {stream.language_equals}"

    if reason is None:
        return "rules matched", evidence
    return reason, evidence


def stream_match_reason(
    stream: CompiledKeywordStream,
    *,
    title: str,
    content_text: str,
    source_url: str | None,
    language: str | None,
) -> str | None:
    return stream_rule_match_outcome(
        stream,
        title=title,
        content_text=content_text,
        source_url=source_url,
        language=language,
    )[0]


class StreamService:
    async def list_streams(self, session: AsyncSession, user_id: UUID) -> list[KeywordStream]:
        query = select(KeywordStream).where(KeywordStream.user_id == user_id).order_by(
            KeywordStream.priority.asc(),
            KeywordStream.name.asc(),
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def list_active_compiled_streams(self, session: AsyncSession, user_id: UUID) -> list[CompiledKeywordStream]:
        query = (
            select(KeywordStream)
            .where(KeywordStream.user_id == user_id, KeywordStream.is_active.is_(True))
            .order_by(KeywordStream.priority.asc(), KeywordStream.name.asc())
        )
        result = await session.execute(query)
        return [compile_stream(stream) for stream in result.scalars().all()]

    async def create_stream(self, session: AsyncSession, user_id: UUID, payload: KeywordStreamCreate) -> KeywordStream:
        include_keywords = _normalize_keywords(payload.include_keywords)
        exclude_keywords = _normalize_keywords(payload.exclude_keywords)
        include_regex = _normalize_regex_patterns(payload.include_regex)
        exclude_regex = _normalize_regex_patterns(payload.exclude_regex)
        match_query = _normalize_optional_text(payload.match_query)
        source_contains = _normalize_optional_text(payload.source_contains)
        language_equals = _normalize_optional_lower(payload.language_equals)
        classifier_config = _normalize_classifier_config(payload.classifier_config)

        _compile_regex_patterns(include_regex, field_label="include")
        _compile_regex_patterns(exclude_regex, field_label="exclude")

        if match_query:
            try:
                parse_search_query(match_query)
            except SearchQuerySyntaxError as exc:
                raise StreamValidationError(str(exc)) from exc

        classifier_plugin = _normalize_optional_text(payload.classifier_plugin)
        _validate_criteria(
            include_keywords,
            include_regex,
            match_query,
            source_contains,
            language_equals,
            classifier_mode=payload.classifier_mode,
            classifier_plugin=classifier_plugin,
        )

        stream = KeywordStream(
            user_id=user_id,
            name=payload.name.strip(),
            description=_normalize_optional_text(payload.description),
            is_active=payload.is_active,
            priority=payload.priority,
            match_query=match_query,
            include_keywords_json=_keywords_to_json(include_keywords),
            exclude_keywords_json=_keywords_to_json(exclude_keywords),
            include_regex_json=_regex_to_json(include_regex),
            exclude_regex_json=_regex_to_json(exclude_regex),
            source_contains=source_contains,
            language_equals=language_equals,
            classifier_mode=_normalize_classifier_mode(payload.classifier_mode),
            classifier_plugin=classifier_plugin,
            classifier_config_json=_classifier_config_to_json(classifier_config),
            classifier_min_confidence=payload.classifier_min_confidence,
        )
        session.add(stream)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise StreamConflictError("Stream with the same name already exists") from exc

        await session.refresh(stream)
        return stream

    async def update_stream(
        self,
        session: AsyncSession,
        user_id: UUID,
        stream_id: UUID,
        payload: KeywordStreamUpdate,
    ) -> KeywordStream:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise StreamNotFoundError(f"Stream {stream_id} not found")

        if payload.name is not None:
            stream.name = payload.name.strip()
        if payload.description is not None:
            stream.description = _normalize_optional_text(payload.description)
        if payload.is_active is not None:
            stream.is_active = payload.is_active
        if payload.priority is not None:
            stream.priority = payload.priority
        if payload.match_query is not None:
            stream.match_query = _normalize_optional_text(payload.match_query)
        if payload.include_keywords is not None:
            stream.include_keywords_json = _keywords_to_json(payload.include_keywords)
        if payload.exclude_keywords is not None:
            stream.exclude_keywords_json = _keywords_to_json(payload.exclude_keywords)
        if payload.include_regex is not None:
            stream.include_regex_json = _regex_to_json(payload.include_regex)
        if payload.exclude_regex is not None:
            stream.exclude_regex_json = _regex_to_json(payload.exclude_regex)
        if payload.source_contains is not None:
            stream.source_contains = _normalize_optional_text(payload.source_contains)
        if payload.language_equals is not None:
            stream.language_equals = _normalize_optional_lower(payload.language_equals)
        if payload.classifier_mode is not None:
            stream.classifier_mode = _normalize_classifier_mode(payload.classifier_mode)
        if payload.classifier_plugin is not None:
            stream.classifier_plugin = _normalize_optional_text(payload.classifier_plugin)
        if payload.classifier_config is not None:
            stream.classifier_config_json = _classifier_config_to_json(
                _normalize_classifier_config(payload.classifier_config)
            )
        if payload.classifier_min_confidence is not None:
            stream.classifier_min_confidence = payload.classifier_min_confidence

        if stream.match_query:
            try:
                parse_search_query(stream.match_query)
            except SearchQuerySyntaxError as exc:
                raise StreamValidationError(str(exc)) from exc

        include_keywords = _keywords_from_json(stream.include_keywords_json)
        include_regex = _regex_from_json(stream.include_regex_json)
        exclude_regex = _regex_from_json(stream.exclude_regex_json)
        _compile_regex_patterns(include_regex, field_label="include")
        _compile_regex_patterns(exclude_regex, field_label="exclude")
        match_query = _normalize_optional_text(stream.match_query)
        source_contains = _normalize_optional_text(stream.source_contains)
        language_equals = _normalize_optional_lower(stream.language_equals)
        _validate_criteria(
            include_keywords,
            include_regex,
            match_query,
            source_contains,
            language_equals,
            classifier_mode=stream.classifier_mode,
            classifier_plugin=stream.classifier_plugin,
        )
        _normalize_classifier_config(_classifier_config_from_json(stream.classifier_config_json))

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise StreamConflictError("Stream with the same name already exists") from exc

        await session.refresh(stream)
        return stream

    async def delete_stream(self, session: AsyncSession, user_id: UUID, stream_id: UUID) -> None:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise StreamNotFoundError(f"Stream {stream_id} not found")

        await session.delete(stream)
        await session.commit()

    async def get_stream(self, session: AsyncSession, user_id: UUID, stream_id: UUID) -> KeywordStream | None:
        query = select(KeywordStream).where(KeywordStream.id == stream_id, KeywordStream.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()

    async def list_stream_articles(
        self,
        session: AsyncSession,
        user_id: UUID,
        stream_id: UUID,
        limit: int = 100,
    ) -> list[StreamArticleOut]:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise StreamNotFoundError(f"Stream {stream_id} not found")

        query = (
            select(KeywordStreamMatch, Article)
            .join(Article, Article.id == KeywordStreamMatch.article_id)
            .where(KeywordStreamMatch.stream_id == stream_id)
            .order_by(KeywordStreamMatch.matched_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)

        matches: list[StreamArticleOut] = []
        for match, article in result.all():
            matches.append(
                StreamArticleOut(
                    matched_at=match.matched_at,
                    match_reason=match.match_reason,
                    match_evidence=_match_evidence_from_json(match.match_evidence_json),
                    article=ArticleOut.model_validate(article),
                )
            )
        return matches

    async def list_stream_classifier_runs(
        self,
        session: AsyncSession,
        user_id: UUID,
        stream_id: UUID,
        limit: int = 100,
    ) -> list[StreamClassifierRunOut]:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise StreamNotFoundError(f"Stream {stream_id} not found")

        query = (
            select(StreamClassifierRun)
            .where(
                StreamClassifierRun.user_id == user_id,
                StreamClassifierRun.stream_id == stream_id,
            )
            .order_by(StreamClassifierRun.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(query)
        return [self.to_classifier_run_out(row) for row in result.scalars().all()]

    def to_classifier_run_out(self, run: StreamClassifierRun) -> StreamClassifierRunOut:
        return StreamClassifierRunOut(
            id=run.id,
            stream_id=run.stream_id,
            article_id=run.article_id,
            feed_id=run.feed_id,
            classifier_mode=cast(Literal["classifier_only", "hybrid"], run.classifier_mode),
            plugin_name=run.plugin_name,
            provider=run.provider,
            model_name=run.model_name,
            model_version=run.model_version,
            matched=run.matched,
            confidence=run.confidence,
            threshold=run.threshold,
            reason=run.reason,
            run_status=cast(Literal["ok", "no_decision"], run.run_status),
            error_message=run.error_message,
            duration_ms=run.duration_ms,
            created_at=run.created_at,
        )

    async def run_stream_backfill(
        self,
        session: AsyncSession,
        user_id: UUID,
        stream_id: UUID,
        *,
        plugin_manager: PluginManager,
    ) -> StreamBackfillResultOut:
        stream = await self.get_stream(session=session, user_id=user_id, stream_id=stream_id)
        if stream is None:
            raise StreamNotFoundError(f"Stream {stream_id} not found")

        try:
            compiled_stream = compile_stream(stream)
        except SearchQuerySyntaxError as exc:
            raise StreamValidationError(str(exc)) from exc

        article_rows_result = await session.execute(
            select(
                Article.id,
                Article.feed_id,
                Article.title,
                Article.content_text,
                Article.language,
                RawEntry.source_url,
            )
            .join(Feed, Feed.id == Article.feed_id)
            .outerjoin(
                RawEntry,
                and_(RawEntry.feed_id == Article.feed_id, RawEntry.source_id == Article.source_id),
            )
            .where(Feed.owner_id == user_id)
        )
        article_rows = article_rows_result.all()

        matched_rows: list[KeywordStreamMatch] = []
        classifier_run_rows: list[StreamClassifierRun] = []
        for article_id, feed_id, title, content_text, language, source_url in article_rows:
            matching_decisions, classifier_runs = await self.collect_matching_stream_decisions_with_classifier_runs(
                [compiled_stream],
                title=title,
                content_text=content_text,
                source_url=source_url,
                language=language,
                plugin_manager=plugin_manager,
            )
            if matching_decisions:
                matched_rows.extend(self.make_match_rows(matching_decisions, article_id))
            if classifier_runs:
                classifier_run_rows.extend(
                    self.make_classifier_run_rows(
                        classifier_runs,
                        user_id=user_id,
                        article_id=article_id,
                        feed_id=feed_id,
                    )
                )

        previous_count_result = await session.execute(
            select(func.count())
            .select_from(KeywordStreamMatch)
            .where(KeywordStreamMatch.stream_id == stream_id)
        )
        previous_match_count = int(previous_count_result.scalar_one() or 0)

        await session.execute(delete(KeywordStreamMatch).where(KeywordStreamMatch.stream_id == stream_id))
        session.add_all(matched_rows)
        session.add_all(classifier_run_rows)
        await session.commit()

        return StreamBackfillResultOut(
            stream_id=stream_id,
            scanned_count=len(article_rows),
            previous_match_count=previous_match_count,
            matched_count=len(matched_rows),
        )

    def to_out(self, stream: KeywordStream) -> KeywordStreamOut:
        return KeywordStreamOut(
            id=stream.id,
            user_id=stream.user_id,
            name=stream.name,
            description=stream.description,
            is_active=stream.is_active,
            priority=stream.priority,
            match_query=stream.match_query,
            include_keywords=_keywords_from_json(stream.include_keywords_json),
            exclude_keywords=_keywords_from_json(stream.exclude_keywords_json),
            include_regex=_regex_from_json(stream.include_regex_json),
            exclude_regex=_regex_from_json(stream.exclude_regex_json),
            source_contains=stream.source_contains,
            language_equals=stream.language_equals,
            classifier_mode=_normalize_classifier_mode(stream.classifier_mode),
            classifier_plugin=stream.classifier_plugin,
            classifier_config=_classifier_config_from_json(stream.classifier_config_json),
            classifier_min_confidence=stream.classifier_min_confidence,
            created_at=stream.created_at,
            updated_at=stream.updated_at,
        )

    async def collect_matching_stream_ids(
        self,
        streams: list[CompiledKeywordStream],
        *,
        title: str,
        content_text: str,
        source_url: str | None,
        language: str | None,
        plugin_manager: PluginManager,
    ) -> list[UUID]:
        decisions, _ = await self.collect_matching_stream_decisions_with_classifier_runs(
            streams,
            title=title,
            content_text=content_text,
            source_url=source_url,
            language=language,
            plugin_manager=plugin_manager,
        )
        return [decision.stream_id for decision in decisions]

    async def collect_matching_stream_decisions_with_classifier_runs(
        self,
        streams: list[CompiledKeywordStream],
        *,
        title: str,
        content_text: str,
        source_url: str | None,
        language: str | None,
        plugin_manager: PluginManager,
    ) -> tuple[list[StreamMatchDecision], list[StreamClassifierRunDecision]]:
        matches: list[StreamMatchDecision] = []
        classifier_runs: list[StreamClassifierRunDecision] = []
        article_context = ArticleContext(
            article_id="",
            title=title,
            content_text=content_text,
            metadata={"source_url": source_url or "", "language": language or ""},
        )
        for stream in streams:
            rules_reason, rules_evidence = stream_rule_match_outcome(
                stream,
                title=title,
                content_text=content_text,
                source_url=source_url,
                language=language,
            )
            rules_match = rules_reason is not None

            classifier_match = False
            classifier_reason: str | None = None
            classifier_evidence: dict[str, Any] | None = None
            if stream.classifier_mode in {"classifier_only", "hybrid"} and stream.classifier_plugin:
                start_time = perf_counter()
                decision = await plugin_manager.classify_stream(
                    plugin_name=stream.classifier_plugin,
                    article=article_context,
                    stream=StreamClassifierContext(
                        stream_id=str(stream.id),
                        stream_name=stream.name,
                        include_keywords=stream.include_keywords,
                        exclude_keywords=stream.exclude_keywords,
                        source_contains=stream.source_contains,
                        language_equals=stream.language_equals,
                        classifier_config=stream.classifier_config,
                        metadata={"source_url": source_url or "", "language": language or ""},
                    ),
                )
                duration_ms = int((perf_counter() - start_time) * 1000)
                confidence = decision.confidence if decision else None
                classifier_match = bool(
                    decision
                    and decision.matched
                    and decision.confidence >= stream.classifier_min_confidence
                )
                classifier_runs.append(
                    StreamClassifierRunDecision(
                        stream_id=stream.id,
                        classifier_mode=cast(Literal["classifier_only", "hybrid"], stream.classifier_mode),
                        plugin_name=stream.classifier_plugin,
                        provider=decision.provider if decision else None,
                        model_name=decision.model_name if decision else None,
                        model_version=decision.model_version if decision else None,
                        matched=classifier_match,
                        confidence=round(confidence, 4) if confidence is not None else None,
                        threshold=round(stream.classifier_min_confidence, 4),
                        reason=decision.reason.strip() if decision and decision.reason.strip() else None,
                        run_status="ok" if decision else "no_decision",
                        error_message=None,
                        duration_ms=duration_ms,
                    )
                )
                if classifier_match and decision:
                    normalized_findings = _normalize_classifier_findings(decision.findings)
                    classifier_evidence = {
                        "matcher_type": "classifier",
                        "plugin": stream.classifier_plugin,
                        "provider": decision.provider,
                        "model_name": decision.model_name,
                        "model_version": decision.model_version,
                        "confidence": round(decision.confidence, 4),
                        "threshold": round(stream.classifier_min_confidence, 4),
                    }
                    if decision.reason.strip():
                        classifier_reason = f"classifier: {decision.reason.strip()}"
                        classifier_evidence["reason"] = decision.reason.strip()
                        classifier_evidence["snippets"] = [{"text": decision.reason.strip()}]
                    elif normalized_findings:
                        finding_reason = _classifier_finding_reason(normalized_findings)
                        if finding_reason:
                            classifier_reason = f"classifier: {finding_reason}"
                    else:
                        classifier_reason = (
                            f"classifier confidence {decision.confidence:.2f} ({stream.classifier_plugin})"
                        )
                    if normalized_findings:
                        classifier_evidence["findings"] = normalized_findings
                        snippets = [
                            {"text": finding["text"]}
                            for finding in normalized_findings
                            if isinstance(finding.get("text"), str) and finding["text"]
                        ]
                        if snippets:
                            classifier_evidence["snippets"] = snippets[:5]

            final_match = False
            final_reason: str | None = None
            final_evidence: dict[str, Any] | None = None
            if stream.classifier_mode == "rules_only":
                final_match = rules_match
                final_reason = rules_reason
                final_evidence = rules_evidence
            elif stream.classifier_mode == "classifier_only":
                final_match = classifier_match
                final_reason = classifier_reason
                final_evidence = classifier_evidence
            elif stream.classifier_mode == "hybrid":
                final_match = rules_match or classifier_match
                final_reason = rules_reason or classifier_reason
                final_evidence = {
                    "matcher_type": "hybrid",
                    "rules": rules_evidence if rules_match else None,
                    "classifier": classifier_evidence if classifier_match else None,
                }

            if final_match:
                matches.append(
                    StreamMatchDecision(
                        stream_id=stream.id,
                        reason=final_reason or "matched",
                        evidence=final_evidence,
                    )
                )
        return matches, classifier_runs

    async def collect_matching_stream_decisions(
        self,
        streams: list[CompiledKeywordStream],
        *,
        title: str,
        content_text: str,
        source_url: str | None,
        language: str | None,
        plugin_manager: PluginManager,
    ) -> list[StreamMatchDecision]:
        matches, _ = await self.collect_matching_stream_decisions_with_classifier_runs(
            streams,
            title=title,
            content_text=content_text,
            source_url=source_url,
            language=language,
            plugin_manager=plugin_manager,
        )
        return matches

    def make_match_rows(
        self,
        stream_matches: list[UUID] | list[StreamMatchDecision],
        article_id: UUID,
    ) -> list[KeywordStreamMatch]:
        now = datetime.now(UTC)
        rows: list[KeywordStreamMatch] = []
        for item in stream_matches:
            if isinstance(item, UUID):
                stream_id = item
                reason = None
                evidence = None
            else:
                stream_id = item.stream_id
                reason = item.reason
                evidence = item.evidence
            rows.append(
                KeywordStreamMatch(
                    stream_id=stream_id,
                    article_id=article_id,
                    matched_at=now,
                    match_reason=reason,
                    match_evidence_json=_match_evidence_to_json(evidence),
                )
            )
        return rows

    def make_classifier_run_rows(
        self,
        classifier_runs: list[StreamClassifierRunDecision],
        *,
        user_id: UUID,
        article_id: UUID,
        feed_id: UUID | None,
    ) -> list[StreamClassifierRun]:
        return [
            StreamClassifierRun(
                user_id=user_id,
                stream_id=run.stream_id,
                article_id=article_id,
                feed_id=feed_id,
                classifier_mode=run.classifier_mode,
                plugin_name=run.plugin_name,
                provider=run.provider,
                model_name=run.model_name,
                model_version=run.model_version,
                matched=run.matched,
                confidence=run.confidence,
                threshold=run.threshold,
                reason=run.reason,
                run_status=run.run_status,
                error_message=run.error_message,
                duration_ms=run.duration_ms,
            )
            for run in classifier_runs
        ]


stream_service = StreamService()
