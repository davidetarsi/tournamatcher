from unittest.mock import patch, MagicMock

def test_get_db_initializes_once():
    with patch("firebase_admin.initialize_app") as mock_init, \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()):
        import db
        db._app = None
        db.firestore_client = None

        result1 = db.get_db()
        result2 = db.get_db()

        assert mock_init.call_count == 1
        assert result1 is result2
