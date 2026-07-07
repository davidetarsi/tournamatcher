from __future__ import annotations
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(mock_db):
    from main import app
    return TestClient(app)


def test_parse_allowed_origins_strips_trailing_slash_and_spaces():
    from main import parse_allowed_origins
    raw = "https://app.vercel.app/, https://tuodominio.com ,http://localhost:3000"
    assert parse_allowed_origins(raw) == [
        "https://app.vercel.app",
        "https://tuodominio.com",
        "http://localhost:3000",
    ]


def test_cors_preflight_allows_default_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_cors_rejects_unknown_origin(client):
    response = client.options(
        "/health",
        headers={
            "Origin": "https://evil.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # Starlette risponde 400 ai preflight con origin non consentito
    assert "access-control-allow-origin" not in response.headers
