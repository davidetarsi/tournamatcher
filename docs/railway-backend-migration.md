# Railway Backend Migration Notes

When deploying the FastAPI backend to Railway instead of a VPS, these changes are required.

## 1. Firebase service account key — file → env var

Currently `db.py` reads the key from a file path:
```python
key_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")
cred = credentials.Certificate(key_path)
```

Railway uses environment variables, not Docker secrets. Set `FIREBASE_SERVICE_ACCOUNT_KEY_JSON` as a Railway env var containing the full JSON content of `serviceAccountKey.json`, then update `db.py`:

```python
import json, os
from firebase_admin import credentials, firestore
import firebase_admin

key_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY_JSON")
cred = credentials.Certificate(json.loads(key_json))
firebase_admin.initialize_app(cred)
firestore_client = firestore.client()
```

## 2. nginx.conf — not needed on Railway

Railway handles HTTPS and routing automatically. The `nginx.conf` written for the VPS setup is not used on Railway. Rate limiting (nginx zones) must be handled entirely by slowapi — which is already in place on all endpoints.

## 3. docker-compose.yml — not used on Railway

Railway deploys directly from the `Dockerfile`. The `docker-compose.yml` is only for local development. On Railway:
- Set all environment variables in the Railway dashboard
- The `tmpfs` and `read_only` settings are not available — Railway manages the container environment

## 4. CORS — add to FastAPI

When the frontend is on Vercel and the backend is on Railway, they are on different origins. Add CORS middleware to `backend/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-app.vercel.app"],  # replace with real Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

Restrict `allow_origins` to the exact Vercel domain — never use `"*"` in production.

## 5. Health check on Railway

Railway uses the `/health` endpoint (already implemented) for health checks. In the Railway dashboard, set:
- Health check path: `/health`
- Port: `8000`
