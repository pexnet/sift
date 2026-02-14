import time
from datetime import UTC

from sift.services.ingestion_service import _make_source_id, _parse_published_at


def test_make_source_id_prefers_declared_id() -> None:
    entry = {"id": "urn:entry:1", "title": "Example"}
    assert _make_source_id(entry) == "urn:entry:1"


def test_make_source_id_uses_stable_hash_fallback() -> None:
    entry = {"title": "Example", "published": "2026-02-14"}
    first = _make_source_id(entry)
    second = _make_source_id(entry)

    assert first.startswith("hash:")
    assert first == second


def test_parse_published_at_from_struct_time() -> None:
    parsed = time.gmtime(1739486400)
    result = _parse_published_at({"published_parsed": parsed})

    assert result is not None
    assert result.tzinfo == UTC

