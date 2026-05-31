from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

FAKE_TOKEN = {"uid": "team-owner-uid", "email": "captain@test.com"}
TOURNAMENT_ID = "tournament-abc"
TEAM_ID = "team-xyz"

@pytest.fixture
def client(mock_db):
    from main import app
    from db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)

def _setup_mock_schema(mock_db):
    schema_doc = MagicMock()
    schema_doc.exists = True
    schema_doc.to_dict.return_value = {
        "team_fields": [
            {"key": "name", "type": "text", "required": True, "max_length": 100},
            {"key": "contact_email", "type": "email", "required": True},
        ],
        "invite_codes": {"enabled": False},
    }
    # Chain: db.collection("tournaments").document(tid).collection("config").document("schema").get()
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = schema_doc
    return schema_doc

def test_register_team_returns_201(client, mock_db):
    _setup_mock_schema(mock_db)

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.post(
            f"/tournaments/{TOURNAMENT_ID}/teams",
            json={"fields": {"name": "Leoni Blu", "contact_email": "a@b.com"}},
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 201
    assert "team_id" in response.json()

def test_update_availability_returns_200(client, mock_db):
    team_doc = MagicMock()
    team_doc.exists = True
    team_doc.get.return_value = "team-owner-uid"  # matches FAKE_TOKEN uid
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = team_doc

    mock_db.batch.return_value = MagicMock()

    slots_payload = [
        {"slot_id": "2026-06-10_14", "available": True},
        {"slot_id": "2026-06-10_16", "available": False},
    ]

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
            json=slots_payload,
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 200

def test_update_availability_wrong_owner_returns_403(client, mock_db):
    team_doc = MagicMock()
    team_doc.exists = True
    team_doc.get.return_value = "different-owner-uid"  # does NOT match FAKE_TOKEN uid
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = team_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
            json=[{"slot_id": "2026-06-10_14", "available": True}],
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 403
