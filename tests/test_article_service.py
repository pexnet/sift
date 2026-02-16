from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, ArticleState, Feed, KeywordStream, KeywordStreamMatch, User
from sift.services.article_service import ArticleStateValidationError, article_service


@pytest.mark.asyncio
async def test_list_articles_filters_by_scope_and_state() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="article-scope@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Feed A", url="https://scope-a.example.com/rss")
        session.add(feed)
        await session.flush()

        article_one = Article(feed_id=feed.id, source_id="a1", title="Alpha", content_text="First")
        article_two = Article(feed_id=feed.id, source_id="a2", title="Beta", content_text="Second")
        session.add_all([article_one, article_two])
        await session.flush()

        session.add(
            ArticleState(
                user_id=str(user.id),
                article_id=article_one.id,
                is_read=True,
                is_starred=True,
                is_archived=False,
            )
        )
        await session.commit()

        unread = await article_service.list_articles(
            session=session,
            user_id=user.id,
            scope_type="system",
            scope_id=None,
            state="unread",
            q=None,
            limit=50,
            offset=0,
            sort="newest",
        )
        assert len(unread.items) == 1
        assert unread.items[0].id == article_two.id

        saved = await article_service.list_articles(
            session=session,
            user_id=user.id,
            scope_type="system",
            scope_id=None,
            state="saved",
            q=None,
            limit=50,
            offset=0,
            sort="newest",
        )
        assert len(saved.items) == 1
        assert saved.items[0].id == article_one.id

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_articles_scope_stream() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="article-stream@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Feed B", url="https://scope-b.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(feed_id=feed.id, source_id="s1", title="Stream Item", content_text="Payload")
        session.add(article)
        await session.flush()

        stream = KeywordStream(user_id=user.id, name="monitor", include_keywords_json='["stream"]', exclude_keywords_json="[]")
        session.add(stream)
        await session.flush()
        session.add(KeywordStreamMatch(stream_id=stream.id, article_id=article.id, match_reason="keyword: stream"))
        await session.commit()

        scoped = await article_service.list_articles(
            session=session,
            user_id=user.id,
            scope_type="stream",
            scope_id=stream.id,
            state="all",
            q=None,
            limit=50,
            offset=0,
            sort="newest",
        )
        assert len(scoped.items) == 1
        assert scoped.items[0].id == article.id
        assert scoped.items[0].stream_match_reasons is not None
        assert scoped.items[0].stream_match_reasons.get(stream.id) == "keyword: stream"

        detail = await article_service.get_article_detail(
            session=session,
            user_id=user.id,
            article_id=article.id,
        )
        assert detail.stream_match_reasons is not None
        assert detail.stream_match_reasons.get(stream.id) == "keyword: stream"

    await engine.dispose()


@pytest.mark.asyncio
async def test_patch_and_bulk_patch_state() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="article-state@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Feed C", url=f"https://scope-c-{uuid4()}.example.com/rss")
        session.add(feed)
        await session.flush()

        articles = [
            Article(feed_id=feed.id, source_id="c1", title="One", content_text="Body"),
            Article(feed_id=feed.id, source_id="c2", title="Two", content_text="Body"),
        ]
        session.add_all(articles)
        await session.commit()

        patched = await article_service.patch_state(
            session=session,
            user_id=user.id,
            article_id=articles[0].id,
            is_read=True,
            is_starred=None,
            is_archived=None,
        )
        assert patched.is_read is True

        updated_count = await article_service.bulk_patch_state(
            session=session,
            user_id=user.id,
            article_ids=[article.id for article in articles],
            is_read=None,
            is_starred=True,
            is_archived=None,
        )
        assert updated_count == 2

        listed = await article_service.list_articles(
            session=session,
            user_id=user.id,
            scope_type="system",
            scope_id=None,
            state="saved",
            q=None,
            limit=50,
            offset=0,
            sort="newest",
        )
        assert len(listed.items) == 2

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_articles_supports_advanced_query_language() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="article-search@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Threat Feed", url=f"https://search-{uuid4()}.example.com/rss")
        session.add(feed)
        await session.flush()

        session.add_all(
            [
                Article(
                    feed_id=feed.id,
                    source_id="q1",
                    title="Microsoft Sentinel incident",
                    content_text="Cloud SIEM update",
                ),
                Article(
                    feed_id=feed.id,
                    source_id="q2",
                    title="Microsoft sports bulletin",
                    content_text="Irrelevant sports news",
                ),
            ]
        )
        await session.commit()

        result = await article_service.list_articles(
            session=session,
            user_id=user.id,
            scope_type="system",
            scope_id=None,
            state="all",
            q="microsoft AND NOT sports",
            limit=50,
            offset=0,
            sort="newest",
        )
        assert len(result.items) == 1
        assert result.items[0].title == "Microsoft Sentinel incident"

    await engine.dispose()


@pytest.mark.asyncio
async def test_list_articles_rejects_invalid_advanced_query() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="article-search-invalid@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Feed", url=f"https://invalid-{uuid4()}.example.com/rss")
        session.add(feed)
        await session.flush()
        session.add(Article(feed_id=feed.id, source_id="q3", title="One", content_text="Body"))
        await session.commit()

        with pytest.raises(ArticleStateValidationError):
            await article_service.list_articles(
                session=session,
                user_id=user.id,
                scope_type="system",
                scope_id=None,
                state="all",
                q='"unterminated',
                limit=50,
                offset=0,
                sort="newest",
            )

    await engine.dispose()
