# Tournament Manager
## Roadmap v5 — Architettura Schema-Driven + Write-Through API
**Next.js • FastAPI • Firebase Firestore • Defense in Depth**

> **Cosa cambia dalla v4:** Le Firestore Security Rules diventano statiche e non cambiano mai.
> Tutte le scritture passano per FastAPI (Admin SDK), che bypassa le Rules.
> Il client Firestore SDK è read-only. Eliminato `generateFirestoreRules(schema)`.

---

## Principio Guida: Schema-Driven + Write-Through API

Un file JSON per torneo è l'unica fonte di verità dell'intero sistema: genera form, struttura DB e validazione. La sicurezza è stratificata in 5 livelli indipendenti.

**Aggiunta rispetto alla v4:** il client non scrive mai direttamente su Firestore. Ogni scrittura passa per FastAPI, che usa l'Admin SDK (immune alle Rules). Le Rules coprono solo autenticazione e ownership — non contengono nomi di campo, tipi, o lunghezze massime. Questo significa che non vanno mai ridistribuite quando uno schema cambia.

```
Client (browser)
    │
    ├── READS  ──────────────────► Firestore SDK (real-time, diretto)
    │                                   │
    │                              Firestore Rules (statiche)
    │                              solo auth/ownership
    │
    └── WRITES ──────────────────► FastAPI
                                       │
                                  verify_token()  ← Firebase JWT
                                       │
                                  Pydantic + nh3  ← validazione schema
                                       │
                                  Admin SDK       ← bypassa Rules
                                       │
                                  Firestore
```

---

## Il File schema.json — Unica Fonte di Verità

Ogni torneo ha il suo documento Firestore `tournaments/{id}/config/schema`:

```json
{
  "tournament_id": "abc123",
  "sport": "calcetto",
  "max_teams": 32,
  "teams_per_group": 4,
  "public": false,
  "invite_codes": {
    "enabled": true,
    "partial": true
  },
  "team_fields": [
    { "key": "name", "type": "text", "required": true, "max_length": 100 },
    { "key": "contact_email", "type": "email", "required": true },
    { "key": "city", "type": "text", "required": false, "max_length": 80 }
  ],
  "player_fields": [
    { "key": "full_name", "type": "text", "required": true },
    { "key": "birth_date", "type": "date", "required": true },
    { "key": "jersey_number", "type": "number", "required": false }
  ],
  "admin_controls": {
    "can_set_strength": true,
    "max_teams": 32
  }
}
```

---

## Struttura Firestore

```
tournaments/
  {tournamentId}/
    admin_uid: "firebase_uid_admin"
    public: false
    config/schema          ← schema.json (fonte di verità)
    teams/{teamId}
      owner_uid: "firebase_uid_team"
      invite_code_hash: "sha256..."
      confirmed: false
      ...campi da team_fields
      players/{playerId}
        owner_uid: "firebase_uid_team"
        ...campi da player_fields
      availability_slots/{slotId}
        slot_id: "2026-06-10_14"
        available: true
    matches/{matchId}
      home_team_id, away_team_id, scheduled_at, group_name
```

---

## Architettura di Sicurezza — 5 Livelli (Defense in Depth)

### L1 — Firestore Security Rules (Statiche)

Le Rules non contengono logica schema-dipendente. Coprono solo autenticazione e ownership. **Non cambiano mai**, indipendentemente da quanti tornei vengono creati o come cambiano i loro schemi.

```js
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    match /{document=**} {
      allow read, write: if false;
    }

    match /tournaments/{tId} {
      allow read: if isAdmin(tId) || isConfirmedTeam(tId);
      allow write: if false;  // solo Admin SDK (FastAPI)

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
      // Verifica base: solo autenticazione. La conferma effettiva è controllata in FastAPI.
      return isAuthenticated();
    }
    function isPublic(tId) {
      return get(/databases/$(database)/documents/tournaments/$(tId))
        .data.public == true;
    }
  }
}
```

### L2 — Rate Limiting: Nginx + FastAPI (slowapi)

