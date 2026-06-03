# Plan F: SaaS Platform — Slug Routing, Logo Upload & Landing Page

**Data:** 2026-06-03

## Obiettivo

Trasformare l'app in un prodotto pubblico self-service: chiunque con un account Google può creare un torneo, che ottiene un URL leggibile (`/t/nome-torneo-2026-07-15`), una pagina pubblica con metadata Open Graph per le anteprime sui social, e un logo personalizzato. Una landing page marketing introduce il prodotto e consente l'accesso rapido ai tornei gestiti dall'utente.

---

## Architettura generale

Il progetto si divide in due fasi indipendenti e sequenziali:

- **Fase 1** — Infrastruttura slug + ristrutturazione URL + endpoint di supporto
- **Fase 2** — Logo upload, metadata SEO, landing page

Ogni fase produce software funzionante e testabile prima che inizi la successiva.

---

## Fase 1 — Slug Routing & Ristrutturazione URL

### 1.1 Data Model

**Nuova collection Firestore: `tournament_slugs`**

```
tournament_slugs/{slug}  →  { tournament_id: string }
```

Lettura pubblica richiesta (aggiornare `firestore.rules`):

```
match /tournament_slugs/{slug} {
  allow read: if true;
}
```

**Campo aggiuntivo nel documento torneo (`tournaments/{id}`):**

```
slug: string   // es. "torneo-estivo-2026-07-15"
```

**Generazione slug** (logica in `backend/services/tournament_service.py`):

```python
def generate_slug(name: str, start_date: str | None) -> str:
    """
    "Torneo Estivo" + "2026-07-15" → "torneo-estivo-2026-07-15"
    "Torneo Estivo" + None         → "torneo-estivo"
    """
    base = re.sub(r"[^a-z0-9]+", "-", name.lower().strip()).strip("-")
    if start_date:
        base = f"{base}-{start_date}"
    return base
```

**Gestione collisioni** (stesso helper):

```python
def unique_slug(transaction, base: str) -> str:
    """Dentro una transazione Firestore, aggiunge -2, -3, ... finché lo slug è libero."""
    candidate = base
    i = 2
    while transaction.get(slugs_ref.document(candidate)).exists:
        candidate = f"{base}-{i}"
        i += 1
    return candidate
```

### 1.2 Backend

#### `POST /tournaments` — aggiornamento

Tutto avviene in una **singola transazione Firestore**:

1. Genera `base_slug` da `name` + `start_date` (se presente nello schema)
2. Chiama `unique_slug()` per trovare lo slug libero
3. `transaction.set(tournament_slugs/{slug}, {tournament_id})`
4. `transaction.set(tournaments/{id}, {..., slug})`

Se la transazione fallisce (conflitto o errore Firestore) → il torneo non viene creato, nessun documento orfano.

La risposta include il campo `slug`:

```json
{ "tournament_id": "uuid", "slug": "torneo-estivo-2026-07-15" }
```

#### Nuovo endpoint: `GET /tournaments/by-slug/{slug}`

Nessuna auth. Rate limit: 30/minute.

Risposta:

```json
{
  "tournament_id": "uuid",
  "name": "Torneo Estivo",
  "logo_url": "https://storage.googleapis.com/..." // null se non caricato
}
```

Usato da: `generateMetadata` server-side in Next.js (backend call), con cache 1h.

Il client usa invece il Firebase SDK diretto (vedi §1.3) per evitare roundtrip a Railway.

#### Nuovo endpoint: `GET /my-tournaments`

Auth: `Depends(verify_token)` (Firebase). Rate limit: 20/minute.

Risposta:

```json
[
  { "name": "Torneo Estivo", "slug": "torneo-estivo-2026-07-15", "status": "draft" }
]
```

Query Firestore: `tournaments` where `admin_uid == user["uid"]`, ordinati per data di creazione desc.

### 1.3 Frontend — Routing

**Rinomina cartelle Next.js:**

| Vecchio | Nuovo |
|---|---|
| `app/t/[id]/page.tsx` | `app/t/[slug]/page.tsx` |
| `app/t/[id]/register/page.tsx` | `app/t/[slug]/register/page.tsx` |
| `app/t/[id]/team/[teamId]/page.tsx` | `app/t/[slug]/team/[teamId]/page.tsx` |
| `app/admin/[id]/page.tsx` | `app/t/[slug]/admin/page.tsx` |
| `app/admin/[id]/schema/page.tsx` | `app/t/[slug]/admin/schema/page.tsx` |

`/admin/new` rimane invariato — è il wizard di creazione, protetto da Google login via middleware.

