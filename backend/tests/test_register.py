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
