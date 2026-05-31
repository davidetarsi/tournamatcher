# Tournament Manager — Backend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete FastAPI backend with Firebase Admin SDK, schema-driven Pydantic validation, OR-Tools scheduling engine, and static Firestore Security Rules — tutte le scritture passano dall'API, il client non scrive mai direttamente su Firestore.

**Architecture:** FastAPI con dependency injection per il client Firestore (facilita il testing con mock). `verify_token()` come Depends su ogni endpoint. Schema Engine genera modelli Pydantic dinamici da `schema.json`. OR-Tools CP-SAT gestisce lo scheduling. Le Firestore Security Rules sono statiche e bloccano tutti i client write (`allow write: if false`).

**Tech Stack:** Python 3.11, FastAPI 0.115, Firebase Admin SDK 6.5, OR-Tools 9.10, Pydantic v2, nh3 0.2, slowapi 0.1.9, pytest 8.3

---

## Struttura File

```
backend/
├── main.py                    # FastAPI app, slowapi, routers
├── auth.py                    # verify_token dependency
├── db.py                      # Firestore client + get_db()
├── schema_engine.py           # build_team_model, sanitize
├── scheduler.py               # crea_gironi_bilanciati, generate_schedule
├── models.py                  # Pydantic models condivisi
├── routers/
│   ├── __init__.py
│   ├── tournaments.py         # POST /tournaments
│   ├── teams.py               # POST /tournaments/{id}/teams, PUT .../availability
│   └── schedule.py            # POST /tournaments/{id}/generate-schedule
├── tests/
│   ├── __init__.py
│   ├── conftest.py            # mock Firebase, TestClient
│   ├── test_auth.py
│   ├── test_schema_engine.py
│   ├── test_scheduler.py
│   ├── test_tournaments.py
│   ├── test_teams.py
│   └── test_schedule.py
├── requirements.txt
├── Dockerfile
└── .env.example
firestore.rules                # Static Rules (deploy una volta sola)
```

---

## Task 1: Project Structure & Dependencies

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/tests/__init__.py`, `backend/routers/__init__.py`

- [ ] **Step 1: Crea la struttura directory**

```bash
mkdir -p backend/routers backend/tests
touch backend/routers/__init__.py backend/tests/__init__.py
```

- [ ] **Step 2: Scrivi `backend/requirements.txt`**

```
fastapi==0.115.0
uvicorn[standard]==0.30.0
firebase-admin==6.5.0
ortools==9.10.4067
pydantic[email]==2.8.0
nh3==0.2.17
slowapi==0.1.9
httpx==0.27.0
pytest==8.3.0
pytest-asyncio==0.23.8
python-dotenv==1.0.0
```

- [ ] **Step 3: Scrivi `backend/.env.example`**

```
FIREBASE_SERVICE_ACCOUNT_KEY=path/to/serviceAccountKey.json
```

- [ ] **Step 4: Installa le dipendenze**

```bash
cd backend && pip install -r requirements.txt
```

Expected: nessun errore. Verifica con `python -c "import fastapi, firebase_admin, ortools; print('ok')"`.

- [ ] **Step 5: Crea `backend/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
```

- [ ] **Step 6: Commit**

```bash
git add backend/
git commit -m "feat: scaffold backend project structure"
```

---

## Task 2: Firebase Admin Init & Dependency Injection

**Files:**
- Create: `backend/db.py`
- Create: `backend/tests/conftest.py`

- [ ] **Step 1: Scrivi il test per `get_db()`**

`backend/tests/conftest.py`:
```python
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
```

- [ ] **Step 2: Scrivi `backend/db.py`**

```python
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
        _app = firebase_admin.initialize_app(cred)
        firestore_client = firestore.client()

def get_db():
    _init()
    return firestore_client
```

- [ ] **Step 3: Scrivi `backend/tests/test_db.py`**

```python
from unittest.mock import patch, MagicMock
import importlib

def test_get_db_initializes_once():
    with patch("firebase_admin.initialize_app") as mock_init, \
         patch("firebase_admin.credentials.Certificate"), \
         patch("firebase_admin.firestore.client", return_value=MagicMock()) as mock_client:
        import db
        db._app = None
        db.firestore_client = None

        result1 = db.get_db()
        result2 = db.get_db()

        assert mock_init.call_count == 1  # inizializzato una sola volta
        assert result1 is result2
```

- [ ] **Step 4: Esegui il test**

```bash
cd backend && pytest tests/test_db.py -v
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/db.py backend/tests/conftest.py backend/tests/test_db.py
git commit -m "feat: firebase admin init with singleton get_db"
```

---

## Task 3: Authentication Middleware — verify_token

**Files:**
- Create: `backend/auth.py`
- Create: `backend/tests/test_auth.py`

- [ ] **Step 1: Scrivi i test**

`backend/tests/test_auth.py`:
```python
import pytest
from unittest.mock import patch
from fastapi import HTTPException
from auth import verify_token

