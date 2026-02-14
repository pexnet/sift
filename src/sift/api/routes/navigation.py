from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import NavigationTreeOut
from sift.services.navigation_service import navigation_service

router = APIRouter()


@router.get("", response_model=NavigationTreeOut)
async def get_navigation(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> NavigationTreeOut:
    return await navigation_service.get_navigation_tree(session=session, user_id=current_user.id)
