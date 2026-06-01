# Admin Frontend — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Next.js 14 admin frontend (TypeScript, Vercel) with Google Auth, tournament creation wizard, team dashboard, schema editor, and schedule generation — plus the backend `PUT /schema` endpoint.

**Architecture:** Next.js App Router with client components for all Firebase/Firestore interactions. Session cookie set via a Next.js API route after Google Sign-In; middleware protects `/admin/new` and `/admin/[id]*`. All Firestore reads use `onSnapshot` directly from the browser; all writes go through Railway FastAPI with a Bearer token.

**Tech Stack:** Next.js 14, TypeScript, Tailwind CSS, shadcn/ui, react-hook-form, zod, Firebase client SDK (Auth + Firestore), Jest + React Testing Library

---

## Struttura File

```
backend/
  routers/tournaments.py      ← MODIFY: add PUT /{id}/schema
  tests/test_tournaments.py   ← MODIFY: add 2 tests

frontend/
  app/
    layout.tsx                ← root layout with AuthProvider
    middleware.ts             ← protect /admin/new and /admin/[id]*
    api/auth/session/
      route.ts                ← POST/DELETE session cookie
    admin/
      page.tsx                ← login or tournament list
      new/page.tsx            ← tournament creation wizard
      [id]/
        page.tsx              ← dashboard with 3 tabs
        schema/page.tsx       ← schema field editor
  components/
    auth/
      AuthProvider.tsx        ← Firebase context + token refresh
      GoogleSignInButton.tsx
    tournament/
      TournamentList.tsx
      TournamentWizard.tsx
      TeamTable.tsx
      InviteCodesPanel.tsx
      SchedulePanel.tsx
      SchemaEditor.tsx
    ui/                       ← shadcn/ui components (auto-generated)
  lib/
    firebase.ts
    api.ts
    schema.ts                 ← generateZodSchema()
    hooks/
      useFirebaseToken.ts
      useTournament.ts
  types/
    schema.ts
  __tests__/
    schema.test.ts
    session-route.test.ts
    middleware.test.ts
    GoogleSignInButton.test.tsx
    TournamentList.test.tsx
    TournamentWizard.test.tsx
    TeamTable.test.tsx
    SchedulePanel.test.tsx
    SchemaEditor.test.tsx
  jest.config.js
  jest.setup.ts
  .env.local.example
```

---

## Task 1: Backend — PUT /tournaments/{id}/schema

**Files:**
- Modify: `backend/routers/tournaments.py`
- Modify: `backend/tests/test_tournaments.py`

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_tournaments.py`:

```python
def test_update_schema_returns_200(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "admin-uid-123"}

    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            "/tournaments/t-123/schema",
            json=TOURNAMENT_PAYLOAD["schema_config"],
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 200
    assert response.json()["status"] == "updated"


def test_update_schema_non_admin_returns_403(client, mock_db):
    tournament_doc = MagicMock()
    tournament_doc.exists = True
    tournament_doc.to_dict.return_value = {"admin_uid": "other-uid"}

    mock_ref = MagicMock()
    mock_ref.get.return_value = tournament_doc
    mock_db.collection.return_value.document.return_value = mock_ref

    with patch("auth.firebase_auth.verify_id_token", return_value=FAKE_TOKEN):
        response = client.put(
            "/tournaments/t-123/schema",
            json=TOURNAMENT_PAYLOAD["schema_config"],
            headers={"Authorization": "Bearer fake.jwt.token"},
        )

    assert response.status_code == 403
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd backend && python3 -m pytest tests/test_tournaments.py -v -k "update_schema"
```

Expected: FAIL — `405 Method Not Allowed` (route doesn't exist yet).

- [ ] **Step 3: Add the endpoint to tournaments.py**

Add `HTTPException` to the existing import and append the new route:

```python
from fastapi import APIRouter, Depends, HTTPException, Request
from models import TournamentCreate, SchemaConfig
```

```python
@router.put("/{tournament_id}/schema")
@limiter.limit("10/minute")
async def update_schema(
    request: Request,
    tournament_id: str,
    schema: SchemaConfig,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    t = t_ref.get()
    if not t.exists:
        raise HTTPException(status_code=404, detail="Torneo non trovato")
    if t.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(status_code=403, detail="Non autorizzato")
    t_ref.collection("config").document("schema").set(schema.model_dump())
    return {"status": "updated"}
```

- [ ] **Step 4: Run all backend tests to verify they pass**

```bash
python3 -m pytest -q
```

Expected: `30 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/routers/tournaments.py backend/tests/test_tournaments.py
git commit -m "feat: PUT /tournaments/{id}/schema endpoint (admin only)"
```

---

## Task 2: Frontend Project Setup

**Files:**
- Create: `frontend/` (Next.js 14 project)
- Create: `frontend/jest.config.js`
- Create: `frontend/jest.setup.ts`
- Create: `frontend/.env.local.example`

- [ ] **Step 1: Scaffold Next.js 14 with TypeScript and Tailwind**

Run from the project root:

```bash
npx create-next-app@14 frontend --typescript --tailwind --app --no-src-dir --import-alias "@/*"
```

When prompted:
- ESLint → Yes
- App Router → Yes (already set by flag)

- [ ] **Step 2: Install dependencies**

```bash
cd frontend
npm install firebase react-hook-form zod @hookform/resolvers
npm install -D jest jest-environment-jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event ts-jest @types/jest
```

- [ ] **Step 3: Initialize shadcn/ui**

```bash
npx shadcn-ui@latest init
```

Accept defaults (style: Default, base color: Slate, CSS variables: Yes).

Then add the components used in this plan:

```bash
npx shadcn-ui@latest add button input label select table tabs badge switch
```

- [ ] **Step 4: Create jest.config.js**

```javascript
const nextJest = require('next/jest')
const createJestConfig = nextJest({ dir: './' })

module.exports = createJestConfig({
  setupFilesAfterEnv: ['<rootDir>/jest.setup.ts'],
  testEnvironment: 'jest-environment-jsdom',
  moduleNameMapper: {
    '^@/(.*)$': '<rootDir>/$1',
  },
})
```

- [ ] **Step 5: Create jest.setup.ts**

```typescript
import '@testing-library/jest-dom'
```

- [ ] **Step 6: Add test script to package.json**

In `frontend/package.json`, ensure `scripts` contains:

```json
"test": "jest",
"test:watch": "jest --watch"
```

- [ ] **Step 7: Create .env.local.example**

```
NEXT_PUBLIC_RAILWAY_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
```

Copy to `.env.local` and fill in real values before running.

- [ ] **Step 8: Verify Jest runs**

```bash
npx jest --passWithNoTests
```

Expected: `Test Suites: 0 passed`.

- [ ] **Step 9: Commit**

```bash
cd ..
git add frontend/
git commit -m "feat: scaffold Next.js 14 frontend with shadcn/ui and Jest"
```

---

## Task 3: TypeScript Types + Firebase + API Client

**Files:**
- Create: `frontend/types/schema.ts`
- Create: `frontend/lib/firebase.ts`
- Create: `frontend/lib/api.ts`

- [ ] **Step 1: Create frontend/types/schema.ts**

```typescript
export type FieldType = 'text' | 'email' | 'number' | 'date'

export interface SchemaField {
  key: string
  type: FieldType
  required: boolean
  max_length?: number
}

export interface InviteCodes {
  enabled: boolean
  partial: boolean
}

export interface AdminControls {
  can_set_strength: boolean
  max_teams: number
}

export interface TournamentSchema {
  sport: string
  max_teams: number
  teams_per_group: number
  public: boolean
  invite_codes: InviteCodes
  team_fields: SchemaField[]
  player_fields: SchemaField[]
  admin_controls: AdminControls
}

export interface Tournament {
  id: string
  name: string
  admin_uid: string
  public: boolean
  status: 'draft' | 'scheduled'
}

export interface Team {
  id: string
  nome: string
  forza: number
  confirmed: boolean
  owner_uid: string
}

export interface TournamentCreate {
  name: string
  schema_config: TournamentSchema
}

export interface TeamUpdate {
  forza?: number
  confirmed?: boolean
}
```

- [ ] **Step 2: Create frontend/lib/firebase.ts**

```typescript
import { initializeApp, getApps } from 'firebase/app'
import { getAuth } from 'firebase/auth'
import { getFirestore } from 'firebase/firestore'

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY!,
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN!,
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID!,
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID!,
}

