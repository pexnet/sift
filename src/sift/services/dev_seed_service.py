import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.config import Settings
from sift.db.models import Feed, FeedFolder, User
from sift.domain.schemas import KeywordStreamCreate
from sift.services.auth_service import auth_service, normalize_email
from sift.services.stream_service import StreamConflictError, StreamValidationError, stream_service

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ParsedSeedFeed:
    title: str
    xml_url: str
    folder_name: str | None


@dataclass(slots=True)
class ParsedMonitoringFeed:
    title: str
    source_id: str
    source_url: str | None


@dataclass(slots=True)
class ParsedInoreaderSeed:
    feeds: list[ParsedSeedFeed]
    monitoring_feeds: list[ParsedMonitoringFeed]


def _is_outline_tag(tag: str) -> bool:
    return tag == "outline" or tag.endswith("}outline")


def _is_body_tag(tag: str) -> bool:
    return tag == "body" or tag.endswith("}body")


def _attr(element: ElementTree.Element, *names: str) -> str | None:
    for name in names:
        value = element.attrib.get(name)
        if value:
            return value.strip()
    return None


def _normalize_feed_url(raw_url: str) -> str | None:
    value = raw_url.strip()
    if not value:
        return None

    parsed = urlsplit(value)
    if parsed.scheme.lower() not in {"http", "https"} or not parsed.netloc:
        return None

    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    return urlunsplit(normalized)


def parse_monitoring_keywords(expression: str) -> list[str]:
    cleaned = re.sub(r"^\[[^\]]+\]\s*", "", expression).strip()
    if not cleaned:
        return []

    tokens: list[str] = []
    for match in re.finditer(r'"([^"]+)"|([^\s]+)', cleaned):
        candidate = (match.group(1) or match.group(2) or "").strip().strip("()").strip()
        if not candidate:
            continue
        if candidate.upper() in {"AND", "OR", "NOT"}:
            continue
        tokens.append(candidate.lower())

    deduped: list[str] = []
    seen: set[str] = set()
    for token in tokens:
        if token not in seen:
            deduped.append(token)
            seen.add(token)

    return deduped


def _walk_outlines(
    node: ElementTree.Element,
    *,
    top_folder: str | None,
    monitoring_folder_name: str,
    into_feeds: list[ParsedSeedFeed],
    into_monitoring: list[ParsedMonitoringFeed],
) -> None:
    for child in list(node):
        if not _is_outline_tag(child.tag):
            _walk_outlines(
                child,
                top_folder=top_folder,
                monitoring_folder_name=monitoring_folder_name,
                into_feeds=into_feeds,
                into_monitoring=into_monitoring,
            )
            continue

        title = _attr(child, "title", "text", "TITLE", "TEXT") or ""
        xml_url = _attr(child, "xmlUrl", "xmlurl", "XMLURL")
        html_url = _attr(child, "htmlUrl", "htmlurl", "HTMLURL")

        child_folder = top_folder
        if xml_url is None and title:
            child_folder = title

        is_monitoring = bool(
            (top_folder and top_folder.strip().lower() == monitoring_folder_name.strip().lower())
            or (child_folder and child_folder.strip().lower() == monitoring_folder_name.strip().lower())
            or (xml_url and xml_url.lower().startswith("keyword-monitoring-"))
        )

        if xml_url:
            if is_monitoring:
                into_monitoring.append(
                    ParsedMonitoringFeed(
                        title=(title or xml_url),
                        source_id=xml_url,
                        source_url=html_url,
                    )
                )
            else:
                into_feeds.append(
                    ParsedSeedFeed(
                        title=(title or xml_url),
                        xml_url=xml_url,
                        folder_name=top_folder,
                    )
                )

        _walk_outlines(
            child,
            top_folder=child_folder,
            monitoring_folder_name=monitoring_folder_name,
            into_feeds=into_feeds,
            into_monitoring=into_monitoring,
        )


def parse_inoreader_seed_opml(content: bytes, *, monitoring_folder_name: str = "Monitoring feeds") -> ParsedInoreaderSeed:
    root = ElementTree.fromstring(content)
    body: ElementTree.Element | None = None
    for node in root.iter():
        if _is_body_tag(node.tag):
            body = node
            break

    if body is None:
        raise ValueError("OPML body element not found")

    feeds: list[ParsedSeedFeed] = []
    monitoring: list[ParsedMonitoringFeed] = []
    _walk_outlines(
        body,
        top_folder=None,
        monitoring_folder_name=monitoring_folder_name,
        into_feeds=feeds,
        into_monitoring=monitoring,
    )
    return ParsedInoreaderSeed(feeds=feeds, monitoring_feeds=monitoring)


