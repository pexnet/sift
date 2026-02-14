from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext


class KeywordHeuristicClassifierPlugin:
    name = "keyword_heuristic_classifier"

    async def classify_stream(
        self,
        article: ArticleContext,
        stream: StreamClassifierContext,
    ) -> StreamClassificationDecision:
        payload = f"{article.title}\n{article.content_text}".lower()
        source = stream.metadata.get("source_url", "").lower()
        language = stream.metadata.get("language", "").lower()

        if stream.exclude_keywords and any(keyword in payload for keyword in stream.exclude_keywords):
            return StreamClassificationDecision(matched=False, confidence=0.0, reason="excluded keyword present")

        if stream.source_contains and stream.source_contains.lower() not in source:
            return StreamClassificationDecision(matched=False, confidence=0.0, reason="source mismatch")

        if stream.language_equals and stream.language_equals.lower() != language:
            return StreamClassificationDecision(matched=False, confidence=0.0, reason="language mismatch")

        if not stream.include_keywords:
            return StreamClassificationDecision(matched=True, confidence=0.55, reason="fallback match")

        matched_keywords = sum(1 for keyword in stream.include_keywords if keyword in payload)
        confidence = matched_keywords / len(stream.include_keywords)
        return StreamClassificationDecision(
            matched=confidence > 0.0,
            confidence=confidence,
            reason=f"{matched_keywords}/{len(stream.include_keywords)} include keywords matched",
        )