const app = getApps().length ? getApps()[0] : initializeApp(firebaseConfig)
export const auth = getAuth(app)
export const db = getFirestore(app)
```

- [ ] **Step 3: Create frontend/lib/api.ts**

```typescript
import type { TournamentCreate, TournamentSchema, TeamUpdate } from '@/types/schema'

const BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL!

async function apiFetch(path: string, token: string, options: RequestInit = {}) {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json()
}

export async function createTournament(data: TournamentCreate, token: string) {
  return apiFetch('/tournaments', token, { method: 'POST', body: JSON.stringify(data) })
}

export async function patchTeam(tId: string, teamId: string, data: TeamUpdate, token: string) {
  return apiFetch(`/tournaments/${tId}/teams/${teamId}`, token, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function generateSchedule(tId: string, token: string) {
  return apiFetch(`/tournaments/${tId}/generate-schedule`, token, { method: 'POST' })
}

export async function updateSchema(tId: string, schema: TournamentSchema, token: string) {
  return apiFetch(`/tournaments/${tId}/schema`, token, {
    method: 'PUT',
    body: JSON.stringify(schema),
  })
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/types/ frontend/lib/firebase.ts frontend/lib/api.ts
git commit -m "feat: TypeScript types, Firebase client init, typed API client"
```

---

## Task 4: generateZodSchema

**Files:**
- Create: `frontend/lib/schema.ts`
- Create: `frontend/__tests__/schema.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/schema.test.ts`:

```typescript
import { generateZodSchema } from '@/lib/schema'
import type { SchemaField } from '@/types/schema'

describe('generateZodSchema', () => {
  it('validates text field with max_length', () => {
    const fields: SchemaField[] = [{ key: 'nome', type: 'text', required: true, max_length: 10 }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({ nome: 'ok' }).success).toBe(true)
    expect(schema.safeParse({ nome: 'x'.repeat(11) }).success).toBe(false)
  })

  it('validates email field', () => {
    const fields: SchemaField[] = [{ key: 'email', type: 'email', required: true }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({ email: 'a@b.com' }).success).toBe(true)
    expect(schema.safeParse({ email: 'not-email' }).success).toBe(false)
  })

  it('validates number field', () => {
    const fields: SchemaField[] = [{ key: 'jersey', type: 'number', required: true }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({ jersey: 10 }).success).toBe(true)
    expect(schema.safeParse({ jersey: 'ten' }).success).toBe(false)
  })

  it('makes optional field accept undefined', () => {
    const fields: SchemaField[] = [{ key: 'city', type: 'text', required: false, max_length: 80 }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({}).success).toBe(true)
    expect(schema.safeParse({ city: 'Milano' }).success).toBe(true)
  })

  it('rejects required field when missing', () => {
    const fields: SchemaField[] = [{ key: 'nome', type: 'text', required: true, max_length: 100 }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({}).success).toBe(false)
  })

  it('skips unknown field types without crashing', () => {
    const fields = [{ key: 'x', type: 'unknown' as any, required: true }]
    const schema = generateZodSchema(fields)
    expect(schema.safeParse({}).success).toBe(true)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd frontend && npx jest __tests__/schema.test.ts
```

Expected: FAIL — `Cannot find module '@/lib/schema'`.

- [ ] **Step 3: Create frontend/lib/schema.ts**

```typescript
import { z } from 'zod'
import type { SchemaField } from '@/types/schema'

export function generateZodSchema(
  fields: SchemaField[]
): z.ZodObject<Record<string, z.ZodTypeAny>> {
  const shape: Record<string, z.ZodTypeAny> = {}
  for (const f of fields) {
    let base: z.ZodTypeAny
    switch (f.type) {
      case 'text':   base = z.string().max(f.max_length ?? 200); break
      case 'email':  base = z.string().email(); break
      case 'number': base = z.number(); break
      case 'date':   base = z.string().date(); break
      default:       continue
    }
    shape[f.key] = f.required ? base : base.optional()
  }
  return z.object(shape)
}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
npx jest __tests__/schema.test.ts
```

Expected: `6 passed`.

- [ ] **Step 5: Commit**

```bash
git add frontend/lib/schema.ts frontend/__tests__/schema.test.ts
git commit -m "feat: generateZodSchema — dynamic zod schema from schema.json fields"
```

---

## Task 5: Hooks — useFirebaseToken + useTournament

**Files:**
- Create: `frontend/lib/hooks/useFirebaseToken.ts`
- Create: `frontend/lib/hooks/useTournament.ts`

- [ ] **Step 1: Create frontend/lib/hooks/useFirebaseToken.ts**

```typescript
'use client'
import { useCallback } from 'react'
import { auth } from '@/lib/firebase'

export function useFirebaseToken() {
  const getToken = useCallback(async (): Promise<string> => {
    const user = auth.currentUser
    if (!user) throw new Error('Not authenticated')
    return user.getIdToken()
  }, [])

  return { getToken }
}
```

- [ ] **Step 2: Create frontend/lib/hooks/useTournament.ts**

```typescript
'use client'
import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import type { Tournament } from '@/types/schema'

export function useTournament(tournamentId: string) {
  const [data, setData] = useState<Tournament | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const ref = doc(db, 'tournaments', tournamentId)
    const unsubscribe = onSnapshot(
      ref,
      (snap) => {
        setData(snap.exists() ? ({ id: snap.id, ...snap.data() } as Tournament) : null)
        setLoading(false)
      },
      (err) => {
        setError(err)
        setLoading(false)
      }
    )
    return unsubscribe
  }, [tournamentId])

  return { data, loading, error }
}
```

- [ ] **Step 3: Verify TypeScript compiles**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/lib/hooks/
git commit -m "feat: useFirebaseToken and useTournament hooks"
```

---

## Task 6: Auth Session API Route + Middleware

**Files:**
- Create: `frontend/app/api/auth/session/route.ts`
- Create: `frontend/middleware.ts`
- Create: `frontend/__tests__/middleware.test.ts`

- [ ] **Step 1: Write the failing middleware test**

Create `frontend/__tests__/middleware.test.ts`:

```typescript
import { middleware } from '@/middleware'
import { NextRequest } from 'next/server'

describe('middleware', () => {
  it('redirects to /admin if no session cookie', () => {
    const req = new NextRequest('http://localhost/admin/new')
    const res = middleware(req)
    expect(res.headers.get('location')).toContain('/admin')
    expect(res.status).toBe(307)
  })

  it('allows request through if session cookie exists', () => {
    const req = new NextRequest('http://localhost/admin/new', {
      headers: { Cookie: 'session=fake.jwt.token' },
    })
    const res = middleware(req)
    expect(res.status).toBe(200)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx jest __tests__/middleware.test.ts
```

Expected: FAIL — `Cannot find module '@/middleware'`.

- [ ] **Step 3: Create frontend/middleware.ts**

```typescript
import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const session = request.cookies.get('session')
  if (!session?.value) {
    return NextResponse.redirect(new URL('/admin', request.url))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/admin/new', '/admin/:id*'],
}
```

- [ ] **Step 4: Create frontend/app/api/auth/session/route.ts**

```typescript
import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const body = await request.json()
  const { token } = body
  if (!token || typeof token !== 'string') {
    return NextResponse.json({ error: 'Invalid token' }, { status: 400 })
  }
  cookies().set('session', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    maxAge: 60 * 60,
    path: '/',
    sameSite: 'lax',
  })
  return NextResponse.json({ status: 'ok' })
}

export async function DELETE() {
  cookies().delete('session')
  return NextResponse.json({ status: 'ok' })
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx jest __tests__/middleware.test.ts
```

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/middleware.ts frontend/app/api/
git commit -m "feat: auth session cookie API route and admin route middleware"
```

---

## Task 7: AuthProvider + Layout + GoogleSignInButton

**Files:**
- Create: `frontend/components/auth/AuthProvider.tsx`
- Create: `frontend/components/auth/GoogleSignInButton.tsx`
- Modify: `frontend/app/layout.tsx`
- Create: `frontend/__tests__/GoogleSignInButton.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/GoogleSignInButton.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'

jest.mock('@/lib/firebase', () => ({ auth: {} }))
jest.mock('firebase/auth', () => ({
  GoogleAuthProvider: jest.fn().mockImplementation(() => ({})),
  signInWithPopup: jest.fn().mockResolvedValue({ user: {} }),
}))

describe('GoogleSignInButton', () => {
  it('renders a sign-in button', () => {
    render(<GoogleSignInButton />)
    expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
  })

  it('calls signInWithPopup on click', async () => {
    const { signInWithPopup } = require('firebase/auth')
    render(<GoogleSignInButton />)
    fireEvent.click(screen.getByRole('button', { name: /google/i }))
    expect(signInWithPopup).toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx jest __tests__/GoogleSignInButton.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create frontend/components/auth/AuthProvider.tsx**

```typescript
'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { User, onIdTokenChanged } from 'firebase/auth'
import { auth } from '@/lib/firebase'

interface AuthContextValue {
  user: User | null
  loading: boolean
}

const AuthContext = createContext<AuthContextValue>({ user: null, loading: true })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    return onIdTokenChanged(auth, async (u) => {
      setUser(u)
      setLoading(false)
      if (u) {
        const token = await u.getIdToken()
        await fetch('/api/auth/session', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token }),
        })
      } else {
        await fetch('/api/auth/session', { method: 'DELETE' })
      }
    })
  }, [])

  return <AuthContext.Provider value={{ user, loading }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
```

- [ ] **Step 4: Create frontend/components/auth/GoogleSignInButton.tsx**

```typescript
'use client'
import { GoogleAuthProvider, signInWithPopup } from 'firebase/auth'
import { auth } from '@/lib/firebase'
import { Button } from '@/components/ui/button'

export function GoogleSignInButton() {
  const handleSignIn = async () => {
    const provider = new GoogleAuthProvider()
    await signInWithPopup(auth, provider)
    // onIdTokenChanged in AuthProvider fires automatically and sets the session cookie
  }

  return (
    <Button onClick={handleSignIn} variant="outline">
      Accedi con Google
    </Button>
  )
}
```

- [ ] **Step 5: Update frontend/app/layout.tsx**

```typescript
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { AuthProvider } from '@/components/auth/AuthProvider'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Tournament Manager',
  description: 'Gestione tornei sportivi',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="it">
      <body className={inter.className}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  )
}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
npx jest __tests__/GoogleSignInButton.test.tsx
```

Expected: `2 passed`.

- [ ] **Step 7: Commit**

```bash
git add frontend/components/auth/ frontend/app/layout.tsx
git commit -m "feat: AuthProvider with token refresh, GoogleSignInButton, layout"
```

---

## Task 8: Admin Page — Login + TournamentList

**Files:**
- Create: `frontend/app/admin/page.tsx`
- Create: `frontend/components/tournament/TournamentList.tsx`
- Create: `frontend/__tests__/TournamentList.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/TournamentList.test.tsx`:

```typescript
import { render, screen } from '@testing-library/react'
import { TournamentList } from '@/components/tournament/TournamentList'

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/components/auth/AuthProvider', () => ({
  useAuth: () => ({ user: { uid: 'admin-uid-123' }, loading: false }),
}))
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  query: jest.fn(),
  where: jest.fn(),
  onSnapshot: jest.fn((_q, cb) => {
    cb({
      docs: [
        { id: 't-1', data: () => ({ name: 'Torneo Test', status: 'draft', public: false, admin_uid: 'admin-uid-123' }) },
      ],
    })
    return jest.fn()
  }),
}))

describe('TournamentList', () => {
  it('renders tournament names', () => {
    render(<TournamentList />)
    expect(screen.getByText('Torneo Test')).toBeInTheDocument()
  })

  it('shows empty message when no tournaments', () => {
    const { onSnapshot } = require('firebase/firestore')
    onSnapshot.mockImplementationOnce((_q: any, cb: any) => { cb({ docs: [] }); return jest.fn() })
    render(<TournamentList />)
    expect(screen.getByText(/nessun torneo/i)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx jest __tests__/TournamentList.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create frontend/components/tournament/TournamentList.tsx**

```typescript
'use client'
import { useEffect, useState } from 'react'
import { collection, query, where, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useAuth } from '@/components/auth/AuthProvider'
import type { Tournament } from '@/types/schema'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'

export function TournamentList() {
  const { user } = useAuth()
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return
    const q = query(collection(db, 'tournaments'), where('admin_uid', '==', user.uid))
    const unsubscribe = onSnapshot(q, (snap) => {
      setTournaments(snap.docs.map((d) => ({ id: d.id, ...d.data() } as Tournament)))
      setLoading(false)
    })
    return unsubscribe
  }, [user])

  if (loading) return <p>Caricamento tornei...</p>
  if (tournaments.length === 0) return <p>Nessun torneo ancora. Creane uno!</p>

  return (
    <ul className="space-y-2">
      {tournaments.map((t) => (
        <li key={t.id}>
          <Link href={`/admin/${t.id}`} className="flex items-center justify-between p-4 border rounded hover:bg-gray-50">
            <span className="font-medium">{t.name}</span>
            <Badge variant={t.status === 'scheduled' ? 'default' : 'secondary'}>{t.status}</Badge>
          </Link>
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 4: Create frontend/app/admin/page.tsx**

```typescript
'use client'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'
import { TournamentList } from '@/components/tournament/TournamentList'
import { Button } from '@/components/ui/button'

export default function AdminPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  if (loading) return <div className="flex min-h-screen items-center justify-center">Caricamento...</div>

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold">Tournament Manager</h1>
          <GoogleSignInButton />
        </div>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">I tuoi tornei</h1>
        <Button onClick={() => router.push('/admin/new')}>Nuovo torneo</Button>
      </div>
      <TournamentList />
    </main>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx jest __tests__/TournamentList.test.tsx
```

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/admin/page.tsx frontend/components/tournament/TournamentList.tsx frontend/__tests__/TournamentList.test.tsx
git commit -m "feat: admin login page and real-time tournament list"
```

---

## Task 9: Tournament Creation Wizard

**Files:**
- Create: `frontend/app/admin/new/page.tsx`
- Create: `frontend/components/tournament/TournamentWizard.tsx`
- Create: `frontend/__tests__/TournamentWizard.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/TournamentWizard.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TournamentWizard } from '@/components/tournament/TournamentWizard'
import * as api from '@/lib/api'

jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }))

describe('TournamentWizard', () => {
  it('shows template options on step 1', () => {
    render(<TournamentWizard />)
    expect(screen.getByText(/calcetto/i)).toBeInTheDocument()
    expect(screen.getByText(/basket/i)).toBeInTheDocument()
    expect(screen.getByText(/personalizzato/i)).toBeInTheDocument()
  })

  it('disables Avanti button until a template is selected', () => {
    render(<TournamentWizard />)
    expect(screen.getByRole('button', { name: /avanti/i })).toBeDisabled()
  })

  it('advances to step 2 after selecting a template', async () => {
    render(<TournamentWizard />)
    fireEvent.click(screen.getByText(/calcetto/i))
    fireEvent.click(screen.getByRole('button', { name: /avanti/i }))
    await waitFor(() => {
      expect(screen.getByLabelText(/nome torneo/i)).toBeInTheDocument()
    })
  })

  it('calls createTournament and redirects on submit', async () => {
    const mockCreate = jest.spyOn(api, 'createTournament').mockResolvedValue({ tournament_id: 't-new' })
    const { push } = require('next/navigation').useRouter()
    render(<TournamentWizard />)
    fireEvent.click(screen.getByText(/calcetto/i))
    fireEvent.click(screen.getByRole('button', { name: /avanti/i }))
    await waitFor(() => screen.getByLabelText(/nome torneo/i))
    fireEvent.change(screen.getByLabelText(/nome torneo/i), { target: { value: 'Torneo 2026' } })
    fireEvent.click(screen.getByRole('button', { name: /crea torneo/i }))
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Torneo 2026' }),
        'fake-token'
      )
    })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx jest __tests__/TournamentWizard.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create frontend/components/tournament/TournamentWizard.tsx**

```typescript
'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { createTournament } from '@/lib/api'
import type { SchemaField } from '@/types/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

const TEMPLATES: Record<string, { sport: string; team_fields: SchemaField[] }> = {
  calcetto: {
    sport: 'calcetto',
    team_fields: [
      { key: 'nome', type: 'text', required: true, max_length: 100 },
      { key: 'contact_email', type: 'email', required: true },
      { key: 'city', type: 'text', required: false, max_length: 80 },
    ],
  },
  basket: {
    sport: 'basket',
    team_fields: [
      { key: 'nome', type: 'text', required: true, max_length: 100 },
      { key: 'contact_email', type: 'email', required: true },
      { key: 'jersey_number', type: 'number', required: false },
    ],
  },
  personalizzato: { sport: '', team_fields: [] },
}

export function TournamentWizard() {
  const [step, setStep] = useState(1)
  const [template, setTemplate] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [maxTeams, setMaxTeams] = useState(8)
  const [teamsPerGroup, setTeamsPerGroup] = useState(4)
  const [isPublic, setIsPublic] = useState(false)
  const { getToken } = useFirebaseToken()
  const router = useRouter()

  const handleSubmit = async () => {
    if (!template) return
    const tmpl = TEMPLATES[template]
    const token = await getToken()
    const result = await createTournament(
      {
        name,
        schema_config: {
          sport: tmpl.sport,
          max_teams: maxTeams,
          teams_per_group: teamsPerGroup,
          public: isPublic,
          invite_codes: { enabled: false, partial: false },
          team_fields: tmpl.team_fields,
          player_fields: [],
          admin_controls: { can_set_strength: true, max_teams: maxTeams },
        },
      },
      token
    )
    router.push(`/admin/${result.tournament_id}`)
  }

  if (step === 1) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Scegli template</h2>
        <div className="grid grid-cols-3 gap-4">
          {Object.keys(TEMPLATES).map((key) => (
            <button
              key={key}
              className={`p-6 border-2 rounded-lg capitalize font-medium transition-colors ${
                template === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-400'
              }`}
              onClick={() => setTemplate(key)}
            >
              {key}
            </button>
          ))}
        </div>
        <Button onClick={() => setStep(2)} disabled={!template}>
          Avanti
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-md">
      <h2 className="text-xl font-bold">Configura torneo</h2>
      <div>
        <Label htmlFor="name">Nome torneo</Label>
        <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div>
        <Label htmlFor="max-teams">Max squadre</Label>
        <Input
          id="max-teams"
          type="number"
          value={maxTeams}
          onChange={(e) => setMaxTeams(Number(e.target.value))}
        />
      </div>
      <div>
        <Label htmlFor="teams-per-group">Squadre per girone</Label>
        <Input
          id="teams-per-group"
          type="number"
          value={teamsPerGroup}
          onChange={(e) => setTeamsPerGroup(Number(e.target.value))}
        />
      </div>
      <div className="flex items-center gap-2">
        <Switch id="public" checked={isPublic} onCheckedChange={setIsPublic} />
        <Label htmlFor="public">Torneo pubblico</Label>
      </div>
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(1)}>
          Indietro
        </Button>
        <Button onClick={handleSubmit} disabled={!name}>
          Crea Torneo
        </Button>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/app/admin/new/page.tsx**

```typescript
import { TournamentWizard } from '@/components/tournament/TournamentWizard'

export default function NewTournamentPage() {
  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Nuovo torneo</h1>
      <TournamentWizard />
    </main>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx jest __tests__/TournamentWizard.test.tsx
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/admin/new/ frontend/components/tournament/TournamentWizard.tsx frontend/__tests__/TournamentWizard.test.tsx
git commit -m "feat: tournament creation wizard with template selection"
```

---

## Task 10: Dashboard + TeamTable

**Files:**
- Create: `frontend/app/admin/[id]/page.tsx`
- Create: `frontend/components/tournament/TeamTable.tsx`
- Create: `frontend/__tests__/TeamTable.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/TeamTable.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TeamTable } from '@/components/tournament/TeamTable'
import * as api from '@/lib/api'

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  onSnapshot: jest.fn((_ref, cb) => {
    cb({
      docs: [
        { id: 'team-1', data: () => ({ nome: 'Leoni', forza: 5, confirmed: false, owner_uid: 'u1' }) },
      ],
    })
    return jest.fn()
  }),
}))

describe('TeamTable', () => {
  it('renders team names from Firestore', () => {
    render(<TeamTable tournamentId="t-123" />)
    expect(screen.getByText('Leoni')).toBeInTheDocument()
  })

  it('shows empty state when no teams', () => {
    const { onSnapshot } = require('firebase/firestore')
    onSnapshot.mockImplementationOnce((_r: any, cb: any) => { cb({ docs: [] }); return jest.fn() })
    render(<TeamTable tournamentId="t-123" />)
    expect(screen.getByText(/nessuna squadra/i)).toBeInTheDocument()
  })

  it('calls patchTeam when confirm toggle is clicked', async () => {
    const mockPatch = jest.spyOn(api, 'patchTeam').mockResolvedValue({})
    render(<TeamTable tournamentId="t-123" />)
    fireEvent.click(screen.getByRole('switch'))
    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('t-123', 'team-1', { confirmed: true }, 'fake-token')
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx jest __tests__/TeamTable.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create frontend/components/tournament/TeamTable.tsx**

```typescript
'use client'
import { useEffect, useState } from 'react'
import { collection, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { patchTeam } from '@/lib/api'
import type { Team } from '@/types/schema'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Props {
  tournamentId: string
}

export function TeamTable({ tournamentId }: Props) {
  const [teams, setTeams] = useState<Team[]>([])
  const { getToken } = useFirebaseToken()

  useEffect(() => {
    const ref = collection(db, 'tournaments', tournamentId, 'teams')
    const unsubscribe = onSnapshot(ref, (snap) => {
      setTeams(snap.docs.map((d) => ({ id: d.id, ...d.data() } as Team)))
    })
    return unsubscribe
  }, [tournamentId])

  const handlePatch = async (teamId: string, data: { forza?: number; confirmed?: boolean }) => {
    const token = await getToken()
    await patchTeam(tournamentId, teamId, data, token)
  }

  if (teams.length === 0) return <p>Nessuna squadra registrata.</p>

  return (
    <table className="w-full">
      <thead>
        <tr className="text-left border-b">
          <th className="p-2">Nome</th>
          <th className="p-2">Strength</th>
          <th className="p-2">Confermata</th>
        </tr>
      </thead>
      <tbody>
        {teams.map((team) => (
          <tr key={team.id} className="border-b">
            <td className="p-2">{team.nome}</td>
            <td className="p-2">
              <Select
                value={String(team.forza)}
                onValueChange={(v) => handlePatch(team.id, { forza: Number(v) })}
              >
                <SelectTrigger className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </td>
            <td className="p-2">
              <Switch
                checked={team.confirmed}
                onCheckedChange={(checked) => handlePatch(team.id, { confirmed: checked })}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
```

- [ ] **Step 4: Create frontend/app/admin/[id]/page.tsx**

```typescript
'use client'
import Link from 'next/link'
import { useTournament } from '@/lib/hooks/useTournament'
import { TeamTable } from '@/components/tournament/TeamTable'
import { InviteCodesPanel } from '@/components/tournament/InviteCodesPanel'
import { SchedulePanel } from '@/components/tournament/SchedulePanel'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function DashboardPage({ params }: { params: { id: string } }) {
  const { data: tournament, loading } = useTournament(params.id)

  if (loading) return <div className="p-6">Caricamento...</div>
  if (!tournament) return <div className="p-6">Torneo non trovato.</div>

  return (
    <main className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{tournament.name}</h1>
        <Link href={`/admin/${params.id}/schema`}>
          <Button variant="outline">Modifica schema</Button>
        </Link>
      </div>
      <Tabs defaultValue="teams">
        <TabsList>
          <TabsTrigger value="teams">Squadre</TabsTrigger>
          <TabsTrigger value="invite">Invite Codes</TabsTrigger>
          <TabsTrigger value="schedule">Calendario</TabsTrigger>
        </TabsList>
        <TabsContent value="teams" className="mt-4">
          <TeamTable tournamentId={params.id} />
        </TabsContent>
        <TabsContent value="invite" className="mt-4">
          <InviteCodesPanel tournamentId={params.id} />
        </TabsContent>
        <TabsContent value="schedule" className="mt-4">
          <SchedulePanel tournamentId={params.id} />
        </TabsContent>
      </Tabs>
    </main>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx jest __tests__/TeamTable.test.tsx
```

Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/app/admin/\[id\]/ frontend/components/tournament/TeamTable.tsx frontend/__tests__/TeamTable.test.tsx
git commit -m "feat: tournament dashboard with real-time team table"
```

---

## Task 11: InviteCodesPanel + SchedulePanel

**Files:**
- Create: `frontend/components/tournament/InviteCodesPanel.tsx`
- Create: `frontend/components/tournament/SchedulePanel.tsx`
- Create: `frontend/__tests__/SchedulePanel.test.tsx`

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/SchedulePanel.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SchedulePanel } from '@/components/tournament/SchedulePanel'
import * as api from '@/lib/api'

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('@/lib/hooks/useTournament', () => ({
  useTournament: () => ({ data: { id: 't-123', status: 'draft' }, loading: false }),
}))
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  query: jest.fn(),
  where: jest.fn(),
  onSnapshot: jest.fn((_q, cb) => { cb({ size: 3 }); return jest.fn() }),
}))

describe('SchedulePanel', () => {
  it('shows current status', () => {
    render(<SchedulePanel tournamentId="t-123" />)
    expect(screen.getByText(/draft/i)).toBeInTheDocument()
  })

  it('enables generate button when confirmed teams >= 2', () => {
    render(<SchedulePanel tournamentId="t-123" />)
    expect(screen.getByRole('button', { name: /genera gironi/i })).not.toBeDisabled()
  })

  it('calls generateSchedule on button click', async () => {
    const mockGenerate = jest.spyOn(api, 'generateSchedule').mockResolvedValue({ status: 'generated', matches: 6 })
    render(<SchedulePanel tournamentId="t-123" />)
    fireEvent.click(screen.getByRole('button', { name: /genera gironi/i }))
    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith('t-123', 'fake-token')
    })
  })

  it('shows error message on failure', async () => {
    jest.spyOn(api, 'generateSchedule').mockRejectedValue(new Error('Infeasible'))
    render(<SchedulePanel tournamentId="t-123" />)
    fireEvent.click(screen.getByRole('button', { name: /genera gironi/i }))
    await waitFor(() => {
      expect(screen.getByText(/infeasible/i)).toBeInTheDocument()
    })
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

```bash
npx jest __tests__/SchedulePanel.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create frontend/components/tournament/InviteCodesPanel.tsx**

```typescript
'use client'
import { useTournament } from '@/lib/hooks/useTournament'

interface Props {
  tournamentId: string
}

export function InviteCodesPanel({ tournamentId }: Props) {
  const { data: tournament } = useTournament(tournamentId)

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        La gestione dei codici invito sarà disponibile nella prossima versione (Plan C).
      </p>
      {tournament && (
        <p>
          Modalità accesso:{' '}
          <strong>{tournament.public ? 'Pubblica' : 'Su invito'}</strong>
        </p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/components/tournament/SchedulePanel.tsx**

```typescript
'use client'
import { useEffect, useState } from 'react'
import { collection, query, where, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useTournament } from '@/lib/hooks/useTournament'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { generateSchedule } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface Props {
  tournamentId: string
}

export function SchedulePanel({ tournamentId }: Props) {
  const { data: tournament } = useTournament(tournamentId)
  const { getToken } = useFirebaseToken()
  const [confirmedCount, setConfirmedCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  useEffect(() => {
    const q = query(
      collection(db, 'tournaments', tournamentId, 'teams'),
      where('confirmed', '==', true)
    )
    return onSnapshot(q, (snap) => setConfirmedCount(snap.size))
  }, [tournamentId])

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const token = await getToken()
      const res = await generateSchedule(tournamentId, token)
      setResult(`Generato: ${res.matches} partite`)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const isScheduled = tournament?.status === 'scheduled'

  return (
    <div className="space-y-4">
      <p>
        Stato: <strong>{tournament?.status ?? '—'}</strong>
      </p>
      <p className="text-sm text-gray-600">
        Squadre confermate: {confirmedCount}
      </p>
      {error && <p className="text-red-600">{error}</p>}
      {result && <p className="text-green-600">{result}</p>}
      <Button
        onClick={handleGenerate}
        disabled={loading || confirmedCount < 2 || isScheduled}
      >
        {loading ? 'Generazione...' : 'Genera Gironi'}
      </Button>
    </div>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
npx jest __tests__/SchedulePanel.test.tsx
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```bash
git add frontend/components/tournament/InviteCodesPanel.tsx frontend/components/tournament/SchedulePanel.tsx frontend/__tests__/SchedulePanel.test.tsx
git commit -m "feat: InviteCodesPanel and SchedulePanel with generate-schedule integration"
```

---

## Task 12: SchemaEditor

**Files:**
- Create: `frontend/components/tournament/SchemaEditor.tsx`
- Create: `frontend/app/admin/[id]/schema/page.tsx`
- Create: `frontend/__tests__/SchemaEditor.test.tsx`

- [ ] **Step 1: Write the failing tests**

Create `frontend/__tests__/SchemaEditor.test.tsx`:

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SchemaEditor } from '@/components/tournament/SchemaEditor'
import * as api from '@/lib/api'

const mockSchema = {
  sport: 'calcetto',
  max_teams: 8,
  teams_per_group: 4,
  public: false,
  invite_codes: { enabled: false, partial: false },
  team_fields: [{ key: 'nome', type: 'text', required: true, max_length: 100 }],
  player_fields: [],
  admin_controls: { can_set_strength: true, max_teams: 8 },
}

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('firebase/firestore', () => ({
  doc: jest.fn(),
  getDoc: jest.fn().mockResolvedValue({
    exists: () => true,
    data: () => mockSchema,
  }),
}))

describe('SchemaEditor', () => {
  it('renders existing fields after load', async () => {
    render(<SchemaEditor tournamentId="t-123" />)
    await waitFor(() => {
      expect(screen.getByText('nome')).toBeInTheDocument()
    })
  })

  it('removes a field when the remove button is clicked', async () => {
    render(<SchemaEditor tournamentId="t-123" />)
    await waitFor(() => screen.getByText('nome'))
    fireEvent.click(screen.getByRole('button', { name: /rimuovi nome/i }))
    expect(screen.queryByText('nome')).not.toBeInTheDocument()
  })

  it('calls updateSchema on save', async () => {
    const mockUpdate = jest.spyOn(api, 'updateSchema').mockResolvedValue({ status: 'updated' })
    render(<SchemaEditor tournamentId="t-123" />)
    await waitFor(() => screen.getByText('nome'))
    fireEvent.click(screen.getByRole('button', { name: /salva schema/i }))
    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith('t-123', expect.objectContaining({ sport: 'calcetto' }), 'fake-token')
    })
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
npx jest __tests__/SchemaEditor.test.tsx
```

Expected: FAIL — module not found.

- [ ] **Step 3: Create frontend/components/tournament/SchemaEditor.tsx**

```typescript
'use client'
import { useEffect, useState } from 'react'
import { doc, getDoc } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { updateSchema } from '@/lib/api'
import type { TournamentSchema, SchemaField } from '@/types/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

interface Props {
  tournamentId: string
}

export function SchemaEditor({ tournamentId }: Props) {
  const [schema, setSchema] = useState<TournamentSchema | null>(null)
  const [fields, setFields] = useState<SchemaField[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const { getToken } = useFirebaseToken()

  useEffect(() => {
    const ref = doc(db, 'tournaments', tournamentId, 'config', 'schema')
    getDoc(ref).then((snap) => {
      if (snap.exists()) {
        const s = snap.data() as TournamentSchema
        setSchema(s)
        setFields(s.team_fields)
      }
    })
  }, [tournamentId])

  const removeField = (key: string) =>
    setFields((prev) => prev.filter((f) => f.key !== key))

  const addField = (field: SchemaField) =>
    setFields((prev) => [...prev, field])

  const handleSave = async () => {
    if (!schema) return
    setSaving(true)
    setSaved(false)
    try {
      const token = await getToken()
      await updateSchema(tournamentId, { ...schema, team_fields: fields }, token)
      setSaved(true)
    } finally {
      setSaving(false)
    }
  }

  if (!schema) return <p>Caricamento schema...</p>

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        {fields.map((f) => (
          <div key={f.key} className="flex items-center gap-3 p-3 border rounded">
            <span className="font-mono font-medium">{f.key}</span>
            <Badge variant="secondary">{f.type}</Badge>
            <span className="text-sm text-gray-500">{f.required ? 'richiesto' : 'opzionale'}</span>
            <Button
              variant="destructive"
              size="sm"
              aria-label={`rimuovi ${f.key}`}
              onClick={() => removeField(f.key)}
              className="ml-auto"
            >
              Rimuovi
            </Button>
          </div>
        ))}
      </div>

      <AddFieldForm onAdd={addField} existingKeys={fields.map((f) => f.key)} />

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Salvataggio...' : 'Salva Schema'}
        </Button>
        {saved && <span className="text-green-600 text-sm">Salvato!</span>}
      </div>
    </div>
  )
}

function AddFieldForm({
  onAdd,
  existingKeys,
}: {
  onAdd: (f: SchemaField) => void
  existingKeys: string[]
}) {
  const [key, setKey] = useState('')
  const [type, setType] = useState<SchemaField['type']>('text')
  const [required, setRequired] = useState(true)
  const [maxLength, setMaxLength] = useState(100)

  const isDuplicate = existingKeys.includes(key)

  const handleAdd = () => {
    if (!key || isDuplicate) return
    onAdd({ key, type, required, max_length: type === 'text' ? maxLength : undefined })
    setKey('')
  }

  return (
    <div className="flex flex-wrap gap-2 items-end border-t pt-4">
      <div>
        <label className="text-sm text-gray-600">Chiave</label>
        <Input
          placeholder="es. phone"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="w-32"
        />
        {isDuplicate && <p className="text-red-500 text-xs">Chiave già esistente</p>}
      </div>
      <div>
        <label className="text-sm text-gray-600">Tipo</label>
        <Select value={type} onValueChange={(v) => setType(v as SchemaField['type'])}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="text">text</SelectItem>
            <SelectItem value="email">email</SelectItem>
            <SelectItem value="number">number</SelectItem>
            <SelectItem value="date">date</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {type === 'text' && (
        <div>
          <label className="text-sm text-gray-600">Max length</label>
          <Input
            type="number"
            value={maxLength}
            onChange={(e) => setMaxLength(Number(e.target.value))}
            className="w-24"
          />
        </div>
      )}
      <Button onClick={handleAdd} disabled={!key || isDuplicate}>
        Aggiungi campo
      </Button>
    </div>
  )
}
```

- [ ] **Step 4: Create frontend/app/admin/[id]/schema/page.tsx**

```typescript
import { SchemaEditor } from '@/components/tournament/SchemaEditor'

export default function SchemaPage({ params }: { params: { id: string } }) {
  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Editor Schema Campi</h1>
      <SchemaEditor tournamentId={params.id} />
    </main>
  )
}
```

- [ ] **Step 5: Run all frontend tests**

```bash
npx jest
```

Expected: all test suites pass.

- [ ] **Step 6: Run backend tests to verify no regressions**

```bash
cd .. && cd backend && python3 -m pytest -q
```

Expected: `30 passed`.

- [ ] **Step 7: Commit**

```bash
cd ..
git add frontend/components/tournament/SchemaEditor.tsx frontend/app/admin/\[id\]/schema/ frontend/__tests__/SchemaEditor.test.tsx
git commit -m "feat: schema field editor — add/remove fields, save via PUT /schema"
```

---

## Self-Review

**Spec coverage:**
- ✅ Next.js 14, TypeScript, shadcn/ui, Tailwind — Task 2
- ✅ Firebase Google Sign-In — Task 7
- ✅ Session cookie + middleware route protection — Task 6
- ✅ `onIdTokenChanged` token refresh loop — Task 7 (AuthProvider)
- ✅ Real-time Firestore reads via `onSnapshot` — Tasks 8, 10
- ✅ `/admin` — login + tournament list — Task 8
- ✅ `/admin/new` — wizard 2 step con template — Task 9
- ✅ `/admin/[id]` — dashboard con 3 tab — Task 10
- ✅ TeamTable con strength e conferma — Task 10
- ✅ InviteCodesPanel — Task 11
- ✅ SchedulePanel con `POST /generate-schedule` — Task 11
- ✅ `/admin/[id]/schema` — SchemaEditor — Task 12
- ✅ `PUT /tournaments/{id}/schema` backend — Task 1
- ✅ `generateZodSchema` con unit test — Task 4
- ✅ `useFirebaseToken` e `useTournament` hooks — Task 5
- ✅ Vercel deploy — no config needed beyond `.env.local`; `next.config.ts` default è sufficiente

**Type consistency:** `SchemaField`, `TournamentSchema`, `Tournament`, `Team`, `TeamUpdate`, `TournamentCreate` definiti in Task 3 e usati coerentemente in tutti i task successivi. `generateZodSchema` usa `SchemaField` dal Task 3. `updateSchema` in `api.ts` usa `TournamentSchema`. Tutti coerenti.
