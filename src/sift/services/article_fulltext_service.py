import html
import ipaddress
import re
import socket
from datetime import UTC, datetime
from typing import Final, Literal, cast
from urllib.parse import urlparse
from uuid import UUID

import httpx
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article, ArticleFulltext, Feed
from sift.domain.schemas import ArticleFulltextFetchOut
from sift.services.article_service import ArticleNotFoundError

_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})
_FETCH_TIMEOUT_SECONDS: Final[float] = 20.0
_MAX_RESPONSE_BYTES: Final[int] = 2_000_000
_EXTRACTOR_NAME: Final[str] = "builtin_simple_html_v1"
FulltextStatus = Literal["idle", "pending", "succeeded", "failed"]

_TAG_BLOCK_RE = re.compile(r"(?is)<(script|style|noscript).*?>.*?</\1>")
_COMMENT_RE = re.compile(r"(?is)<!--.*?-->")
_BODY_TAG_RE = re.compile(r"(?is)<body\b[^>]*>(.*?)</body>")
_MAIN_TAG_RE = re.compile(r"(?is)<main\b[^>]*>(.*?)</main>")
_ARTICLE_TAG_RE = re.compile(r"(?is)<article\b[^>]*>(.*?)</article>")
_TAG_RE = re.compile(r"(?is)<[^>]+>")
_WS_RE = re.compile(r"\s+")


class ArticleFulltextValidationError(Exception):
    pass


class ArticleFulltextService:
    async def fetch_for_article(
        self,
        *,
        session: AsyncSession,
        user_id: UUID,
        article_id: UUID,
    ) -> ArticleFulltextFetchOut:
        article = await self._get_visible_article(session=session, user_id=user_id, article_id=article_id)
        row = await self._get_or_create_row(
            session=session,
            article_id=article.id,
            source_url=article.canonical_url,
        )

        row.status = "pending"
        row.error_message = None
        row.source_url = article.canonical_url
        row.final_url = None
        row.content_text = None
        row.content_html = None
        row.extractor = None
        await session.flush()

        try:
            source_url = article.canonical_url
            if not source_url:
                raise ArticleFulltextValidationError("Article has no canonical URL to fetch.")

            validated_url = _validate_fetch_url(source_url)
            final_url, payload = await self._fetch_source_page(validated_url)
            extracted_html, extracted_text = _extract_readable_content(payload)

            row.status = "succeeded"
            row.final_url = final_url
            row.content_html = extracted_html
            row.content_text = extracted_text
            row.extractor = _EXTRACTOR_NAME
            row.error_message = None
            row.fetched_at = datetime.now(UTC)
        except ArticleFulltextValidationError as exc:
            row.status = "failed"
            row.error_message = str(exc)
            row.fetched_at = None
        except Exception as exc:  # noqa: BLE001
            row.status = "failed"
            row.error_message = f"Fetch failed: {exc}"
            row.fetched_at = None

        await session.commit()
        return _to_fetch_out(row)

    async def get_for_article(self, *, session: AsyncSession, article_id: UUID) -> ArticleFulltext | None:
        result = await session.execute(select(ArticleFulltext).where(ArticleFulltext.article_id == article_id))
        return result.scalar_one_or_none()

    async def _fetch_source_page(self, url: str) -> tuple[str, str]:
        async with httpx.AsyncClient(timeout=_FETCH_TIMEOUT_SECONDS, follow_redirects=True) as client:
            response = await client.get(url, headers={"User-Agent": "sift-fulltext-fetch/1.0"})

        if response.status_code != 200:
            raise ArticleFulltextValidationError(f"Unexpected status {response.status_code} while fetching source page.")

        content_type = (response.headers.get("Content-Type") or "").lower()
        if content_type and "text/html" not in content_type:
            raise ArticleFulltextValidationError("Source response is not HTML content.")

        body = response.content
        if len(body) > _MAX_RESPONSE_BYTES:
            raise ArticleFulltextValidationError("Source response exceeded size limit.")

        try:
            payload = body.decode(response.encoding or "utf-8", errors="replace")
        except LookupError as exc:
            raise ArticleFulltextValidationError(f"Unsupported response encoding: {exc}") from exc

        return str(response.url), payload

    async def _get_visible_article(self, *, session: AsyncSession, user_id: UUID, article_id: UUID) -> Article:
        query = (
            select(Article)
            .join(Feed, Feed.id == Article.feed_id)
            .where(and_(Article.id == article_id, Feed.owner_id == user_id))
        )
        result = await session.execute(query)
        article = result.scalar_one_or_none()
        if article is None:
            raise ArticleNotFoundError(f"Article {article_id} not found")
        return article

    async def _get_or_create_row(
        self,
        *,
        session: AsyncSession,
        article_id: UUID,
        source_url: str | None,
    ) -> ArticleFulltext:
        existing = await self.get_for_article(session=session, article_id=article_id)
        if existing is not None:
            return existing

        row = ArticleFulltext(
            article_id=article_id,
            status="idle",
            source_url=source_url,
        )
        session.add(row)
        await session.flush()
        return row


def _to_fetch_out(row: ArticleFulltext) -> ArticleFulltextFetchOut:
    status = _normalize_status(row.status)
    return ArticleFulltextFetchOut(
        article_id=row.article_id,
        status=status,
        error_message=row.error_message,
        fetched_at=row.fetched_at,
        content_source="full_article" if status == "succeeded" and bool(row.content_text) else "feed_excerpt",
    )


def _normalize_status(value: str) -> FulltextStatus:
    if value in {"idle", "pending", "succeeded", "failed"}:
        return cast(FulltextStatus, value)
    return "failed"


def _validate_fetch_url(raw_url: str) -> str:
    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ArticleFulltextValidationError("Unsupported URL scheme. Only http/https are allowed.")
    if not parsed.hostname:
        raise ArticleFulltextValidationError("Canonical URL is missing a hostname.")

    _assert_public_host(parsed.hostname)
    return parsed.geturl()


def _assert_public_host(hostname: str) -> None:
    if hostname.lower() == "localhost":
        raise ArticleFulltextValidationError("Loopback/localhost fetch targets are not allowed.")

    try:
        _assert_public_ip(ipaddress.ip_address(hostname))
        return
    except ValueError:
        pass

    try:
        addresses = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise ArticleFulltextValidationError(f"Failed resolving canonical URL host: {exc}") from exc

    for entry in addresses:
        ip_raw = entry[4][0]
        _assert_public_ip(ipaddress.ip_address(ip_raw))


def _assert_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        raise ArticleFulltextValidationError("Private or non-routable fetch targets are not allowed.")


def _extract_readable_content(payload: str) -> tuple[str, str]:
    cleaned = _COMMENT_RE.sub(" ", _TAG_BLOCK_RE.sub(" ", payload))
    fragment = _pick_primary_fragment(cleaned)
    fragment = fragment.strip()
    if not fragment:
        raise ArticleFulltextValidationError("No readable content found in source page.")

    text = html.unescape(_TAG_RE.sub(" ", fragment))
    text = _WS_RE.sub(" ", text).strip()
    if not text:
        raise ArticleFulltextValidationError("No readable text content found in source page.")

    return fragment, text


def _pick_primary_fragment(payload: str) -> str:
    for pattern in (_ARTICLE_TAG_RE, _MAIN_TAG_RE, _BODY_TAG_RE):
        match = pattern.search(payload)
        if match:
            return match.group(1)
    return payload


article_fulltext_service = ArticleFulltextService()
