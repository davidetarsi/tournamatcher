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
        "invite_codes": {"enabled": False, "partial": False},
        "team_fields": [{"key": "nome", "type": "text", "required": True, "max_length": 100}],
        "num_giorni": 3,
        "num_slots_per_giorno": 2,
        "max_public_teams": 0,
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
    assert "points_system" not in data
    assert "tiebreaker_rules" not in data
    assert "admin_controls" not in data


def test_registration_config_not_found(client, mock_db):
    _setup_registration_config(mock_db, exists=False)
    resp = client.get(f"/tournaments/{TOURNAMENT_ID}/registration-config")
    assert resp.status_code == 404


def test_registration_config_schema_not_found(client, mock_db):
    _setup_registration_config(mock_db, schema_exists=False)
    resp = client.get(f"/tournaments/{TOURNAMENT_ID}/registration-config")
    assert resp.status_code == 404


from unittest.mock import patch


def _setup_register(mock_db, max_teams=8, invite_enabled=False, invite_partial=False,
                    max_public=0, public_count=0, invite_count=0):
    t_doc = MagicMock()
    t_doc.exists = True
    t_doc.to_dict.return_value = {"name": "Torneo Test", "admin_uid": "admin-1"}

    schema_doc = MagicMock()
    schema_doc.exists = True
    schema_doc.to_dict.return_value = {
        "max_teams": max_teams,
        "invite_codes": {"enabled": invite_enabled, "partial": invite_partial},
        "team_fields": [{"key": "nome", "type": "text", "required": True, "max_length": 100}],
        "max_public_teams": max_public,
        "num_giorni": 1,
        "num_slots_per_giorno": 1,
    }

    stats_doc = MagicMock()
    stats_doc.exists = True
    stats_doc.to_dict.return_value = {"public_count": public_count, "invite_count": invite_count}

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