**Hook `useSlugResolution`** (`frontend/lib/hooks/useSlugResolution.ts`):

Legge direttamente la collection `tournament_slugs` via Firebase SDK (non chiama Railway):

```typescript
export function useSlugResolution(slug: string) {
  const [tournamentId, setTournamentId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

useEffect(() => {
  let isMounted = true;
  getDoc(doc(db, 'tournament_slugs', slug)).then((snap) => {
    if (!isMounted) return;
    if (snap.exists()) {
      setTournamentId(snap.data().tournament_id)
    } else {
      setNotFound(true)
    }
    setLoading(false)
  }).catch((err) => {
    if (!isMounted) return;
    setNotFound(true);
    setLoading(false);
  });

  return () => { isMounted = false; };
}, [slug])

  return { tournamentId, loading, notFound }
}
```

Tutte le pagine in `/t/[slug]/*` chiamano questo hook al mount e usano `tournamentId` per tutte le API e le query Firestore successive.

**Aggiornamento `middleware.ts`:**

La regex di protezione admin cambia da `/admin/*` a `/t/.*/admin`:

```typescript
// PRIMA
matcher: ['/admin/:path*']

// DOPO
matcher: ['/admin/:path*', '/t/:slug/admin/:path*']
```

**Flusso creazione torneo:**

Landing → "Crea il tuo torneo" → `/admin/new` (middleware reindirizza a Google login se non autenticato) → wizard → submit → backend risponde con `slug` → frontend reindirizza a `/t/[slug]/admin`.

---

## Fase 2 — Logo Upload, SEO Metadata & Landing Page

### 2.1 Logo Upload

**Frontend (`TournamentWizard`):**

- Campo file opzionale: `accept="image/png,image/jpeg,image/webp"`, max 2MB (validazione client).
- Nessun vincolo di proporzioni: il display usa CSS `aspect-square object-cover` (crop visivo).
- Se valido, il file viene convertito in stringa Base64 prima dell'invio.
- Il payload `POST /tournaments` si arricchisce di: `logo_base64?: string` (data URL completo, es. `"data:image/jpeg;base64,/9j/4AAQ..."`).

**Backend (`POST /tournaments`):**

Se `logo_base64` è presente, **prima** di scrivere su Firestore:

1. Decodifica Base64, determina estensione dal MIME type nel prefisso data URL.
2. Upload su Firebase Storage: `tournament-logos/{tournament_id}.{ext}` (Firebase Admin SDK).
3. Recupera il download URL pubblico → `logo_url`.
4. Se l'upload Storage **fallisce** → restituisce 500 senza scrivere su Firestore (nessun documento orfano).

Dopo l'upload Storage, si esegue la transazione Firestore (§1.2). Se la transazione fallisce dopo un upload Storage riuscito → il backend ESEGUE UNA TASK IN BACKGROUND (o usa un blocco finally robusto) per chiamare bucket.blob(path).delete(). Sebbene il best-effort sia tollerabile per i file orfani, il log di errore non deve essere silenziato, ma tracciato esplicitamente (es. logger.error), altrimenti si accumulerà spazio su Storage senza visibilità per lo sviluppatore.

Il campo `logo_url` viene salvato nel documento torneo e incluso nella risposta di `GET /tournaments/by-slug/{slug}`.

**Fallback:** se `logo_url` è `null`, i componenti frontend usano `process.env.NEXT_PUBLIC_DEFAULT_LOGO_URL` (URL del logo generico già caricato su Storage).

Il logo è visibile in:
- Header della pagina pubblica `/t/[slug]`
- Header dell'admin `/t/[slug]/admin`

### 2.2 SEO Metadata (Open Graph)

**Aggiornamento `GET /tournaments/by-slug/{slug}`:** già previsto in §1.2 — restituisce `name` e `logo_url`.

**Split Server/Client di `/t/[slug]/page.tsx`:**

`generateMetadata` richiede un Server Component. La pagina pubblica è attualmente un client component. Soluzione:

```
app/t/[slug]/page.tsx                    ← Server Component (solo metadata + render del client)
app/t/[slug]/TournamentPublicClient.tsx  ← 'use client' (tutta la logica esistente)
```

`page.tsx` (server):

