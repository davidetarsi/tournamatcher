from __future__ import annotations

import json
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
        key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_JSON")
        if key_json:
            cred = credentials.Certificate(json.loads(key_json))
        else:
            # fallback locale: path al file della service account
            cred = credentials.Certificate(os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY"))

        options = {}
        bucket = os.getenv("FIREBASE_STORAGE_BUCKET")
        if bucket:
            options["storageBucket"] = bucket

        try:
            _app = firebase_admin.initialize_app(cred, options)
            firestore_client = firestore.client()
        except Exception:
            _app = None  # reset so next call retries
            raise


def get_db():
    _init()
    return firestore_client