```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=register:10m rate=2r/m;
limit_req_zone $binary_remote_addr zone=generate:10m rate=1r/m;

location /api/          { limit_req zone=api burst=20 nodelay; }
location /api/register  { limit_req zone=register burst=3 nodelay; }
location /api/generate  { limit_req zone=generate burst=2 nodelay; }
```

```python
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/register")
@limiter.limit("5/minute")
async def register_team(request: Request, ...): ...

@app.post("/api/generate-schedule")
@limiter.limit("3/minute")
async def generate_schedule(request: Request, ...): ...

@app.put("/api/tournaments/{tournament_id}/teams/{team_id}/availability")
@limiter.limit("30/minute")
async def update_availability(request: Request, ...): ...
```

### L3 — Validazione Input: Pydantic + nh3

Nota: si usa `nh3` al posto di `bleach` — è il successore attivo con binding Rust, stessa API ma più veloce e mantenuto. In Pydantic v2, `constr` è deprecato: si usa `Annotated[str, StringConstraints(max_length=...)]`.

```python
from pydantic import create_model, EmailStr
from pydantic import StringConstraints
from typing import Annotated
from datetime import date
import nh3

def build_team_model(schema: dict):
    fields = {}
    for f in schema["team_fields"]:
        if f["type"] == "text":
            max_len = f.get("max_length", 200)
            fields[f["key"]] = (Annotated[str, StringConstraints(max_length=max_len)], ...)
        elif f["type"] == "email":
            fields[f["key"]] = (EmailStr, ...)
        elif f["type"] == "number":
            fields[f["key"]] = (int, ...)
        elif f["type"] == "date":
            fields[f["key"]] = (date, ...)
    return create_model("TeamData", **fields)

def sanitize(value: str) -> str:
    return nh3.clean(value, tags=set())

import hashlib, hmac

def hash_invite_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()

def verify_invite_code(input_code: str, stored_hash: str) -> bool:
    return hmac.compare_digest(hash_invite_code(input_code), stored_hash)
```

**Endpoint availability slots** — unico endpoint di scrittura aggiunto rispetto alla v4:

```python
class AvailabilitySlot(BaseModel):
    slot_id: str       # formato: "YYYY-MM-DD_HH"
    available: bool

@app.put("/api/tournaments/{tournament_id}/teams/{team_id}/availability")
@limiter.limit("30/minute")
async def update_availability(
    tournament_id: str,
    team_id: str,
    slots: list[AvailabilitySlot],
    user=Depends(verify_token)
):
    team = db.collection("tournaments").document(tournament_id)\
             .collection("teams").document(team_id).get()
    if not team.exists or team.get("owner_uid") != user["uid"]:
        raise HTTPException(403)

    batch = db.batch()
    slots_ref = db.collection(f"tournaments/{tournament_id}/teams/{team_id}/availability_slots")
    for slot in slots:
        batch.set(slots_ref.document(slot.slot_id), slot.dict())
    batch.commit()
```

La UX della griglia disponibilità rimane fluida: il client accumula le modifiche localmente e fa un singolo PUT al submit.

### L4 — Autenticazione: Verifica Token Firebase

```python
from firebase_admin import auth
from fastapi import Depends, HTTPException, Header

async def verify_token(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        decoded = auth.verify_id_token(token)
        return decoded
    except Exception:
        raise HTTPException(status_code=401, detail="Token non valido")

@app.post("/api/generate-schedule")
async def generate_schedule(
    user=Depends(verify_token),
    data: ScheduleRequest = Body(...)
):
    tournament = db.collection("tournaments").document(data.tournament_id).get()
    if tournament.get("admin_uid") != user["uid"]:
        raise HTTPException(status_code=403)
    ...
```

I token Firebase scadono ogni ora. Il client Next.js fa refresh automatico con `onAuthStateChanged`.

### L5 — Hardening Infrastruttura VPS + Docker

```bash
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw default deny incoming
ufw enable

apt install fail2ban
```

