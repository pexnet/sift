from sift.services.filter_service import _matches_keywords, _normalize_keywords


def test_normalize_keywords_deduplicates_and_lowercases() -> None:
    keywords = [" Python ", "python", "LLM", ""]
    assert _normalize_keywords(keywords) == ["python", "llm"]


def test_matches_keywords_requires_include() -> None:
    content = "Daily news about python and data engineering."
    assert _matches_keywords(content, include_keywords=["python"], exclude_keywords=[]) is True
    assert _matches_keywords(content, include_keywords=["golang"], exclude_keywords=[]) is False


def test_matches_keywords_honors_exclude() -> None:
    content = "Model update and release notes."
    assert _matches_keywords(content, include_keywords=["model"], exclude_keywords=["release"]) is False