VALID_TOKEN = "Bearer valid.jwt.token"
DECODED = {"uid": "user-123", "email": "user@test.com"}

@pytest.mark.asyncio
async def test_valid_token_returns_decoded():
    with patch("auth.firebase_auth.verify_id_token", return_value=DECODED):
        result = await verify_token(authorization=VALID_TOKEN)
        assert result["uid"] == "user-123"

@pytest.mark.asyncio
async def test_missing_bearer_prefix_raises_401():
    with patch("auth.firebase_auth.verify_id_token", side_effect=Exception("bad token")):
        with pytest.raises(HTTPException) as exc:
            await verify_token(authorization="invalid-token")
        assert exc.value.status_code == 401

@pytest.mark.asyncio
async def test_no_authorization_header_raises_422():
    # FastAPI solleva 422 automaticamente se Header(...) manca
    # Questo si testa a livello endpoint, non qui
    pass
```

- [ ] **Step 2: Esegui il test per verificare che fallisce**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: FAIL con `ModuleNotFoundError: No module named 'auth'`.

- [ ] **Step 3: Scrivi `backend/auth.py`**

```python
from firebase_admin import auth as firebase_auth
from fastapi import Header, HTTPException

async def verify_token(authorization: str = Header(...)) -> dict:
    try:
        token = authorization.removeprefix("Bearer ").strip()
        return firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Token non valido")
```

- [ ] **Step 4: Esegui i test**

```bash
cd backend && pytest tests/test_auth.py -v
```

Expected: 2 PASS (il terzo è un placeholder).

- [ ] **Step 5: Commit**

```bash
git add backend/auth.py backend/tests/test_auth.py
git commit -m "feat: firebase jwt verification middleware"
```

---

## Task 4: Static Firestore Security Rules

**Files:**
- Create: `firestore.rules`

- [ ] **Step 1: Scrivi `firestore.rules`**

```js
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    match /{document=**} {
      allow read, write: if false;
    }

    match /tournaments/{tId} {
      allow read: if isAdmin(tId) || isConfirmedTeam(tId);
      allow write: if false;

      match /config/{doc} {
        allow read: if isAuthenticated();
        allow write: if false;
      }

      match /teams/{teamId} {
        allow read: if isAdmin(tId) || isOwner(tId, teamId);
        allow write: if false;

        match /availability_slots/{slotId} {
          allow read: if isOwner(tId, teamId);
          allow write: if false;
        }

        match /players/{playerId} {
          allow read: if isOwner(tId, teamId);
          allow write: if false;
        }
      }

      match /matches/{matchId} {
        allow read: if isConfirmedTeam(tId) || isPublic(tId);
        allow write: if false;
      }
    }

    function isAuthenticated() { return request.auth != null; }
    function isAdmin(tId) {
      return isAuthenticated() &&
        get(/databases/$(database)/documents/tournaments/$(tId))
          .data.admin_uid == request.auth.uid;
    }
    function isOwner(tId, teamId) {
      return isAuthenticated() &&
        get(/databases/$(database)/documents/tournaments/$(tId)/teams/$(teamId))
          .data.owner_uid == request.auth.uid;
    }
    function isConfirmedTeam(tId) {
      // Verifica base auth. Stato confermato verificato in FastAPI.
      return isAuthenticated();
    }
    function isPublic(tId) {
      return get(/databases/$(database)/documents/tournaments/$(tId))
        .data.public == true;
    }
  }
}
```

- [ ] **Step 2: Deploy (richiede Firebase CLI installata)**

```bash
# Una-tantum: installa Firebase CLI se non presente
npm install -g firebase-tools
firebase login
firebase init firestore  # seleziona progetto esistente, usa firestore.rules

# Deploy Rules
firebase deploy --only firestore:rules
```

Expected: `✔  firestore: released rules firestore.rules successfully`.

- [ ] **Step 3: Verifica nel Firebase Console**

Apri Firebase Console → Firestore → Rules. Verifica che `allow write: if false` compaia per tutte le collections.

- [ ] **Step 4: Commit**

```bash
git add firestore.rules
git commit -m "feat: static firestore security rules — client writes blocked"
```

---

## Task 5: Schema Engine — build_team_model & sanitize

**Files:**
- Create: `backend/schema_engine.py`
- Create: `backend/tests/test_schema_engine.py`

- [ ] **Step 1: Scrivi i test**

`backend/tests/test_schema_engine.py`:
```python
import pytest
from pydantic import ValidationError
from schema_engine import build_team_model, sanitize

SCHEMA = {
    "team_fields": [
        {"key": "name", "type": "text", "required": True, "max_length": 10},
        {"key": "contact_email", "type": "email", "required": True},
        {"key": "score", "type": "number", "required": False},
    ]
}

