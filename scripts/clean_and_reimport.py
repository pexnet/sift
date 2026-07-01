"""Clean a user's feed/subscription/article data, then reimport an OPML file.

Usage (inside the backend container):
    uv run python scripts/clean_and_reimport.py --opml <path> [--user-email <email>] [--apply]

Default mode is dry-run: prints counts of rows that would be deleted and
the import that would be run, without modifying the database. Pass --apply
to actually delete and reimport.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Sequence

from sqlalchemy import delete, func, select

# Make the 'sift' package importable when running inside the container.
sys.path.insert(0, os.environ.get("PYTHONPATH", "/app/src"))

from sift.db.models import (  # noqa: E402
    Article,
    ArticleState,
    Feed,
    FeedFolder,
    RawEntry,
    Subscription,
    User,
)
from sift.db.session import SessionLocal  # noqa: E402
from sift.services.opml_service import opml_service  # noqa: E402


async def _count_for_user(session, user_id) -> dict[str, int]:
    counts: dict[str, int] = {}

    counts["folders"] = (
        await session.execute(
            select(func.count(FeedFolder.id)).where(FeedFolder.user_id == user_id)
        )
    ).scalar_one()

    feed_ids_q = select(Feed.id).where(Feed.owner_id == user_id)
    feed_ids_subq = feed_ids_q.subquery()
    counts["feeds"] = (
        await session.execute(
            select(func.count(Feed.id)).where(Feed.owner_id == user_id)
        )
    ).scalar_one()

    counts["articles"] = (
        await session.execute(
            select(func.count(Article.id)).where(Article.feed_id.in_(feed_ids_subq))
        )
    ).scalar_one()

    counts["raw_entries"] = (
        await session.execute(
            select(func.count(RawEntry.id)).where(RawEntry.feed_id.in_(feed_ids_subq))
        )
    ).scalar_one()

    counts["subscriptions"] = (
        await session.execute(
            select(func.count(Subscription.id)).where(Subscription.user_id == str(user_id))
        )
    ).scalar_one()

    counts["article_states"] = (
        await session.execute(
            select(func.count(ArticleState.id)).where(ArticleState.user_id == str(user_id))
        )
    ).scalar_one()

    return counts


async def _delete_user_data(session, user_id) -> None:
    feed_ids_subq = select(Feed.id).where(Feed.owner_id == user_id).subquery()
    article_ids_subq = (
        select(Article.id).where(Article.feed_id.in_(feed_ids_subq)).subquery()
    )

    await session.execute(
        delete(ArticleState).where(ArticleState.user_id == str(user_id))
    )
    await session.execute(
        delete(Subscription).where(Subscription.user_id == str(user_id))
    )
    await session.execute(
        delete(Article).where(Article.feed_id.in_(feed_ids_subq))
    )
    await session.execute(
        delete(RawEntry).where(RawEntry.feed_id.in_(feed_ids_subq))
    )
    await session.execute(delete(Feed).where(Feed.owner_id == user_id))
    await session.execute(delete(FeedFolder).where(FeedFolder.user_id == user_id))
    await session.commit()


async def _import_opml(session, user_id, opml_path: Path) -> dict:
    content = opml_path.read_bytes()
    report = await opml_service.import_from_bytes(
        session=session, user_id=user_id, content=content
    )
    await session.commit()
    return report.model_dump()


async def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--opml", required=True, type=Path, help="Path to the OPML file")
    parser.add_argument(
        "--user-email",
        default=os.environ.get("SIFT_DEV_SEED_DEFAULT_USER_EMAIL", "dev@sift.dev"),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete rows and import. Without this, the run is a dry-run.",
    )
    args = parser.parse_args(argv)

    async with SessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.email == args.user_email))
        ).scalar_one_or_none()
        if user is None:
            print(f"ERROR: user {args.user_email!r} not found")
            return 2

        counts = await _count_for_user(session, user.id)
        print(f"user: {user.email} ({user.id})")
        print("would_delete:")
        for k, v in counts.items():
            print(f"  {k:15s} {v}")
        if not args.opml.exists():
            print(f"ERROR: OPML file {args.opml} does not exist")
            return 2
        opml_size = args.opml.stat().st_size
        print(f"\nopml_path: {args.opml}  size={opml_size} bytes")

        if not args.apply:
            print("\nDRY RUN: pass --apply to perform the deletion and reimport")
            return 0

        print("\napplying: deleting user data...")
        await _delete_user_data(session, user.id)
        after_delete = await _count_for_user(session, user.id)
        print("after_delete:")
        for k, v in after_delete.items():
            print(f"  {k:15s} {v}")

        print("\napplying: importing OPML...")
        import_result = await _import_opml(session, user.id, args.opml)
        summary = {k: v for k, v in import_result.items() if k != "results"}
        print("import_summary:")
        for k, v in summary.items():
            print(f"  {k:22s} {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
