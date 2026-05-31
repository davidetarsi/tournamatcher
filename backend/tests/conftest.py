import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

FAKE_UID = "test-user-uid"
FAKE_ADMIN_UID = "admin-uid"

@pytest.fixture(autouse=True)
def mock_firebase(monkeypatch):
    """Patch firebase_admin prima di qualsiasi import."""
    mock_db = MagicMock()
    monkeypatch.setattr("db.firestore_client", mock_db)
    return mock_db

@pytest.fixture
def mock_db(mock_firebase):
    return mock_firebase
