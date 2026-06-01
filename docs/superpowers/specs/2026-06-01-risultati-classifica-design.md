# Risultati & Classifica — Design Spec

**Data:** 2026-06-01
**Plan:** C

---

## Obiettivo

Aggiungere inserimento risultati partite, calcolo classifica per girone e vista personale della squadra. Le standings si aggiornano in real-time via Firestore `onSnapshot`. Nessuna pagina pubblica per ora — gironi e calendario restano nell'admin; la pagina pubblica `/t/[id]` arriva in un plan futuro.

---

## Architettura

```
Admin inserisce risultato
        │
        ▼
POST /tournaments/{id}/matches/{matchId}/result  (FastAPI, admin-only)
        │
        ├── Scrive home_goals/away_goals/played_at su matches/{matchId}
        │
        └── Ricalcola standings → scrive standings/{groupId}  (Admin SDK)
                │
                ▼
        Frontend (onSnapshot su standings/ e matches/)
        aggiorna StandingsTable e MatchCalendarView in real-time
```

Nessun endpoint `GET /standings` — il frontend legge Firestore direttamente.

---

## Modello Dati

### Estensione match document

```
tournaments/{id}/matches/{matchId}
  giorno: int           ← esistente
  slot: int             ← esistente
  girone: str           ← esistente (nome gruppo, es. "A")
  squadre: [str, str]   ← esistente (team_id[0] = home, [1] = away)
  home_goals: int | null        ← NEW
  away_goals: int null          ← NEW
  played_at: timestamp | null   ← NEW
```

### Nuova subcollection standings

```
tournaments/{id}/standings/{groupId}
  group_name: str
  computed_at: timestamp
  # {groupId} = nome girone, es. "A", "B" (stesso valore del campo girone nei match)
  entries: [
    {
      team_id: str
      team_name: str
      played: int
      wins: int
      draws: int
      losses: int
      goals_for: int
      goals_against: int
      goal_difference: int
      points: int
      position: int        ← 1-based, dopo ordinamento
    }
  ]
```

### Estensione schema config

Due campi nuovi nel documento `tournaments/{id}/config/schema`:

```json
"points_system": {
  "win": 3,
  "draw": 1,
  "loss": 0,
  "draws_allowed": true
},
"tiebreaker_rules": ["goal_difference", "goals_for", "head_to_head"]
```

- `draws_allowed: false` per basket — nasconde la colonna P ovunque nell'UI
- Valori default: calcio → `win:3, draw:1, loss:0, draws_allowed:true`; basket → `win:2, draw:0, loss:0, draws_allowed:false`
- L'admin modifica questi valori dallo `SchemaEditor` esistente
- tiebreaker_rules è una lista ordinata. Nota algoritmica obbligatoria: l'implementazione di head_to_head non deve limitarsi al confronto a due. In caso di parità tra 3 o più squadre, deve instanziare una "classifica avulsa" (mini-girone) calcolando punti e differenza reti esclusivamente sui match giocati tra le squadre coinvolte nel tiebreaker.

---

## Backend

### File da creare/modificare

```
backend/
  routers/
    results.py          ← NEW
  standings.py          ← NEW
  models.py             ← modifica: aggiungere MatchResult, StandingsEntry
  main.py               ← modifica: includere results router
```

### `backend/routers/results.py`

```python
POST /tournaments/{tournament_id}/matches/{match_id}/result
  Auth: verify_token + assert admin_uid == user["uid"]
  Body: MatchResult { home_goals: int ≥ 0, away_goals: int ≥ 0 }
  Validazione: se draws_allowed=False e home_goals==away_goals → 422
  Side-effect: chiama compute_and_cache_standings(db, tournament_id)
  Response: { "status": "ok" }
```

### `backend/standings.py`

```python
def compute_standings(
    matches: list[dict],
    teams: dict[str, str],           # team_id → team_name
    points_system: dict,             # win/draw/loss/draws_allowed
    tiebreaker_rules: list[str]
) -> dict[str, list[StandingsEntry]]:
    # Raggruppa match per girone
    # Per ogni match con risultato: aggiorna V/P/S/GF/GS
    # Calcola punti e goal_difference
    # Ordina per tiebreaker_rules (points → goal_difference → goals_for → head_to_head)
    # Assegna position (1-based)
    # Ritorna { "A": [StandingsEntry, ...], "B": [...] }

def compute_and_cache_standings(db, tournament_id: str) -> None:
    # Legge schema (points_system, tiebreaker_rules)
    # Legge tutti i match e le squadre
    # Chiama compute_standings()
    # Apre una Transazione Firestore: legge tutti i match, calcola le classifiche e scrive su standings/{groupId} all'interno della stessa transazione per garantire consistenza assoluta in caso di inserimenti simultanei.
```

### `backend/models.py` — aggiunte

```python
class MatchResult(BaseModel):
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)

class StandingsEntry(BaseModel):
    team_id: str
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    position: int
```

