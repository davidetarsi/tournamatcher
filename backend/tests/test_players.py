from __future__ import annotations
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from services.auth_service import create_team_token

TOURNAMENT_ID = "t-abc"
TEAM_ID = "team-xyz"


@pytest.fixture
def client(mock_db):
    from main import app
    from db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)


def _make_jwt(team_id=TEAM_ID):
    return create_team_token(TOURNAMENT_ID, team_id)


def _setup_schema(mock_db, player_fields=None, deadline=None):
    """Sets up t_ref mock with schema doc containing player_fields."""
    schema_doc = MagicMock()
    schema_doc.exists = True
    d: dict = {
        "player_fields": player_fields or [
            {"key": "nome", "type": "text", "required": True, "max_length": 100}
        ],
    }
    if deadline:
        d["edit_deadline"] = deadline
    schema_doc.to_dict.return_value = d

    t_ref = MagicMock()
    # t_ref.collection("config").document("schema").get() -> schema_doc
    t_ref.collection.return_value.document.return_value.get.return_value = schema_doc
    mock_db.collection.return_value.document.return_value = t_ref
    return t_ref


def _setup_team_doc(mock_db, players=None):
    """Sets up mock so team doc .get() returns given players."""
    team_doc = MagicMock()
    team_doc.exists = True
    team_doc.to_dict.return_value = {"players": players or []}

    t_ref = MagicMock()
    t_ref.collection.return_value.document.return_value.get.return_value = team_doc
    mock_db.collection.return_value.document.return_value = t_ref
    return t_ref


# --- GET /players ---

def test_get_players_returns_empty_list(client, mock_db):
    _setup_team_doc(mock_db, players=[])
    token = _make_jwt()
    resp = client.get(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"players": []}


def test_get_players_returns_list(client, mock_db):
    _setup_team_doc(mock_db, players=[{"nome": "Mario"}])
    token = _make_jwt()
    resp = client.get(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["players"] == [{"nome": "Mario"}]


def test_get_players_wrong_team_jwt_returns_403(client, mock_db):
    _setup_team_doc(mock_db)
    wrong_token = _make_jwt(team_id="other-team")
    resp = client.get(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert resp.status_code == 403


# --- PUT /players ---

def test_put_players_success(client, mock_db):
    t_ref = _setup_schema(mock_db)
    token = _make_jwt()
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        json={"players": [{"nome": "Mario Rossi"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 1
    t_ref.collection.return_value.document.return_value.update.assert_called_once()


def test_put_players_empty_list_clears(client, mock_db):
    _setup_schema(mock_db)
    token = _make_jwt()
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        json={"players": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["updated"] == 0


def test_put_players_invalid_field_returns_422(client, mock_db):
    _setup_schema(mock_db)  # "nome" is required
    token = _make_jwt()
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        json={"players": [{}]},  # nome missing
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 422


def test_put_players_deadline_exceeded_returns_403(client, mock_db):
    _setup_schema(mock_db, deadline="2020-01-01T00:00:00Z")
    token = _make_jwt()
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        json={"players": [{"nome": "Mario"}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


def test_put_players_wrong_team_jwt_returns_403(client, mock_db):
    _setup_schema(mock_db)
    wrong_token = _make_jwt(team_id="wrong-team")
    resp = client.put(
        f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/players",
        json={"players": [{"nome": "Mario"}]},
        headers={"Authorization": f"Bearer {wrong_token}"},
    )
    assert resp.status_code == 403
