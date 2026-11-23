# Architecture

## System overview

Tre servizi, deploy automatico a ogni `git push` su `main` (vedi [Deploy](#deploy)):

```
Browser (Next.js su Cloudflare Pages)
  │
  ├── legge Firestore direttamente (Firebase Client SDK)
  └── scrive solo via FastAPI (Admin SDK, Docker su Railway)
                    │
                    └── Firestore (Firebase)
                              │
                              └── CP-SAT solver (ortools, dentro FastAPI)
```

## Contratto fondamentale: write-through

**Il client non scrive mai su Firestore.** Le Firestore Security Rules riflettono questo:
```
allow write: if false;  // su ogni collection
```

Tutti i write passano per FastAPI che usa l'Admin SDK (bypassa le rules).
Tutti i read dal browser usano il Client SDK (soggetti alle rules).

Conseguenza: aggiungere una feature significa aggiungere un endpoint FastAPI,
non modificare le rules. Le rules sono un layer di difesa statico, non logica.

## Auth a due tracce

| Chi | Come | Token |
|-----|------|-------|
| Admin | Firebase Auth (Google login) | Firebase ID token (JWT verificato da Firebase) |
| Squadra | PIN numerico → login | JWT custom firmato con `TEAM_JWT_SECRET` (`create_team_token` in `backend/auth.py`) |

L'admin ottiene il suo token via `getIdToken()` nel browser e lo passa come `Authorization: Bearer`.
La squadra fa `POST /teams/{id}/login` con PIN e riceve un JWT da usare per `PUT /availability` e futuri endpoint.

## Formato slot_id

Il frontend genera slot id come `g{N}_s{M}` **1-indexed** (es. `g1_s1` = giorno 0, slot 0).

```
"g1_s1" → (giorno=0, slot=0)   # parse_slot_id() in backend/scheduler.py
"g2_s3" → (giorno=1, slot=2)
```

Questo formato appare in:
- `availability` array nel documento team: `[{slot_id: "g1_s1", available: true}, ...]`
- `AvailabilityGrid.tsx` (generazione lato frontend)
- `parse_slot_id()` in `backend/scheduler.py` (parsing lato backend)

**Mai usare indici 0-based come slot_id nei dati Firestore** — li genera solo il frontend in formato 1-based.

## Generazione calendario: batch atomico

`POST /tournaments/{id}/schedule/generate` fa una sola cosa ma deve farlo in modo atomico:

```python
batch = db.batch()
# 1. Scrive tutte le partite (home_goals=None, away_goals=None)
# 2. Scrive standings azzerate per ogni girone (document id = str(girone))
# 3. Aggiorna status torneo a "scheduled"
batch.commit()  # tutto o niente
```

Perché atomico: se il processo muore a metà, lo status resta `draft` e l'admin può riprovare
senza duplicare partite. La guardia 409 (`status == "scheduled"`) è la seconda linea di difesa.

Perché standings al momento della generazione: la pagina pubblica mappa UUID squadra → nome
tramite i documenti `standings/`. Senza standings iniziali la vista mostra UUID grezzi.

## Standings: zero letture Firestore

`compute_standings(match_dicts, team_names, points_system, tiebreaker_rules)` in `backend/standings.py`
è una funzione pura — nessuna lettura da Firestore. Riceve i dati già in memoria.

**Bug latente chiuso (luglio 2026):** `girone` nei match è `int`, ma i document ID Firestore
devono essere `str`. Usare sempre `str(group_id)` come document ID delle standings.

## Schema dinamico

Ogni torneo ha un `schema_config` (documento `config/schema` in Firestore) che definisce:
- campi del form di registrazione squadra/giocatore
- `max_teams`, `teams_per_group`, `num_giorni`, `num_slots_per_giorno`, `num_campi`
- `points_system` e `tiebreaker_rules`

Il backend legge lo schema per validare le registrazioni e calcolare le standings.
Il frontend legge lo schema per costruire i form dinamicamente.

## Invariante chiave del solver

```
num_giorni × num_slots_per_giorno × 2 == num_squadre × (squadre_per_girone - 1)
```

Se questo non vale, il solver CP-SAT non trova una soluzione valida.
Il wizard di creazione torneo calcola questa formula e mostra i valori possibili prima di confermare.

**Limite noto:** il solver (`generate_schedule` in `backend/scheduler.py`) usa `AddAllDifferent`
su tutte le partite, cioè **una partita per slot**. Il campo `num_campi` dello schema viene
raccolto dal wizard ma il solver non lo usa ancora: più campi in parallelo non sono supportati.

## Slug routing

I tornei si raggiungono via slug (`/t/my-tournament/`).
La collection `tournament_slugs/{slug}` contiene `{tournament_id: "..."}` e si legge
pubblicamente (rules: `allow read: if true`).

Il hook `useSlugResolution` in `frontend/lib/hooks/` risolve slug → ID e poi carica i dati.

## Registrazione squadre

La registrazione è pubblica, limitata solo dal tetto `max_teams` dello schema
(il sistema di codici invito è stato rimosso). Il conteggio e l'inserimento avvengono
in una transazione Firestore, così due iscrizioni simultanee non superano il tetto.

## Deploy

Ogni push su `main` deploya tutto in automatico:

| Componente | Servizio | Trigger |
|---|---|---|
| Frontend | Cloudflare Pages (`@cloudflare/next-on-pages`, root `frontend/`) | ogni push su `main` |
| Backend | Railway (Docker, root `backend/`, config in `backend/railway.json`) | ogni push su `main` |
| Firestore rules | GitHub Actions (`.github/workflows/deploy-rules.yml`) | push su `main` che modifica `firestore.rules` |

Setup iniziale, variabili d'ambiente e secret: [docs/deployment-setup.md](docs/deployment-setup.md).
