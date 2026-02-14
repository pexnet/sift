from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.db.models import User
from sift.db.session import get_db_session
from sift.services.auth_service import auth_service


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> User:
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_session_cookie_name)
    if not raw_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    user = await auth_service.get_user_by_session_token(session, raw_token=raw_token)
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

    return await auth_service.get_user_by_session_token(session, raw_token=raw_token)

