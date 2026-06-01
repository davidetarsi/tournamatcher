# Admin Frontend — Design Spec

**Data:** 2026-06-01
**Piano:** B (Giorni 4-5 della roadmap v5)

---

## Goal

Costruire il frontend admin del Tournament Manager: login Google, lista tornei, creazione torneo con template, dashboard squadre, editor visuale schema campi, generazione calendario. Deployato su Vercel. Comunica con il backend FastAPI su Railway.

---

## Stack Tecnologico

| Componente | Tecnologia |
|---|---|
| Framework | Next.js 14 (App Router, TypeScript) |
| UI | shadcn/ui + Tailwind CSS |
| Form | react-hook-form + zod |
| Auth | Firebase Auth (Google Sign-In) |
| DB reads | Firebase Firestore SDK (client, real-time) |
| API writes | fetch nativo → Railway FastAPI |
| Deploy | Vercel |

---

## Architettura

### Data Flow

```
Browser
  ├── READS  → Firestore SDK (onSnapshot, real-time)
  └── WRITES → fetch → Railway FastAPI (Bearer token)
                           │
                      verify_token() → Admin SDK → Firestore
```

### Protezione Route

1. Google Sign-In → Firebase restituisce ID token
2. Client chiama `POST /api/auth/session` (Next.js API route) con il token
3. API route imposta cookie HttpOnly `session` con il token Firebase
4. `middleware.ts` controlla presenza del cookie su ogni `/admin/*` — nessun cookie → redirect a `/admin`
5. Ogni chiamata FastAPI include `Authorization: Bearer <token>` — la vera verifica di sicurezza è su FastAPI

### CORS

FastAPI su Railway configurato con:
```python
allow_origins=["https://your-app.vercel.app"]  # dominio Vercel reale
```
(vedere `docs/railway-backend-migration.md` per i dettagli di configurazione Railway)

---

## Struttura File

```
frontend/
├── app/
│   ├── layout.tsx                  # root layout, FirebaseProvider
│   ├── middleware.ts               # protezione /admin/* con cookie check
│   ├── api/
│   │   └── auth/
│   │       └── session/route.ts   # POST: imposta cookie session
│   └── admin/
│       ├── page.tsx                # login + lista tornei
│       ├── new/
│       │   └── page.tsx            # crea torneo (wizard 2 step)
│       └── [id]/
│           ├── page.tsx            # dashboard torneo (tab: squadre, invite, calendario)
│           └── schema/
│               └── page.tsx        # editor visuale campi
├── components/
│   ├── auth/
│   │   └── GoogleSignInButton.tsx
│   ├── tournament/
│   │   ├── TournamentList.tsx      # lista real-time con onSnapshot
│   │   ├── TournamentWizard.tsx    # wizard crea torneo (2 step)
│   │   ├── TeamTable.tsx           # tabella squadre con strength e conferma
│   │   ├── InviteCodesPanel.tsx    # gestione invite codes
│   │   ├── SchedulePanel.tsx       # bottone genera + stato calendario
│   │   └── SchemaEditor.tsx        # editor visuale campi schema
│   └── ui/                         # componenti shadcn/ui (auto-generati)
├── lib/
│   ├── firebase.ts                 # inizializzazione Firebase client SDK
│   ├── api.ts                      # funzioni tipizzate per Railway FastAPI
│   ├── schema.ts                   # generateZodSchema(fields) → zod schema
│   └── hooks/
│       ├── useFirebaseToken.ts     # token aggiornato + auto-refresh
│       └── useTournament.ts        # onSnapshot wrapper per un torneo
├── types/
│   └── schema.ts                   # SchemaField, TournamentSchema, Team, ecc.
├── next.config.ts
├── tailwind.config.ts
└── package.json
```

---

## Pagine

### `/admin` — Login + Lista Tornei

Due stati:
- **Non autenticato**: bottone Google Sign-In centrato nella pagina
- **Autenticato**: lista tornei dell'admin (real-time da Firestore) + bottone "Nuovo torneo"

Al login: Google popup → ID token → `POST /api/auth/session` → cookie → reload.

### `/admin/new` — Crea Torneo

Wizard 2 step:

