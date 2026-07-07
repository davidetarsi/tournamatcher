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


def test_init_uses_json_env_var_when_present(monkeypatch):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_KEY_JSON", '{"type": "service_account"}')
    monkeypatch.delenv("FIREBASE_SERVICE_ACCOUNT_KEY", raising=False)
    with patch("firebase_admin.initialize_app") as mock_init, \
         patch("firebase_admin.credentials.Certificate") as mock_cert, \
         patch("firebase_admin.firestore.client", return_value=MagicMock()):
        import db
        db._app = None
        db.firestore_client = None

        db.get_db()

        mock_cert.assert_called_once_with({"type": "service_account"})
        mock_init.assert_called_once()


def test_init_passes_storage_bucket_option(monkeypatch):
    monkeypatch.setenv("FIREBASE_SERVICE_ACCOUNT_KEY_JSON", '{"type": "service_account"}')
    monkeypatch.setenv("FIREBASE_STORAGE_BUCKET", "my-project.appspot.com")
    with patch("firebase_admin.initialize_app") as mock_init, \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()):
        import db
        db._app = None
        db.firestore_client = None

        db.get_db()

        # options è il secondo argomento posizionale di initialize_app(cred, options)
        assert mock_init.call_args[0][1] == {"storageBucket": "my-project.appspot.com"}
