from __future__ import annotations

import os
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv

load_dotenv()

_app = None
firestore_client = None


def _init():
    global _app, firestore_client
    if _app is None:
        key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
        cred = credentials.Certificate(key_path)
        try:
            _app = firebase_admin.initialize_app(cred)
            firestore_client = firestore.client()
        except Exception:
            _app = None  # reset so next call retries
            raise


def get_db():
    _init()
    return firestore_client