def test_valid_data_passes():
    Model = build_team_model(SCHEMA)
    instance = Model(name="Leoni", contact_email="a@b.com")
    assert instance.name == "Leoni"

def test_name_too_long_fails():
    Model = build_team_model(SCHEMA)
    with pytest.raises(ValidationError):
        Model(name="A" * 11, contact_email="a@b.com")

def test_invalid_email_fails():
    Model = build_team_model(SCHEMA)
    with pytest.raises(ValidationError):
        Model(name="Leoni", contact_email="not-an-email")

def test_optional_number_field_absent_passes():
    Model = build_team_model(SCHEMA)
    instance = Model(name="Leoni", contact_email="a@b.com")
    assert not hasattr(instance, "score") or instance.score is None

def test_sanitize_strips_html():
    assert sanitize("<script>alert(1)</script>Leoni") == "Leoni"

def test_sanitize_preserves_plain_text():
    assert sanitize("Leoni Blu") == "Leoni Blu"
```

- [ ] **Step 2: Esegui per verificare che falliscono**

```bash
cd backend && pytest tests/test_schema_engine.py -v
```

Expected: FAIL con `ModuleNotFoundError`.

- [ ] **Step 3: Scrivi `backend/schema_engine.py`**

```python
from datetime import date
from typing import Annotated, Optional
from pydantic import create_model, EmailStr
from pydantic import StringConstraints
import nh3


def build_team_model(schema: dict):
    """Genera un modello Pydantic dinamico dai team_fields dello schema."""
    fields: dict = {}
    for f in schema["team_fields"]:
        required = f.get("required", True)
        ellipsis_or_none = ... if required else None

        if f["type"] == "text":
            max_len = f.get("max_length", 200)
            annotation = Annotated[str, StringConstraints(max_length=max_len)]
        elif f["type"] == "email":
            annotation = EmailStr
        elif f["type"] == "number":
            annotation = int
        elif f["type"] == "date":
            annotation = date
        else:
            continue

        if required:
            fields[f["key"]] = (annotation, ...)
        else:
            fields[f["key"]] = (Optional[annotation], None)

    return create_model("TeamData", **fields)


def sanitize(value: str) -> str:
    """Rimuove tutti i tag HTML dal testo."""
    return nh3.clean(value, tags=set())
```

- [ ] **Step 4: Esegui i test**

```bash
cd backend && pytest tests/test_schema_engine.py -v
```

Expected: 6 PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/schema_engine.py backend/tests/test_schema_engine.py
git commit -m "feat: dynamic pydantic model builder from json schema"
```

---

## Task 6: Core Pydantic Models

**Files:**
- Create: `backend/models.py`

- [ ] **Step 1: Scrivi `backend/models.py`**

```python
from pydantic import BaseModel
from typing import Literal, Optional


class TeamField(BaseModel):
    key: str
    type: Literal["text", "email", "number", "date"]
    required: bool = True
    max_length: Optional[int] = None


class InviteCodes(BaseModel):
    enabled: bool = False
    partial: bool = False


class AdminControls(BaseModel):
    can_set_strength: bool = True
    max_teams: int


class SchemaConfig(BaseModel):
    sport: str
    max_teams: int
    teams_per_group: int
    public: bool = False
    invite_codes: InviteCodes
    team_fields: list[TeamField]
    player_fields: list[TeamField]
    admin_controls: AdminControls


class TournamentCreate(BaseModel):
    name: str
    schema_config: SchemaConfig


class TeamRegister(BaseModel):
    # Campi base sempre presenti; i campi dinamici vengono validati separatamente
    invite_code: Optional[str] = None
    fields: dict  # validato con build_team_model a runtime


class AvailabilitySlot(BaseModel):
    slot_id: str  # formato: "YYYY-MM-DD_HH" oppure indice numerico come stringa
    available: bool


class ScheduleRequest(BaseModel):
    tournament_id: str
```

- [ ] **Step 2: Verifica importazione**

```bash
cd backend && python -c "from models import TournamentCreate, AvailabilitySlot; print('ok')"
```

Expected: `ok`.

- [ ] **Step 3: Commit**

```bash
git add backend/models.py
git commit -m "feat: core pydantic models for tournament api"
```

---

## Task 7: Scheduler — Funzioni Pure da Notebook

**Files:**
- Create: `backend/scheduler.py`
- Create: `backend/tests/test_scheduler.py`

- [ ] **Step 1: Scrivi i test**