```nginx
add_header X-Frame-Options DENY;
add_header X-Content-Type-Options nosniff;
add_header Referrer-Policy strict-origin;
add_header Content-Security-Policy "default-src 'self'";
add_header Strict-Transport-Security "max-age=31536000";
```

```yaml
services:
  backend:
    security_opt: [no-new-privileges:true]
    read_only: true
    user: "1000:1000"
```

---

## Mappa Completa delle Minacce Coperte

| Minaccia | Livello | Meccanismo di difesa |
|---|---|---|
| Accesso non autenticato al DB | L1 + L4 | Rules `isAuthenticated()` + `verify_token()` |
| Lettura dati di altri tornei | L1 | Rules isolano per `tournamentId` |
| Squadra modifica dati altrui | L1 | `isOwner()` verifica `owner_uid` |
| **Scrittura diretta su Firestore bypassando FastAPI** | **L1** | **`allow write: if false` — nessun client può scrivere** |
| Injection campi arbitrari nel DB | L3 | Pydantic schema dinamico + Admin SDK scrive solo dati validati |
| XSS / script injection nei testi | L3 + L5 | `nh3.clean()` + Content-Security-Policy |
| Brute force invite codes | L2 + L3 | Rate limit 2/min + hash sha256 + `hmac.compare_digest` |
| DDoS / flood di richieste | L2 | Rate limit Nginx + slowapi per utente |
| Token JWT rubato e riusato | L4 | Scadenza automatica 1h + Firebase token revocation |
| Accesso SSH non autorizzato al VPS | L5 | Fail2ban + autenticazione solo con chiave SSH |
| Escalation privilegi nel container | L5 | `no-new-privileges` + user non-root + `read_only` filesystem |
| Enumerazione ID risorse (guessing) | L1 | ID Firestore sono UUID random non sequenziali |

---

## Stack Tecnologico

| Layer | Tecnologia | Ruolo |
|---|---|---|
| Frontend | Next.js 14 (App Router) | UI Admin + UI Squadre, form schema-driven |
| Form engine | react-hook-form + zod | Validazione e rendering da JSON schema |
| Backend API | FastAPI (Python) | Scheduling, validazione schema, **unico writer su Firestore** |
| Database + Auth | Firebase (Firestore + Auth) | NoSQL gerarchico, un torneo = una collection isolata |
| Config centrale | schema.json per torneo | Fonte di verità: UI + validazione (non più Rules) |
| Deploy | VPS + Nginx | Reverse proxy: frontend :3000, API :8000 |

---

## Architettura delle Pagine

| Pagina | Descrizione |
|---|---|
| `/admin` | Login admin, lista tornei gestiti |
| `/admin/new` | Crea torneo: sceglie template, personalizza schema.json |
| `/admin/[id]` | Dashboard torneo: squadre, strength, invite codes, scheduling |
| `/admin/[id]/schema` | Editor visuale campi (aggiunge/rimuove field dallo schema) |
| `/t/[id]` | Pagina pubblica torneo: gironi, calendario, risultati |
| `/t/[id]/register` | Registrazione squadra: form generato da schema.json |

---

## Flusso Generazione Calendario (FastAPI)

1. Verifica token Firebase (`verify_token`) — blocca subito se non valido
2. Controlla che `uid` sia admin del torneo su Firestore
3. Legge `schema.json` da `tournaments/{id}/config/schema`
4. Legge squadre confermate e i loro slot di disponibilità
5. Aggiunge squadra BYE se numero squadre è dispari
6. Valida dati contro schema con Pydantic + sanitizza testi con nh3
7. Chiama `generate_schedule(teams, slots, config)` da `scheduler.py`
8. Scrive matches in `tournaments/{id}/matches/` via Admin SDK, aggiorna status

---

## Roadmap — 12 Giorni di Sviluppo

