from __future__ import annotations
from unittest.mock import MagicMock, patch
from limiter import get_real_ip


def test_get_real_ip_from_forwarded_for():
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "1.2.3.4, 5.6.7.8, 9.10.11.12"}
    assert get_real_ip(req) == "1.2.3.4"


def test_get_real_ip_single_ip():
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "  203.0.113.5  "}
    assert get_real_ip(req) == "203.0.113.5"


def test_get_real_ip_fallback():
    req = MagicMock()
    req.headers = {}
    with patch("limiter.get_remote_address", return_value="192.168.1.1"):
        assert get_real_ip(req) == "192.168.1.1"


def test_get_real_ip_whitespace_only_forwarded_for():
    req = MagicMock()
    req.headers = {"X-Forwarded-For": "   "}
    with patch("limiter.get_remote_address", return_value="192.168.1.1"):
        assert get_real_ip(req) == "192.168.1.1"