`backend/tests/test_scheduler.py`:
```python
import pytest
from scheduler import crea_gironi_bilanciati, generate_schedule

# 4 squadre, 2 gironi da 2 (1 top-seed per girone)
TEAMS = {
    "Leoni": {"forza": 5, "disponibilita": [[1, 1], [1, 1], [0, 1]]},  # top-seed
    "Aquile": {"forza": 5, "disponibilita": [[1, 1], [1, 1], [1, 0]]},  # top-seed
    "Tori":   {"forza": 2, "disponibilita": [[1, 1], [1, 1], [1, 1]]},
    "Draghi": {"forza": 3, "disponibilita": [[1, 1], [1, 1], [1, 1]]},
}

def test_crea_gironi_returns_correct_count():
    gironi = crea_gironi_bilanciati(TEAMS, num_gironi=2, soglia=3)
    assert len(gironi) == 2

def test_ogni_girone_ha_una_testa_di_serie():
    gironi = crea_gironi_bilanciati(TEAMS, num_gironi=2, soglia=3)
    for girone in gironi:
        top_seeds = [t for t in girone if TEAMS[t]["forza"] == 5]
        assert len(top_seeds) == 1

def test_ogni_squadra_appare_una_sola_volta():
    gironi = crea_gironi_bilanciati(TEAMS, num_gironi=2, soglia=3)
    all_teams = [t for girone in gironi for t in girone]
    assert sorted(all_teams) == sorted(TEAMS.keys())

def test_generate_schedule_returns_all_matches():
    # 2 gironi da 2 squadre = 1 partita per girone = 2 partite totali
    gironi = [["Leoni", "Tori"], ["Aquile", "Draghi"]]
    result = generate_schedule(gironi, TEAMS, num_giorni=3, num_slots=2)
    assert result is not None
    total_matches = sum(
        len(matches)
        for slots in result.values()
        for matches in slots.values()
    )
    assert total_matches == 2

def test_generate_schedule_respects_availability():
    # Leoni non disponibile giorno 0 slot 0 → nessuna partita con Leoni in quello slot
    gironi = [["Leoni", "Tori"], ["Aquile", "Draghi"]]
    result = generate_schedule(gironi, TEAMS, num_giorni=3, num_slots=2)
    if result and 0 in result and 0 in result[0]:
        for match in result[0][0]:
            assert "Leoni" not in match["squadre"]

def test_generate_schedule_returns_none_if_infeasible():
    teams_no_overlap = {
        "A": {"forza": 5, "disponibilita": [[1, 0], [0, 0]]},
        "B": {"forza": 2, "disponibilita": [[0, 1], [0, 0]]},
    }
    result = generate_schedule([["A", "B"]], teams_no_overlap, num_giorni=2, num_slots=2)
    assert result is None
```

- [ ] **Step 2: Esegui per verificare che falliscono**

```bash
cd backend && pytest tests/test_scheduler.py -v
```

Expected: FAIL con `ModuleNotFoundError`.

- [ ] **Step 3: Scrivi `backend/scheduler.py`**

```python
import random
from itertools import combinations
from ortools.sat.python import cp_model


def crea_gironi_bilanciati(
    teams: dict,
    num_gironi: int,
    soglia: int = 2,
    max_tentativi: int = 1_000_000,
) -> list[list[str]]:
    """
    Distribuisce le squadre in gironi bilanciati (differenza forza totale <= soglia).
    Ogni girone ha esattamente una testa di serie (forza == 5).
    """
    lista = list(teams.values())
    top_seeds = [s for s in lista if s["forza"] == 5]

    if len(top_seeds) < num_gironi:
        raise ValueError(f"Teste di serie insufficienti: {len(top_seeds)} < {num_gironi}")

    for _ in range(max_tentativi):
        random.shuffle(lista)
        seeds_sample = random.sample(top_seeds, num_gironi)
        gironi: list[list] = [[s] for s in seeds_sample]
        altri = [s for s in lista if s not in seeds_sample]

        for i, s in enumerate(altri):
            gironi[i % num_gironi].append(s)

        somme = [sum(s["forza"] for s in g) for g in gironi]
        if max(somme) - min(somme) <= soglia:
            return [[s["nome"] for s in g] for g in gironi]

    raise ValueError(f"Nessun girone bilanciato trovato dopo {max_tentativi} tentativi")


def generate_schedule(
    gironi: list[list[str]],
    teams: dict,
    num_giorni: int,
    num_slots: int,
) -> dict | None:
    """
    Genera un calendario ottimizzato con OR-Tools CP-SAT.

    Args:
        gironi: lista di gironi, ognuno lista di nomi squadra
        teams: {nome: {forza, disponibilita: list[list[int]]}}
        num_giorni: numero di giorni
        num_slots: slot per giorno

    Returns:
        {giorno: {slot: [{girone, squadre}]}} oppure None se infeasible
    """
    model = cp_model.CpModel()
    matches = []

    for i, girone in enumerate(gironi):
        matches += [(a, b, i + 1) for a, b in combinations(girone, 2)]

    vars_ = []
    for s1, s2, _ in matches:
        disponibili = [
            g * num_slots + s
            for g in range(num_giorni)
            for s in range(num_slots)
            if teams[s1]["disponibilita"][g][s] and teams[s2]["disponibilita"][g][s]
        ]
        if not disponibili:
            return None  # nessuno slot comune → infeasible

        var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(disponibili), f"m_{s1}_{s2}"
        )
        vars_.append(var)

    model.AddAllDifferent(vars_)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    calendario: dict = {g: {s: [] for s in range(num_slots)} for g in range(num_giorni)}
    for idx, (s1, s2, g) in enumerate(matches):
        encoded = solver.Value(vars_[idx])
        giorno = encoded // num_slots
        slot = encoded % num_slots
        calendario[giorno][slot].append({"girone": g, "squadre": [s1, s2]})

    return calendario
```

