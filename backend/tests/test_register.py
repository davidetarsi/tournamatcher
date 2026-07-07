# backend/tests/test_register.py
from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

TOURNAMENT_ID = "t-abc"


@pytest.fixture
def client(mock_db):
    from main import app
    from db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)


def _setup_registration_config(mock_db, exists=True, schema_exists=True):
    t_doc = MagicMock()
    t_doc.exists = exists
    t_doc.to_dict.return_value = {"name": "Torneo Test", "admin_uid": "admin-1"}

    schema_doc = MagicMock()
    schema_doc.exists = schema_exists
    schema_doc.to_dict.return_value = {
        "sport": "calcetto",
        "max_teams": 8,
        "team_fields": [{"key": "nome", "type": "text", "required": True, "max_length": 100}],
        "player_fields": [{"key": "nome", "type": "text", "required": True, "max_length": 100}],
        "num_giorni": 3,
        "num_slots_per_giorno": 2,
        "start_date": None,
        "edit_deadline": None,
    }

    t_ref = MagicMock()
    t_ref.get.return_value = t_doc
    t_ref.collection.return_value.document.return_value.get.return_value = schema_doc
    mock_db.collection.return_value.document.return_value = t_ref
    return t_ref


def test_registration_config_success(client, mock_db):
    _setup_registration_config(mock_db)
    resp = client.get(f"/tournaments/{TOURNAMENT_ID}/registration-config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Torneo Test"
    assert data["sport"] == "calcetto"
    assert data["num_giorni"] == 3
    assert data["num_slots_per_giorno"] == 2
    assert data["max_teams"] == 8
    assert "team_fields" in data
    assert "invite_codes" not in data
    assert "max_public_teams" not in data
    assert "points_system" not in data
    assert "tiebreaker_rules" not in data
    assert "admin_controls" not in data
    assert "start_date" in data       # may be None
    assert "edit_deadline" in data    # may be None
    assert "player_fields" in data


def test_registration_config_not_found(client, mock_db):
    _setup_registration_config(mock_db, exists=False)
    resp = client.get(f"/tournaments/{TOURNAMENT_ID}/registration-config")
    assert resp.status_code == 404


def test_registration_config_schema_not_found(client, mock_db):
    _setup_registration_config(mock_db, schema_exists=False)
    resp = client.get(f"/tournaments/{TOURNAMENT_ID}/registration-config")
    assert resp.status_code == 404


from unittest.mock import patch


def _setup_register(mock_db, max_teams=8):
    t_doc = MagicMock()
    t_doc.exists = True
    t_doc.to_dict.return_value = {"name": "Torneo Test", "admin_uid": "admin-1"}

    schema_doc = MagicMock()
    schema_doc.exists = True
    schema_doc.to_dict.return_value = {
        "max_teams": max_teams,
        "team_fields": [{"key": "nome", "type": "text", "required": True, "max_length": 100}],
        "num_giorni": 1,
        "num_slots_per_giorno": 1,
    }

    t_ref = MagicMock()
    t_ref.get.return_value = t_doc
    t_ref.collection.return_value.document.return_value.get.return_value = schema_doc

    mock_db.collection.return_value.document.return_value = t_ref
    return t_ref


@patch("routers.teams._register_in_transaction", return_value=("team-uuid-1", "ABCD1234"))
def test_register_success(mock_txn, client, mock_db):
    _setup_register(mock_db)
    resp = client.post(
        f"/tournaments/{TOURNAMENT_ID}/register",
        json={"fields": {"nome": "Aquile"}, "availability_slots": []},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["team_id"] == "team-uuid-1"
    assert data["team_code_plain"] == "ABCD1234"


def test_register_tournament_not_found(client, mock_db):
    t_doc = MagicMock()
    t_doc.exists = False
    t_ref = MagicMock()
    t_ref.get.return_value = t_doc
    mock_db.collection.return_value.document.return_value = t_ref

    resp = client.post(
        f"/tournaments/{TOURNAMENT_ID}/register",
        json={"fields": {"nome": "Aquile"}, "availability_slots": []},
    )
    assert resp.status_code == 404


def test_register_invalid_fields(client, mock_db):
    _setup_register(mock_db)
    with patch("routers.teams._register_in_transaction", return_value=("id", "PIN")):
        resp = client.post(
            f"/tournaments/{TOURNAMENT_ID}/register",
            json={"fields": {}, "availability_slots": []},  # 'nome' required but missing
        )
    assert resp.status_code == 422


def _setup_auth(mock_db, team_exists=True, stored_hash=None):
    from services.auth_service import hash_pin
    pin = "ABCD1234"
    if stored_hash is None:
        stored_hash = hash_pin(pin)

    team_doc = MagicMock()
    team_doc.exists = team_exists
    team_doc.to_dict.return_value = {"team_code_hash": stored_hash, "nome": "Aquile"}

    t_ref = MagicMock()
    t_ref.collection.return_value.document.return_value.get.return_value = team_doc
    mock_db.collection.return_value.document.return_value = t_ref
    return pin


def test_auth_success(client, mock_db):
    pin = _setup_auth(mock_db)
    resp = client.post(
        f"/tournaments/{TOURNAMENT_ID}/teams/team-1/auth",
        json={"team_code": pin},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_auth_wrong_pin(client, mock_db):
    _setup_auth(mock_db)
    resp = client.post(
        f"/tournaments/{TOURNAMENT_ID}/teams/team-1/auth",
        json={"team_code": "WRONG123"},
    )
    assert resp.status_code == 403


def test_auth_team_not_found(client, mock_db):
    _setup_auth(mock_db, team_exists=False)
    resp = client.post(
        f"/tournaments/{TOURNAMENT_ID}/teams/team-1/auth",
        json={"team_code": "ABCD1234"},
    )
    assert resp.status_code == 404