class DevSeedService:
    async def run(self, session: AsyncSession, settings: Settings) -> None:
        user = await self._get_or_create_dev_user(session=session, settings=settings)
        opml_path = self._resolve_opml_path(settings)
        if opml_path is None:
            logger.info("Dev seed: OPML path not configured or file missing, seeded user only")
            return

        content = opml_path.read_bytes()
        parsed = parse_inoreader_seed_opml(content, monitoring_folder_name=settings.dev_seed_monitoring_folder_name)
        await self._seed_feeds_and_folders(session=session, user_id=user.id, feeds=parsed.feeds)
        await self._seed_monitoring_streams(session=session, user_id=user.id, monitoring_feeds=parsed.monitoring_feeds)

    def _resolve_opml_path(self, settings: Settings) -> Path | None:
        candidate_paths: list[Path] = []
        if settings.dev_seed_opml_path:
            candidate_paths.append(Path(settings.dev_seed_opml_path))
        candidate_paths.append(Path("dev-data/local-seed.opml"))
        candidate_paths.append(Path("dev-data/public-sample.opml"))

        for candidate in candidate_paths:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    async def _get_or_create_dev_user(self, session: AsyncSession, settings: Settings) -> User:
        email = normalize_email(settings.dev_seed_default_user_email)
        user_query = select(User).where(User.email == email)
        user_result = await session.execute(user_query)
        existing = user_result.scalar_one_or_none()
        if existing is not None:
            return existing

        return await auth_service.register_local_user(
            session=session,
            email=email,
            password=settings.dev_seed_default_user_password,
            display_name=settings.dev_seed_default_user_display_name,
        )

    async def _seed_feeds_and_folders(self, session: AsyncSession, user_id: UUID, feeds: list[ParsedSeedFeed]) -> None:
        existing_folders_query = select(FeedFolder).where(FeedFolder.user_id == user_id)
        existing_folders_result = await session.execute(existing_folders_query)
        folders_by_name = {folder.name.strip().lower(): folder for folder in existing_folders_result.scalars().all()}

        normalized_feed_entries: list[tuple[ParsedSeedFeed, str]] = []
        for entry in feeds:
            normalized = _normalize_feed_url(entry.xml_url)
            if normalized:
                normalized_feed_entries.append((entry, normalized))

        if not normalized_feed_entries:
            return

        existing_feed_query = select(Feed).where(Feed.url.in_([item[1] for item in normalized_feed_entries]))
        existing_feed_result = await session.execute(existing_feed_query)
        existing_feeds_by_url = {feed.url: feed for feed in existing_feed_result.scalars().all()}

        for entry, normalized_url in normalized_feed_entries:
            folder_id: UUID | None = None
            if entry.folder_name:
                key = entry.folder_name.strip().lower()
                folder = folders_by_name.get(key)
                if folder is None:
                    folder = FeedFolder(
                        user_id=user_id,
                        name=entry.folder_name.strip()[:255],
                        description="Imported from OPML",
                        sort_order=100,
                    )
                    session.add(folder)
                    await session.flush()
                    folders_by_name[key] = folder
                folder_id = folder.id

            existing_feed = existing_feeds_by_url.get(normalized_url)
            if existing_feed is None:
                feed = Feed(
                    owner_id=user_id,
                    folder_id=folder_id,
                    title=(entry.title or normalized_url)[:255],
                    url=normalized_url,
                )
                session.add(feed)
                existing_feeds_by_url[normalized_url] = feed
                continue

            if existing_feed.owner_id != user_id:
                continue
            if folder_id is not None and existing_feed.folder_id != folder_id:
                existing_feed.folder_id = folder_id

        await session.commit()

    async def _seed_monitoring_streams(
        self,
        session: AsyncSession,
        user_id: UUID,
        monitoring_feeds: list[ParsedMonitoringFeed],
    ) -> None:
        for item in monitoring_feeds:
            description_payload = {
                "source": "inoreader-monitoring",
                "source_id": item.source_id,
                "source_url": item.source_url,
                "expression": item.title,
            }
            keywords = parse_monitoring_keywords(item.title)
            if not keywords:
                keywords = [item.title.strip().lower()]

            payload = KeywordStreamCreate(
                name=item.title[:255],
                description=json.dumps(description_payload)[:1000],
                include_keywords=keywords,
            )
            try:
                await stream_service.create_stream(session=session, user_id=user_id, payload=payload)
            except (StreamConflictError, StreamValidationError):
                continue


dev_seed_service = DevSeedService()