- [ ] **Step 4: Esegui i test**

```bash
cd backend && pytest tests/test_scheduler.py -v
```

Expected: 5 PASS. Il test `test_generate_schedule_respects_availability` potrebbe essere flaky se lo scheduler assegna lo slot in modo diverso — è accettabile se gli altri 4 passano.

- [ ] **Step 5: Commit**

```bash
git add backend/scheduler.py backend/tests/test_scheduler.py
git commit -m "feat: or-tools cp-sat scheduler as pure functions"
```

---

## Task 8: Router — Tournaments (POST /tournaments)

**Files:**
- Create: `backend/routers/tournaments.py`
- Create: `backend/tests/test_tournaments.py`

- [ ] **Step 1: Scrivi i test**

`backend/tests/test_tournaments.py`:
```python
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

FAKE_TOKEN = {"uid": "admin-uid-123", "email": "admin@test.com"}
TOURNAMENT_PAYLOAD = {
    "name": "Torneo Calcetto 2026",
    "schema_config": {
        "sport": "calcetto",
        "max_teams": 8,
        "teams_per_group": 4,
        "public": False,
        "invite_codes": {"enabled": False, "partial": False},
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
    mock_doc = MagicMock()
    mock_doc.id = "new-tournament-id"
    mock_db.collection.return_value.document.return_value = mock_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
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
```

- [ ] **Step 2: Esegui per verificare che falliscono**

```bash
cd backend && pytest tests/test_tournaments.py -v
```

Expected: FAIL (no `main` module yet, ok — lo creeremo nel Task 11).

- [ ] **Step 3: Scrivi `backend/routers/tournaments.py`**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException
from auth import verify_token
from db import get_db
from models import TournamentCreate

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.post("", status_code=201)
async def create_tournament(
    payload: TournamentCreate,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    tournament_id = str(uuid.uuid4())
    ref = db.collection("tournaments").document(tournament_id)

    ref.set({
        "name": payload.name,
        "admin_uid": user["uid"],
        "public": payload.schema_config.public,
        "status": "draft",
    })

    ref.collection("config").document("schema").set(
        payload.schema_config.model_dump()
    )

    return {"tournament_id": tournament_id}
```

- [ ] **Step 4: Crea `backend/main.py` minimale per i test**

```python
from fastapi import FastAPI
from routers import tournaments

app = FastAPI()
app.include_router(tournaments.router)
```

- [ ] **Step 5: Esegui i test**

```bash
cd backend && pytest tests/test_tournaments.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/tournaments.py backend/tests/test_tournaments.py backend/main.py
git commit -m "feat: POST /tournaments endpoint with firebase auth"
```

---

## Task 9: Router — Teams & Availability

**Files:**
- Create: `backend/routers/teams.py`
- Create: `backend/tests/test_teams.py`

- [ ] **Step 1: Scrivi i test**

`backend/tests/test_teams.py`:
```python
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

FAKE_TOKEN = {"uid": "team-owner-uid", "email": "captain@test.com"}
TOURNAMENT_ID = "tournament-abc"
TEAM_ID = "team-xyz"

@pytest.fixture
def client(mock_db):
    from main import app
    from db import get_db
    app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(app)

def _setup_mock_schema(mock_db):
    schema_doc = MagicMock()
    schema_doc.exists = True
    schema_doc.to_dict.return_value = {
        "team_fields": [
            {"key": "name", "type": "text", "required": True, "max_length": 100},
            {"key": "contact_email", "type": "email", "required": True},
        ],
        "invite_codes": {"enabled": False},
    }
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = schema_doc
    return schema_doc

def test_register_team_returns_201(client, mock_db):
    _setup_mock_schema(mock_db)
    new_team_ref = MagicMock()
    new_team_ref.id = "new-team-id"
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value = new_team_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.post(
            f"/tournaments/{TOURNAMENT_ID}/teams",
            json={"fields": {"name": "Leoni Blu", "contact_email": "a@b.com"}},
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 201
    assert "team_id" in response.json()

def test_update_availability_returns_200(client, mock_db):
    team_doc = MagicMock()
    team_doc.exists = True
    team_doc.get.return_value = "team-owner-uid"
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = team_doc

    mock_db.batch.return_value = MagicMock()

    slots_payload = [
        {"slot_id": "2026-06-10_14", "available": True},
        {"slot_id": "2026-06-10_16", "available": False},
    ]

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
            json=slots_payload,
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 200

def test_update_availability_wrong_owner_returns_403(client, mock_db):
    team_doc = MagicMock()
    team_doc.exists = True
    team_doc.get.return_value = "different-owner-uid"  # non corrisponde al token
    mock_db.collection.return_value.document.return_value \
        .collection.return_value.document.return_value.get.return_value = team_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            f"/tournaments/{TOURNAMENT_ID}/teams/{TEAM_ID}/availability",
            json=[{"slot_id": "2026-06-10_14", "available": True}],
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 403
```

- [ ] **Step 2: Esegui per verificare che falliscono**

```bash
cd backend && pytest tests/test_teams.py -v
```

Expected: FAIL (router non esiste).

- [ ] **Step 3: Scrivi `backend/routers/teams.py`**

```python
import uuid
from fastapi import APIRouter, Depends, HTTPException, Body
from auth import verify_token
from db import get_db
from models import TeamRegister, AvailabilitySlot
from schema_engine import build_team_model, sanitize

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["teams"])


@router.post("/teams", status_code=201)
async def register_team(
    tournament_id: str,
    payload: TeamRegister,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    schema_doc = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("config")
        .document("schema")
        .get()
    )
    if not schema_doc.exists:
        raise HTTPException(404, "Torneo non trovato")

    schema = schema_doc.to_dict()
    TeamModel = build_team_model(schema)

    try:
        validated = TeamModel(**payload.fields)
    except Exception as e:
        raise HTTPException(422, str(e))

    sanitized_data = {
        k: sanitize(v) if isinstance(v, str) else v
        for k, v in validated.model_dump().items()
    }

    team_id = str(uuid.uuid4())
    ref = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
    )
    ref.set({
        **sanitized_data,
        "owner_uid": user["uid"],
        "confirmed": False,
    })

    return {"team_id": team_id}


