from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.db.models import User
from sift.db.session import get_db_session
from sift.services.auth_service import AuthenticationError, ConflictError, auth_service
from sift.services.feed_service import feed_service

router = APIRouter()
templates = Jinja2Templates(directory="src/sift/web/templates")


def _set_session_cookie(response: RedirectResponse, session_token: str) -> None:
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


def _clear_session_cookie(response: RedirectResponse) -> None:
    settings = get_settings()
    response.delete_cookie(key=settings.auth_session_cookie_name, path="/")


async def _get_optional_user(request: Request, session: AsyncSession) -> User | None:
    settings = get_settings()
    raw_token = request.cookies.get(settings.auth_session_cookie_name)
    if not raw_token:
        return None
    return await auth_service.get_user_by_session_token(session=session, raw_token=raw_token)


@router.get("/")
async def home(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    feeds = await feed_service.list_feeds(session=session, user_id=current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"feeds": feeds, "title": "Sift", "current_user": current_user},
    )


@router.get("/login")
async def login_page(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"title": "Login", "error_message": None},
    )


@router.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        user = await auth_service.authenticate_local(session=session, email=email, password=password)
    except AuthenticationError as exc:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"title": "Login", "error_message": str(exc)},
            status_code=401,
        )

    raw_session_token = await auth_service.create_session(
        session=session,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    response = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(response, raw_session_token)
    return response


@router.get("/register")
async def register_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is not None:
        return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context={"title": "Register", "error_message": None},
    )


@router.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    try:
        user = await auth_service.register_local_user(
            session=session,
            email=email,
            password=password,
            display_name=display_name,
        )
    except ConflictError as exc:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"title": "Register", "error_message": str(exc)},
            status_code=409,
        )

    raw_session_token = await auth_service.create_session(
        session=session,
        user=user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    response = RedirectResponse(url="/", status_code=303)
    _set_session_cookie(response, raw_session_token)
    return response


@router.post("/logout")
async def logout_submit(request: Request, session: AsyncSession = Depends(get_db_session)) -> RedirectResponse:
    settings = get_settings()
    raw_session_token = request.cookies.get(settings.auth_session_cookie_name)
    if raw_session_token:
        await auth_service.revoke_session(session=session, raw_token=raw_session_token)

    response = RedirectResponse(url="/login", status_code=303)
    _clear_session_cookie(response)
    return response


@router.get("/logout")
async def logout_shortcut(request: Request, session: AsyncSession = Depends(get_db_session)) -> RedirectResponse:
    return await logout_submit(request=request, session=session)


@router.get("/account")
async def account_page(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="account.html",
        context={"title": "Account", "current_user": current_user},
    )

