from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Article, ArticleFulltext, Feed, User
from sift.services.article_fulltext_service import article_fulltext_service
from sift.services.article_service import ArticleNotFoundError, article_service


@pytest.mark.asyncio
async def test_fetch_for_article_success_persists_fulltext(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="fulltext-success@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Fulltext Feed", url=f"https://fulltext-{uuid4()}.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(
            feed_id=feed.id,
            source_id="f1",
            canonical_url="https://example.com/article",
            title="Title",
            content_text="Excerpt",
        )
        session.add(article)
        await session.commit()

        async def fake_fetch_source_page(url: str) -> tuple[str, str]:
            assert url == "https://example.com/article"
            return (
                "https://example.com/article?ref=final",
                "<html><body><article><h1>Title</h1><p>Full article content.</p></article></body></html>",
            )

        monkeypatch.setattr(article_fulltext_service, "_fetch_source_page", fake_fetch_source_page)
        result = await article_fulltext_service.fetch_for_article(
            session=session,
            user_id=user.id,
            article_id=article.id,
        )

        assert result.status == "succeeded"
        assert result.content_source == "full_article"

        detail = await article_service.get_article_detail(session=session, user_id=user.id, article_id=article.id)
        assert detail.fulltext_status == "succeeded"
        assert detail.content_source == "full_article"
        assert detail.fulltext_content_text is not None
        assert "Full article content." in detail.fulltext_content_text

        stored_result = await session.execute(select(ArticleFulltext).where(ArticleFulltext.article_id == article.id))
        stored = stored_result.scalar_one_or_none()
        assert stored is not None
        assert stored.status == "succeeded"
        assert stored.final_url == "https://example.com/article?ref=final"
        assert stored.extractor == "builtin_simple_html_v1"

    await engine.dispose()


@pytest.mark.asyncio
async def test_fetch_for_article_invalid_url_sets_failed_status() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        user = User(email="fulltext-invalid-url@example.com")
        session.add(user)
        await session.flush()

        feed = Feed(owner_id=user.id, title="Fulltext Feed", url=f"https://fulltext-{uuid4()}.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(
            feed_id=feed.id,
            source_id="f2",
            canonical_url="ftp://example.com/article",
            title="Title",
            content_text="Excerpt",
        )
        session.add(article)
        await session.commit()

        result = await article_fulltext_service.fetch_for_article(
            session=session,
            user_id=user.id,
            article_id=article.id,
        )
        assert result.status == "failed"
        assert result.content_source == "feed_excerpt"
        assert result.error_message is not None
        assert "Unsupported URL scheme" in result.error_message

        detail = await article_service.get_article_detail(session=session, user_id=user.id, article_id=article.id)
        assert detail.fulltext_status == "failed"
        assert detail.content_source == "feed_excerpt"
        assert detail.fulltext_content_text is None

    await engine.dispose()


@pytest.mark.asyncio
async def test_fetch_for_article_requires_ownership() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_maker() as session:
        owner = User(email="fulltext-owner@example.com")
        other = User(email="fulltext-other@example.com")
        session.add_all([owner, other])
        await session.flush()

        feed = Feed(owner_id=owner.id, title="Owner Feed", url=f"https://owner-{uuid4()}.example.com/rss")
        session.add(feed)
        await session.flush()

        article = Article(
            feed_id=feed.id,
            source_id="f3",
            canonical_url="https://example.com/article",
            title="Title",
            content_text="Excerpt",
        )
        session.add(article)
        await session.commit()

        with pytest.raises(ArticleNotFoundError):
            await article_fulltext_service.fetch_for_article(
                session=session,
                user_id=other.id,
                article_id=article.id,
            )

    await engine.dispose()
