from typing import Literal, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import get_settings
from sift.db.models import User
from sift.db.session import get_db_session
from sift.services.article_service import ArticleNotFoundError, article_service
from sift.services.auth_service import AuthenticationError, ConflictError, auth_service
from sift.services.navigation_service import navigation_service

router = APIRouter()
templates = Jinja2Templates(directory="src/sift/web/templates")


ScopeType = Literal["system", "folder", "feed", "stream"]
StateFilter = Literal["all", "unread", "saved", "archived", "fresh", "recent"]
SortMode = Literal["newest", "oldest", "unread_first"]


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
    return RedirectResponse(url="/app", status_code=303)


def _parse_scope_type(value: str | None) -> ScopeType:
    if value in {"system", "folder", "feed", "stream"}:
        return cast(ScopeType, value)
    return "system"


def _parse_state(value: str | None) -> StateFilter:
    if value in {"all", "unread", "saved", "archived", "fresh", "recent"}:
        return cast(StateFilter, value)
    return "all"


def _parse_sort(value: str | None) -> SortMode:
    if value in {"newest", "oldest", "unread_first"}:
        return cast(SortMode, value)
    return "newest"


def _parse_uuid(value: str | None) -> UUID | None:
    if not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None


def _parse_int(value: str | None, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    return max(minimum, min(maximum, parsed))


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return None


def _query_context(request: Request) -> dict[str, object]:
    params = request.query_params
    scope_type = _parse_scope_type(params.get("scope_type"))
    state = _parse_state(params.get("state"))
    sort = _parse_sort(params.get("sort"))
    return {
        "scope_type": scope_type,
        "scope_id": _parse_uuid(params.get("scope_id")),
        "state": state,
        "q": (params.get("q") or "").strip() or None,
        "sort": sort,
        "limit": _parse_int(params.get("limit"), default=100, minimum=1, maximum=500),
        "offset": _parse_int(params.get("offset"), default=0, minimum=0, maximum=1_000_000),
    }


def _query_context_from_form(form: dict[str, str]) -> dict[str, object]:
    scope_type = _parse_scope_type(form.get("scope_type"))
    state = _parse_state(form.get("state"))
    sort = _parse_sort(form.get("sort"))
    return {
        "scope_type": scope_type,
        "scope_id": _parse_uuid(form.get("scope_id")),
        "state": state,
        "q": (form.get("q") or "").strip() or None,
        "sort": sort,
        "limit": _parse_int(form.get("limit"), default=100, minimum=1, maximum=500),
        "offset": _parse_int(form.get("offset"), default=0, minimum=0, maximum=1_000_000),
    }


async def _build_workspace_context(
    *,
    request: Request,
    session: AsyncSession,
    current_user: User,
) -> dict[str, object]:
    query = _query_context(request)
    navigation = await navigation_service.get_navigation_tree(session=session, user_id=current_user.id)
    article_list = await article_service.list_articles(
        session=session,
        user_id=current_user.id,
        scope_type=query["scope_type"],  # type: ignore[arg-type]
        scope_id=query["scope_id"],  # type: ignore[arg-type]
        state=query["state"],  # type: ignore[arg-type]
        q=query["q"],  # type: ignore[arg-type]
        limit=query["limit"],  # type: ignore[arg-type]
        offset=query["offset"],  # type: ignore[arg-type]
        sort=query["sort"],  # type: ignore[arg-type]
    )

    selected_article_id = _parse_uuid(request.query_params.get("article_id"))
    if selected_article_id is None and article_list.items:
        selected_article_id = article_list.items[0].id

    article_detail = None
    if selected_article_id is not None:
        try:
            article_detail = await article_service.get_article_detail(
                session=session,
                user_id=current_user.id,
                article_id=selected_article_id,
            )
        except ArticleNotFoundError:
            article_detail = None

    return {
        "title": "Sift",
        "current_user": current_user,
        "navigation": navigation,
        "article_list": article_list,
        "article_detail": article_detail,
        "query": query,
        "selected_article_id": selected_article_id,
    }


@router.get("/app")
async def app_workspace(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return RedirectResponse(url="/login", status_code=303)
    context = await _build_workspace_context(request=request, session=session, current_user=current_user)
    return templates.TemplateResponse(request=request, name="app.html", context=context)


@router.get("/web/partials/nav-tree")
async def nav_tree_partial(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return Response(status_code=401)
    navigation = await navigation_service.get_navigation_tree(session=session, user_id=current_user.id)
    return templates.TemplateResponse(
        request=request,
        name="partials/nav_tree.html",
        context={"navigation": navigation, "query": _query_context(request), "current_user": current_user},
    )


@router.get("/web/partials/article-list")
async def article_list_partial(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return Response(status_code=401)

    query = _query_context(request)
    article_list = await article_service.list_articles(
        session=session,
        user_id=current_user.id,
        scope_type=query["scope_type"],  # type: ignore[arg-type]
        scope_id=query["scope_id"],  # type: ignore[arg-type]
        state=query["state"],  # type: ignore[arg-type]
        q=query["q"],  # type: ignore[arg-type]
        limit=query["limit"],  # type: ignore[arg-type]
        offset=query["offset"],  # type: ignore[arg-type]
        sort=query["sort"],  # type: ignore[arg-type]
    )
    selected_article_id = _parse_uuid(request.query_params.get("article_id"))
    return templates.TemplateResponse(
        request=request,
        name="partials/article_list.html",
        context={
            "article_list": article_list,
            "query": query,
            "selected_article_id": selected_article_id,
            "current_user": current_user,
        },
    )


@router.get("/web/partials/article-reader/{article_id}")
async def article_reader_partial(
    article_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return Response(status_code=401)

    try:
        detail = await article_service.get_article_detail(
            session=session,
            user_id=current_user.id,
            article_id=article_id,
        )
    except ArticleNotFoundError:
        return Response(status_code=404)

    return templates.TemplateResponse(
        request=request,
        name="partials/article_reader.html",
        context={"article_detail": detail, "query": _query_context(request), "current_user": current_user},
    )


@router.patch("/web/actions/article/{article_id}/state")
async def article_state_action(
    article_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return Response(status_code=401)

    form = {str(k): str(v) for k, v in (await request.form()).items()}
    query = _query_context_from_form(form)
    try:
        await article_service.patch_state(
            session=session,
            user_id=current_user.id,
            article_id=article_id,
            is_read=_parse_bool(form.get("is_read")),
            is_starred=_parse_bool(form.get("is_starred")),
            is_archived=_parse_bool(form.get("is_archived")),
        )
    except (ArticleNotFoundError, ValueError):
        return Response(status_code=404)

    article_list = await article_service.list_articles(
        session=session,
        user_id=current_user.id,
        scope_type=query["scope_type"],  # type: ignore[arg-type]
        scope_id=query["scope_id"],  # type: ignore[arg-type]
        state=query["state"],  # type: ignore[arg-type]
        q=query["q"],  # type: ignore[arg-type]
        limit=query["limit"],  # type: ignore[arg-type]
        offset=query["offset"],  # type: ignore[arg-type]
        sort=query["sort"],  # type: ignore[arg-type]
    )
    selected_article_id = _parse_uuid(form.get("article_id"))
    return templates.TemplateResponse(
        request=request,
        name="partials/article_list.html",
        context={
            "article_list": article_list,
            "query": query,
            "selected_article_id": selected_article_id,
            "current_user": current_user,
        },
    )


@router.post("/web/actions/article/bulk-state")
async def article_bulk_state_action(request: Request, session: AsyncSession = Depends(get_db_session)) -> Response:
    current_user = await _get_optional_user(request=request, session=session)
    if current_user is None:
        return Response(status_code=401)

    form = {str(k): str(v) for k, v in (await request.form()).items()}
    query = _query_context_from_form(form)
    ids_raw = form.get("article_ids", "")
    article_ids = [UUID(item) for item in ids_raw.split(",") if item.strip()]
    await article_service.bulk_patch_state(
        session=session,
        user_id=current_user.id,
        article_ids=article_ids,
        is_read=_parse_bool(form.get("is_read")),
        is_starred=_parse_bool(form.get("is_starred")),
        is_archived=_parse_bool(form.get("is_archived")),
    )
    article_list = await article_service.list_articles(
        session=session,
        user_id=current_user.id,
        scope_type=query["scope_type"],  # type: ignore[arg-type]
        scope_id=query["scope_id"],  # type: ignore[arg-type]
        state=query["state"],  # type: ignore[arg-type]
        q=query["q"],  # type: ignore[arg-type]
        limit=query["limit"],  # type: ignore[arg-type]
        offset=query["offset"],  # type: ignore[arg-type]
        sort=query["sort"],  # type: ignore[arg-type]
    )
    selected_article_id = _parse_uuid(form.get("article_id"))
    return templates.TemplateResponse(
        request=request,
        name="partials/article_list.html",
        context={
            "article_list": article_list,
            "query": query,
            "selected_article_id": selected_article_id,
            "current_user": current_user,
        },
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

