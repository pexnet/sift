"""Tests for API token service (Task 2 — MCP prerequisite)."""

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import User
from sift.services.token_service import TokenNotFoundError, token_service


@pytest.mark.asyncio
async def test_create_and_validate_token() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="token-test@example.com")
        session.add(user)
        await session.commit()

        raw_token, record = await token_service.create_token(
            session=session,
            user_id=user.id,
            name="MCP Test Token",
            scopes=["mcp:read", "mcp:write"],
        )
        assert raw_token
        assert raw_token.startswith("sft_")
        assert record.name == "MCP Test Token"
        assert record.token_hash != raw_token

        validated = await token_service.validate_token(session, raw_token)
        assert validated is not None
        assert validated.user_id == user.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_validate_rejects_unknown_token() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        result = await token_service.validate_token(session, "sft_nonexistent")
        assert result is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_validate_rejects_wrong_prefix() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        result = await token_service.validate_token(session, "badprefix_abc123")
        assert result is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_token() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="token-revoke@example.com")
        session.add(user)
        await session.commit()

        raw_token, record = await token_service.create_token(
            session=session,
            user_id=user.id,
            name="To Revoke",
        )
        await token_service.revoke_token(
            session=session,
            user_id=user.id,
            token_id=record.id,
        )
        validated = await token_service.validate_token(session, raw_token)
        assert validated is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_nonexistent_token_raises() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    from uuid import uuid4

    async with session_maker() as session:
        user = User(email="token-revoke-missing@example.com")
        session.add(user)
        await session.commit()

        with pytest.raises(TokenNotFoundError):
            await token_service.revoke_token(
                session=session,
                user_id=user.id,
                token_id=uuid4(),
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_tokens() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="token-list@example.com")
        session.add(user)
        await session.commit()

        await token_service.create_token(session=session, user_id=user.id, name="Token A")
        await token_service.create_token(session=session, user_id=user.id, name="Token B")
        tokens = await token_service.list_tokens(session=session, user_id=user.id)
        assert len(tokens) == 2

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_tokens_excludes_revoked() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="token-list-revoked@example.com")
        session.add(user)
        await session.commit()

        _, record_a = await token_service.create_token(
            session=session, user_id=user.id, name="Token A"
        )
        await token_service.create_token(session=session, user_id=user.id, name="Token B")
        await token_service.revoke_token(session=session, user_id=user.id, token_id=record_a.id)
        tokens = await token_service.list_tokens(session=session, user_id=user.id)
        assert len(tokens) == 1
        assert tokens[0].name == "Token B"

    await engine.dispose()


@pytest.mark.asyncio
async def test_revoke_token_other_user_fails() -> None:
    """Revoke must not work for tokens owned by a different user."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user_a = User(email="token-owner@example.com")
        user_b = User(email="token-attacker@example.com")
        session.add_all([user_a, user_b])
        await session.commit()

        _, record = await token_service.create_token(
            session=session, user_id=user_a.id, name="Token A"
        )
        with pytest.raises(TokenNotFoundError):
            await token_service.revoke_token(
                session=session,
                user_id=user_b.id,
                token_id=record.id,
            )

    await engine.dispose()