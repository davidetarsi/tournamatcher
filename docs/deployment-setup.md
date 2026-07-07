# Deployment Setup

Stack: **Cloudflare Pages** (frontend) + **Railway** (backend Python) + **GitHub Actions** (Firebase rules)

Dopo questo setup, `git push` su `main` deploya tutto in automatico.

---

## 1. Railway — backend Python

### Prima volta
1. Vai su [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
2. Seleziona questo repo
3. **Root Directory: `backend`** (importante — Railway trova il `Dockerfile` lì)
4. Railway usa `backend/railway.json` per health check e restart automatico

### Environment variables (tab Variables)
| Variabile | Valore |
|-----------|--------|
| `FIREBASE_SERVICE_ACCOUNT_KEY_JSON` | Contenuto di `serviceAccountKey.json` come stringa JSON inline |
| `TEAM_JWT_SECRET` | Stringa casuale lunga (es. genera con `openssl rand -hex 32`) |
| `ALLOWED_ORIGINS` | URL del frontend Cloudflare Pages (es. `https://tournament-frontend.pages.dev`) |

### Aggiornamenti automatici
Railway rileva ogni push su `main` e rebuilda l'immagine Docker automaticamente.
Non serve fare nulla — collegando il repo una volta, è automatico.

### URL del backend
Una volta deployato, Railway assegna un URL tipo `https://xxx.railway.app`.
Copialo — serve come `NEXT_PUBLIC_RAILWAY_API_URL` nel frontend.

---

## 2. Cloudflare Pages — frontend Next.js

### Prima volta
1. [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**
2. Seleziona questo repo
3. **Root directory: `frontend`**

### Build settings
| Campo | Valore |
|-------|--------|
| Build command | `npx @cloudflare/next-on-pages@1` |
| Output directory | `.vercel/output/static` |

### Environment variables (Settings → Environment variables)
| Variabile | Dove trovarla |
|-----------|---------------|
| `NEXT_PUBLIC_FIREBASE_API_KEY` | Firebase console → Project settings → Web app |
| `NEXT_PUBLIC_FIREBASE_APP_ID` | Firebase console → Project settings → Web app |
| `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN` | Firebase console → Project settings → Web app |
| `NEXT_PUBLIC_FIREBASE_PROJECT_ID` | Firebase console → Project settings → General |
| `NEXT_PUBLIC_RAILWAY_API_URL` | URL copiato da Railway al punto precedente |

### Compatibility flag (obbligatorio per Next.js)
**Settings → Functions → Compatibility flags** → aggiungi `nodejs_compat`

### Aggiornamenti automatici
Cloudflare Pages rebuilda ad ogni push su `main`, esattamente come il tuo sito statico su Cloudflare.

---

## 3. GitHub Actions — Firebase Security Rules

Questo step è necessario solo per aggiornare `firestore.rules` senza usare il CLI manualmente.

### Setup token Firebase (una volta sola, in locale)
```bash
npm install -g firebase-tools
firebase login:ci
# Copia il token che stampa a schermo
```

### Aggiungi il token a GitHub
1. GitHub repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
2. Nome: `FIREBASE_TOKEN`
3. Valore: il token copiato sopra

### Come funziona
Il file `.github/workflows/deploy-rules.yml` è già nel repo.
Si attiva **solo** quando un push su `main` modifica `firestore.rules` — nessun deploy inutile.

---

## Flusso a regime

```
git push origin main
        │
        ├── frontend cambiato?  → Cloudflare Pages rebuilda e deploya
        ├── backend cambiato?   → Railway rebuilda il Docker e rideploya
        └── firestore.rules?    → GitHub Actions deploya le rules su Firebase
```

---

## Variabili d'ambiente locali (sviluppo)

Crea `frontend/.env.local` (non committare, è in `.gitignore`):
```
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_APP_ID=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=...
NEXT_PUBLIC_FIREBASE_PROJECT_ID=...
NEXT_PUBLIC_RAILWAY_API_URL=http://localhost:8000
NEXT_PUBLIC_DEV_BYPASS_AUTH=true
```

Crea `backend/.env` (non committare):
```
FIREBASE_SERVICE_ACCOUNT_KEY_JSON=<contenuto serviceAccountKey.json>
TEAM_JWT_SECRET=<stringa casuale>
ALLOWED_ORIGINS=http://localhost:3000
```

Per avviare tutto in locale:
```bash
# Backend
cd backend && uvicorn main:app --reload --port 8000

# Frontend (altro terminale)
cd frontend && npm run dev
```