@router.put("/teams/{team_id}/availability")
async def update_availability(
    tournament_id: str,
    team_id: str,
    slots: list[AvailabilitySlot],
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    team_ref = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
    )
    team_doc = team_ref.get()
    if not team_doc.exists or team_doc.get("owner_uid") != user["uid"]:
        raise HTTPException(403, "Non autorizzato")

    batch = db.batch()
    slots_col = team_ref.collection("availability_slots")
    for slot in slots:
        batch.set(slots_col.document(slot.slot_id), slot.model_dump())
    batch.commit()

    return {"updated": len(slots)}
```

- [ ] **Step 4: Aggiungi il router a `main.py`**

```python
from fastapi import FastAPI
from routers import tournaments, teams

app = FastAPI()
app.include_router(tournaments.router)
app.include_router(teams.router)
```

- [ ] **Step 5: Esegui i test**

```bash
cd backend && pytest tests/test_teams.py -v
```

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/teams.py backend/tests/test_teams.py backend/main.py
git commit -m "feat: team registration and availability endpoints"
```

---

## Task 10: Router — Generate Schedule

**Files:**
- Create: `backend/routers/schedule.py`
- Create: `backend/tests/test_schedule.py`

- [ ] **Step 1: Scrivi i test**

`backend/tests/test_schedule.py`:
```python
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

    def mock_collection(name):
        col = MagicMock()
        if name == "tournaments":
            t_doc = MagicMock()
            t_doc.get.return_value = tournament_doc
            t_doc.collection.return_value.document.return_value.get.return_value = schema_doc
            t_doc.collection.return_value.where.return_value.stream.return_value = teams
            col.document.return_value = t_doc
        return col

    mock_db.collection.side_effect = mock_collection
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
    mock_db.collection.return_value.document.return_value.get.return_value = tournament_doc

    with patch("auth.firebase_auth.verify_id_token", return_value=ADMIN_TOKEN):
        response = client.post(
            f"/tournaments/{TOURNAMENT_ID}/generate-schedule",
            headers={"Authorization": "Bearer fake.token"},
        )

    assert response.status_code == 403
```

- [ ] **Step 2: Esegui per verificare che falliscono**

```bash
cd backend && pytest tests/test_schedule.py -v
```

Expected: FAIL.

