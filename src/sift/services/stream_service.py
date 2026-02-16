import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, KeywordStream, KeywordStreamMatch
from sift.domain.schemas import (
    ArticleOut,
    KeywordStreamCreate,
    KeywordStreamOut,
    KeywordStreamUpdate,
    StreamArticleOut,
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
    source_contains: str | None
    language_equals: str | None
    classifier_mode: Literal["rules_only", "classifier_only", "hybrid"]
    classifier_plugin: str | None
    classifier_min_confidence: float


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
    if match_query:
        return
    if source_contains:
        return
    if language_equals:
        return
    if normalized_mode in {"classifier_only", "hybrid"} and classifier_plugin:
        return
    raise StreamValidationError(
        "A stream needs at least one positive criterion (include keyword, source, or language)"
    )


def compile_stream(stream: KeywordStream) -> CompiledKeywordStream:
    compiled_query: ParsedSearchQuery | None = None
    if stream.match_query:
        compiled_query = parse_search_query(stream.match_query)
    return CompiledKeywordStream(
        id=stream.id,
        name=stream.name,
        priority=stream.priority,
        match_query=compiled_query,
        include_keywords=_keywords_from_json(stream.include_keywords_json),
        exclude_keywords=_keywords_from_json(stream.exclude_keywords_json),
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
    payload = f"{title}\n{content_text}".lower()
    source = (source_url or "").lower()
    normalized_language = (language or "").lower()

    if stream.match_query and not stream.match_query.matches(
        title=title,
        content_text=content_text,
        source_text=source_url,
    ):
        return False
    if stream.include_keywords and not any(keyword in payload for keyword in stream.include_keywords):
        return False
    if stream.exclude_keywords and any(keyword in payload for keyword in stream.exclude_keywords):
        return False
    if stream.source_contains and stream.source_contains not in source:
        return False
    if stream.language_equals and stream.language_equals != normalized_language:
        return False

    return True


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
        match_query = _normalize_optional_text(payload.match_query)
        source_contains = _normalize_optional_text(payload.source_contains)
        language_equals = _normalize_optional_lower(payload.language_equals)

        if match_query:
            try:
                parse_search_query(match_query)
            except SearchQuerySyntaxError as exc:
                raise StreamValidationError(str(exc)) from exc

        classifier_plugin = _normalize_optional_text(payload.classifier_plugin)
        _validate_criteria(
            include_keywords,
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
        match_query = _normalize_optional_text(stream.match_query)
        source_contains = _normalize_optional_text(stream.source_contains)
        language_equals = _normalize_optional_lower(stream.language_equals)
        _validate_criteria(
            include_keywords,
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
            matches.append(StreamArticleOut(matched_at=match.matched_at, article=ArticleOut.model_validate(article)))
        return matches

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
        matching_ids: list[UUID] = []
        article_context = ArticleContext(
            article_id="",
            title=title,
            content_text=content_text,
            metadata={"source_url": source_url or "", "language": language or ""},
        )
        for stream in streams:
            rules_match = stream_matches(
                stream,
                title=title,
                content_text=content_text,
                source_url=source_url,
                language=language,
            )

            classifier_match = False
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

            final_match = False
            if stream.classifier_mode == "rules_only":
                final_match = rules_match
            elif stream.classifier_mode == "classifier_only":
                final_match = classifier_match
            elif stream.classifier_mode == "hybrid":
                final_match = rules_match or classifier_match

            if final_match:
                matching_ids.append(stream.id)
        return matching_ids

    def make_match_rows(self, stream_ids: list[UUID], article_id: UUID) -> list[KeywordStreamMatch]:
        now = datetime.now(UTC)
        return [
            KeywordStreamMatch(stream_id=stream_id, article_id=article_id, matched_at=now)
            for stream_id in stream_ids
        ]


stream_service = StreamService()
