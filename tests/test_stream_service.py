from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, Feed, User
from sift.domain.schemas import KeywordStreamCreate, KeywordStreamUpdate
from sift.plugins.base import StreamClassificationDecision
from sift.search.query_language import parse_search_query
from sift.services.stream_service import (
    CompiledKeywordStream,
    StreamConflictError,
    StreamValidationError,
    stream_matches,
    stream_service,
)


class FakePluginManager:
    async def classify_stream(self, **kwargs):
        plugin_name = kwargs["plugin_name"]
        if plugin_name == "always_match":
            return StreamClassificationDecision(matched=True, confidence=0.95, reason="test")
        if plugin_name == "low_conf":
            return StreamClassificationDecision(matched=True, confidence=0.25, reason="low")
        return None


@pytest.mark.asyncio
async def test_create_stream_requires_positive_criteria() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(StreamValidationError):
            await stream_service.create_stream(
                session=session,
                user_id=user.id,
                payload=KeywordStreamCreate(name="empty", include_keywords=[], source_contains=None, language_equals=None),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_update_and_conflict_stream() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams2@example.com")
        session.add(user)
        await session.commit()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="ai-news", include_keywords=["ai"]),
        )
        assert stream.name == "ai-news"

        updated = await stream_service.update_stream(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            payload=KeywordStreamUpdate(priority=10, description="AI stream"),
        )
        assert updated.priority == 10
        assert updated.description == "AI stream"

        with pytest.raises(StreamConflictError):
            await stream_service.create_stream(
                session=session,
                user_id=user.id,
                payload=KeywordStreamCreate(name="ai-news", include_keywords=["llm"]),
            )

    await engine.dispose()


def test_stream_matches_include_exclude_source_language() -> None:
    compiled_stream = CompiledKeywordStream(
        id=uuid4(),
        name="test",
        priority=100,
        match_query=None,
        include_keywords=["ai"],
        exclude_keywords=["sports"],
        source_contains="example.com",
        language_equals="en",
        classifier_mode="rules_only",
        classifier_plugin=None,
        classifier_min_confidence=0.7,
    )
    match = stream_matches(
        stream=compiled_stream,
        title="AI update",
        content_text="model launch",
        source_url="https://example.com/feed",
        language="en",
    )
    assert match is True

    mismatch = stream_matches(
        stream=compiled_stream,
        title="Sports AI",
        content_text="sports roundup",
        source_url="https://example.com/feed",
        language="en",
    )
    assert mismatch is False


@pytest.mark.asyncio
async def test_collect_matching_stream_ids_with_classifier_modes() -> None:
    plugin_manager = FakePluginManager()

    streams = [
        CompiledKeywordStream(
            id=uuid4(),
            name="rules",
            priority=10,
            match_query=None,
            include_keywords=["ai"],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="rules_only",
            classifier_plugin=None,
            classifier_min_confidence=0.7,
        ),
        CompiledKeywordStream(
            id=uuid4(),
            name="classifier",
            priority=20,
            match_query=None,
            include_keywords=[],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="classifier_only",
            classifier_plugin="always_match",
            classifier_min_confidence=0.7,
        ),
        CompiledKeywordStream(
            id=uuid4(),
            name="low-conf",
            priority=30,
            match_query=None,
            include_keywords=[],
            exclude_keywords=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="classifier_only",
            classifier_plugin="low_conf",
            classifier_min_confidence=0.7,
        ),
    ]

    matched = await stream_service.collect_matching_stream_ids(
        streams,
        title="AI update",
        content_text="new model launch",
        source_url="https://example.com/feed",
        language="en",
        plugin_manager=plugin_manager,  # type: ignore[arg-type]
    )
    assert streams[0].id in matched
    assert streams[1].id in matched
    assert streams[2].id not in matched


@pytest.mark.asyncio
async def test_list_stream_articles_returns_matches() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams3@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Feed", url="https://streams3.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(feed_id=feed.id, source_id="s1", title="AI", content_text="LLM", canonical_url=feed.url)
        session.add(article)
        await session.flush()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="ai", include_keywords=["ai"]),
        )
        session.add_all(stream_service.make_match_rows([stream.id], article.id))
        await session.commit()

        matches = await stream_service.list_stream_articles(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            limit=10,
        )
        assert len(matches) == 1
        assert matches[0].article.id == article.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_stream_create_supports_match_query_without_include_keywords() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams4@example.com")
        session.add(user)
        await session.commit()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="query-only", match_query="microsoft AND sentinel"),
        )
        assert stream.match_query == "microsoft AND sentinel"

    await engine.dispose()


def test_stream_matches_respects_match_query() -> None:
    compiled_stream = CompiledKeywordStream(
        id=uuid4(),
        name="query",
        priority=100,
        match_query=parse_search_query("microsoft AND NOT sports"),
        include_keywords=[],
        exclude_keywords=[],
        source_contains=None,
        language_equals=None,
        classifier_mode="rules_only",
        classifier_plugin=None,
        classifier_min_confidence=0.7,
    )

    assert (
        stream_matches(
            stream=compiled_stream,
            title="microsoft sentinel update",
            content_text="security telemetry",
            source_url="https://example.com/feed",
            language="en",
        )
        is True
    )
    assert (
        stream_matches(
            stream=compiled_stream,
            title="microsoft sports roundup",
            content_text="security telemetry",
            source_url="https://example.com/feed",
            language="en",
        )
        is False
    )
