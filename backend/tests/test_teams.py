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

def test_update_team_strength_as_admin_returns_200(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "team-owner-uid"}
    mock_db.collection.return_value.document.return_value.get.return_value = tournament_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.patch(
            f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}",
            json={"forza": 5, "confirmed": True},
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 200
    assert "forza" in response.json()["updated"]


def test_update_team_non_admin_returns_403(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "other-admin-uid"}  # not FAKE_TOKEN
    mock_db.collection.return_value.document.return_value.get.return_value = tournament_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.patch(
            f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}",
            json={"forza": 5},
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 403


from services.auth_service import create_team_token


def _make_availability_jwt(tournament_id=TOURNAMENT_ID, team_id=TEAM_ID):
    return create_team_token(tournament_id, team_id)


def _setup_availability_mock(mock_db, past_deadline=False):
    schema_doc = MagicMock()
    schema_doc.exists = True
    d: dict = {"team_fields": [], "invite_codes": {"enabled": False}}
    if past_deadline:
        d["edit_deadline"] = "2020-01-01T00:00:00Z"
    schema_doc.to_dict.return_value = d

    # schema chain: .collection.rv.document.rv.collection.rv.document.rv.get() -> schema_doc
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = schema_doc


def test_update_availability_with_team_jwt(client, mock_db):
    _setup_availability_mock(mock_db)
    token = _make_availability_jwt()
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
        json=[{"slot_id": "g1_s1", "available": True}],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1


def test_update_availability_deadline_exceeded_returns_403(client, mock_db):
    _setup_availability_mock(mock_db, past_deadline=True)
    token = _make_availability_jwt()
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
        json=[{"slot_id": "g1_s1", "available": True}],
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_update_availability_wrong_team_jwt_returns_403(client, mock_db):
    _setup_availability_mock(mock_db)
    wrong_token = create_team_token(TOURNAMENT_ID, "other-team-id")
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
        json=[{"slot_id": "g1_s1", "available": True}],
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert resp.status_code == 403