### Giorno 1 — Setup & Infrastruttura
- Provisioning VPS, SSH con chiave (no password), cambio porta SSH
- Setup UFW firewall, fail2ban, Docker con `no-new-privileges`
- Creazione progetto Firebase, Firestore e Firebase Auth
- Nginx con SSL (Let's Encrypt) e security headers

### Giorno 2 — Schema Engine
- Definizione struttura schema.json e template predefiniti
- `generateZodSchema(schema)` → validatore dinamico per react-hook-form
- `build_team_model(schema)` → modello Pydantic dinamico per FastAPI
- ~~`generateFirestoreRules(schema)`~~ — **eliminato: Rules sono statiche**
- Test unitari engine con vari tipi di schema

### Giorno 3 — Conversione Notebook + FastAPI Sicuro
- Pulizia Jupyter Notebook in `scheduler.py` (funzioni pure)
- FastAPI con `verify_token()` su tutti gli endpoint
- Endpoint `/create-tournament`: crea struttura Firestore + scrive `config/schema`
  - **Non deploya Rules** — le Rules statiche sono già in produzione dal Giorno 1
- Endpoint `PUT /availability` per slot disponibilità

### Giorno 4-5 — Frontend Admin
- Login admin con Firebase Auth + protezione route con middleware Next.js
- Dashboard: crea torneo, scelta template, personalizzazione schema
- Editor visuale campi + gestione squadre + strength + invite codes
- Pulsante "Genera Gironi" → FastAPI (con token Bearer) → calendario

### Giorno 6-7 — Frontend Squadre
- Pagina `/t/[id]/register`: form generato dinamicamente da schema.json
- Gestione invite code (visibile solo se enabled), verifica lato server
- Griglia disponibilità interattiva → `PUT /availability` al submit
- Pagina conferma + visualizzazione partite (real-time Firestore read)

### Giorno 8 — Invite Codes & Controllo Accessi
- Generazione codici univoci con `secrets` Python alla creazione torneo
- Hash sha256 + `hmac.compare_digest` (no timing attack)
- Tre modalità: aperto / solo invito / invito parziale
- UI admin per copiare/inviare codici, validazione server-side

### Giorno 9 — Security — Implementazione Completa
- **Deploy Rules statiche una volta sola** (Giorno 1 o qui) — nessun redeploy futuro
- Rate limiting Nginx: zone separate per `/register` e `/generate`
- Rate limiting FastAPI con slowapi per utente autenticato
- Test penetrazione: tentare scrittura diretta su Firestore con token valido, injection, brute force codici

### Giorno 10-11 — Risultati, Classifica & Pagina Pubblica
- Form inserimento risultati partite (admin, con verifica token)
- Calcolo automatico classifica per girone
- Pagina pubblica `/t/[id]`: gironi, calendario, risultati real-time (Firestore read)
- Gestione differenze regolamentari calcetto vs basket

### Giorno 12 — Test End-to-End & Deploy Finale
- Test completo: crea torneo → registrazione → scheduling → risultati
- Verifica edge cases: squadre dispari, slot insufficienti, schema vuoto
- Test multi-torneo con schemi diversi in parallelo
- Monitoring, logging errori, documentazione finale

---

## Riepilogo Stima Tempi

| Fase | Ottimista | Realistico |
|---|---|---|
| Setup + infrastruttura + Firebase | 1g | 1g |
| Schema engine (JSON → form + validazione) | 0.5g | 1g |
| Conversione Notebook → FastAPI | 0.5g | 1g |
| Frontend Admin (schema-driven) | 1.5g | 2g |
| Frontend Squadre (schema-driven) | 1g | 2g |
| Invite codes + controllo accessi | 0.5g | 1g |
| Risultati & classifica | 1g | 1g |
| Sicurezza (Rules statiche, rate limit, hardening) | 0.5g | 1g |
| Test, edge cases, deploy | 0.5g | 1g |
| **TOTALE** | **~7 giorni** | **~11 giorni** |

> Risparmio rispetto alla v4: ~0.5 giorni (eliminato `generateFirestoreRules` e deploy dinamico).

---

*Tournament Manager • Roadmap v5 Write-Through API Edition • 31/05/2026*
