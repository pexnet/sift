"""Shared SSRF validation for outbound URL fetching.

Used by ingestion service, discovery candidate validation, and fulltext fetch
to ensure the server never issues HTTP requests to private/loopback/metadata endpoints.
"""

import ipaddress
import socket
from typing import Final
from urllib.parse import urlparse

_ALLOWED_SCHEMES: Final[frozenset[str]] = frozenset({"http", "https"})


class UrlValidationError(Exception):
    """Raised when a URL is not safe for server-side fetching."""


def validate_fetch_url(raw_url: str) -> str:
    """Validate that *raw_url* is safe to fetch (public http/https, no private IPs).

    Returns the normalized URL string on success, raises ``UrlValidationError`` on failure.
    """
    parsed = urlparse(raw_url.strip())
    scheme = parsed.scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise UrlValidationError("Unsupported URL scheme. Only http/https are allowed.")
    if not parsed.hostname:
        raise UrlValidationError("URL is missing a hostname.")

    _assert_public_host(parsed.hostname)
    return parsed.geturl()


def _assert_public_host(hostname: str) -> None:
    if hostname.lower() == "localhost":
        raise UrlValidationError("Loopback/localhost fetch targets are not allowed.")

    try:
        _assert_public_ip(ipaddress.ip_address(hostname))
        return
    except ValueError:
        pass

    try:
        addresses = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UrlValidationError(f"Failed resolving URL host: {exc}") from exc

    for entry in addresses:
        ip_raw = entry[4][0]
        _assert_public_ip(ipaddress.ip_address(ip_raw))


def _assert_public_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> None:
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        raise UrlValidationError("Private or non-routable fetch targets are not allowed.")
