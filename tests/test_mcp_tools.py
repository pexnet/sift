"""Tests for MCP tool definitions and handlers."""

import json
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, Feed, User
from sift.domain.schemas import KeywordStreamCreate
from sift.mcp.tools import TOOL_DEFINITIONS, execute_tool
from sift.services.stream_service import stream_service


def test_tool_definitions_exist():
    assert len(TOOL_DEFINITIONS) >= 8
    names = [t.name for t in TOOL_DEFINITIONS]
    assert "sift_list_feeds" in names
    assert "sift_search_articles" in names
    assert "sift_get_article" in names
    assert "sift_add_feed" in names
    assert "sift_mark_articles_read" in names
    assert "sift_list_streams" in names
    assert "sift_get_navigation" in names
    assert "sift_get_feed_health" in names


def test_tool_definitions_have_required_fields():
    for tool in TOOL_DEFINITIONS:
        assert tool.name
        assert tool.description
        assert tool.inputSchema
        assert tool.inputSchema.get("type") == "object"


@pytest.mark.asyncio
async def test_unknown_tool_returns_error(monkeypatch):
    """Unknown tool name should return a JSON error string."""
    # We need a user_id but no DB is needed for the error path
    result = await execute_tool("nonexistent", {}, uuid4())
    parsed = json.loads(result)
    assert "error" in parsed


@pytest.mark.asyncio
async def test_sift_search_articles_returns_results(monkeypatch):
    """Search articles tool should return matching articles."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="mcp-search@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Feed", url="https://mcp-search.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(feed_id=feed.id, source_id="s1", title="AI breakthrough", content_text="LLM update")
        session.add(article)
        await session.commit()

    # Patch SessionLocal to use our test engine
    monkeypatch.setattr("sift.mcp.tools.SessionLocal", session_maker)

    result_str = await execute_tool(
        "sift_search_articles",
        {"q": "AI", "state": "all", "scope_type": "system", "limit": 10, "offset": 0, "sort": "newest"},
        user.id,
    )
    parsed = json.loads(result_str)
    assert len(parsed["items"]) >= 1
    assert parsed["items"][0]["title"] == "AI breakthrough"

    await engine.dispose()


@pytest.mark.asyncio
async def test_sift_list_streams_returns_streams(monkeypatch):
    """List streams tool should return monitoring streams."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="mcp-streams@example.com")
        session.add(user)
        await session.commit()

        await stream_service.create_stream(
            session=session,
            user_id=user.id,
            payload=KeywordStreamCreate(name="ai-monitor", include_keywords=["ai"]),
        )
        await session.commit()

    monkeypatch.setattr("sift.mcp.tools.SessionLocal", session_maker)

    result_str = await execute_tool("sift_list_streams", {}, user.id)
    parsed = json.loads(result_str)
    assert len(parsed) == 1
    assert parsed[0]["name"] == "ai-monitor"

    await engine.dispose()
