from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import (
    ArticleDetailOut,
    ArticleListResponse,
    ArticleOut,
    ArticleScopeReadPatch,
    ArticleStateBulkPatch,
    ArticleStateOut,
    ArticleStatePatch,
    KeywordFilterPreviewRequest,
)
from sift.services.article_service import (
    ArticleNotFoundError,
    ArticleStateValidationError,
    article_service,
)
from sift.services.filter_service import keyword_filter_service

router = APIRouter()


@router.post("/filter-preview", response_model=list[ArticleOut])
async def filter_preview(
    payload: KeywordFilterPreviewRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[ArticleOut]:
    articles = await keyword_filter_service.preview(
        session=session,
        user_id=current_user.id,
        include_keywords=payload.include_keywords,
        exclude_keywords=payload.exclude_keywords,
        limit=payload.limit,
    )
    return [ArticleOut.model_validate(article) for article in articles]


@router.get("", response_model=ArticleListResponse)
async def list_articles(
    scope_type: Literal["system", "folder", "feed", "stream"] = Query(default="system"),
    scope_id: UUID | None = Query(default=None),
    state: Literal["all", "unread", "saved", "archived", "fresh", "recent"] = Query(default="all"),
    q: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    sort: Literal["newest", "oldest", "unread_first"] = Query(default="newest"),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ArticleListResponse:
    try:
        return await article_service.list_articles(
            session=session,
            user_id=current_user.id,
            scope_type=scope_type,
            scope_id=scope_id,
            state=state,
            q=q,
            limit=limit,
            offset=offset,
            sort=sort,
        )
    except ArticleStateValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/state/bulk", status_code=status.HTTP_200_OK)
async def bulk_patch_article_state(
    payload: ArticleStateBulkPatch,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    try:
        updated_count = await article_service.bulk_patch_state(
            session=session,
            user_id=current_user.id,
            article_ids=payload.article_ids,
            is_read=payload.is_read,
            is_starred=payload.is_starred,
            is_archived=payload.is_archived,
        )
    except ArticleStateValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"updated_count": updated_count}


@router.post("/state/mark-scope-read", status_code=status.HTTP_200_OK)
async def mark_scope_as_read(
    payload: ArticleScopeReadPatch,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    try:
        updated_count = await article_service.mark_scope_as_read(
            session=session,
            user_id=current_user.id,
            scope_type=payload.scope_type,
            scope_id=payload.scope_id,
            state=payload.state,
            q=payload.q,
        )
    except ArticleStateValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"updated_count": updated_count}


@router.get("/{article_id}", response_model=ArticleDetailOut)
async def get_article(
    article_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ArticleDetailOut:
    try:
        return await article_service.get_article_detail(
            session=session,
            user_id=current_user.id,
            article_id=article_id,
        )
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.patch("/{article_id}/state", response_model=ArticleStateOut)
async def patch_article_state(
    article_id: UUID,
    payload: ArticleStatePatch,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> ArticleStateOut:
    try:
        return await article_service.patch_state(
            session=session,
            user_id=current_user.id,
            article_id=article_id,
            is_read=payload.is_read,
            is_starred=payload.is_starred,
            is_archived=payload.is_archived,
        )
    except ArticleNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ArticleStateValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
