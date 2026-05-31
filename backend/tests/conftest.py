from __future__ import annotations
import pytest
from unittest.mock import MagicMock, patch

FAKE_UID = "test-user-uid"
FAKE_ADMIN_UID = "admin-uid"

@pytest.fixture(autouse=True)
def mock_firebase(monkeypatch):
    """
    Patches db.firestore_client and blocks real Firebase SDK calls.
    autouse=True ensures no test can accidentally reach Firebase.
    """
    mock_db = MagicMock()
    monkeypatch.setattr("db.firestore_client", mock_db)
    with patch("firebase_admin.initialize_app"), \
         patch("firebase_admin.credentials.Certificate"):
        yield mock_db

@pytest.fixture
def mock_db(mock_firebase):
    return mock_firebase

@pytest.fixture(autouse=True)
def disable_rate_limiter(monkeypatch):
    """Disable slowapi rate limiting in tests (TestClient IP causes key errors)."""
    from limiter import limiter
    monkeypatch.setattr(limiter, "enabled", False)
