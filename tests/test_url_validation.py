import pytest

from sift.services.url_validation import UrlValidationError, validate_fetch_url


def test_validate_fetch_url_rejects_localhost():
    with pytest.raises(UrlValidationError, match="Loopback"):
        validate_fetch_url("http://localhost/admin")


def test_validate_fetch_url_rejects_127_0_0_1():
    with pytest.raises(UrlValidationError, match="non-routable"):
        validate_fetch_url("http://127.0.0.1/")


def test_validate_fetch_url_rejects_private_ip_10():
    with pytest.raises(UrlValidationError, match="Private"):
        validate_fetch_url("http://10.0.0.1/internal")


def test_validate_fetch_url_rejects_private_ip_192_168():
    with pytest.raises(UrlValidationError, match="Private"):
        validate_fetch_url("http://192.168.1.1/router")


def test_validate_fetch_url_rejects_private_ip_172_16():
    with pytest.raises(UrlValidationError, match="Private"):
        validate_fetch_url("http://172.16.0.1/")


def test_validate_fetch_url_rejects_metadata_endpoint():
    with pytest.raises(UrlValidationError, match="Private|non-routable"):
        validate_fetch_url("http://169.254.169.254/latest/meta-data/")


def test_validate_fetch_url_rejects_non_http_scheme():
    with pytest.raises(UrlValidationError, match="scheme"):
        validate_fetch_url("file:///etc/passwd")


def test_validate_fetch_url_rejects_ftp_scheme():
    with pytest.raises(UrlValidationError, match="scheme"):
        validate_fetch_url("ftp://example.com/file")


def test_validate_fetch_url_rejects_missing_hostname():
    with pytest.raises(UrlValidationError, match="hostname"):
        validate_fetch_url("http:///path")


def test_validate_fetch_url_accepts_public_url():
    result = validate_fetch_url("https://example.com/feed.xml")
    assert result == "https://example.com/feed.xml"


def test_validate_fetch_url_accepts_http_url():
    result = validate_fetch_url("http://example.com/rss")
    assert result == "http://example.com/rss"


def test_validate_fetch_url_strips_whitespace():
    result = validate_fetch_url("  https://example.com/feed  ")
    assert result == "https://example.com/feed"


def test_validate_fetch_url_normalizes_scheme_case():
    result = validate_fetch_url("HTTPS://example.com/feed")
    assert "example.com" in result