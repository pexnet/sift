from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.config import get_settings
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import AuthLoginRequest, AuthRegisterRequest, UserOut
from sift.services.auth_service import AuthenticationError, ConflictError, auth_service

router = APIRouter()


def _set_session_cookie(response: Response, session_token: str) -> None:
    settings = get_settings()
    max_age = settings.auth_session_ttl_days * 24 * 60 * 60
    response.set_cookie(
        key=settings.auth_session_cookie_name,
        value=session_token,
        max_age=max_age,
        httponly=True,
        samesite="lax",
        secure=settings.auth_cookie_secure,
        path="/",
    )


def _clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_session_cookie_name, path="/")


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(
    payload: AuthRegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    try:
        user = await auth_service.register_local_user(
            session=session,
            email=str(payload.email),
            password=payload.password,
            display_name=payload.display_name,
        )
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    raw_session_token = await auth_service.create_session(
        session=session,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, raw_session_token)
    return UserOut.model_validate(user)


@router.post("/login", response_model=UserOut)
async def login(
    payload: AuthLoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> UserOut:
    try:
        user = await auth_service.authenticate_local(
            session=session,
            email=str(payload.email),
            password=payload.password,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    raw_session_token = await auth_service.create_session(
        session=session,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    _set_session_cookie(response, raw_session_token)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    settings = get_settings()
    raw_session_token = request.cookies.get(settings.auth_session_cookie_name)
    if raw_session_token:
        await auth_service.revoke_session(session=session, raw_token=raw_session_token)
    _clear_session_cookie(response)
    return response


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
