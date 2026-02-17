from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext


def _build_snippet(text: str, *, start: int, end: int, radius: int = 40) -> str:
    snippet_start = max(0, start - radius)
    snippet_end = min(len(text), end + radius)
    snippet = text[snippet_start:snippet_end].strip()
    if snippet_start > 0:
        snippet = f"...{snippet}"
    if snippet_end < len(text):
        snippet = f"{snippet}..."
    return snippet


def _find_keyword_finding(title: str, content_text: str, keyword: str) -> dict[str, str | int] | None:
    title_lower = title.lower()
    title_index = title_lower.find(keyword)
    if title_index >= 0:
        title_end = title_index + len(keyword)
        return {
            "field": "title",
            "value": title[title_index:title_end],
            "start": title_index,
            "end": title_end,
            "snippet": _build_snippet(title, start=title_index, end=title_end),
        }

    content_lower = content_text.lower()
    content_index = content_lower.find(keyword)
    if content_index >= 0:
        content_end = content_index + len(keyword)
        return {
            "field": "content_text",
            "value": content_text[content_index:content_end],
            "start": content_index,
            "end": content_end,
            "snippet": _build_snippet(content_text, start=content_index, end=content_end),
        }

    return None


class KeywordHeuristicClassifierPlugin:
    name = "keyword_heuristic_classifier"
    provider = "builtin"
    model_name = "keyword_heuristic"
    model_version = "v1"

    async def classify_stream(
        self,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision:
        payload = f"{article.title}\n{article.content_text}".lower()
        source = stream.metadata.get("source_url", "").lower()
        language = stream.metadata.get("language", "").lower()
        config = dict(stream.classifier_config)

        if stream.exclude_keywords and any(keyword in payload for keyword in stream.exclude_keywords):
            return StreamClassificationDecision(
                matched=False,
                confidence=0.0,
                reason="excluded keyword present",
                provider=self.provider,
                model_name=self.model_name,
                model_version=self.model_version,
            )

        if stream.source_contains and stream.source_contains.lower() not in source:
            return StreamClassificationDecision(
                matched=False,
                confidence=0.0,
                reason="source mismatch",
                provider=self.provider,
                model_name=self.model_name,
                model_version=self.model_version,
            )

        if stream.language_equals and stream.language_equals.lower() != language:
            return StreamClassificationDecision(
                matched=False,
                confidence=0.0,
                reason="language mismatch",
                provider=self.provider,
                model_name=self.model_name,
                model_version=self.model_version,
            )

        if not stream.include_keywords:
            return StreamClassificationDecision(
                matched=True,
                confidence=0.55,
                reason="fallback match",
                provider=self.provider,
                model_name=self.model_name,
                model_version=self.model_version,
                findings=[
                    {
                        "label": "fallback rule",
                        "text": "No include keywords configured, fallback classifier match was applied.",
                        "score": 0.55,
                    }
                ],
            )

        matched_keywords = 0
        findings: list[dict[str, str | int | float]] = []
        for keyword in stream.include_keywords:
            if keyword not in payload:
                continue
            matched_keywords += 1
            keyword_finding = _find_keyword_finding(article.title, article.content_text, keyword)
            if not keyword_finding:
                continue
            findings.append(
                {
                    "label": f'include keyword "{keyword}"',
                    "field": str(keyword_finding["field"]),
                    "value": str(keyword_finding["value"]),
                    "start": int(keyword_finding["start"]),
                    "end": int(keyword_finding["end"]),
                    "offset_basis": "field_text_v1",
                    "text": str(keyword_finding["snippet"]),
                    "score": round(1.0 / len(stream.include_keywords), 4),
                }
            )

        confidence = matched_keywords / len(stream.include_keywords)
        min_ratio_raw = config.get("min_keyword_ratio", 0.0)
        require_all_raw = config.get("require_all_include_keywords", False)
        try:
            min_ratio = float(min_ratio_raw)
        except (TypeError, ValueError):
            min_ratio = 0.0
        min_ratio = max(0.0, min(1.0, min_ratio))
        require_all = bool(require_all_raw)
        threshold = 1.0 if require_all else min_ratio
        matched = confidence >= threshold and confidence > 0.0
        return StreamClassificationDecision(
            matched=matched,
            confidence=confidence,
            reason=(
                f"{matched_keywords}/{len(stream.include_keywords)} include keywords matched "
                f"(threshold={threshold:.2f})"
            ),
            provider=self.provider,
            model_name=self.model_name,
            model_version=self.model_version,
            findings=findings
            + [
                {
                    "label": "keyword coverage",
                    "text": f"{matched_keywords}/{len(stream.include_keywords)} include keywords matched",
                    "score": round(confidence, 4),
                }
            ],
        )
