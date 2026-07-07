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
    mock_snap_free = MagicMock()
    mock_snap_free.exists = False
    mock_tx = MagicMock()
    mock_tx.get.return_value = mock_snap_free
    mock_db.transaction.return_value = mock_tx
    mock_db.collection.return_value.document.return_value = MagicMock()

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN), \
         patch("firebase_admin.firestore.transactional", side_effect=lambda f: f):
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


def test_update_schema_returns_200(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "admin-uid-123"}

    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            "/tournaments/t-123/schema",
            json=TOURNAMENT_PAYLOAD["schema_config"],
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    mock_ref.collection.return_value.document.return_value.set.assert_called_once()


def test_update_schema_not_found_returns_404(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = False

    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            "/tournaments/nonexistent/schema",
            json=TOURNAMENT_PAYLOAD["schema_config"],
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 404


def test_update_schema_non_admin_returns_403(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "other-uid"}

    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            "/tournaments/t-123/schema",
            json=TOURNAMENT_PAYLOAD["schema_config"],
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 403


def test_patch_config_success(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "admin-uid-123"}
    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.patch(
            "/tournaments/t-123/config",
            json={"start_date": "2026-07-15", "edit_deadline": "2026-07-14T21:59:00Z"},
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"
    mock_ref.collection.return_value.document.return_value.set.assert_called_once()


def test_patch_config_not_admin_returns_403(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "other-uid"}
    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.patch(
            "/tournaments/t-123/config",
            json={"start_date": "2026-07-15"},
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 403


def test_patch_config_not_found_returns_404(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = False
    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.patch(
            "/tournaments/nonexistent/config",
            json={"start_date": "2026-07-15"},
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 404


def test_patch_config_invalid_date_returns_400(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "admin-uid-123"}
    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.patch(
            "/tournaments/t-123/config",
            json={"start_date": "not-a-date"},
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 400


# ---- NEW TESTS for Task 2 ----


def test_create_tournament_returns_slug(client, mock_db):
    """POST /tournaments must return slug in response."""
    mock_snap_free = MagicMock()
    mock_snap_free.exists = False
    mock_tx = MagicMock()
    mock_tx.get.return_value = mock_snap_free
    mock_db.transaction.return_value = mock_tx

    mock_db.collection.return_value.document.return_value = MagicMock()

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN), \
         patch("firebase_admin.firestore.transactional", side_effect=lambda f: f):
        response = client.post(
            "/tournaments",
            json=TOURNAMENT_PAYLOAD,
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 201
    data = response.json()
    assert "tournament_id" in data
    assert "slug" in data
    assert data["slug"].startswith("torneo-calcetto")


def test_get_tournament_by_slug_found(client, mock_db):
    slug_doc = MagicMock()
    slug_doc.exists = True
    slug_doc.to_dict.return_value = {"tournament_id": "uuid-123"}

    t_doc = MagicMock()
    t_doc.exists = True
    t_doc.to_dict.return_value = {"name": "Torneo Calcetto 2026", "logo_url": None}

    def collection_side_effect(name):
        coll = MagicMock()
        if name == "tournament_slugs":
            coll.document.return_value.get.return_value = slug_doc
        else:
            coll.document.return_value.get.return_value = t_doc
        return coll

    mock_db.collection.side_effect = collection_side_effect

    response = client.get("/tournaments/by-slug/torneo-calcetto-2026")

    assert response.status_code == 200
    data = response.json()
    assert data["tournament_id"] == "uuid-123"
    assert data["name"] == "Torneo Calcetto 2026"
    assert data["logo_url"] is None


def test_get_tournament_by_slug_not_found(client, mock_db):
    slug_doc = MagicMock()
    slug_doc.exists = False
    mock_db.collection.return_value.document.return_value.get.return_value = slug_doc

    response = client.get("/tournaments/by-slug/slug-inesistente")

    assert response.status_code == 404


def test_get_my_tournaments_returns_list(client, mock_db):
    t1 = MagicMock()
    t1.to_dict.return_value = {"name": "Torneo A", "slug": "torneo-a", "status": "draft"}
    t2 = MagicMock()
    t2.to_dict.return_value = {"name": "Torneo B", "slug": "torneo-b", "status": "draft"}

    mock_db.collection.return_value.where.return_value.order_by.return_value.stream.return_value = [t1, t2]

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.get(
            "/tournaments/my-tournaments",
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["slug"] == "torneo-a"
    assert data[1]["name"] == "Torneo B"


def test_get_my_tournaments_requires_auth(client):
    response = client.get("/tournaments/my-tournaments")
    assert response.status_code == 422


def test_create_tournament_with_logo(client, mock_db):
    """Logo Base64 triggers Storage upload; logo_url saved in doc."""
    mock_snap_free = MagicMock()
    mock_snap_free.exists = False
    mock_tx = MagicMock()
    mock_tx.get.return_value = mock_snap_free
    mock_db.transaction.return_value = mock_tx
    mock_db.collection.return_value.document.return_value = MagicMock()

    payload_with_logo = {**TOURNAMENT_PAYLOAD, "logo_base64": "data:image/png;base64,iVBORw0KGgo="}

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN), \
         patch("firebase_admin.firestore.transactional", side_effect=lambda f: f), \
         patch("routers.tournaments.upload_logo", return_value="https://storage.googleapis.com/bucket/logo.png") as mock_upload:
        response = client.post(
            "/tournaments",
            json=payload_with_logo,
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 201
    mock_upload.assert_called_once()


def test_create_tournament_logo_upload_failure_returns_500(client, mock_db):
    """If Storage upload fails, tournament is NOT created (no Firestore write)."""
    payload_with_logo = {**TOURNAMENT_PAYLOAD, "logo_base64": "data:image/png;base64,iVBORw0KGgo="}

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN), \
         patch("routers.tournaments.upload_logo", side_effect=Exception("Storage error")):
        response = client.post(
            "/tournaments",
            json=payload_with_logo,
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 500
    mock_db.transaction.assert_not_called()
