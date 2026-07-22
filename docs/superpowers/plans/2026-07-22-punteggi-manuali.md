# Punteggi manuali per giocatori non su FIBA — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permettere di inserire in una squadra, accanto agli URL FIBA, righe manuali `nome,punteggio` (punteggio opzionale) per i giocatori non registrati su FIBA.

**Architecture:** Approccio ibrido. Il frontend (index.html) fa lo split URL-vs-manuale con una regex e costruisce l'oggetto giocatore; il backend (app.py) è la rete di sicurezza testata: normalizza il punteggio manuale al salvataggio, salta i manuali durante il fetch, e li conta nella media del pool. Nessuna nuova firma API, schema `giocatori` invariato nella forma.

**Tech Stack:** Python 3.9+, FastAPI, pytest, HTML+JS vanilla, pytest-playwright.

**Spec:** `docs/superpowers/specs/2026-07-22-punteggi-manuali-design.md`

## Global Constraints

- Discriminatore univoco: **`url` vuoto ⇒ giocatore manuale** (i giocatori FIBA hanno sempre `url` non vuoto).
- Convenzione `fetch_status` (estende quella esistente `ok` / `ok: N/A (0 punti)` / `ok: media stimata (N)` / `errore: ...`):
  - `"manuale (N)"` = punteggio manuale fisso, N intero > 0 (badge blu).
  - `"manuale: N/A"` = riga manuale senza numero valido → riceve la media (badge arancione, come i N/A).
