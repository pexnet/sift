from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.db.models import User
from sift.db.session import get_db_session
from sift.services.auth_service import auth_service
from sift.services.token_service import token_service


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        user = await auth_service.get_user_by_session_token(session, raw_token=raw_token)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")

    return user


async def get_optional_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User | None:
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_session_cookie_name)
    if not raw_token:
        return None

    try:
        return await auth_service.get_user_by_session_token(session, raw_token=raw_token)
    except SQLAlchemyError:
        return None


async def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user


async def get_current_user_from_token(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Authenticate via Bearer API token in Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required")
    raw_token = auth_header[7:]
    token = await token_service.validate_token(session, raw_token)
    if token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    stmt = select(User).where(User.id == token.user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user not found")
    return user


async def get_current_user_flexible(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    """Try cookie session auth first, fall back to Bearer API token.

    Used by the MCP endpoint and other routes that accept both browser
    sessions and machine-to-machine API tokens.
    """
    settings = get_settings()
    raw_cookie = request.cookies.get(settings.auth_session_cookie_name)
    if raw_cookie:
        try:
            user = await auth_service.get_user_by_session_token(session, raw_token=raw_cookie)
            if user is not None:
                return user
        except SQLAlchemyError:
            pass

    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
        token = await token_service.validate_token(session, raw_token)
        if token is not None:
            stmt = select(User).where(User.id == token.user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is not None:
                return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
