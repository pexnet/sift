from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID

from defusedxml import ElementTree
from defusedxml.common import DefusedXmlException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Feed, FeedFolder
from sift.domain.schemas import OpmlImportEntryResult, OpmlImportResult

MAX_OPML_BYTES = 5_000_000
MAX_OPML_DEPTH = 100


class OpmlParseError(Exception):
    pass


@dataclass(slots=True)
class ParsedOpmlEntry:
    url: str
    title: str


@dataclass(slots=True)
class ParsedOpmlFolder:
    name: str
    feeds: list[ParsedOpmlEntry]


def _is_outline_tag(tag: str) -> bool:
    return tag == "outline" or tag.endswith("}outline")


def _is_body_tag(tag: str) -> bool:
    return tag == "body" or tag.endswith("}body")


def _attr(element: ElementTree.Element, *names: str) -> str | None:
    for name in names:
        value = element.attrib.get(name)
        if value:
            return value
    return None


def _normalize_feed_url(raw_url: str) -> str | None:
    candidate = raw_url.strip()
    if not candidate:
        return None

    parsed = urlsplit(candidate)
    if parsed.scheme.lower() not in {"http", "https"}:
        return None
    if not parsed.netloc:
        return None

    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    return urlunsplit(normalized)


def _walk_outlines(
    node: ElementTree.Element,
    *,
    current_folder: str | None,
    into: list[ParsedOpmlFolder],
    depth: int,
    max_depth: int,
) -> None:
    if depth > max_depth:
        raise OpmlParseError(f"OPML nesting depth exceeds maximum of {max_depth}")

    for child in list(node):
        if not _is_outline_tag(child.tag):
            _walk_outlines(
                child,
                current_folder=current_folder,
                into=into,
                depth=depth + 1,
                max_depth=max_depth,
            )
            continue

        xml_url = _attr(child, "xmlUrl", "xmlurl", "XMLURL")
        child_outline_children = [c for c in list(child) if _is_outline_tag(c.tag)]

        if xml_url:
            folder_name = current_folder or (_attr(child, "title", "text", "TITLE", "TEXT") or "Uncategorized")
            title = (_attr(child, "title", "text", "TITLE", "TEXT") or xml_url).strip()
            into.append(ParsedOpmlFolder(name=folder_name.strip() or "Uncategorized", feeds=[]))
            into[-1].feeds.append(ParsedOpmlEntry(url=xml_url, title=title))

        if child_outline_children:
            child_folder = _attr(child, "title", "text", "TITLE", "TEXT") or "Uncategorized"
            child_folder = child_folder.strip() or "Uncategorized"
            _walk_outlines(
                child,
                current_folder=child_folder,
                into=into,
                depth=depth + 1,
                max_depth=max_depth,
            )


def parse_opml(content: bytes) -> list[ParsedOpmlEntry]:
    """Parse an OPML document into a flat list of feed entries (legacy)."""
    return [entry for folder in parse_opml_folders(content) for entry in folder.feeds]


def parse_opml_folders(content: bytes) -> list[ParsedOpmlFolder]:
    """Parse an OPML document preserving the catalog/folder structure."""
    if len(content) > MAX_OPML_BYTES:
        raise OpmlParseError(f"OPML file too large (max {MAX_OPML_BYTES} bytes)")

    try:
        root = ElementTree.fromstring(content)
    except (ElementTree.ParseError, DefusedXmlException) as exc:
        raise OpmlParseError("Invalid OPML/XML content") from exc

    body: ElementTree.Element | None = None
    for node in root.iter():
        if _is_body_tag(node.tag):
            body = node
            break

    if body is None:
        raise OpmlParseError("OPML body element not found")

    raw: list[ParsedOpmlFolder] = []
    _walk_outlines(body, current_folder=None, into=raw, depth=0, max_depth=MAX_OPML_DEPTH)

    merged: list[ParsedOpmlFolder] = []
    for folder in raw:
        if merged and merged[-1].name == folder.name:
            merged[-1].feeds.extend(folder.feeds)
        else:
            merged.append(folder)
    return merged


