import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.services.auth_service import AuthenticationError, ConflictError, auth_service


@pytest.mark.asyncio
async def test_register_and_authenticate_local_user() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = await auth_service.register_local_user(
            session=session,
            email="User@Example.com",
            password="correct horse battery staple",
            display_name="User A",
        )

        assert user.email == "user@example.com"

        authed_user = await auth_service.authenticate_local(
            session=session,
            email="user@example.com",
            password="correct horse battery staple",
        )
        assert authed_user.id == user.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_conflict() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        await auth_service.register_local_user(
            session=session,
            email="dup@example.com",
            password="password-1234",
            display_name="Dup",
        )

        with pytest.raises(ConflictError):
            await auth_service.register_local_user(
                session=session,
                email="dup@example.com",
                password="password-1234",
                display_name="Dup",
            )

    await engine.dispose()


@pytest.mark.asyncio
async def test_session_create_lookup_and_revoke() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = await auth_service.register_local_user(
            session=session,
            email="session@example.com",
            password="password-1234",
            display_name="Session User",
        )

        raw_token = await auth_service.create_session(
            session=session,
            user=user,
            ip_address="127.0.0.1",
            user_agent="pytest",
        )

        resolved_user = await auth_service.get_user_by_session_token(session=session, raw_token=raw_token)
        assert resolved_user is not None
        assert resolved_user.id == user.id

        await auth_service.revoke_session(session=session, raw_token=raw_token)

        revoked_user = await auth_service.get_user_by_session_token(session=session, raw_token=raw_token)
        assert revoked_user is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_authenticate_invalid_password_raises() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        await auth_service.register_local_user(
            session=session,
            email="wrongpass@example.com",
            password="password-1234",
            display_name="Wrong Pass",
        )

        with pytest.raises(AuthenticationError):
            await auth_service.authenticate_local(
                session=session,
                email="wrongpass@example.com",
                password="bad-password",
            )

    await engine.dispose()
