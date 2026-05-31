from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

FAKE_TOKEN = {"uid": "admin-uid-123", "email": "admin@test.com"}
TOURNAMENT_PAYLOAD = {
    "name": "Torneo Calcetto 2026",
    "schema_config": {
        "sport": "calcetto",
        "max_teams": 8,
        "teams_per_group": 4,
        "public": False,
        "invite_codes": {"enabled": False, "partial": False},
        "team_fields": [
            {"key": "name", "type": "text", "required": True, "max_length": 100},
            {"key": "contact_email", "type": "email", "required": True},
        ],
        "player_fields": [],
        "admin_controls": {"can_set_strength": True, "max_teams": 8},
    },
}

@pytest.fixture
def client(mock_db):
    from main import app
    from db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)

def test_create_tournament_returns_201(client, mock_db):
    mock_doc = MagicMock()
    mock_doc.id = "new-tournament-id"
    mock_db.collection.return_value.document.return_value = mock_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.post(
            "/tournaments",
            json=TOURNAMENT_PAYLOAD,
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 201
    assert "tournament_id" in response.json()

def test_create_tournament_without_token_returns_422(client):
    response = client.post("/tournaments", json=TOURNAMENT_PAYLOAD)
    assert response.status_code == 422

def test_create_tournament_with_invalid_token_returns_401(client):
    with patch("auth.firebase_auth.verify_id_token", side_effect=Exception("bad")):
        response = client.post(
            "/tournaments",
            json=TOURNAMENT_PAYLOAD,
            headers={"Authorization": "Bearer bad.token"},
        )
    assert response.status_code == 401