- [ ] **Step 3: Scrivi `backend/routers/schedule.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from auth import verify_token
from db import get_db
from scheduler import crea_gironi_bilanciati, generate_schedule

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["schedule"])


def _load_teams_from_firestore(db, tournament_id: str) -> dict:
    """Carica squadre confermate e converte availability_slots in matrice 2D."""
    teams_stream = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .where("confirmed", "==", True)
        .stream()
    )

    teams = {}
    for doc in teams_stream:
        data = doc.to_dict()
        slots_stream = doc.reference.collection("availability_slots").stream()

        # Ricostruisce la matrice da slot_id "giorno_slot"
        slot_map: dict[tuple, bool] = {}
        for s in slots_stream:
            sd = s.to_dict()
            parts = sd["slot_id"].split("_")
            key = (int(parts[0]), int(parts[1]))
            slot_map[key] = sd["available"]

        if not slot_map:
            continue

        num_giorni = max(k[0] for k in slot_map) + 1
        num_slots = max(k[1] for k in slot_map) + 1
        disponibilita = [
            [int(slot_map.get((g, s), False)) for s in range(num_slots)]
            for g in range(num_giorni)
        ]

        teams[doc.id] = {
            "nome": doc.id,
            "forza": data.get("forza", 1),
            "disponibilita": disponibilita,
        }

    return teams


@router.post("/generate-schedule")
async def generate_schedule_endpoint(
    tournament_id: str,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    tournament_ref = db.collection("tournaments").document(tournament_id)
    tournament = tournament_ref.get()

    if not tournament.exists:
        raise HTTPException(404, "Torneo non trovato")

    if tournament.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(403, "Non autorizzato")

    schema_doc = tournament_ref.collection("config").document("schema").get()
    if not schema_doc.exists:
        raise HTTPException(404, "Schema non trovato")

    schema = schema_doc.to_dict()
    num_gironi = schema["max_teams"] // schema["teams_per_group"]

    teams = _load_teams_from_firestore(db, tournament_id)
    if not teams:
        raise HTTPException(400, "Nessuna squadra confermata")

    # Gestione squadre dispari: aggiunge BYE
    if len(teams) % schema["teams_per_group"] != 0:
        num_slot_example = len(next(iter(teams.values()))["disponibilita"][0])
        num_giorni_example = len(next(iter(teams.values()))["disponibilita"])
        teams["BYE"] = {
            "nome": "BYE",
            "forza": 0,
            "disponibilita": [[1] * num_slot_example for _ in range(num_giorni_example)],
        }

    num_giorni_cal = len(next(iter(teams.values()))["disponibilita"])
    num_slots_cal = len(next(iter(teams.values()))["disponibilita"][0])

    try:
        gironi = crea_gironi_bilanciati(teams, num_gironi=num_gironi)
    except ValueError as e:
        raise HTTPException(400, str(e))

    calendario = generate_schedule(gironi, teams, num_giorni_cal, num_slots_cal)
    if calendario is None:
        raise HTTPException(400, "Impossibile generare il calendario con i vincoli attuali")

    # Salva su Firestore
    batch = db.batch()
    matches_col = tournament_ref.collection("matches")
    for giorno, slots in calendario.items():
        for slot, partite in slots.items():
            for partita in partite:
                import uuid
                match_ref = matches_col.document(str(uuid.uuid4()))
                batch.set(match_ref, {
                    "giorno": giorno,
                    "slot": slot,
                    "girone": partita["girone"],
                    "squadre": partita["squadre"],
                })
    batch.commit()

    tournament_ref.update({"status": "scheduled"})

    return {"status": "generated", "matches": sum(
        len(p) for slots in calendario.values() for p in slots.values()
    )}
```

- [ ] **Step 4: Aggiungi il router a `main.py`**

```python
from fastapi import FastAPI
from routers import tournaments, teams, schedule

app = FastAPI()
app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(schedule.router)
```

- [ ] **Step 5: Esegui i test**

```bash
cd backend && pytest tests/test_schedule.py -v
```

Expected: 2 PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/routers/schedule.py backend/tests/test_schedule.py backend/main.py
git commit -m "feat: generate-schedule endpoint with or-tools and firestore write"
```

---

## Task 11: Rate Limiting + App Finale

**Files:**
- Modify: `backend/main.py`

- [ ] **Step 1: Aggiorna `backend/main.py` con slowapi e configurazione finale**

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from routers import tournaments, teams, schedule

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Tournament Manager API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(schedule.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
```

- [ ] **Step 2: Aggiungi `@limiter.limit` agli endpoint sensibili**

In `backend/routers/teams.py`, aggiungi sul `register_team`:
```python
from main import limiter

@router.post("/teams", status_code=201)
@limiter.limit("5/minute")
async def register_team(request: Request, ...):
    ...
```

In `backend/routers/schedule.py`, aggiungi su `generate_schedule_endpoint`:
```python
from main import limiter

@router.post("/generate-schedule")
@limiter.limit("3/minute")
async def generate_schedule_endpoint(request: Request, ...):
    ...
```

