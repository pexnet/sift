from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sift.db.models import Article


def _normalize_keywords(keywords: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for keyword in keywords:
        item = keyword.strip().lower()
        if item and item not in seen:
            normalized.append(item)
            seen.add(item)
    return normalized


def _matches_keywords(content: str, include_keywords: list[str], exclude_keywords: list[str]) -> bool:
    lowered = content.lower()
    has_required = not include_keywords or any(keyword in lowered for keyword in include_keywords)
    has_excluded = any(keyword in lowered for keyword in exclude_keywords)
    return has_required and not has_excluded


class KeywordFilterService:
    async def preview(
        self,
        session: AsyncSession,
        include_keywords: list[str],
        exclude_keywords: list[str],
        limit: int = 50,
    ) -> Sequence[Article]:
        normalized_include = _normalize_keywords(include_keywords)
        normalized_exclude = _normalize_keywords(exclude_keywords)

        scan_limit = max(limit * 5, 100)
        query = select(Article).order_by(Article.created_at.desc()).limit(scan_limit)
        result = await session.execute(query)
        candidates = result.scalars().all()

        filtered: list[Article] = []
        for article in candidates:
            payload = f"{article.title}\n{article.content_text}"
            if _matches_keywords(payload, normalized_include, normalized_exclude):
                filtered.append(article)
            if len(filtered) >= limit:
                break
        return filtered


keyword_filter_service = KeywordFilterService()