- Un punteggio manuale con numero **conta nella media del pool** (come un dato FIBA reale) ma **non viene mai ri-stimato**.
- Il fetch **salta i giocatori manuali**: non li interroga, non li marca `errore`, non ne sovrascrive il punteggio.
- Re-serializzazione in modifica **context-aware** (preserva l'intento): FIBA→URL; `"manuale (N)"`→`nome,punteggio`; `"manuale: N/A"`/`"ok: media stimata (N)"`→**solo `nome`**.
- Regex di parsing riga manuale (frontend): `/^(.*?)(?:\s*,\s*(\d+))?$/` — gruppo 1 = nome, gruppo 2 = punteggio (solo se cifre in coda alla riga).
- Scritture JSON sempre via `storage.save_json` (atomiche). Testi in italiano. Tutto in `fiba-tool/`. `copia_di_generazione_squadre.py` mai toccato.

## File Structure

```
fiba-tool/app.py          # normalizza_giocatore_manuale + normalizza_manuali (nuove);
                          # crea_squadra/aggiorna_squadra le applicano; _esegui_fetch salta
                          # i manuali; applica_fallback_medio li conta nella media
fiba-tool/static/index.html  # parsing riga (regex), badge blu + CSS, promemoria di scala,
                          # re-serializzazione context-aware in modifica
fiba-tool/tests/test_app.py  # unit + integrazione backend
```

---

### Task 1: Backend — normalizzazione punteggio manuale al salvataggio

**Files:**
- Modify: `fiba-tool/app.py` (nuove funzioni + `crea_squadra`/`aggiorna_squadra`)
- Test: `fiba-tool/tests/test_app.py` (append)

**Interfaces:**
- Consumes: `leggi_squadre`, `save_json`, `SQUADRE` (esistenti); la fixture `client` in test_app.py.
- Produces: `normalizza_giocatore_manuale(g: dict) -> dict` (muta `g` in place; url-vuoto → valida ranking_points a int>0 o None + fetch_status coerente); `normalizza_manuali(giocatori: list[dict]) -> list[dict]` (applica la precedente ai soli giocatori con url vuoto, muta in place).

- [ ] **Step 1: Write the failing tests** (append a `fiba-tool/tests/test_app.py`)

```python
def test_normalizza_manuale_con_numero():
    import app
    g = {"url": "", "nome": "Mario", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": "vecchio"}
    app.normalizza_giocatore_manuale(g)
    assert g["ranking_points"] == 1500
    assert g["fetch_status"] == "manuale (1500)"
    assert g["fetched_at"] is None


def test_normalizza_manuale_senza_numero_valido():
    import app
    for raw in [None, "", "abc", -5, 0, "12x"]:
        g = {"url": "", "nome": "Mario", "ranking_points": raw,
             "fetch_status": "manuale", "fetched_at": None}
        app.normalizza_giocatore_manuale(g)
        assert g["ranking_points"] is None, raw
        assert g["fetch_status"] == "manuale: N/A", raw


def test_normalizza_manuale_accetta_stringa_di_cifre():
    import app
    g = {"url": "", "nome": "M", "ranking_points": "1500",
         "fetch_status": "manuale", "fetched_at": None}
    app.normalizza_giocatore_manuale(g)
    assert g["ranking_points"] == 1500
    assert g["fetch_status"] == "manuale (1500)"


def test_normalizza_manuali_lascia_intatti_i_fiba():
    import app
    giocatori = [
        {"url": "https://play.fiba3x3.com/players/x", "nome": "F",
         "ranking_points": 900, "fetch_status": "ok", "fetched_at": "t"},
        {"url": "", "nome": "M", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": None},
    ]
    app.normalizza_manuali(giocatori)
    assert giocatori[0]["fetch_status"] == "ok"       # FIBA intatto
    assert giocatori[0]["ranking_points"] == 900
    assert giocatori[1]["fetch_status"] == "manuale (1500)"


def test_crea_e_modifica_squadra_normalizzano_i_manuali(client):
    corpo = {"nome": "T", "disponibilita": [], "giocatori": [
        {"url": "", "nome": "Mario", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": None}]}
    sid = client.post("/api/squadre", json=corpo).json()["id"]
    g = client.get("/api/squadre").json()["squadre"][0]["giocatori"][0]
    assert g["fetch_status"] == "manuale (1500)" and g["ranking_points"] == 1500

    # in modifica un manuale senza numero torna N/A
    corpo2 = {"nome": "T", "disponibilita": [], "giocatori": [
        {"url": "", "nome": "Mario", "ranking_points": None,
         "fetch_status": "manuale", "fetched_at": None}]}
    client.put(f"/api/squadre/{sid}", json=corpo2)
    g = client.get("/api/squadre").json()["squadre"][0]["giocatori"][0]
    assert g["fetch_status"] == "manuale: N/A" and g["ranking_points"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd fiba-tool && python3 -m pytest tests/test_app.py -v -k "normalizza or normalizzano"`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'normalizza_giocatore_manuale'`

- [ ] **Step 3: Implement** (in `fiba-tool/app.py`)

Aggiungi le due funzioni subito prima di `applica_fallback_medio` (cioè prima della riga
`def applica_fallback_medio(dati):`):

```python
def normalizza_giocatore_manuale(g):
    """Rete di sicurezza per un giocatore manuale (url vuoto): valida ranking_points a
    int > 0 oppure None, e imposta un fetch_status coerente, indipendentemente da cosa
    manda il frontend.
      int > 0 -> ranking_points = N, fetch_status = "manuale (N)"     (punteggio fisso)
      altro   -> ranking_points = None, fetch_status = "manuale: N/A" (verrà stimato)
    Muta g in place; ritorna g."""
    raw = g.get("ranking_points")
    try:
        n = int(raw)
    except (TypeError, ValueError):
        n = None
    if n is not None and n > 0:
        g["ranking_points"] = n
        g["fetch_status"] = f"manuale ({n})"
    else:
        g["ranking_points"] = None
        g["fetch_status"] = "manuale: N/A"
    g["fetched_at"] = None
    return g


def normalizza_manuali(giocatori):
    """Applica normalizza_giocatore_manuale a ogni giocatore con url vuoto (manuale).
    I giocatori FIBA (url non vuoto) restano intatti. Muta la lista in place."""
    for g in giocatori:
        if not (g.get("url") or "").strip():
            normalizza_giocatore_manuale(g)
    return giocatori
```

In `crea_squadra` (attualmente righe ~62-70), aggiungi la normalizzazione dopo
`nuova = squadra.model_dump()`:

```python
@app.post("/api/squadre")
def crea_squadra(squadra: SquadraIn):
    dati = leggi_squadre()
    nuova = squadra.model_dump()
    normalizza_manuali(nuova["giocatori"])
    nuova["id"] = uuid.uuid4().hex[:8]
    nuova["da_riconfermare"] = False
    dati["squadre"].append(nuova)
    save_json(SQUADRE, dati)
    return nuova
```

In `aggiorna_squadra` (attualmente righe ~73-82), normalizza prima di salvare:

```python
@app.put("/api/squadre/{sid}")
def aggiorna_squadra(sid: str, squadra: SquadraIn):
    dati = leggi_squadre()
    for i, s in enumerate(dati["squadre"]):
        if s["id"] == sid:
            aggiornata = {**squadra.model_dump(), "id": sid, "da_riconfermare": False}
            normalizza_manuali(aggiornata["giocatori"])
            dati["squadre"][i] = aggiornata
            save_json(SQUADRE, dati)
            return dati["squadre"][i]
    raise HTTPException(404, "Squadra non trovata")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd fiba-tool && python3 -m pytest tests/test_app.py -v`
Expected: tutti passed (i 5 nuovi + i preesistenti)

- [ ] **Step 5: Commit**

```bash
git add fiba-tool/app.py fiba-tool/tests/test_app.py
git commit -m "feat(fiba-tool): normalizza il punteggio manuale al salvataggio squadra"
```

---

### Task 2: Backend — il fetch salta i manuali e la media li conta

**Files:**
- Modify: `fiba-tool/app.py` (`_esegui_fetch` + `applica_fallback_medio`)
- Test: `fiba-tool/tests/test_app.py` (append)

**Interfaces:**
- Consumes: `normalizza_manuali` (Task 1), `fiba_client.fetch_team_players`, `applica_fallback_medio`.
- Produces: `_esegui_fetch` che fetcha solo i giocatori con url non vuoto; `applica_fallback_medio` che include i manuali-con-numero nella media e stima anche i `"manuale: N/A"`.

- [ ] **Step 1: Write the failing tests** (append a `fiba-tool/tests/test_app.py`)

```python
def test_media_conta_i_manuali_con_numero():
    import app
    dati = {"squadre": [
        {"giocatori": [{"ranking_points": 1000, "fetch_status": "manuale (1000)"}]},
        {"giocatori": [{"ranking_points": None, "fetch_status": "manuale: N/A"}]},
    ]}
    aggiornati = app.applica_fallback_medio(dati)
    assert aggiornati == 1
    stimato = dati["squadre"][1]["giocatori"][0]
    assert stimato["ranking_points"] == 1000            # media = solo il 1000 manuale
    assert stimato["fetch_status"] == "ok: media stimata (1000)"


def test_media_non_ristima_i_manuali_con_numero():
    import app
    dati = {"squadre": [
        {"giocatori": [{"ranking_points": 500, "fetch_status": "ok"}]},
        {"giocatori": [{"ranking_points": 1500, "fetch_status": "manuale (1500)"}]},
    ]}
    app.applica_fallback_medio(dati)
    manuale = dati["squadre"][1]["giocatori"][0]
    assert manuale["ranking_points"] == 1500            # NON ristimato
    assert manuale["fetch_status"] == "manuale (1500)"


def test_fetch_salta_i_giocatori_manuali(client, monkeypatch):
    import fiba_client
    client.post("/api/squadre", json={"nome": "Mix", "disponibilita": [], "giocatori": [
        {"url": "https://play.fiba3x3.com/players/u1", "nome": "", "ranking_points": None,
         "fetch_status": "mai", "fetched_at": None},
        {"url": "", "nome": "Manuale", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": None}]})
    urls_fetchate = []

    def finto(urls, session=None, pausa=None, on_progress=None):
        urls_fetchate.extend(urls)
        return [{"url": u, "ok": True,
                 "dati": {"id": "x", "nome": "R", "ranking_points": 800,
                          "fetched_at": "2026-07-22T00:00:00+00:00"}} for u in urls]

    monkeypatch.setattr(fiba_client, "fetch_team_players", finto)
    job = client.post("/api/fetch").json()["job_id"]
    for _ in range(60):
        st = client.get(f"/api/jobs/{job}/status").json()
        if st.get("stato") in ("completato", "errore"):
            break
        time.sleep(0.25)
    assert st["stato"] == "completato"
    # solo l'URL è stato interrogato, il manuale è stato saltato
    assert urls_fetchate == ["https://play.fiba3x3.com/players/u1"]
    giocatori = client.get("/api/squadre").json()["squadre"][0]["giocatori"]
    manuale = [g for g in giocatori if g["nome"] == "Manuale"][0]
    assert manuale["fetch_status"] == "manuale (1500)"  # intatto, non errore
    assert manuale["ranking_points"] == 1500
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd fiba-tool && python3 -m pytest tests/test_app.py -v -k "manuali or manuale"`
Expected: FAIL — `test_media_conta_i_manuali_con_numero` (la media oggi ignora i manuali) e `test_fetch_salta_i_giocatori_manuali` (oggi il manuale verrebbe passato a fetch → `errore`)

- [ ] **Step 3: Implement** (in `fiba-tool/app.py`)

Nel filtro `reali` di `applica_fallback_medio` (attualmente righe ~157-159), includi i
manuali-con-numero, e nel set di ri-stima (righe ~166-167) includi anche `"manuale: N/A"`:

```python
    reali = [g["ranking_points"]
             for s in dati["squadre"] for g in s["giocatori"]
             if (g.get("fetch_status") == "ok"
                 or (g.get("fetch_status") or "").startswith("manuale"))
             and (g.get("ranking_points") or 0) > 0]
    if not reali:
        return 0
    media = round(sum(reali) / len(reali))
    aggiornati = 0
    for s in dati["squadre"]:
        for g in s["giocatori"]:
            st = g.get("fetch_status") or ""
            if (st.startswith("ok: N/A") or st.startswith("ok: media stimata")
                    or st.startswith("manuale: N/A")):
                g["ranking_points"] = media
                g["fetch_status"] = f"ok: media stimata ({media})"
                aggiornati += 1
    return aggiornati
```

Nel loop di `_esegui_fetch` (attualmente righe ~184-196), fetcha SOLO i giocatori con url
non vuoto (i manuali vengono saltati e restano intatti):

```python
            if squadra:
                fetchabili = [g for g in squadra["giocatori"]
                              if (g.get("url") or "").strip()]
                risultati = fiba_client.fetch_team_players(
                    [g["url"] for g in fetchabili], sessione)
                for g, r in zip(fetchabili, risultati):
                    if r["ok"]:
                        g.update(r["dati"])
                        # 0 punti = giocatore non in classifica FIBA: marcato N/A,
                        # riceverà il punteggio medio del pool nel passo finale.
                        g["fetch_status"] = ("ok" if g["ranking_points"] > 0
                                             else "ok: N/A (0 punti)")
                    else:
                        g["fetch_status"] = f"errore: {r['errore']}"
                save_json(SQUADRE, dati)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd fiba-tool && python3 -m pytest tests/test_app.py -v`
Expected: tutti passed (i preesistenti restano validi: `test_fetch_job_e_squadra_aggiornata` usa un URL, non un manuale)

- [ ] **Step 5: Commit**

```bash
git add fiba-tool/app.py fiba-tool/tests/test_app.py
git commit -m "feat(fiba-tool): fetch salta i manuali; la media del pool li include"
```

---

### Task 3: Dashboard — parsing riga, badge blu, promemoria, re-serializzazione

**Files:**
- Modify: `fiba-tool/static/index.html`

**Interfaces:**
- Consumes: la convenzione `fetch_status` (`"manuale (N)"` / `"manuale: N/A"`) e la
  normalizzazione backend dei Task 1-2. Discriminatore: `url` vuoto = manuale.
- Produces: nessuna nuova interfaccia; comportamento UI.

- [ ] **Step 1: CSS badge blu**

In `fiba-tool/static/index.html`, alla riga dei colori badge
(`.verde{...}.giallo{...}.rosso{...}.arancione{background:#e67e22}`), aggiungi in coda:

```css
.verde{background:#2e7d32}.giallo{background:#f9a825}.rosso{background:#c62828}.arancione{background:#e67e22}.blu{background:#2b6cb0}
```

- [ ] **Step 2: Label + promemoria di scala**

Sostituisci il blocco `<label>URL profili giocatori ...</label>` (righe ~42-43) con:

```html
    <label>Profili giocatori — un URL play.fiba3x3.com per riga, oppure "Nome,punteggio" per un giocatore non su FIBA (senza punteggio = stimato dalla media)
      <textarea id="urls-giocatori" rows="3"></textarea></label>
    <p style="font-size:13px;color:#666;margin:2px 0 0">Il punteggio manuale va sulla stessa scala dei punti FIBA (tipicamente migliaia–decine di migliaia).</p>
```

- [ ] **Step 3: `classeBadge` con ramo blu**

Sostituisci la funzione `classeBadge` con (il ramo blu per il manuale-fisso va per primo;
il manuale-senza-numero `"manuale: N/A"` resta arancione come le stime):

```javascript
function classeBadge(g) {
  const st = g.fetch_status || '';
  if (st.startsWith('manuale (')) return 'blu';        // punteggio manuale fisso
  if (st.startsWith('ok: N/A') || st.startsWith('ok: media stimata')
      || st.startsWith('manuale: N/A')) return 'arancione';  // stimato / da stimare
  if (!g.fetched_at || st !== 'ok') return 'rosso';
  return g.fetched_at.slice(0, 10) === new Date().toISOString().slice(0, 10)
    ? 'verde' : 'giallo';
}
```

- [ ] **Step 4: Parsing riga in `salva-squadra` (URL vs manuale)**

Nella handler `$('#salva-squadra').onclick` (righe ~165-193), sostituisci la costruzione di
`urls`/`corpo` con il parsing per riga. Cambia da:

```javascript
  const urls = $('#urls-giocatori').value.split('\n')
    .map(u => u.trim()).filter(Boolean);
  const esistente = modificaId && squadre.find(s => s.id === modificaId);
  const corpo = {
    nome: $('#nome-squadra').value.trim(),
    giocatori: urls.map(u => {
      const vecchio = esistente && esistente.giocatori.find(g => g.url === u);
      return vecchio || {url: u, nome: '', ranking_points: null,
                         fetch_status: 'mai', fetched_at: null};
    }),
    disponibilita: griglia,
  };
```

a:

```javascript
  const righe = $('#urls-giocatori').value.split('\n')
    .map(u => u.trim()).filter(Boolean);
  const esistente = modificaId && squadre.find(s => s.id === modificaId);
  const giocatori = righe.map(riga => {
    if (riga.includes('play.fiba3x3.com/players/')) {
      // riga URL FIBA: riusa l'oggetto esistente per non perdere il fetch già fatto
      const vecchio = esistente && esistente.giocatori.find(g => g.url === riga);
      return vecchio || {url: riga, nome: '', ranking_points: null,
                         fetch_status: 'mai', fetched_at: null};
    }
    // riga manuale "Nome,punteggio": punteggio estratto solo se cifre in coda alla riga.
    // Il backend normalizza fetch_status/ranking_points; qui basta url vuoto + best-effort.
    const m = riga.match(/^(.*?)(?:\s*,\s*(\d+))?$/);
    return {url: '', nome: (m[1] || '').trim(),
            ranking_points: m[2] ? parseInt(m[2], 10) : null,
            fetch_status: 'manuale', fetched_at: null};
  });
  const corpo = {
    nome: $('#nome-squadra').value.trim(),
    giocatori,
    disponibilita: griglia,
  };
```

E aggiorna il controllo di validazione (righe ~183) da:

```javascript
    if (!corpo.nome || !urls.length) throw new Error('Servono nome e almeno un URL giocatore');
```

a:

```javascript
    if (!corpo.nome || !giocatori.length) throw new Error('Servono nome e almeno un giocatore');
```

- [ ] **Step 5: Re-serializzazione context-aware in `modifica`**

Aggiungi una funzione helper subito prima di `function modifica(id) {` e usala in `modifica`:

```javascript
function serializzaGiocatore(g) {
  if ((g.url || '').trim()) return g.url;                          // FIBA -> URL
  const st = g.fetch_status || '';
  if (st.startsWith('manuale (')) return `${g.nome},${g.ranking_points}`;  // manuale fisso
  return g.nome;   // manuale stimato / da stimare -> solo nome: continua a fluttuare
}

function modifica(id) {
  const s = squadre.find(x => x.id === id);
  modificaId = id;
  $('#titolo-form').textContent = 'Modifica: ' + s.nome;
  $('#nome-squadra').value = s.nome;
  $('#urls-giocatori').value = s.giocatori.map(serializzaGiocatore).join('\n');
  renderGriglia(s.disponibilita);
  $('#annulla-modifica').hidden = false;
}
```

- [ ] **Step 6: Verifica manuale nel browser (percorso completo + round-trip)**

Run:
```bash
cd fiba-tool
rm -rf /tmp/fiba-manuali-check
FIBA_DATA_DIR=/tmp/fiba-manuali-check FIBA_FAKE=1 python3 app.py &
sleep 2
```
Apri `http://127.0.0.1:8000`. Nella vista Squadre crea una squadra "Mista" con queste tre
righe nella casella giocatori:
```
https://play.fiba3x3.com/players/reale1
Bianchi Mario,1500
Verdi Luca
```
Verifica:
- salvataggio ok; in tabella il giocatore `Bianchi Mario` ha badge **blu** (tooltip "manuale (1500)"),
  `Verdi Luca` ha badge **arancione** (tooltip "manuale: N/A"), il terzo è rosso (mai fetchato).
- **round-trip**: clicca "Modifica" sulla squadra → la casella mostra le tre righe come
  `.../reale1`, `Bianchi Mario,1500`, `Verdi Luca` (NON `Verdi Luca,<numero>`). Salva senza
  modifiche → `Verdi Luca` resta arancione `manuale: N/A` (non diventa blu hardcoded), `Bianchi
  Mario` resta blu `manuale (1500)`.
- il promemoria di scala è visibile sotto la casella.

Poi ferma e pulisci:
```bash
lsof -ti:8000 | xargs kill; rm -rf /tmp/fiba-manuali-check
```

- [ ] **Step 7: Lo smoke test Playwright resta verde**

Run: `cd fiba-tool && python3 -m pytest tests/test_smoke.py -v`
Expected: 1 passed (le righe del test contengono `play.fiba3x3.com/players/` → percorso URL invariato)

- [ ] **Step 8: Commit**

```bash
git add fiba-tool/static/index.html
git commit -m "feat(fiba-tool): righe manuali in dashboard (parsing, badge blu, round-trip)"
```

---

## Verifica finale

1. `cd fiba-tool && python3 -m pytest tests/ -v` → tutti verdi (42 preesistenti + i nuovi)
2. Verifica manuale end-to-end (Task 3 Step 6): squadra mista URL+manuale, badge corretti, round-trip che preserva l'intento.
3. `git diff main -- copia_di_generazione_squadre.py` → vuoto (mai toccato)
4. `git log --oneline` → un commit per task
