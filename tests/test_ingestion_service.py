import time
from datetime import UTC

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, Feed
from sift.services.dedup_service import build_content_fingerprint, dedup_service, normalize_canonical_url
from sift.services.ingestion_service import _make_source_id, _parse_published_at, ingestion_service


def test_make_source_id_prefers_declared_id() -> None:
    entry = {"id": "urn:entry:1", "title": "Example"}
    assert _make_source_id(entry) == "urn:entry:1"


def test_make_source_id_uses_stable_hash_fallback() -> None:
    entry = {"title": "Example", "published": "2026-02-14"}
    first = _make_source_id(entry)
    second = _make_source_id(entry)

    assert first.startswith("hash:")
    assert first == second


def test_parse_published_at_from_struct_time() -> None:
    parsed = time.gmtime(1739486400)
    result = _parse_published_at({"published_parsed": parsed})

    assert result is not None
    assert result.tzinfo == UTC


def test_normalize_canonical_url_strips_tracking_query_and_fragment() -> None:
    normalized = normalize_canonical_url("https://Example.com/path/?utm_source=x&b=2&a=1#frag")
    assert normalized == "https://example.com/path?a=1&b=2"


def test_build_content_fingerprint_is_stable() -> None:
    first = build_content_fingerprint(title="AI News", content_text="Model   launch")
    second = build_content_fingerprint(title=" ai news ", content_text="model launch")
    assert first is not None
    assert first == second


@pytest.mark.asyncio
async def test_resolve_canonical_duplicate_by_normalized_url() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        feed = Feed(title="Feed A", url="https://feed-a.example.com/rss")
        session.add(feed)
        await session.flush()

        existing = Article(
            feed_id=feed.id,
            source_id="a1",
            canonical_url="https://example.com/post?a=1&utm_source=foo",
            canonical_url_normalized="https://example.com/post?a=1",
            content_fingerprint="f1",
            title="Post",
            content_text="Body",
        )
        session.add(existing)
        await session.commit()

        decision = await dedup_service.resolve_canonical_duplicate(
            session=session,
            canonical_url_normalized="https://example.com/post?a=1",
            content_fingerprint=None,
        )
        assert decision.duplicate_of_id == existing.id
        assert decision.confidence == 0.92

    await engine.dispose()


class _PluginManagerStub:
    async def run_ingested_hooks(self, article_context):  # type: ignore[no-untyped-def]
        return article_context


class _ResponseStub:
    def __init__(self, status_code: int, content: bytes = b"", headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = headers or {}


@pytest.mark.asyncio
async def test_ingest_feed_sets_last_fetch_success_at_on_304(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    class _ClientStub:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        async def get(self, _url: str, headers: dict[str, str] | None = None) -> _ResponseStub:
            assert headers is not None
            return _ResponseStub(status_code=304)

    monkeypatch.setattr(httpx, "AsyncClient", _ClientStub)

    async with session_maker() as session:
        feed = Feed(title="304 Feed", url="https://ingestion.example.com/304.xml")
        session.add(feed)
        await session.commit()

        result = await ingestion_service.ingest_feed(
            session=session,
            feed_id=feed.id,
            plugin_manager=_PluginManagerStub(),  # type: ignore[arg-type]
        )
        assert result.errors == []

        refreshed = await session.scalar(select(Feed).where(Feed.id == feed.id))
        assert refreshed is not None
        assert refreshed.last_fetch_success_at is not None
        assert refreshed.last_fetch_error is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_ingest_feed_sets_last_fetch_success_at_on_success_and_error_timestamp_on_failure(monkeypatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    class _SuccessClientStub:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        async def get(self, _url: str, headers: dict[str, str] | None = None) -> _ResponseStub:
            assert headers is not None
            return _ResponseStub(
                status_code=200,
                content=b"<rss><channel><title>test</title></channel></rss>",
            )

    class _FailureClientStub:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
            return None

        async def get(self, _url: str, headers: dict[str, str] | None = None) -> _ResponseStub:
            raise httpx.ConnectError("network down")

    async with session_maker() as session:
        success_feed = Feed(title="200 Feed", url="https://ingestion.example.com/200.xml")
        failure_feed = Feed(title="Error Feed", url="https://ingestion.example.com/error.xml")
        session.add_all([success_feed, failure_feed])
        await session.commit()

        monkeypatch.setattr(httpx, "AsyncClient", _SuccessClientStub)
        success_result = await ingestion_service.ingest_feed(
            session=session,
            feed_id=success_feed.id,
            plugin_manager=_PluginManagerStub(),  # type: ignore[arg-type]
        )
        assert success_result.errors == []

        refreshed_success_feed = await session.scalar(select(Feed).where(Feed.id == success_feed.id))
        assert refreshed_success_feed is not None
        assert refreshed_success_feed.last_fetch_success_at is not None
        assert refreshed_success_feed.last_fetch_error is None

        monkeypatch.setattr(httpx, "AsyncClient", _FailureClientStub)
        failure_result = await ingestion_service.ingest_feed(
            session=session,
            feed_id=failure_feed.id,
            plugin_manager=_PluginManagerStub(),  # type: ignore[arg-type]
        )
        assert len(failure_result.errors) == 1

        refreshed_failure_feed = await session.scalar(select(Feed).where(Feed.id == failure_feed.id))
        assert refreshed_failure_feed is not None
        assert refreshed_failure_feed.last_fetch_error is not None
        assert refreshed_failure_feed.last_fetch_error_at is not None

    await engine.dispose()
