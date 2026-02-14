import time
from datetime import UTC

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, Feed
from sift.services.dedup_service import build_content_fingerprint, dedup_service, normalize_canonical_url
from sift.services.ingestion_service import _make_source_id, _parse_published_at


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