```typescript
import type { Metadata } from 'next'
import { TournamentPublicClient } from './TournamentPublicClient'

type Props = { params: { slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const apiUrl = process.env.RAILWAY_API_URL  // server-side, non NEXT_PUBLIC_
  try {
    const res = await fetch(`${apiUrl}/tournaments/by-slug/${params.slug}`, {
  // Revalidate impostato a 60 secondi invece di 3600.
  // L'endpoint FastAPI ha già un rate limit a monte (30/min),
  // quindi Next.js deve essere più reattivo se l'admin aggiorna il logo.
  next: { revalidate: 60 },
})
    if (!res.ok) return { title: 'Torneo non trovato' }
    const data = await res.json()
    const image = data.logo_url || process.env.NEXT_PUBLIC_DEFAULT_LOGO_URL || ''
    return {
      title: `${data.name} | Tournament Manager`,
      openGraph: {
        title: data.name,
        description: 'Iscrizioni aperte, risultati e classifiche in tempo reale.',
        images: [image],
      },
    }
  } catch {
    return { title: 'Tournament Manager' }
  }
}

export default function TournamentPage({ params }: Props) {
  return <TournamentPublicClient slug={params.slug} />
}
```

Poiché Next.js App Router memorizza la cache a livello di Data Fetching, un revalidate di 1 ora (3600s) manterrebbe la preview del logo bloccata per un'ora intera dopo che l'admin l'ha modificato. 60 secondi garantiscono prestazioni ottimali senza stressare il backend

La stessa variabile d'ambiente `RAILWAY_API_URL` (senza `NEXT_PUBLIC_`) viene aggiunta a `.env.local` e alle variabili d'ambiente di Vercel.

### 2.3 Landing Page (`app/page.tsx`)

La pagina è un Server Component (nessun hook client necessario per il contenuto statico). Il drawer autenticazione è estratto in un componente separato `'use client'`.

**Struttura:**

```
[Header]
  - Logo/nome servizio (link a /)
  - Nav links (es. "Come funziona")
  - AuthButton ('use client'): "Accedi" → Google popup,
    oppure Avatar → Drawer laterale

[Hero]
  - Headline principale
  - Sottotitolo
  - CTA "Crea il tuo torneo" → /admin/new

[Feature Grid] — 4 card
  1. Gironi e calendario automatico
  2. Iscrizione squadre con codice
  3. Pagina pubblica real-time
  4. Gestione giocatori con deadline

[CTA Finale]
  - "Inizia gratis" → /admin/new

[Footer]
  - Privacy policy | Termini di servizio | Contatti
```

**`AuthButton` + Drawer (`'use client'`):**

- Non autenticato: bottone "Accedi" → `signInWithPopup(auth, googleProvider)`
- Autenticato: avatar Google → apre Drawer laterale
- Drawer: bottone "Logout" + lista tornei da `GET /my-tournaments` → ogni voce → `/t/[slug]/admin`
- Loading state per la lista tornei (skeleton o spinner)

**Contenuto copy:** headline, sottotitolo e descrizioni feature sono placeholder nel codice — il testo definitivo va deciso separatamente (es. via Figma) e sostituito prima del deploy.

---

## Variabili d'ambiente

| Variabile | Dove | Scopo |
|---|---|---|
| `RAILWAY_API_URL` | Vercel (server) | Chiamate server-side (generateMetadata) |
| `NEXT_PUBLIC_RAILWAY_API_URL` | Vercel + `.env.local` | Chiamate client-side (già presente) |
| `NEXT_PUBLIC_DEFAULT_LOGO_URL` | Vercel + `.env.local` | Logo fallback per tornei senza logo |

---

## Firestore Security Rules — aggiornamento

```
match /tournament_slugs/{slug} {
  allow read: if true;
  allow write: if false;  // solo il backend scrive via Admin SDK
}
```

---

## Cosa NON cambia

- Logica interna delle pagine `/t/[slug]/register` e `/t/[slug]/team/[teamId]` — solo il parametro si chiama `slug` invece di `id`, risolto via `useSlugResolution`.
- `AvailabilityGrid`, `SchemaEditor`, `TournamentDatesPanel`, `PlayerEditor` — invariati.
- Auth delle squadre (team JWT) — invariata.
- Tutti i test backend esistenti — invariati (80/80 passano).

---

## Sequenza implementazione consigliata

1. `generate_slug` + `unique_slug` helpers + test (backend puro, zero frontend)
2. Transazione atomica in `POST /tournaments` + `GET /tournaments/by-slug/{slug}` + `GET /my-tournaments`
3. `tournament_slugs` security rules + deploy
4. `useSlugResolution` hook + rename cartelle frontend + middleware update
5. Logo upload (backend Storage + frontend Base64)
6. `generateMetadata` + split Server/Client della pagina pubblica
7. Landing page + `AuthButton` + Drawer
