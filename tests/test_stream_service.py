import re
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, Feed, FeedFolder, KeywordStreamMatch, StreamClassifierRun, User
from sift.domain.schemas import KeywordStreamCreate, KeywordStreamUpdate
from sift.plugins.base import StreamClassificationDecision
from sift.search.query_language import parse_search_query
from sift.services.stream_service import (
    CompiledKeywordStream,
    StreamConflictError,
    StreamFolderNotFoundError,
    StreamMatchDecision,
    StreamValidationError,
    stream_matches,
    stream_rule_match_outcome,
    stream_service,
)


class FakePluginManager:
    async def classify_stream(self, **kwargs):
        plugin_name = kwargs["plugin_name"]
        stream_ctx = kwargs["stream"]
        article_ctx = kwargs["article"]
        if plugin_name == "always_match":
            return StreamClassificationDecision(
                matched=True,
                confidence=0.95,
                reason="test",
                provider="test_provider",
                model_name="test_model",
                model_version="v1.2.3",
                findings=[
                    {
                        "label": "provider finding",
                        "field": "content_text",
                        "start": 4,
                        "end": 10,
                        "text": "model launch context",
                        "score": 0.87,
                    }
                ],
            )
        if plugin_name == "low_conf":
            return StreamClassificationDecision(matched=True, confidence=0.25, reason="low")
        if plugin_name == "config_match":
            expected = str(stream_ctx.classifier_config.get("expected_token", "")).lower()
            payload = f"{article_ctx.title}\n{article_ctx.content_text}".lower()
            matched = bool(expected and expected in payload)
            return StreamClassificationDecision(
                matched=matched,
                confidence=0.9 if matched else 0.0,
                reason=f"expected_token={expected}" if expected else "expected_token missing",
                provider="test_provider",
                model_name="test_model",
                model_version="v1.2.3",
            )
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
                payload=KeywordStreamCreate(
                    name="empty", include_keywords=[], source_contains=None, language_equals=None
                ),
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
        assert stream.classifier_config_json == "{}"

        updated = await stream_service.update_stream(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            payload=KeywordStreamUpdate(
                priority=10,
                description="AI stream",
                classifier_config={"topic": "security"},
            ),
        )
        assert updated.priority == 10
        assert updated.description == "AI stream"
        assert updated.classifier_config_json == '{"topic":"security"}'

        with pytest.raises(StreamConflictError):
            await stream_service.create_stream(
                session=session,
                user_id=user.id,
                payload=KeywordStreamCreate(name="ai-news", include_keywords=["llm"]),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_update_stream_folder_assignment() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams-folder@example.com")
        other_user = User(email="streams-folder-other@example.com")
        session.add_all([user, other_user])
        await session.flush()

        folder = FeedFolder(user_id=user.id, name="Monitoring")
        other_folder = FeedFolder(user_id=other_user.id, name="Other")
        session.add_all([folder, other_folder])
        await session.flush()
        await session.commit()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="foldered", include_keywords=["ioc"], folder_id=folder.id),
        )
        assert stream.folder_id == folder.id

        cleared = await stream_service.update_stream(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            payload=KeywordStreamUpdate(folder_id=None),
        )
        assert cleared.folder_id is None

        with pytest.raises(StreamFolderNotFoundError):
            await stream_service.update_stream(
                session=session,
                user_id=user.id,
                stream_id=stream.id,
                payload=KeywordStreamUpdate(folder_id=other_folder.id),
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
        include_regex=[],
        exclude_regex=[],
        source_contains="example.com",
        language_equals="en",
        classifier_mode="rules_only",
        classifier_plugin=None,
        classifier_config={},
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
            include_regex=[],
            exclude_regex=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="rules_only",
            classifier_plugin=None,
            classifier_config={},
            classifier_min_confidence=0.7,
        ),
        CompiledKeywordStream(
            id=uuid4(),
            name="classifier",
            priority=20,
            match_query=None,
            include_keywords=[],
            exclude_keywords=[],
            include_regex=[],
            exclude_regex=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="classifier_only",
            classifier_plugin="always_match",
            classifier_config={},
            classifier_min_confidence=0.7,
        ),
        CompiledKeywordStream(
            id=uuid4(),
            name="low-conf",
            priority=30,
            match_query=None,
            include_keywords=[],
            exclude_keywords=[],
            include_regex=[],
            exclude_regex=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="classifier_only",
            classifier_plugin="low_conf",
            classifier_config={},
            classifier_min_confidence=0.7,
        ),
        CompiledKeywordStream(
            id=uuid4(),
            name="config-match",
            priority=40,
            match_query=None,
            include_keywords=[],
            exclude_keywords=[],
            include_regex=[],
            exclude_regex=[],
            source_contains=None,
            language_equals=None,
            classifier_mode="classifier_only",
            classifier_plugin="config_match",
            classifier_config={"expected_token": "launch"},
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
    assert streams[3].id in matched

    decisions = await stream_service.collect_matching_stream_decisions(
        streams,
        title="AI update",
        content_text="new model launch",
        source_url="https://example.com/feed",
        language="en",
        plugin_manager=plugin_manager,  # type: ignore[arg-type]
    )
    decision_reasons = {decision.stream_id: decision.reason for decision in decisions}
    decision_evidence = {decision.stream_id: decision.evidence for decision in decisions}
    assert "keyword: ai" in (decision_reasons.get(streams[0].id) or "")
    assert "classifier:" in (decision_reasons.get(streams[1].id) or "")
    assert "expected_token=launch" in (decision_reasons.get(streams[3].id) or "")
    assert decision_evidence.get(streams[0].id) is not None
    assert "keyword_hits" in (decision_evidence.get(streams[0].id) or {})
    assert (decision_evidence.get(streams[1].id) or {}).get("plugin") == "always_match"
    assert (decision_evidence.get(streams[1].id) or {}).get("provider") == "test_provider"
    assert (decision_evidence.get(streams[1].id) or {}).get("model_name") == "test_model"
    assert (decision_evidence.get(streams[1].id) or {}).get("model_version") == "v1.2.3"
    classifier_findings = (decision_evidence.get(streams[1].id) or {}).get("findings")
    assert isinstance(classifier_findings, list)
    assert classifier_findings[0].get("label") == "provider finding"
    assert classifier_findings[0].get("score") == pytest.approx(0.87)

    _, classifier_runs = await stream_service.collect_matching_stream_decisions_with_classifier_runs(
        streams,
        title="AI update",
        content_text="new model launch",
        source_url="https://example.com/feed",
        language="en",
        plugin_manager=plugin_manager,  # type: ignore[arg-type]
    )
    assert len(classifier_runs) == 3
    always_match_run = next(run for run in classifier_runs if run.plugin_name == "always_match")
    assert always_match_run.matched is True
    assert always_match_run.provider == "test_provider"
    assert always_match_run.model_name == "test_model"
    assert always_match_run.model_version == "v1.2.3"
    low_conf_run = next(run for run in classifier_runs if run.plugin_name == "low_conf")
    assert low_conf_run.matched is False
    assert low_conf_run.run_status == "ok"


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
        session.add_all(
            stream_service.make_match_rows(
                [
                    StreamMatchDecision(
                        stream_id=stream.id,
                        reason="keyword: ai",
                        evidence={"matcher_type": "rules", "keyword_hits": [{"value": "ai"}]},
                    )
                ],
                article.id,
            )
        )
        await session.commit()

        matches = await stream_service.list_stream_articles(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            limit=10,
        )
        assert len(matches) == 1
        assert matches[0].article.id == article.id
        assert matches[0].match_reason == "keyword: ai"
        assert matches[0].match_evidence is not None
        assert "keyword_hits" in matches[0].match_evidence

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
        include_regex=[],
        exclude_regex=[],
        source_contains=None,
        language_equals=None,
        classifier_mode="rules_only",
        classifier_plugin=None,
        classifier_config={},
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


def test_stream_rule_match_outcome_includes_query_hits() -> None:
    compiled_stream = CompiledKeywordStream(
        id=uuid4(),
        name="query-hits",
        priority=100,
        match_query=parse_search_query("darktrace AND sentinel*"),
        include_keywords=[],
        exclude_keywords=[],
        include_regex=[],
        exclude_regex=[],
        source_contains=None,
        language_equals=None,
        classifier_mode="rules_only",
        classifier_plugin=None,
        classifier_config={},
        classifier_min_confidence=0.7,
    )

    reason, evidence = stream_rule_match_outcome(
        compiled_stream,
        title="Darktrace security bulletin",
        content_text="SentinelOne telemetry update for enterprise teams.",
        source_url="https://example.com/feed",
        language="en",
    )
    assert reason == "query matched"
    assert evidence is not None
    assert "query" in evidence
    assert "query_hits" in evidence
    query_hits = evidence["query_hits"]
    assert isinstance(query_hits, list)
    assert any(hit.get("field") == "title" and hit.get("token", "").lower() == "darktrace" for hit in query_hits)
    assert any(hit.get("field") == "content_text" and "sentinel" in hit.get("token", "").lower() for hit in query_hits)
    assert all(hit.get("offset_basis") == "field_text_v1" for hit in query_hits)
    assert all(isinstance(hit.get("snippet"), str) and hit["snippet"] for hit in query_hits)


def test_stream_matches_supports_regex_include_exclude() -> None:
    compiled_stream = CompiledKeywordStream(
        id=uuid4(),
        name="regex",
        priority=100,
        match_query=None,
        include_keywords=[],
        exclude_keywords=[],
        include_regex=[re.compile(r"cve-\d{4}-\d+", flags=re.IGNORECASE)],
        exclude_regex=[re.compile(r"mitigated", flags=re.IGNORECASE)],
        source_contains=None,
        language_equals=None,
        classifier_mode="rules_only",
        classifier_plugin=None,
        classifier_config={},
        classifier_min_confidence=0.7,
    )

    assert (
        stream_matches(
            stream=compiled_stream,
            title="New CVE-2026-1234 exploit",
            content_text="active threat",
            source_url="https://example.com/feed",
            language="en",
        )
        is True
    )
    assert (
        stream_matches(
            stream=compiled_stream,
            title="New CVE-2026-1234 exploit mitigated",
            content_text="active threat",
            source_url="https://example.com/feed",
            language="en",
        )
        is False
    )


@pytest.mark.asyncio
async def test_create_stream_supports_include_regex_without_keywords() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams-regex@example.com")
        session.add(user)
        await session.commit()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="regex-only", include_regex=[r"cve-\d{4}-\d+"]),
        )
        assert stream.include_regex_json == '["cve-\\\\d{4}-\\\\d+"]'

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_stream_rejects_invalid_include_regex() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams-regex-invalid@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(StreamValidationError):
            await stream_service.create_stream(
                session=session,
                user_id=user.id,
                payload=KeywordStreamCreate(name="invalid-regex", include_regex=[r"([a-z"]),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_stream_rejects_non_serializable_classifier_config() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams-config-invalid@example.com")
        session.add(user)
        await session.commit()

        payload = KeywordStreamCreate.model_construct(
            name="invalid-config",
            include_keywords=["ai"],
            classifier_config={"bad": object()},
        )
        with pytest.raises(StreamValidationError):
            await stream_service.create_stream(
                session=session,
                user_id=user.id,
                payload=payload,
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_run_stream_backfill_replaces_existing_matches() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams-backfill@example.com")
        other_user = User(email="streams-backfill-other@example.com")
        session.add_all([user, other_user])
        await session.flush()

        feed = Feed(owner_id=user.id, title="Owned feed", url="https://owned-backfill.example.com/rss")
        other_feed = Feed(owner_id=other_user.id, title="Other feed", url="https://other-backfill.example.com/rss")
        session.add_all([feed, other_feed])
        await session.flush()

        matching_article = Article(
            feed_id=feed.id,
            source_id="m1",
            title="Microsoft Sentinel update",
            content_text="security operations",
        )
        non_matching_article = Article(
            feed_id=feed.id,
            source_id="m2",
            title="Football weekly",
            content_text="sports roundup",
        )
        other_user_article = Article(
            feed_id=other_feed.id,
            source_id="m3",
            title="Microsoft Sentinel incident",
            content_text="other account",
        )
        session.add_all([matching_article, non_matching_article, other_user_article])
        await session.flush()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="security", match_query="microsoft AND NOT sports"),
        )
        session.add(KeywordStreamMatch(stream_id=stream.id, article_id=non_matching_article.id))
        await session.commit()

        result = await stream_service.run_stream_backfill(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            plugin_manager=FakePluginManager(),  # type: ignore[arg-type]
        )
        assert result.scanned_count == 2
        assert result.previous_match_count == 1
        assert result.matched_count == 1

        matches = await stream_service.list_stream_articles(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            limit=10,
        )
        assert len(matches) == 1
        assert matches[0].article.id == matching_article.id
        assert matches[0].match_reason == "query matched"
        assert matches[0].match_evidence is not None
        assert matches[0].match_evidence.get("query") is not None
        query_hits = matches[0].match_evidence.get("query_hits")
        assert isinstance(query_hits, list)
        assert any(hit.get("field") == "title" for hit in query_hits)
        assert any(hit.get("token", "").lower() == "microsoft" for hit in query_hits)

    await engine.dispose()


