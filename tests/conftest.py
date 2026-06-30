"""Shared test configuration.

Patches socket.getaddrinfo so that SSRF validation passes for *.example.com
test URLs without requiring real DNS resolution.
"""

import socket
from unittest.mock import patch

import pytest

_REAL_PUBLIC_IP = "93.184.216.34"  # example.com real IP


def _fake_getaddrinfo(hostname, *args, **kwargs):
    """Return a public IP for *.example.com hosts so validate_fetch_url passes in tests."""
    if isinstance(hostname, str) and hostname.endswith(".example.com"):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (_REAL_PUBLIC_IP, 0))]
    return _real_getaddrinfo(hostname, *args, **kwargs)


_real_getaddrinfo = socket.getaddrinfo


@pytest.fixture(autouse=True)
def _mock_example_com_dns():
    with patch("socket.getaddrinfo", side_effect=_fake_getaddrinfo):
        yield
