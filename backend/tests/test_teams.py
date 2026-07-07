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
    d: dict = {"team_fields": []}
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


# ============================================================================
# Unit tests for _register_in_transaction (direct function testing)
# ============================================================================

from routers.teams import _register_in_transaction, _RegistrationError
from models import AvailabilitySlot


def test_register_in_transaction_at_cap_raises_409():
    """Test that _register_in_transaction raises 409 when team_count >= max_teams"""
    # Setup mock transaction
    transaction = MagicMock()

    # Setup mock tournament_ref with stats_doc
    tournament_ref = MagicMock()
    stats_ref = MagicMock()
    stats_doc = MagicMock()
    stats_doc.exists = True
    stats_doc.to_dict.return_value = {"team_count": 8}
    stats_ref.get.return_value = stats_doc
    tournament_ref.collection.return_value.document.return_value = stats_ref

    # Sanitized fields (minimal valid team data)
    sanitized_fields = {"team_name": "Test Team"}

    # Payload with availability slots
    payload = MagicMock()
    payload.availability_slots = [AvailabilitySlot(slot_id="g1_s1", available=True)]

    # Schema: max_teams = 8, so team_count = 8 is at capacity
    schema = {"max_teams": 8}

    # Should raise _RegistrationError with status 409
    with pytest.raises(_RegistrationError) as exc_info:
        _register_in_transaction(transaction, tournament_ref, sanitized_fields, payload, schema)

    assert exc_info.value.status_code == 409
    assert "Iscrizioni chiuse" in exc_info.value.detail


def test_register_in_transaction_legacy_counter_fallback_succeeds():
    """Test that _register_in_transaction falls back to public_count + invite_count when team_count is missing"""
    # Setup mock transaction
    transaction = MagicMock()

    # Setup mock tournament_ref with stats_doc
    tournament_ref = MagicMock()
    stats_ref = MagicMock()
    stats_doc = MagicMock()
    stats_doc.exists = True
    # Old-style counters: no team_count, but public_count and invite_count
    stats_doc.to_dict.return_value = {"public_count": 3, "invite_count": 2}
    stats_ref.get.return_value = stats_doc
    tournament_ref.collection.return_value.document.return_value = stats_ref

    # Sanitized fields (minimal valid team data)
    sanitized_fields = {"team_name": "Test Team"}

    # Payload with availability slots
    payload = MagicMock()
    payload.availability_slots = [AvailabilitySlot(slot_id="g1_s1", available=True)]

    # Schema: max_teams = 10, so 3+2=5 teams is under capacity
    schema = {"max_teams": 10}

    # Should succeed
    team_id, pin = _register_in_transaction(transaction, tournament_ref, sanitized_fields, payload, schema)

    # Verify return values
    assert team_id is not None
    assert pin is not None

    # Verify transaction.set was called twice:
    # 1. For team document
    # 2. For stats document with team_count = 5 + 1 = 6
    assert transaction.set.call_count == 2

    # Find the stats_ref.set call
    calls = transaction.set.call_args_list
    # The second call should be to stats_ref with {"team_count": 6} and merge=True
    stats_call = calls[1]
    assert stats_call[0][0] == stats_ref
    assert stats_call[0][1] == {"team_count": 6}
    assert stats_call[1]["merge"] is True
