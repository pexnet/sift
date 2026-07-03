"""Tests for MCP StreamableHTTP endpoint."""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import User
from sift.db.session import get_db_session
from sift.main import app
from sift.services.token_service import token_service


async def _setup_test_db(monkeypatch):
    """Set up an in-memory SQLite DB and patch the app's session dependency."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async def override_db_session():
        async with session_maker() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_db_session
    # Also patch SessionLocal used by the MCP endpoint directly
    monkeypatch.setattr("sift.main._SessionLocal", session_maker)
    return engine, session_maker


@pytest.mark.asyncio
async def test_mcp_endpoint_requires_auth(monkeypatch):
    """MCP endpoint should return 401 without authentication."""
    engine, _ = await _setup_test_db(monkeypatch)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                },
            )
            assert resp.status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_mcp_endpoint_with_bearer_token(monkeypatch):
    """MCP endpoint should accept a valid Bearer API token."""
    engine, session_maker = await _setup_test_db(monkeypatch)
    try:
        async with session_maker() as session:
            user = User(email="mcp-http@example.com")
            session.add(user)
            await session.commit()
            raw_token, _ = await token_service.create_token(session=session, user_id=user.id, name="MCP Test")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.post(
                "/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "test", "version": "1.0"},
                    },
                },
                headers={"Authorization": f"Bearer {raw_token}"},
            )
            # Should not be 401 — auth passed
            assert resp.status_code != 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
