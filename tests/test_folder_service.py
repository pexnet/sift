import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Feed, User
from sift.domain.schemas import FeedCreate, FeedFolderCreate, FeedFolderUpdate
from sift.services.feed_service import FeedFolderNotFoundError, feed_service
from sift.services.folder_service import FolderConflictError, FolderNotFoundError, folder_service


@pytest.mark.asyncio
async def test_folder_crud_and_delete_unassigns_feeds() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="folders@example.com")
        session.add(user)
        await session.commit()

        created = await folder_service.create_folder(
            session=session,
            user_id=user.id,
            payload=FeedFolderCreate(name="News", description="Main feed folder", sort_order=10),
        )
        assert created.name == "News"

        updated = await folder_service.update_folder(
            session=session,
            user_id=user.id,
            folder_id=created.id,
            payload=FeedFolderUpdate(description="Updated", sort_order=20),
        )
        assert updated.description == "Updated"
        assert updated.sort_order == 20

        feed = await feed_service.create_feed(
            session=session,
            data=FeedCreate(title="Feed", url="https://folder-feed.example.com/rss"),
            user_id=user.id,
        )
        feed = await feed_service.assign_folder(
            session=session,
            feed=feed,
            user_id=user.id,
            folder_id=created.id,
        )
        assert feed.folder_id == created.id

        await folder_service.delete_folder(session=session, user_id=user.id, folder_id=created.id)

        feed_query = select(Feed).where(Feed.id == feed.id)
        feed_result = await session.execute(feed_query)
        stored_feed = feed_result.scalar_one()
        assert stored_feed.folder_id is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_folder_name_conflict_same_user() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="folders2@example.com")
        session.add(user)
        await session.commit()

        payload = FeedFolderCreate(name="Security", sort_order=100)
        await folder_service.create_folder(session=session, user_id=user.id, payload=payload)
        with pytest.raises(FolderConflictError):
            await folder_service.create_folder(session=session, user_id=user.id, payload=payload)

    await engine.dispose()


@pytest.mark.asyncio
async def test_same_folder_name_allowed_across_users() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user_one = User(email="folders3@example.com")
        user_two = User(email="folders4@example.com")
        session.add_all([user_one, user_two])
        await session.commit()

        payload = FeedFolderCreate(name="Shared Name")
        one = await folder_service.create_folder(session=session, user_id=user_one.id, payload=payload)
        two = await folder_service.create_folder(session=session, user_id=user_two.id, payload=payload)
        assert one.id != two.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_assign_folder_rejects_other_users_folder() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        owner = User(email="owner@example.com")
        other = User(email="other@example.com")
        session.add_all([owner, other])
        await session.commit()

        feed = await feed_service.create_feed(
            session=session,
            data=FeedCreate(title="Owner Feed", url="https://owner-feed.example.com/rss"),
            user_id=owner.id,
        )
        foreign_folder = await folder_service.create_folder(
            session=session,
            user_id=other.id,
            payload=FeedFolderCreate(name="Foreign"),
        )

        with pytest.raises(FeedFolderNotFoundError):
            await feed_service.assign_folder(
                session=session,
                feed=feed,
                user_id=owner.id,
                folder_id=foreign_folder.id,
            )

        with pytest.raises(FolderNotFoundError):
            await folder_service.delete_folder(session=session, user_id=owner.id, folder_id=foreign_folder.id)

    await engine.dispose()
