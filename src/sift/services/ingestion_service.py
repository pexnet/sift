import hashlib
import json
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from uuid import UUID

import feedparser
import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, Feed, RawEntry
from sift.domain.schemas import FeedIngestResult
from sift.plugins.base import ArticleContext
from sift.plugins.manager import PluginManager


class FeedNotFoundError(Exception):
    pass


def _safe_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _make_source_id(entry: feedparser.FeedParserDict) -> str:
    candidate = _safe_text(entry.get("id")) or _safe_text(entry.get("guid")) or _safe_text(entry.get("link"))
    if candidate:
        return candidate[:1024]

    seed = f"{_safe_text(entry.get('title'))}|{_safe_text(entry.get('published'))}|{_safe_text(entry.get('updated'))}"
    return f"hash:{hashlib.sha1(seed.encode('utf-8')).hexdigest()}"


def _extract_text(entry: feedparser.FeedParserDict) -> str:
    parts: list[str] = []

    content = entry.get("content", [])
    if isinstance(content, list):
        for part in content:
            if isinstance(part, dict):
                value = _safe_text(part.get("value"))
                if value:
                    parts.append(value)

    summary = _safe_text(entry.get("summary"))
    if summary:
        parts.append(summary)

    return "\n\n".join(parts)


def _parse_published_at(entry: feedparser.FeedParserDict) -> datetime | None:
    parsed_struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if parsed_struct:
        return datetime(
            year=parsed_struct.tm_year,
            month=parsed_struct.tm_mon,
            day=parsed_struct.tm_mday,
            hour=parsed_struct.tm_hour,
            minute=parsed_struct.tm_min,
            second=parsed_struct.tm_sec,
            tzinfo=UTC,
        )

    published_raw = _safe_text(entry.get("published")) or _safe_text(entry.get("updated"))
    if not published_raw:
        return None

    try:
        parsed = parsedate_to_datetime(published_raw)
    except (TypeError, ValueError):
        return None

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _normalize_article(entry: feedparser.FeedParserDict) -> tuple[str, str | None, str, datetime | None]:
    title = _safe_text(entry.get("title")) or "(untitled)"
    canonical_url = _safe_text(entry.get("link")) or None
    content_text = _extract_text(entry)
    published_at = _parse_published_at(entry)
    return title, canonical_url, content_text, published_at


class IngestionService:
    async def ingest_feed(self, session: AsyncSession, feed_id: UUID, plugin_manager: PluginManager) -> FeedIngestResult:
        query = select(Feed).where(Feed.id == feed_id)
        feed_result = await session.execute(query)
        feed = feed_result.scalar_one_or_none()
        if feed is None:
            raise FeedNotFoundError(f"Feed {feed_id} not found")

        result = FeedIngestResult(feed_id=feed.id)

        headers: dict[str, str] = {}
        if feed.etag:
            headers["If-None-Match"] = feed.etag
        if feed.last_modified:
            headers["If-Modified-Since"] = feed.last_modified

        try:
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(feed.url, headers=headers)
        except httpx.HTTPError as exc:
            feed.last_fetch_error = str(exc)
            feed.last_fetched_at = datetime.now(UTC)
            await session.commit()
            result.errors.append(str(exc))
            return result

        feed.last_fetched_at = datetime.now(UTC)
        feed.etag = response.headers.get("ETag", feed.etag)
        feed.last_modified = response.headers.get("Last-Modified", feed.last_modified)

        if response.status_code == 304:
            feed.last_fetch_error = None
            await session.commit()
            return result

        if response.status_code != 200:
            message = f"Unexpected status {response.status_code} while fetching {feed.url}"
            feed.last_fetch_error = message
            await session.commit()
            result.errors.append(message)
            return result

        parsed = feedparser.parse(response.content)
        entries = parsed.entries if hasattr(parsed, "entries") else []
        result.fetched_count = len(entries)

        source_ids = [_make_source_id(entry) for entry in entries]
        if source_ids:
            existing_raw_query = select(RawEntry.source_id).where(
                RawEntry.feed_id == feed.id,
                RawEntry.source_id.in_(source_ids),
            )
            existing_raw_rows = await session.execute(existing_raw_query)
            existing_source_ids = set(existing_raw_rows.scalars().all())
        else:
            existing_source_ids = set()

        for entry, source_id in zip(entries, source_ids, strict=False):
            if source_id in existing_source_ids:
                result.duplicate_count += 1
                continue

            payload = json.dumps(dict(entry), default=str)
            raw_entry = RawEntry(
                feed_id=feed.id,
                source_id=source_id,
                source_guid=_safe_text(entry.get("id")) or None,
                source_url=_safe_text(entry.get("link")) or None,
                payload=payload,
            )
            session.add(raw_entry)

            title, canonical_url, content_text, published_at = _normalize_article(entry)
            article_context = ArticleContext(
                article_id=source_id,
                title=title,
                content_text=content_text,
                metadata={"feed_id": str(feed.id), "source_id": source_id},
            )
            article_context = await plugin_manager.run_ingested_hooks(article_context)
            result.plugin_processed_count += 1

            article = Article(
                feed_id=feed.id,
                source_id=source_id,
                canonical_url=canonical_url,
                title=article_context.title or title,
                content_text=article_context.content_text or content_text,
                published_at=published_at,
            )
            session.add(article)
            result.inserted_count += 1

        feed.last_fetch_error = None
        await session.commit()
        return result


ingestion_service = IngestionService()
