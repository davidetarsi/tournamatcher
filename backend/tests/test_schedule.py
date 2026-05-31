from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

ADMIN_TOKEN = {"uid": "admin-uid", "email": "admin@test.com"}
TOURNAMENT_ID = "t-123"

def _make_team_doc(nome, forza, disponibilita):
    doc = MagicMock()
    doc.id = nome
    doc.to_dict.return_value = {
        "nome": nome,
        "forza": forza,
        "confirmed": True,
        "owner_uid": f"uid-{nome}",
    }
    # Simula availability_slots
    slot_docs = []
    for g, giorno in enumerate(disponibilita):
        for s, val in enumerate(giorno):
            sd = MagicMock()
            sd.to_dict.return_value = {"slot_id": f"{g}_{s}", "available": bool(val)}
            slot_docs.append(sd)
    doc.reference.collection.return_value.stream.return_value = slot_docs
    return doc

@pytest.fixture
def client(mock_db):
    from main import app
    from db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)

def test_generate_schedule_success(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "admin-uid", "status": "draft"}

    schema_doc = MagicMock()
    schema_doc.exists = True
    schema_doc.to_dict.return_value = {
        "max_teams": 4,
        "teams_per_group": 2,
        "admin_controls": {"can_set_strength": True, "max_teams": 4},
    }

    teams = [
        _make_team_doc("Leoni",  5, [[1,1],[1,1],[1,1]]),
        _make_team_doc("Aquile", 5, [[1,1],[1,1],[1,1]]),
        _make_team_doc("Tori",   2, [[1,1],[1,1],[1,1]]),
        _make_team_doc("Draghi", 3, [[1,1],[1,1],[1,1]]),
    ]

    tournament_ref = MagicMock()
    tournament_ref.get.return_value = tournament_doc
    tournament_ref.collection.return_value.document.return_value.get.return_value = schema_doc
    tournament_ref.collection.return_value.where.return_value.stream.return_value = teams
    tournament_ref.update = MagicMock()

    mock_db.collection.return_value.document.return_value = tournament_ref
    mock_db.batch.return_value = MagicMock()

    with patch("auth.firebase_auth.verify_id_token", return_value=ADMIN_TOKEN):
        response = client.post(
            f"/tournaments/{TOURNAMENT_ID}/generate-schedule",
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "generated"

def test_generate_schedule_non_admin_returns_403(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "other-uid"}

    tournament_ref = MagicMock()
    tournament_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = tournament_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=ADMIN_TOKEN):
        response = client.post(
            f"/tournaments/{TOURNAMENT_ID}/generate-schedule",
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 403
