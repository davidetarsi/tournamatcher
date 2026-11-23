# Tournamatcher

Strumenti per organizzare **tornei di basket 3x3**: iscrizione delle squadre, gironi
bilanciati, calendario delle partite generato da un solver a vincoli, risultati e classifiche.

Il repository contiene due progetti che condividono lo stesso cuore (il solver
**OR-Tools CP-SAT** per il calendario) ma hanno scopi diversi:

| Progetto | Cartella | Cos'è | Dove gira |
|---|---|---|---|
| **Tournamatcher (piattaforma web)** | `backend/`, `frontend/` | Piattaforma multi-torneo: pagina pubblica del torneo, iscrizione squadre, disponibilità, calendario, risultati e classifiche | Cloud (Firebase + API FastAPI in Docker) |
| **FIBA Tool** | [`fiba-tool/`](fiba-tool/) | Dashboard locale che forma gironi e calendario usando i **punti ranking reali FIBA 3x3** dei giocatori | Solo in locale, sul tuo computer |

---

## FIBA Tool

Strumento locale (FastAPI + una dashboard HTML) per chi organizza un torneo e vuole seminare
le squadre in base al loro valore reale: pesca i punteggi da
[play.fiba3x3.com](https://play.fiba3x3.com), forma i gironi con un seeding a fasce e genera
il calendario minimizzando le partite consecutive. Accetta anche giocatori non registrati su
FIBA con punteggio inserito a mano o stimato.

Avvio rapido:

```bash
cd fiba-tool
pip install -r requirements.txt
python3 app.py          # poi apri http://127.0.0.1:8000
```

Documentazione completa: **[fiba-tool/README.md](fiba-tool/README.md)**.

---

## Tournamatcher — piattaforma web

```
Browser (Next.js 14)
  ├── legge Firestore direttamente (Firebase Client SDK)
  └── scrive solo tramite l'API FastAPI (Docker)
                    ├── Firestore (Firebase Admin SDK)
                    └── solver CP-SAT per il calendario
```

- **Frontend** (`frontend/`): Next.js + React + Tailwind. Area admin per creare e gestire i
  tornei, pagina pubblica per torneo raggiungibile via slug (`/t/<slug>/`).
- **Backend** (`backend/`): FastAPI. Router per tornei, squadre, calendario e risultati;
  generazione del calendario con CP-SAT e calcolo delle classifiche.
- **Dati**: Firestore. Il client non scrive mai direttamente (le rules negano ogni scrittura):
  tutte le modifiche passano dal backend.
- **Autenticazione a due livelli**: gli admin entrano con Google (Firebase Auth), le squadre
  con un PIN che restituisce un token dedicato.

Sviluppo locale:

```bash
# backend (richiede le credenziali Firebase: serviceAccountKey.json)
cd backend && pip install -r requirements.txt && uvicorn main:app --reload

# frontend
cd frontend && npm install && npm run dev   # http://localhost:3000
```

---

## Struttura del repository

```
.
├── backend/            # API FastAPI della piattaforma (solver, classifiche, auth)
├── frontend/           # app Next.js della piattaforma
├── fiba-tool/          # strumento locale con punteggi FIBA reali (progetto a sé)
├── docs/               # guide di deploy, specifiche e piani di sviluppo
├── firestore.rules     # regole di sicurezza Firestore
└── docker-compose.yml  # avvio locale del backend in container
```

---

## Licenza

Il codice è pubblico ma **non è open source**: tutto il repository è distribuito con la
[**PolyForm Noncommercial License 1.0.0**](LICENSE).

- ✅ **Consentito** usarlo, modificarlo e condividerlo per **scopi non commerciali**: uso personale,
  studio, hobby, tornei amatoriali, associazioni no-profit, scuole ed enti pubblici.
- ❌ **Non consentito** alcun **uso commerciale** senza un accordo scritto con l'autore.

Chi condivide il codice deve includere i termini della licenza e la riga `Required Notice`
presente nel file [LICENSE](LICENSE).

Per un uso commerciale o altre richieste: Davide Tarsi — davidetarsi.dev@gmail.com
