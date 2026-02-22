from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.config import Settings
from sift.db.base import Base
from sift.db.models import Feed, FeedFolder, KeywordStream, User
from sift.services.dev_seed_service import dev_seed_service, parse_inoreader_seed_opml, parse_monitoring_keywords


def test_parse_monitoring_keywords() -> None:
    assert parse_monitoring_keywords('[Global] "Network Detection and Response"') == ["network detection and response"]
    assert parse_monitoring_keywords("microsoft AND corelight") == ["microsoft", "corelight"]


def test_parse_inoreader_seed_opml_extracts_monitoring() -> None:
    content = b"""<?xml version='1.0' encoding='UTF-8'?>
<opml version='1.0'>
  <body>
    <outline text='Tech' title='Tech'>
      <outline text='Example feed' title='Example feed' xmlUrl='https://example.com/rss' />
    </outline>
    <outline text='Monitoring feeds' title='Monitoring feeds'>
      <outline text='corelight AND microsoft' title='corelight AND microsoft' xmlUrl='keyword-monitoring-1' htmlUrl='https://www.inoreader.com/feed/keyword-monitoring-1' />
    </outline>
  </body>
</opml>
"""
    parsed = parse_inoreader_seed_opml(content)
    assert len(parsed.feeds) == 1
    assert parsed.feeds[0].folder_name == "Tech"
    assert len(parsed.monitoring_feeds) == 1
    assert parsed.monitoring_feeds[0].source_id == "keyword-monitoring-1"


@pytest.mark.asyncio
async def test_dev_seed_creates_user_feeds_folders_and_monitoring_streams(tmp_path: Path) -> None:
    opml_path = tmp_path / "seed.opml"
    opml_path.write_text(
        """<?xml version='1.0' encoding='UTF-8'?>
<opml version='1.0'>
  <body>
    <outline text='Security' title='Security'>
      <outline text='Example Feed' title='Example Feed' xmlUrl='https://example.com/rss?utm_source=test' />
    </outline>
    <outline text='Monitoring feeds' title='Monitoring feeds'>
      <outline text='microsoft AND corelight' title='microsoft AND corelight' xmlUrl='keyword-monitoring-123' htmlUrl='https://www.inoreader.com/feed/keyword-monitoring-123' />
    </outline>
  </body>
</opml>
""",
        encoding="utf-8",
    )

    settings = Settings(
        dev_seed_enabled=True,
        dev_seed_default_user_email="dev-seed@example.com",
        dev_seed_default_user_password="devpassword123!",
        dev_seed_default_user_display_name="Dev Seed",
        dev_seed_opml_path=str(opml_path),
    )

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        await dev_seed_service.run(session=session, settings=settings)
        await dev_seed_service.run(session=session, settings=settings)

        user_count = await session.scalar(select(func.count()).select_from(User))
        folder_count = await session.scalar(select(func.count()).select_from(FeedFolder))
        feed_count = await session.scalar(select(func.count()).select_from(Feed))
        stream_count = await session.scalar(select(func.count()).select_from(KeywordStream))

        assert user_count == 1
        assert folder_count == 1
        assert feed_count == 1
        assert stream_count == 1

        feed = await session.scalar(select(Feed))
        assert feed is not None
        assert feed.folder_id is not None
        assert feed.url == "https://example.com/rss?utm_source=test"

    await engine.dispose()
