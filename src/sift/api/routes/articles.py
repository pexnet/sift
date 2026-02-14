from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import ArticleOut, KeywordFilterPreviewRequest
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
