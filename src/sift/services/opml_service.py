from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit
from uuid import UUID
from xml.etree import ElementTree

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Feed
from sift.domain.schemas import OpmlImportEntryResult, OpmlImportResult


class OpmlParseError(Exception):
    pass


@dataclass(slots=True)
class ParsedOpmlEntry:
    url: str
    title: str


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


def _extract_entries(node: ElementTree.Element, into: list[ParsedOpmlEntry]) -> None:
    for child in list(node):
        if not _is_outline_tag(child.tag):
            _extract_entries(child, into)
            continue

        xml_url = _attr(child, "xmlUrl", "xmlurl", "XMLURL")
        if xml_url:
            title = (_attr(child, "title", "text", "TITLE", "TEXT") or xml_url).strip()
            into.append(ParsedOpmlEntry(url=xml_url, title=title))

        _extract_entries(child, into)


def parse_opml(content: bytes) -> list[ParsedOpmlEntry]:
    try:
        root = ElementTree.fromstring(content)
    except ElementTree.ParseError as exc:
        raise OpmlParseError("Invalid OPML/XML content") from exc

    body: ElementTree.Element | None = None
    for node in root.iter():
        if _is_body_tag(node.tag):
            body = node
            break

    if body is None:
        raise OpmlParseError("OPML body element not found")

    entries: list[ParsedOpmlEntry] = []
    _extract_entries(body, entries)
    return entries


class OpmlService:
    async def import_from_bytes(
        self,
        session: AsyncSession,
        user_id: UUID,
        content: bytes,
    ) -> OpmlImportResult:
        parsed_entries = parse_opml(content)
        report = OpmlImportResult(total_entries=len(parsed_entries))

        seen_in_file: set[str] = set()
        candidates: list[ParsedOpmlEntry] = []
        for entry in parsed_entries:
            normalized_url = _normalize_feed_url(entry.url)
            if normalized_url is None:
                report.invalid_count += 1
                report.results.append(
                    OpmlImportEntryResult(
                        url=entry.url,
                        title=entry.title,
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
                        status="duplicate_in_file",
                        reason="Duplicate URL in OPML file",
                    )
                )
                continue

            seen_in_file.add(normalized_url)
            candidates.append(ParsedOpmlEntry(url=normalized_url, title=entry.title))

        report.unique_urls = len(candidates)
        if not candidates:
            return report

        existing_query = select(Feed).where(Feed.url.in_([entry.url for entry in candidates]))
        existing_result = await session.execute(existing_query)
        existing_by_url = {feed.url: feed for feed in existing_result.scalars().all()}

        for entry in candidates:
            existing = existing_by_url.get(entry.url)
            if existing is not None:
                if existing.owner_id == user_id:
                    report.skipped_existing_count += 1
                    report.results.append(
                        OpmlImportEntryResult(
                            url=entry.url,
                            title=entry.title,
                            status="skipped_existing",
                            reason="Feed already exists for this account",
                        )
                    )
                else:
                    report.skipped_conflict_count += 1
                    report.results.append(
                        OpmlImportEntryResult(
                            url=entry.url,
                            title=entry.title,
                            status="skipped_conflict",
                            reason="Feed URL already exists under another account",
                        )
                    )
                continue

            feed = Feed(
                owner_id=user_id,
                title=(entry.title or entry.url)[:255],
                url=entry.url,
            )
            session.add(feed)
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                report.skipped_conflict_count += 1
                report.results.append(
                    OpmlImportEntryResult(
                        url=entry.url,
                        title=entry.title,
                        status="skipped_conflict",
                        reason="Feed URL already exists",
                    )
                )
                continue

            report.created_count += 1
            report.results.append(
                OpmlImportEntryResult(
                    url=entry.url,
                    title=entry.title,
                    status="created",
                    reason=None,
                )
            )

        return report


opml_service = OpmlService()
