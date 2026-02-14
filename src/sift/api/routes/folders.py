from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from sift.api.deps.auth import get_current_user
from sift.db.models import User
from sift.db.session import get_db_session
from sift.domain.schemas import FeedFolderCreate, FeedFolderOut, FeedFolderUpdate
from sift.services.folder_service import FolderConflictError, FolderNotFoundError, folder_service

router = APIRouter()


@router.get("", response_model=list[FeedFolderOut])
async def list_folders(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[FeedFolderOut]:
    folders = await folder_service.list_folders(session=session, user_id=current_user.id)
    return [FeedFolderOut.model_validate(folder) for folder in folders]


@router.post("", response_model=FeedFolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(
    payload: FeedFolderCreate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedFolderOut:
    try:
        folder = await folder_service.create_folder(session=session, user_id=current_user.id, payload=payload)
    except FolderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FeedFolderOut.model_validate(folder)


@router.patch("/{folder_id}", response_model=FeedFolderOut)
async def update_folder(
    folder_id: UUID,
    payload: FeedFolderUpdate,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> FeedFolderOut:
    try:
        folder = await folder_service.update_folder(
            session=session,
            user_id=current_user.id,
            folder_id=folder_id,
            payload=payload,
        )
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FolderConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    return FeedFolderOut.model_validate(folder)


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    try:
        await folder_service.delete_folder(session=session, user_id=current_user.id, folder_id=folder_id)
    except FolderNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