async def _get_or_create_folder(
    session: AsyncSession,
    user_id: UUID,
    name: str,
) -> FeedFolder:
    query = select(FeedFolder).where(FeedFolder.user_id == user_id, FeedFolder.name == name)
    existing = (await session.execute(query)).scalar_one_or_none()
    if existing is not None:
        return existing

    folder = FeedFolder(user_id=user_id, name=name)
    session.add(folder)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        existing = (await session.execute(query)).scalar_one_or_none()
        if existing is not None:
            return existing
        raise OpmlParseError(f"Could not create folder {name!r}: {exc}") from exc
    return folder


class OpmlService:
    async def import_from_bytes(
        self,
        session: AsyncSession,
        user_id: UUID,
        content: bytes,
    ) -> OpmlImportResult:
        parsed_folders = parse_opml_folders(content)
        report = OpmlImportResult(total_entries=0)

        all_candidates: list[tuple[str, str, str]] = []
        seen_in_file: set[str] = set()
        for parsed_folder in parsed_folders:
            for entry in parsed_folder.feeds:
                report.total_entries += 1
                normalized_url = _normalize_feed_url(entry.url)
                if normalized_url is None:
                    report.invalid_count += 1
                    report.results.append(
                        OpmlImportEntryResult(
                            url=entry.url,
                            title=entry.title,
                            folder_name=parsed_folder.name,
                            status="invalid",
                            reason="Unsupported or invalid feed URL",
                        )
                    )
                    continue

                if normalized_url in seen_in_file:
                    report.duplicate_in_file_count += 1
                    report.results.append(
                        OpmlImportEntryResult(
                            url=normalized_url,
                            title=entry.title,
                            folder_name=parsed_folder.name,
                            status="duplicate_in_file",
                            reason="Duplicate URL in OPML file",
                        )
                    )
                    continue

                seen_in_file.add(normalized_url)
                all_candidates.append((normalized_url, entry.title, parsed_folder.name))

        report.unique_urls = len(all_candidates)
        if not all_candidates:
            return report

        candidate_urls = [url for url, _title, _folder in all_candidates]
        existing_query = select(Feed).where(Feed.url.in_(candidate_urls))
        existing_result = await session.execute(existing_query)
        existing_by_url = {feed.url: feed for feed in existing_result.scalars().all()}

        folder_cache: dict[str, FeedFolder] = {}
        folders_created = 0
        for normalized_url, title, folder_name in all_candidates:
            existing = existing_by_url.get(normalized_url)
            if existing is not None:
                if existing.owner_id == user_id:
                    report.skipped_existing_count += 1
                    report.results.append(
                        OpmlImportEntryResult(
                            url=normalized_url,
                            title=title,
                            folder_name=folder_name,
                            status="skipped_existing",
                            reason="Feed already exists for this account",
                        )
                    )
                else:
                    report.skipped_conflict_count += 1
                    report.results.append(
                        OpmlImportEntryResult(
                            url=normalized_url,
                            title=title,
                            folder_name=folder_name,
                            status="skipped_conflict",
                            reason="Feed URL already exists under another account",
                        )
                    )
                continue

            cached = folder_cache.get(folder_name)
            if cached is None:
                before = await session.execute(
                    select(FeedFolder.id).where(FeedFolder.user_id == user_id, FeedFolder.name == folder_name)
                )
                existed_before = before.scalar_one_or_none() is not None
                folder = await _get_or_create_folder(session, user_id, folder_name)
                folder_cache[folder_name] = folder
                if not existed_before:
                    folders_created += 1
            else:
                folder = cached

            feed = Feed(
                owner_id=user_id,
                folder_id=folder.id,
                title=(title or normalized_url)[:255],
                url=normalized_url,
            )
            session.add(feed)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                report.skipped_conflict_count += 1
                report.results.append(
                    OpmlImportEntryResult(
                        url=normalized_url,
                        title=title,
                        folder_name=folder_name,
                        status="skipped_conflict",
                        reason="Feed URL already exists",
                    )
                )
                continue

            report.created_count += 1
            report.results.append(
                OpmlImportEntryResult(
                    url=normalized_url,
                    title=title,
                    folder_name=folder_name,
                    status="created",
                    reason=None,
                )
            )

        report.folders_created = folders_created
        return report


opml_service = OpmlService()
