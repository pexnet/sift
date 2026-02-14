from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Feed, FeedFolder
from sift.domain.schemas import FeedFolderCreate, FeedFolderUpdate


class FolderConflictError(Exception):
    pass


class FolderNotFoundError(Exception):
    pass


class FolderService:
    async def list_folders(self, session: AsyncSession, user_id: UUID) -> list[FeedFolder]:
        query = select(FeedFolder).where(FeedFolder.user_id == user_id).order_by(
            FeedFolder.sort_order.asc(),
            FeedFolder.name.asc(),
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def create_folder(self, session: AsyncSession, user_id: UUID, payload: FeedFolderCreate) -> FeedFolder:
        folder = FeedFolder(
            user_id=user_id,
            name=payload.name.strip(),
            description=payload.description.strip() if payload.description else None,
            sort_order=payload.sort_order,
        )
        session.add(folder)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise FolderConflictError("Folder with the same name already exists") from exc

        await session.refresh(folder)
        return folder

    async def update_folder(
        self,
        session: AsyncSession,
        user_id: UUID,
        folder_id: UUID,
        payload: FeedFolderUpdate,
    ) -> FeedFolder:
        folder = await self.get_folder(session=session, user_id=user_id, folder_id=folder_id)
        if folder is None:
            raise FolderNotFoundError(f"Folder {folder_id} not found")

        if payload.name is not None:
            folder.name = payload.name.strip()
        if payload.description is not None:
            folder.description = payload.description.strip() or None
        if payload.sort_order is not None:
            folder.sort_order = payload.sort_order

        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise FolderConflictError("Folder with the same name already exists") from exc
        await session.refresh(folder)
        return folder

    async def delete_folder(self, session: AsyncSession, user_id: UUID, folder_id: UUID) -> None:
        folder = await self.get_folder(session=session, user_id=user_id, folder_id=folder_id)
        if folder is None:
            raise FolderNotFoundError(f"Folder {folder_id} not found")

        await session.execute(
            update(Feed).where(Feed.owner_id == user_id, Feed.folder_id == folder.id).values(folder_id=None)
        )
        await session.delete(folder)
        await session.commit()

    async def get_folder(self, session: AsyncSession, user_id: UUID, folder_id: UUID) -> FeedFolder | None:
        query = select(FeedFolder).where(FeedFolder.id == folder_id, FeedFolder.user_id == user_id)
        result = await session.execute(query)
        return result.scalar_one_or_none()


folder_service = FolderService()
