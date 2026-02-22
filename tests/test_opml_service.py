import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Feed, User
from sift.services.opml_service import OpmlParseError, opml_service, parse_opml


def test_parse_opml_extracts_nested_outlines() -> None:
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head><title>Feeds</title></head>
  <body>
    <outline text="Tech">
      <outline text="Example" xmlUrl="https://example.com/rss.xml"/>
    </outline>
  </body>
</opml>
"""
    entries = parse_opml(content)
    assert len(entries) == 1
    assert entries[0].url == "https://example.com/rss.xml"
    assert entries[0].title == "Example"


def test_parse_opml_raises_on_invalid_xml() -> None:
    with pytest.raises(OpmlParseError):
        parse_opml(b"<opml><body><outline>")


@pytest.mark.asyncio
async def test_import_from_bytes_reports_created_skipped_invalid() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user_one = User(email="one@example.com")
        user_two = User(email="two@example.com")
        session.add_all([user_one, user_two])
        await session.flush()

        session.add(
            Feed(
                owner_id=user_one.id,
                title="Owned Existing",
                url="https://owned-existing.example.com/rss",
            )
        )
        session.add(
            Feed(
                owner_id=user_two.id,
                title="Other Existing",
                url="https://other-existing.example.com/rss",
            )
        )
        await session.commit()

        content = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="New Feed" xmlUrl="https://new-feed.example.com/rss"/>
    <outline text="Owned Existing" xmlUrl="https://owned-existing.example.com/rss"/>
    <outline text="Other Existing" xmlUrl="https://other-existing.example.com/rss"/>
    <outline text="Invalid" xmlUrl="ftp://invalid.example.com/rss"/>
    <outline text="Duplicate New" xmlUrl="https://new-feed.example.com/rss"/>
  </body>
</opml>
"""
        report = await opml_service.import_from_bytes(session=session, user_id=user_one.id, content=content)

        assert report.total_entries == 5
        assert report.unique_urls == 3
        assert report.created_count == 1
        assert report.skipped_existing_count == 1
        assert report.skipped_conflict_count == 1
        assert report.invalid_count == 1
        assert report.duplicate_in_file_count == 1

    await engine.dispose()
