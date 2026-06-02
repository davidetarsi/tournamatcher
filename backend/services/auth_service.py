# backend/services/auth_service.py
from __future__ import annotations
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

import jwt

SECRET_KEY = os.environ["JWT_SECRET"]
ALGORITHM = "HS256"
TOKEN_TTL_DAYS = 30


def generate_pin() -> str:
    return secrets.token_hex(4).upper()


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def create_team_token(tournament_id: str, team_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=TOKEN_TTL_DAYS)
    payload = {
        "sub": team_id,
        "tournament_id": tournament_id,
        "role": "team",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def verify_team_token(token: str, tournament_id: str, team_id: str) -> dict:
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if payload.get("sub") != team_id or payload.get("tournament_id") != tournament_id:
        raise ValueError("Token non valido per questa risorsa")
    return payload