@pytest.mark.asyncio
async def test_run_stream_backfill_persists_classifier_runs() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="streams-backfill-classifier@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Owned feed", url="https://owned-backfill-classifier.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(
            feed_id=feed.id,
            source_id="m1",
            title="Microsoft Sentinel update",
            content_text="security operations",
        )
        session.add(article)
        await session.flush()

        stream = await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(
                name="classifier-security",
                classifier_mode="classifier_only",
                classifier_plugin="always_match",
            ),
        )
        await session.commit()

        result = await stream_service.run_stream_backfill(
            session=session,
            user_id=user.id,
            stream_id=stream.id,
            plugin_manager=FakePluginManager(),  # type: ignore[arg-type]
        )
        assert result.scanned_count == 1
        assert result.matched_count == 1

        classifier_runs_result = await session.execute(
            select(StreamClassifierRun).where(StreamClassifierRun.stream_id == stream.id)
        )
        classifier_runs = classifier_runs_result.scalars().all()
        assert len(classifier_runs) == 1
        classifier_run = classifier_runs[0]
        assert classifier_run.plugin_name == "always_match"
        assert classifier_run.provider == "test_provider"
        assert classifier_run.model_name == "test_model"
        assert classifier_run.model_version == "v1.2.3"
        assert classifier_run.matched is True
        assert classifier_run.run_status == "ok"
        assert classifier_run.threshold == 0.7
        assert classifier_run.confidence == pytest.approx(0.95)

    await engine.dispose()
