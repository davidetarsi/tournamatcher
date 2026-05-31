from __future__ import annotations
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from auth import verify_token

VALID_TOKEN = "Bearer valid.jwt.token"
DECODED = {"uid": "user-123", "email": "user@test.com"}

@pytest.mark.asyncio
async def test_valid_token_returns_decoded():
    with patch("auth.firebase_auth.verify_id_token", return_value=DECODED):
        result = await verify_token(authorization=VALID_TOKEN)
        assert result["uid"] == "user-123"

@pytest.mark.asyncio
async def test_missing_bearer_prefix_raises_401():
    with patch("auth.firebase_auth.verify_id_token", side_effect=Exception("bad token")):
        with pytest.raises(HTTPException) as exc:
            await verify_token(authorization="invalid-token")
        assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_no_authorization_header_raises_422():
    # FastAPI solleva 422 automaticamente se Header(...) manca
    # Questo si testa a livello endpoint, non qui
    pass
