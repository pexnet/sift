import hashlib
from dataclasses import dataclass
from typing import Final
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article

TRACKING_QUERY_PARAMS: Final[set[str]] = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def normalize_canonical_url(url: str | None) -> str | None:
    if not url:
        return None

    value = url.strip()
    if not value:
        return None

    parsed = urlsplit(value)
    if not parsed.scheme or not parsed.netloc:
        return value.lower()

    scheme = parsed.scheme.lower()
    hostname = (parsed.hostname or "").lower()
    if not hostname:
        return value.lower()

    port = parsed.port
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        netloc = hostname
    elif port:
        netloc = f"{hostname}:{port}"
    else:
        netloc = hostname

    path = parsed.path or "/"
    if path != "/" and path.endswith("/"):
        path = path.rstrip("/")

    query_pairs = parse_qsl(parsed.query, keep_blank_values=False)
    filtered_pairs = [(k, v) for k, v in query_pairs if k.lower() not in TRACKING_QUERY_PARAMS]
    filtered_pairs.sort(key=lambda pair: (pair[0], pair[1]))
    query = urlencode(filtered_pairs, doseq=True)

    return urlunsplit((scheme, netloc, path, query, ""))


def build_content_fingerprint(*, title: str, content_text: str) -> str | None:
    seed = f"{title}\n{content_text}".strip().lower()
    if not seed:
        return None
    collapsed = " ".join(seed.split())
    if not collapsed:
        return None
    return hashlib.sha256(collapsed.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class CanonicalDuplicateDecision:
    duplicate_of_id: UUID | None = None
    confidence: float = 0.0
    reason: str = ""


def _candidate_confidence(
    *,
    incoming_url: str | None,
    incoming_fingerprint: str | None,
    candidate_url: str | None,
    candidate_fingerprint: str | None,
) -> tuple[float, str]:
    url_match = bool(incoming_url and candidate_url and incoming_url == candidate_url)
    fingerprint_match = bool(
        incoming_fingerprint and candidate_fingerprint and incoming_fingerprint == candidate_fingerprint
    )
    if url_match and fingerprint_match:
        return 1.0, "url_and_content"
    if url_match:
        return 0.92, "url"
    if fingerprint_match:
        return 0.82, "content"
    return 0.0, ""


class CrossFeedDedupService:
    async def resolve_canonical_duplicate(
        self,
        *,
        session: AsyncSession,
        canonical_url_normalized: str | None,
        content_fingerprint: str | None,
    ) -> CanonicalDuplicateDecision:
        predicates = []
        if canonical_url_normalized:
            predicates.append(Article.canonical_url_normalized == canonical_url_normalized)
        if content_fingerprint:
            predicates.append(Article.content_fingerprint == content_fingerprint)
        if not predicates:
            return CanonicalDuplicateDecision()

        query = (
            select(
                Article.id,
                Article.duplicate_of_id,
                Article.canonical_url_normalized,
                Article.content_fingerprint,
                Article.created_at,
            )
            .where(or_(*predicates))
            .order_by(Article.created_at.desc())
            .limit(50)
        )
        rows = await session.execute(query)

        best_article_id: UUID | None = None
        best_confidence = 0.0
        best_reason = ""
        for row in rows:
            confidence, reason = _candidate_confidence(
                incoming_url=canonical_url_normalized,
                incoming_fingerprint=content_fingerprint,
                candidate_url=row.canonical_url_normalized,
                candidate_fingerprint=row.content_fingerprint,
            )
            if confidence <= best_confidence:
                continue
            best_article_id = row.duplicate_of_id or row.id
            best_confidence = confidence
            best_reason = reason

        if best_article_id is None:
            return CanonicalDuplicateDecision()
        return CanonicalDuplicateDecision(
            duplicate_of_id=best_article_id,
            confidence=best_confidence,
            reason=best_reason,
        )


dedup_service = CrossFeedDedupService()
