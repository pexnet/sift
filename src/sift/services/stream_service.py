import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, Feed, KeywordStream, KeywordStreamMatch, RawEntry
from sift.domain.schemas import (
    ArticleOut,
    KeywordStreamCreate,
    KeywordStreamOut,
    KeywordStreamUpdate,
    StreamArticleOut,
    StreamBackfillResultOut,
)
from sift.plugins.base import ArticleContext, StreamClassifierContext
from sift.plugins.manager import PluginManager
from sift.search.query_language import ParsedSearchQuery, SearchQuerySyntaxError, parse_search_query


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
    classifier_min_confidence: float


@dataclass(slots=True)
class StreamMatchDecision:
    stream_id: UUID
    reason: str | None


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
        classifier_min_confidence=stream.classifier_min_confidence,
    )


def stream_matches(
    stream: CompiledKeywordStream,
    *,
    title: str,
    content_text: str,
    source_url: str | None,
    language: str | None,
) -> bool:
    return stream_match_reason(
        stream,
        title=title,
        content_text=content_text,
        source_url=source_url,
        language=language,
    ) is not None


def stream_match_reason(
    stream: CompiledKeywordStream,
    *,
    title: str,
    content_text: str,
    source_url: str | None,
    language: str | None,
) -> str | None:
    payload_raw = f"{title}\n{content_text}"
    payload = payload_raw.lower()
    source = (source_url or "").lower()
    normalized_language = (language or "").lower()
    reason: str | None = None

    if stream.match_query and not stream.match_query.matches(
        title=title,
        content_text=content_text,
        source_text=source_url,
    ):
        return None
    if stream.match_query:
        reason = "query matched"

    matched_keyword = next((keyword for keyword in stream.include_keywords if keyword in payload), None)
    if stream.include_keywords and matched_keyword is None:
        return None
    if matched_keyword and reason is None:
        reason = f"keyword: {matched_keyword}"

    matched_regex = next((pattern for pattern in stream.include_regex if pattern.search(payload_raw)), None)
    if stream.include_regex and matched_regex is None:
        return None
    if matched_regex and reason is None:
        reason = f"regex: {matched_regex.pattern}"

    blocked_keyword = next((keyword for keyword in stream.exclude_keywords if keyword in payload), None)
    if blocked_keyword is not None:
        return None

    blocked_regex = next((pattern for pattern in stream.exclude_regex if pattern.search(payload_raw)), None)
    if blocked_regex is not None:
        return None

    if stream.source_contains and stream.source_contains not in source:
        return None
    if stream.source_contains and reason is None:
        reason = f"source: {stream.source_contains}"

    if stream.language_equals and stream.language_equals != normalized_language:
        return None
    if stream.language_equals and reason is None:
        reason = f"language: {stream.language_equals}"

    return reason or "rules matched"


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
                    article=ArticleOut.model_validate(article),
                )
            )
        return matches

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
        for article_id, title, content_text, language, source_url in article_rows:
            matching_decisions = await self.collect_matching_stream_decisions(
                [compiled_stream],
                title=title,
                content_text=content_text,
                source_url=source_url,
                language=language,
                plugin_manager=plugin_manager,
            )
            if matching_decisions:
                matched_rows.extend(self.make_match_rows(matching_decisions, article_id))

        previous_count_result = await session.execute(
            select(func.count())
            .select_from(KeywordStreamMatch)
            .where(KeywordStreamMatch.stream_id == stream_id)
        )
        previous_match_count = int(previous_count_result.scalar_one() or 0)

        await session.execute(delete(KeywordStreamMatch).where(KeywordStreamMatch.stream_id == stream_id))
        session.add_all(matched_rows)
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
        decisions = await self.collect_matching_stream_decisions(
            streams,
            title=title,
            content_text=content_text,
            source_url=source_url,
            language=language,
            plugin_manager=plugin_manager,
        )
        return [decision.stream_id for decision in decisions]

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
        matches: list[StreamMatchDecision] = []
        article_context = ArticleContext(
            article_id="",
            title=title,
            content_text=content_text,
            metadata={"source_url": source_url or "", "language": language or ""},
        )
        for stream in streams:
            rules_reason = stream_match_reason(
                stream,
                title=title,
                content_text=content_text,
                source_url=source_url,
                language=language,
            )
            rules_match = rules_reason is not None

            classifier_match = False
            classifier_reason: str | None = None
            if stream.classifier_mode in {"classifier_only", "hybrid"} and stream.classifier_plugin:
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
                        metadata={"source_url": source_url or "", "language": language or ""},
                    ),
                )
                classifier_match = bool(
                    decision
                    and decision.matched
                    and decision.confidence >= stream.classifier_min_confidence
                )
                if classifier_match and decision:
                    if decision.reason.strip():
                        classifier_reason = f"classifier: {decision.reason.strip()}"
                    else:
                        classifier_reason = (
                            f"classifier confidence {decision.confidence:.2f} ({stream.classifier_plugin})"
                        )

            final_match = False
            final_reason: str | None = None
            if stream.classifier_mode == "rules_only":
                final_match = rules_match
                final_reason = rules_reason
            elif stream.classifier_mode == "classifier_only":
                final_match = classifier_match
                final_reason = classifier_reason
            elif stream.classifier_mode == "hybrid":
                final_match = rules_match or classifier_match
                final_reason = rules_reason or classifier_reason

            if final_match:
                matches.append(StreamMatchDecision(stream_id=stream.id, reason=final_reason or "matched"))
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
            else:
                stream_id = item.stream_id
                reason = item.reason
            rows.append(
                KeywordStreamMatch(
                    stream_id=stream_id,
                    article_id=article_id,
                    matched_at=now,
                    match_reason=reason,
                )
            )
        return rows


stream_service = StreamService()
