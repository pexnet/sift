import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, ArticleState, Feed, FeedFolder, KeywordStream, KeywordStreamMatch, User
from sift.services.navigation_service import navigation_service


@pytest.mark.asyncio
async def test_navigation_tree_counts() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="nav@example.com")
        session.add(user)
        await session.flush()

        folder = FeedFolder(user_id=user.id, name="Security")
        session.add(folder)
        await session.flush()

        feed = Feed(owner_id=user.id, folder_id=folder.id, title="Feed", url="https://nav-feed.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(feed_id=feed.id, source_id="n1", title="Alert", content_text="Body")
        session.add(article)
        await session.flush()

        stream = KeywordStream(user_id=user.id, name="monitor", include_keywords_json='["alert"]', exclude_keywords_json="[]")
        session.add(stream)
        await session.flush()
        session.add(KeywordStreamMatch(stream_id=stream.id, article_id=article.id))
        await session.flush()

        session.add(ArticleState(user_id=str(user.id), article_id=article.id, is_read=False, is_starred=True, is_archived=False))
        await session.commit()

        tree = await navigation_service.get_navigation_tree(session=session, user_id=user.id)
        systems = {node.key: node.unread_count for node in tree.systems}
        assert systems["all"] == 1
        assert systems["saved"] == 1

        assert len(tree.folders) == 1
        assert tree.folders[0].name == "Security"
        assert tree.folders[0].unread_count == 1
        assert len(tree.folders[0].feeds) == 1
        assert tree.folders[0].feeds[0].unread_count == 1

        assert len(tree.streams) == 1
        assert tree.streams[0].unread_count == 1

    await engine.dispose()