**Step 1 — Scegli template:**
- Calcetto (campi predefiniti: nome, email contatto, città)
- Basket (campi predefiniti: nome, email contatto, numero maglia)
- Personalizzato (schema vuoto)

**Step 2 — Configura:**
- Nome torneo, max_teams, teams_per_group, public (toggle)
- Preview dei campi del template selezionato

Submit → `POST /tournaments` → FastAPI → redirect a `/admin/[id]`.

### `/admin/[id]` — Dashboard Torneo

Tre tab:

**Tab Squadre:**
- Tabella real-time (Firestore `onSnapshot` su `tournaments/{id}/teams`)
- Colonne: nome, stato (confermato / in attesa), strength (1–5)
- Per ogni squadra: dropdown strength → `PATCH /tournaments/{id}/teams/{teamId}`, toggle conferma

**Tab Invite Codes:**
- Mostra codici generati con bottone copia
- Toggle modalità: aperto / solo invito / invito parziale
- I codici sono generati dal backend alla creazione del torneo

**Tab Calendario:**
- Stato attuale (`draft` / `scheduled`)
- Bottone "Genera Gironi" (disabilitato se meno di 2 squadre confermate)
- `POST /tournaments/{id}/generate-schedule` → mostra risultato o errore

### `/admin/[id]/schema` — Editor Visuale Campi

- Lista campi attuali: tipo, chiave, required, max_length
- Bottone "Aggiungi campo" → form inline (tipo, chiave, opzioni)
- Bottone rimuovi per ogni campo
- Submit → `PUT /tournaments/{id}/schema` → FastAPI

---

## Form Dinamici

`generateZodSchema(fields: SchemaField[])` costruisce uno schema zod a runtime da `team_fields`:

```ts
function generateZodSchema(fields: SchemaField[]) {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const f of fields) {
    let validator: z.ZodTypeAny
    if (f.type === 'text')   validator = z.string().max(f.max_length ?? 200)
    if (f.type === 'email')  validator = z.string().email()
    if (f.type === 'number') validator = z.number()
    if (f.type === 'date')   validator = z.string().date()
    shape[f.key] = f.required ? validator! : validator!.optional()
  }
  return z.object(shape)
}
```

Usato in `TournamentWizard` e in qualunque form generato da schema.

---

## Chiamate API

`lib/api.ts` espone funzioni tipizzate. Ogni funzione riceve il token come parametro:

```ts
const RAILWAY_API_URL = process.env.NEXT_PUBLIC_RAILWAY_API_URL

export async function createTournament(data: TournamentCreate, token: string) { ... }
export async function patchTeam(tId: string, teamId: string, data: TeamUpdate, token: string) { ... }
export async function generateSchedule(tId: string, token: string) { ... }
export async function updateSchema(tId: string, schema: TournamentSchema, token: string) { ... }
```

`useFirebaseToken()` hook: chiama `auth.currentUser.getIdToken(true)` — `true` forza il refresh se il token è scaduto (Firebase lo rinnova ogni ora automaticamente).

---

## Nuovo Endpoint Backend — `PUT /tournaments/{id}/schema`

Aggiunto a `backend/routers/tournaments.py`:

- **Auth**: `verify_token()` + verifica `admin_uid`
- **Rate limit**: `@limiter.limit("10/minute")`
- **Payload**: stesso schema di `TournamentCreate` (riusa `SchemaConfig`)
- **Azione**: sovrascrive `tournaments/{id}/config/schema` via Admin SDK

---

## Variabili d'Ambiente Vercel

```
NEXT_PUBLIC_RAILWAY_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
```

---

## Testing

- **Unit**: `generateZodSchema` — verifica che ogni tipo di campo produca il validator corretto
- **Component**: `SchemaEditor` con campi mock — aggiunta, rimozione, submit
- **Integration**: `TeamTable` con Firestore mock — verifica che `onSnapshot` aggiorni la UI
- Framework: **Jest + React Testing Library**

---

## Out of Scope (Plan B)

- Pagine pubbliche `/t/[id]` — Plan D
- Registrazione squadre `/t/[id]/register` — Plan C
- Griglia disponibilità — Plan C
- Risultati e classifica — Plan D
- Configurazione Railway del backend — `docs/railway-backend-migration.md`
