# backend/tests/test_auth_service.py
from __future__ import annotations
import os
import pytest

from services.auth_service import generate_pin, hash_pin, create_team_token, verify_team_token
import jwt as _jwt


def test_generate_pin_length():
    assert len(generate_pin()) == 8


def test_generate_pin_uppercase_hex():
    pin = generate_pin()
    assert pin == pin.upper()
    assert all(c in "0123456789ABCDEF" for c in pin)


def test_generate_pin_is_random():
    pins = {generate_pin() for _ in range(100)}
    assert len(pins) > 90


def test_hash_pin_deterministic():
    assert hash_pin("ABCD1234") == hash_pin("ABCD1234")


def test_hash_pin_different_inputs():
    assert hash_pin("ABCD1234") != hash_pin("ABCD1235")


def test_create_team_token_payload():
    token = create_team_token("t-1", "team-1")
    payload = _jwt.decode(token, os.environ["JWT_SECRET"], algorithms=["HS256"])
    assert payload["sub"] == "team-1"
    assert payload["tournament_id"] == "t-1"
    assert payload["role"] == "team"
    assert "exp" in payload


def test_verify_team_token_valid():
    token = create_team_token("t-1", "team-1")
    payload = verify_team_token(token, "t-1", "team-1")
    assert payload["sub"] == "team-1"


def test_verify_team_token_wrong_team():
    token = create_team_token("t-1", "team-1")
    with pytest.raises(ValueError, match="non valido"):
        verify_team_token(token, "t-1", "team-2")


def test_verify_team_token_wrong_tournament():
    token = create_team_token("t-1", "team-1")
    with pytest.raises(ValueError, match="non valido"):
        verify_team_token(token, "t-2", "team-1")


def test_verify_team_token_expired():
    import time
    from datetime import datetime, timedelta, timezone
    import jwt as _jwt
    expired_token = _jwt.encode(
        {"sub": "team-1", "tournament_id": "t-1", "role": "team",
         "exp": datetime.now(timezone.utc) - timedelta(seconds=1)},
        os.environ["JWT_SECRET"],
        algorithm="HS256",
    )
    with pytest.raises(ValueError):
        verify_team_token(expired_token, "t-1", "team-1")
