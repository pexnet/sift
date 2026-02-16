import pytest

from sift.search.query_language import SearchQuerySyntaxError, parse_search_query, requires_advanced_search


def test_requires_advanced_search_detection() -> None:
    assert requires_advanced_search("microsoft AND sentinel") is True
    assert requires_advanced_search('"network detection"') is True
    assert requires_advanced_search("threat*") is True
    assert requires_advanced_search("ransom~1") is True
    assert requires_advanced_search("plain query") is False


def test_parse_query_supports_boolean_and_grouping() -> None:
    query = parse_search_query('(microsoft OR "google cloud") AND NOT sports')

    assert (
        query.matches(
            title="Google cloud update",
            content_text="A technical brief",
            source_text="https://example.com",
        )
        is True
    )
    assert (
        query.matches(
            title="Microsoft sports brief",
            content_text="A technical brief",
            source_text="https://example.com",
        )
        is False
    )


def test_parse_query_supports_suffix_wildcard() -> None:
    query = parse_search_query("threat*")
    assert query.matches(title="Threatintel update", content_text="", source_text=None) is True
    assert query.matches(title="intel update", content_text="", source_text=None) is False


def test_parse_query_supports_fuzzy() -> None:
    query = parse_search_query("ransome~1")
    assert query.matches(title="ransom report", content_text="", source_text=None) is True
    assert query.matches(title="malware report", content_text="", source_text=None) is False


@pytest.mark.parametrize(
    "expression",
    [
        '"unterminated phrase',
        "th*eat",
        "*threat",
        "risk~3",
        "foo~",
        "()",
    ],
)
def test_parse_query_rejects_invalid_syntax(expression: str) -> None:
    with pytest.raises(SearchQuerySyntaxError):
        parse_search_query(expression)

