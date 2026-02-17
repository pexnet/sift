from sift.plugins.base import ArticleContext, StreamClassificationDecision, StreamClassifierContext


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
            )

        matched_keywords = sum(1 for keyword in stream.include_keywords if keyword in payload)
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
        )