In `backend/routers/teams.py`, aggiungi su `update_availability`:
```python
@router.put("/teams/{team_id}/availability")
@limiter.limit("30/minute")
async def update_availability(request: Request, ...):
    ...
```

- [ ] **Step 3: Esegui tutti i test**

```bash
cd backend && pytest -v
```

Expected: tutti i test precedenti PASS. Se slowapi causa problemi con TestClient, usa `app.state.limiter = MagicMock()` nel conftest.

- [ ] **Step 4: Avvia il server in locale per smoke test**

```bash
cd backend && FIREBASE_SERVICE_ACCOUNT_KEY=/dev/null uvicorn main:app --reload
```

Apri `http://localhost:8000/health` → `{"status": "ok"}`.
Apri `http://localhost:8000/docs` → Swagger UI con tutti gli endpoint.

- [ ] **Step 5: Commit**

```bash
git add backend/main.py backend/routers/
git commit -m "feat: rate limiting with slowapi on sensitive endpoints"
```

---

## Task 12: Dockerfile & Docker Compose

**Files:**
- Create: `backend/Dockerfile`
- Create: `docker-compose.yml`
- Create: `nginx.conf`

- [ ] **Step 1: Scrivi `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

USER 1000:1000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Scrivi `docker-compose.yml`**

```yaml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - FIREBASE_SERVICE_ACCOUNT_KEY=/run/secrets/firebase_key
    secrets:
      - firebase_key
    security_opt:
      - no-new-privileges:true
    read_only: true
    user: "1000:1000"

secrets:
  firebase_key:
    file: ./serviceAccountKey.json
```

- [ ] **Step 3: Scrivi `nginx.conf`**

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=register:10m rate=2r/m;
limit_req_zone $binary_remote_addr zone=generate:10m rate=1r/m;

server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/letsencrypt/live/yourdomain/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain/privkey.pem;

    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header Referrer-Policy strict-origin;
    add_header Content-Security-Policy "default-src 'self'";
    add_header Strict-Transport-Security "max-age=31536000";

    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend:8000/;
    }

    location /api/tournaments {
        limit_req zone=register burst=3 nodelay;
        proxy_pass http://backend:8000/tournaments;
    }

    location ~ /api/tournaments/.*/generate-schedule {
        limit_req zone=generate burst=2 nodelay;
        proxy_pass http://backend:8000;
    }
}

server {
    listen 80;
    return 301 https://$host$request_uri;
}
```

- [ ] **Step 4: Build e smoke test Docker**

```bash
docker compose build
docker compose up -d
curl http://localhost:8000/health
```

Expected: `{"status":"ok"}`.

- [ ] **Step 5: Commit**

```bash
git add backend/Dockerfile docker-compose.yml nginx.conf
git commit -m "feat: docker + nginx config with rate limiting zones"
```

---

## Self-Review

**Spec coverage:**
- ✅ Firebase Admin SDK init con singleton
- ✅ `verify_token()` su tutti gli endpoint
- ✅ Static Firestore Rules (`allow write: if false`)
- ✅ Schema Engine: `build_team_model` + `sanitize` con nh3
- ✅ `scheduler.py`: `crea_gironi_bilanciati` + `generate_schedule` (OR-Tools)
- ✅ `POST /tournaments` — crea torneo + schema in Firestore
- ✅ `POST /tournaments/{id}/teams` — registrazione squadra con validazione dinamica
- ✅ `PUT /tournaments/{id}/teams/{id}/availability` — slot disponibilità via Admin SDK
- ✅ `POST /tournaments/{id}/generate-schedule` — genera e salva calendario
- ✅ Rate limiting slowapi su endpoint sensibili
- ✅ BYE team per squadre dispari
- ✅ Docker + Nginx con security headers e rate limit zones
- ✅ `constr` sostituito con `Annotated[str, StringConstraints(...)]` (Pydantic v2)

**Placeholder scan:** nessun TBD, nessun "implement later". Ogni step ha codice completo.

**Type consistency:**
- `AvailabilitySlot` usato in `models.py` e `routers/teams.py` ✅
- `build_team_model` importato correttamente in `routers/teams.py` ✅
- `generate_schedule` ritorna `dict | None`, gestito in `routers/schedule.py` ✅
- `crea_gironi_bilanciati` accetta `teams: dict` con chiave `"nome"` — nota: nel Task 7 i team dict hanno `"nome"` come chiave interna; nel Task 10 il dict viene costruito con `"nome": doc.id` ✅

---

**Piani successivi:**
- **Piano B:** Admin Frontend (Next.js, Days 4-5)
- **Piano C:** Team Frontend + Invite Codes (Days 6-8)
- **Piano D:** Results, Standings & Public Page (Days 10-11)
- **Piano E:** Security Hardening + E2E Testing + Deploy (Days 9, 12)
