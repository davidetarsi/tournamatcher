from __future__ import annotations

from firebase_admin import auth as firebase_auth
from fastapi import Header, HTTPException


async def verify_token(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.removeprefix("Bearer ").strip()
        return firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token non valido")
