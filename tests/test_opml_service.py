import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from sift.db.base import Base
from sift.db.models import Feed, FeedFolder, User
from sift.services.opml_service import (
    MAX_OPML_BYTES,
    MAX_OPML_DEPTH,
    OpmlParseError,
    opml_service,
    parse_opml,
    parse_opml_folders,
)


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


def test_parse_opml_rejects_oversized_file() -> None:
    with pytest.raises(OpmlParseError, match="too large"):
        parse_opml(b"x" * (MAX_OPML_BYTES + 1))


def test_parse_opml_rejects_excessive_nesting_depth() -> None:
    nested_open = "".join('<outline text="nested">' for _ in range(MAX_OPML_DEPTH + 2))
    nested_close = "</outline>" * (MAX_OPML_DEPTH + 2)
    content = f"<opml><body>{nested_open}{nested_close}</body></opml>".encode()

    with pytest.raises(OpmlParseError, match="nesting depth"):
        parse_opml(content)


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
        assert report.folders_created == 1

        folders = (
            (
                await session.execute(
                    select(FeedFolder).where(FeedFolder.user_id == user_one.id).order_by(FeedFolder.name)
                )
            )
            .scalars()
            .all()
        )
        folder_names = {f.name for f in folders}
        assert folder_names == {"New Feed"}

        new_feed = (
            await session.execute(select(Feed).where(Feed.url == "https://new-feed.example.com/rss"))
        ).scalar_one()
        new_feed_folder = (
            await session.execute(select(FeedFolder).where(FeedFolder.id == new_feed.folder_id))
        ).scalar_one()
        assert new_feed_folder.name == "New Feed"

        created_result = next(r for r in report.results if r.status == "created")
        assert created_result.folder_name == "New Feed"

        invalid_result = next(r for r in report.results if r.status == "invalid")
        assert invalid_result.folder_name == "Invalid"

    await engine.dispose()


def test_parse_opml_folders_preserves_catalog_structure() -> None:
    content = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="MS">
      <outline text="Azure Weekly" xmlUrl="https://azureweekly.info/rss.xml"/>
      <outline text="Azure Status" xmlUrl="https://azurestatuscdn.azureedge.net/en-us/status/feed/"/>
    </outline>
    <outline text="Security">
      <outline text="Unit42" xmlUrl="https://feeds.feedburner.com/Unit42"/>
    </outline>
    <outline text="Flat Feed" xmlUrl="https://example.com/flat.xml"/>
  </body>
</opml>
"""
    folders = parse_opml_folders(content)
    assert [f.name for f in folders] == ["MS", "Security", "Flat Feed"]
    assert [f.feeds[0].title for f in folders] == ["Azure Weekly", "Unit42", "Flat Feed"]

    flat_entries = parse_opml(content)
    assert [e.title for e in flat_entries] == [
        "Azure Weekly",
        "Azure Status",
        "Unit42",
        "Flat Feed",
    ]


@pytest.mark.asyncio
async def test_import_creates_per_catalog_folders() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="catalog@example.com")
        session.add(user)
        await session.flush()

        content = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="MS">
      <outline text="Azure Weekly" xmlUrl="https://azureweekly.example.com/rss.xml"/>
      <outline text="Azure Status" xmlUrl="https://azure-status.example.com/feed/"/>
    </outline>
    <outline text="Security">
      <outline text="Unit42" xmlUrl="https://unit42.example.com/feed/"/>
    </outline>
  </body>
</opml>
"""
        report = await opml_service.import_from_bytes(session=session, user_id=user.id, content=content)

        assert report.created_count == 3
        assert report.folders_created == 2
        assert report.unique_urls == 3

        folders = (
            (await session.execute(select(FeedFolder).where(FeedFolder.user_id == user.id).order_by(FeedFolder.name)))
            .scalars()
            .all()
        )
        assert [f.name for f in folders] == ["MS", "Security"]

        azure_feed = (
            await session.execute(select(Feed).where(Feed.url == "https://azureweekly.example.com/rss.xml"))
        ).scalar_one()
        ms_folder = next(f for f in folders if f.name == "MS")
        assert azure_feed.folder_id == ms_folder.id

        result_by_title = {r.title: r for r in report.results}
        assert result_by_title["Azure Weekly"].folder_name == "MS"
        assert result_by_title["Azure Status"].folder_name == "MS"
        assert result_by_title["Unit42"].folder_name == "Security"

    await engine.dispose()


@pytest.mark.asyncio
async def test_import_reuses_existing_folder_on_reimport() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False)
    async with session_maker() as session:
        user = User(email="reimport@example.com")
        session.add(user)
        await session.flush()

        first = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="MS">
      <outline text="Azure Weekly" xmlUrl="https://azureweekly.example.com/rss.xml"/>
    </outline>
  </body>
</opml>
"""
        first_report = await opml_service.import_from_bytes(session=session, user_id=user.id, content=first)
        assert first_report.created_count == 1
        assert first_report.folders_created == 1

        second = b"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <body>
    <outline text="MS">
      <outline text="Azure Status" xmlUrl="https://azure-status.example.com/feed/"/>
    </outline>
  </body>
</opml>
"""
        second_report = await opml_service.import_from_bytes(session=session, user_id=user.id, content=second)
        assert second_report.created_count == 1
        assert second_report.folders_created == 0

        folders = (await session.execute(select(FeedFolder).where(FeedFolder.user_id == user.id))).scalars().all()
        assert len(folders) == 1
        assert folders[0].name == "MS"

        feeds = (await session.execute(select(Feed).where(Feed.owner_id == user.id))).scalars().all()
        assert {f.url for f in feeds} == {
            "https://azureweekly.example.com/rss.xml",
            "https://azure-status.example.com/feed/",
        }
        assert {f.folder_id for f in feeds} == {folders[0].id}

    await engine.dispose()