### Test

```
backend/tests/test_results.py
  test_submit_result_success
  test_submit_result_not_admin → 403
  test_submit_result_draw_not_allowed → 422
  test_standings_computation_calcio     ← unit test su compute_standings()
  test_standings_computation_basket
  test_tiebreaker_goal_difference
  test_tiebreaker_head_to_head
```

---

## Admin Frontend

### Nuova tab "Risultati" in `/admin/[id]`

**File:** `frontend/components/tournament/ResultsTab.tsx`

- Partite recuperate via `onSnapshot` su `matches/`, raggruppate per girone → giorno
- Ogni riga partita:
  - Squadra non giocata: `NomeHome [⬜] – [⬜] NomeAway [Salva]`
  - Squadra giocata: `NomeHome 2 – 1 NomeAway [Modifica]`
- Validazione inline: solo interi ≥ 0; se `draws_allowed:false` e pareggio → errore visibile
- Chiamata `POST .../matches/{id}/result` con token Bearer via `lib/api.ts`
- Aggiornamento standings automatico via `onSnapshot` (nessun refetch manuale)

### Nuova tab "Classifiche" in `/admin/[id]`

**File:** `frontend/components/tournament/StandingsTab.tsx`

- Una `StandingsTable` per ogni girone (da `onSnapshot` su `standings/`)
- Sotto: `MatchCalendarView` con tutte le partite ordinate per giorno/slot con punteggi

### Componente `StandingsTable`

**File:** `frontend/components/tournament/StandingsTable.tsx`

Colonne: `Pos · Squadra · G · V · P · S · GF · GS · +/- · Pt`

- Se `draws_allowed: false`: colonna P omessa
- Progettato per essere riusato anche nella futura pagina pubblica

### Componente `MatchCalendarView`

**File:** `frontend/components/tournament/MatchCalendarView.tsx`

- Lista partite raggruppate per giorno
- Formato: `[Badge Girone A] NomeHome 2 – 1 NomeAway` oppure `– : –` se non giocata
- Riusabile in admin e futuro pubblico

### Aggiunta a `lib/api.ts`

```typescript
export async function submitResult(
  tournamentId: string,
  matchId: string,
  data: { home_goals: number; away_goals: number },
  token: string
): Promise<{ status: string }>
```

---

## Pagina Squadra — Sezione Risultati

**File:** `frontend/app/t/[id]/team/[teamId]/page.tsx`

Accessibile tramite link diretto. Nessuna auth richiesta in Plan C. Le Firestore Security Rules devono essere aggiornate:
- `matches/{matchId}` → `allow read: if true` (punteggi visibili senza auth)
- `standings/{groupId}` → `allow read: if true` (classifica visibile senza auth)
- `teams/{teamId}` → invariato, resta protetto da `isOwner()` (dati squadra non esposti)
Le scritture rimangono `allow write: if false` su tutte le collezioni.

**Contenuto:**
- Mini-riepilogo: `3V · 1P · 2S` (calcolato da onSnapshot su matches/)
- Lista partite della squadra ordinate per giorno:
  ```
  Giorno 1 · vs NomeSfidante · 2 – 1 · [V]
  Giorno 2 · vs NomeSfidante2 · 1 – 1 · [P]
  Giorno 3 · vs NomeSfidante3 · – · –
  ```
- Badge V (verde) / P (giallo) / S (rosso) — mai mostrare i punti
- Recupera il nome della squadra da Firestore (`teams/{teamId}`)

**File:** `frontend/lib/hooks/useTeamMatches.ts`

Hook: filtra i match dove `squadre` contiene `teamId`, li ordina per giorno/slot.

---

## Schema Types — aggiornamento TypeScript

**File:** `frontend/types/schema.ts` — aggiungere:

```typescript
export interface PointsSystem {
  win: number
  draw: number
  loss: number
  draws_allowed: boolean
}

export type TiebreakerRule = 'points' | 'goal_difference' | 'goals_for' | 'head_to_head'

export interface StandingsEntry {
  team_id: string
  team_name: string
  played: number
  wins: number
  draws: number
  losses: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  position: number
}

export interface Match {
  id: string
  giorno: number
  slot: number
  girone: string
  squadre: [string, string]   // [home_team_id, away_team_id]
  home_goals: number | null
  away_goals: number | null
  played_at: string | null
}
```

Aggiungere anche `points_system: PointsSystem` e `tiebreaker_rules: TiebreakerRule[]` a `TournamentSchema`.

---

## Cosa NON è in scope

- Pagina pubblica `/t/[id]` — rinviata a plan futuro
- Form iscrizione e griglia disponibilità squadra — Plan D
- Auth squadre su pagina `/t/[id]/team/[teamId]` — Plan D
- Inserimento risultati da parte delle squadre stesse
- Eliminazione/modifica risultati con log di audit
