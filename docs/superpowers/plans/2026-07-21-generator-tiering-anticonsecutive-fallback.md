# Generator: fasce, anti-consecutive, fallback N/A — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migliorare la generazione tornei di fiba-tool con tre modifiche: seeding a fasce per rango, minimizzazione delle partite consecutive nel solver, e un punteggio di fallback (media) per i giocatori senza ranking FIBA.

**Architecture:** Tre modifiche indipendenti dentro moduli esistenti. `assegna_fasce` + parametro `chiave` in `snake_draft` (generator.py); obiettivo morbido di minimizzazione consecutive con timeout+gap in `genera_calendario` (generator.py); `applica_fallback_medio` come passo finale di `_esegui_fetch` (app.py) + nuovo badge in dashboard. Nessun nuovo file, nessuna firma pubblica (CLI/API) cambiata.

**Tech Stack:** Python 3.9+ (usa `Optional`, non `str | None`), OR-Tools CP-SAT, FastAPI, pytest, pytest-playwright.

**Spec:** `docs/superpowers/specs/2026-07-21-generator-tiering-anticonsecutive-fallback-design.md`

## Global Constraints

- `copia_di_generazione_squadre.py`, `backend/`, `frontend/` NON si toccano.
- Niente retry-loop con soglia per i gironi: la formazione gironi resta deterministica (snake draft).
- Minimizzazione consecutive: obiettivo MORBIDO, mai vincolo rigido (`AddAllDifferent` resta l'unico vincolo di fattibilità → il problema è feasible esattamente quando lo era prima).
- Limite tempo solver: `300` secondi, costante `SOLVER_TIMEOUT`, override env `FIBA_SOLVER_TIMEOUT`.
- Gap relativo solver: `0.01` (1%), costante `SOLVER_GAP`, override env `FIBA_SOLVER_GAP`.
- Fallback punteggio: SOLO per giocatori con fetch riuscito e 0 punti confermati (`fetch_status` che inizia con `"ok: N/A"` o `"ok: media stimata"`); i giocatori in `"errore: ..."` non vengono MAI toccati.
- Scritture JSON sempre via `storage.save_json` (atomiche). Testi/errori in italiano.
- **Semantica del bilanciamento (importante per i test):** con le fasce, i punti reali totali per girone NON tornano quasi-uguali; ciò che si bilancia è il MIX di fasce (una testa di serie per girone, poi 2ª/3ª/4ª fascia distribuite). NON scrivere test che pretendono che lo `sbilanciamento` su punti reali crolli — resta alto in presenza di un outlier; è per costruzione così (come i gironi del Mondiale).

---

### Task 1: Fasce per rango + `snake_draft` con chiave configurabile

**Files:**
- Modify: `fiba-tool/generator.py` (aggiunge `assegna_fasce`, estende `snake_draft`, aggiorna `main()`)
- Test: `fiba-tool/tests/test_generator.py` (append)

**Interfaces:**
- Consumes: `punteggio_squadra(squadra) -> int` (esistente).
- Produces: `assegna_fasce(squadre: list[dict], num_gironi: int) -> dict[int, int]` (mappa `id(squadra) -> fascia 1..5`); `snake_draft(squadre, num_gironi, chiave=punteggio_squadra)` (nuovo terzo parametro opzionale, default invariato → i test esistenti restano validi).
- Schema squadra: `{"id": str, "nome": str, "giocatori": [...], "disponibilita": [...], ...}`.

- [ ] **Step 1: Write the failing tests** (append a `fiba-tool/tests/test_generator.py`)

```python
from generator import assegna_fasce


def test_assegna_fasce_teste_di_serie():
    # 2 gironi → le 2 squadre più forti sono fascia 5 (teste di serie)
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    squadre = [squadra(f"S{p}", [p]) for p in punti]
    fasce = assegna_fasce(squadre, 2)
    cinque = {s["nome"] for s in squadre if fasce[id(s)] == 5}
    assert cinque == {"S800", "S700"}


def test_assegna_fasce_resto_non_divisibile_per_4():
    # 2 teste di serie + 6 resto → dimensione ceil(6/4)=2 → fasce 4,4,3,3,2,2
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    squadre = [squadra(f"S{p}", [p]) for p in punti]
    fasce = assegna_fasce(squadre, 2)
    per_nome = {s["nome"]: fasce[id(s)] for s in squadre}
    assert [per_nome[f"S{p}"] for p in punti] == [5, 5, 4, 4, 3, 3, 2, 2]


def test_assegna_fasce_meno_di_4_nel_resto():
    # 2 teste di serie + 2 resto: nessuna divisione per zero, fasce valide 1..5
    squadre = [squadra(f"S{p}", [p]) for p in [500, 400, 300, 200]]
    fasce = assegna_fasce(squadre, 2)
    assert sorted(fasce.values(), reverse=True) == [5, 5, 4, 4]


def test_snake_draft_con_chiave_fasce_una_testa_di_serie_per_girone():
    # Con un outlier enorme, il seeding per fascia mette comunque
    # una sola testa di serie (fascia 5) per girone.
    punti = [26009, 7062, 4985, 3883, 3883, 3883, 3883, 3883]
    squadre = [squadra(f"S{i}", [p]) for i, p in enumerate(punti)]
    fasce = assegna_fasce(squadre, 2)
    gironi = snake_draft(squadre, 2, chiave=lambda s: fasce[id(s)])
    # ogni girone ha esattamente una fascia-5
    for g in gironi:
        assert sum(1 for s in g if fasce[id(s)] == 5) == 1
    # e le somme di fascia dei due gironi sono bilanciate (delta piccolo)
    somme_fascia = [sum(fasce[id(s)] for s in g) for g in gironi]
    assert max(somme_fascia) - min(somme_fascia) <= 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd fiba-tool && python3 -m pytest tests/test_generator.py -v -k "fasce or chiave"`
Expected: FAIL — `ImportError: cannot import name 'assegna_fasce'`

- [ ] **Step 3: Implement** (in `fiba-tool/generator.py`)

Sostituisci la funzione `snake_draft` esistente (righe ~21-30) con questa versione che aggiunge il parametro `chiave`:

```python
def snake_draft(squadre, num_gironi, chiave=punteggio_squadra):
    """Distribuzione a serpente: 1→N, N→1, 1→N… Le teste di serie (top-N per
    `chiave`) emergono dal primo giro. Euristica greedy, non un ottimo garantito.
    `chiave` di default ordina per punteggio reale; il CLI passa invece la fascia
    (vedi assegna_fasce) per un seeding insensibile agli outlier."""
    ordinate = sorted(squadre, key=chiave, reverse=True)
    gironi = [[] for _ in range(num_gironi)]
    for i, s in enumerate(ordinate):
        giro, pos = divmod(i, num_gironi)
        idx = pos if giro % 2 == 0 else num_gironi - 1 - pos
        gironi[idx].append(s)
    return gironi
```

Aggiungi `assegna_fasce` subito dopo `snake_draft`:

```python
def assegna_fasce(squadre, num_gironi):
    """Converte i punteggi reali in fasce 1-5 per RANGO (stile seeding pot, es.
    gironi del Mondiale FIFA). Insensibile agli outlier: guarda la posizione in
    classifica, non il valore assoluto — un punteggio enorme diventa "il numero 1"
    e non trascina più la somma del suo girone. Le prime num_gironi squadre sono
    fascia 5 (una testa di serie per girone); il resto si divide in 4 fasce il più
    possibile uguali per numero, con l'eventuale eccesso alle fasce più forti (ceil).
    Ritorna {id(squadra): fascia}."""
    ordinate = sorted(squadre, key=punteggio_squadra, reverse=True)
    teste_di_serie = ordinate[:num_gironi]
    resto = ordinate[num_gironi:]
    dimensione = max(1, -(-len(resto) // 4))  # ceil; max(1,…) evita /0 se resto piccolo
    fasce = {id(s): 5 for s in teste_di_serie}
    for i, s in enumerate(resto):
        fasce[id(s)] = 4 - min(i // dimensione, 3)  # 4,3,2,1 a cascata
    return fasce
```

Aggiorna `main()`: sostituisci la riga che chiama `snake_draft` (riga ~169
`gironi = snake_draft(squadre, config["num_gironi"])`) con:

```python
        # Seeding per fasce di rango: il bilanciamento gironi non usa i punti
        # reali assoluti (un outlier li distorce) ma le fasce 1-5 per rango.
        fasce = assegna_fasce(squadre, config["num_gironi"])
        gironi = snake_draft(squadre, config["num_gironi"],
                             chiave=lambda s: fasce[id(s)])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd fiba-tool && python3 -m pytest tests/test_generator.py tests/test_generator_cli.py -v`
Expected: tutti passed (i 4 nuovi + i preesistenti, incluso `test_snake_draft_pattern` che usa il default `chiave` e resta invariato)

- [ ] **Step 5: Commit**

```bash
git add fiba-tool/generator.py fiba-tool/tests/test_generator.py
git commit -m "feat(fiba-tool): seeding gironi a fasce per rango (insensibile agli outlier)"
```

---

### Task 2: Minimizzazione partite consecutive nel solver

**Files:**
- Modify: `fiba-tool/generator.py` (`genera_calendario` + due costanti modulo)
- Test: `fiba-tool/tests/test_generator.py` (append)

**Interfaces:**
- Consumes: `verifica(calendario) -> list[str]` (esistente, per contare le consecutive nei test).
- Produces: costanti modulo `SOLVER_TIMEOUT: float`, `SOLVER_GAP: float`; `genera_calendario` invariata nella firma ma ora minimizza le partite consecutive.
- `genera_calendario(squadre, gironi, num_giorni, num_slots) -> dict` (firma invariata).

- [ ] **Step 1: Write the failing tests** (append a `fiba-tool/tests/test_generator.py`)

```python
import generator


def test_costanti_solver_esistono():
    assert isinstance(generator.SOLVER_TIMEOUT, float)
    assert isinstance(generator.SOLVER_GAP, float)


def test_minimizza_consecutive_trova_zero_quando_possibile():
    # 4 squadre, 1 girone (6 partite), 3 giorni × 2 slot: K4 ha una
    # 1-fattorizzazione in 3 accoppiamenti perfetti → esiste una soluzione con
    # ZERO partite consecutive (ogni squadra gioca una volta al giorno). Un
    # solver di sola fattibilità potrebbe non trovarla; l'obiettivo deve trovarla.
    from generator import genera_calendario, verifica
    squadre = [{"id": n, "nome": n,
                "giocatori": [{"ranking_points": 100}],
                "disponibilita": [[1, 1], [1, 1], [1, 1]]}  # 3 giorni × 2 slot
               for n in ["A", "B", "C", "D"]]
    gironi = [squadre]  # unico girone con tutte e 4
    calendario = genera_calendario(squadre, gironi, num_giorni=3, num_slots=2)
    partite = [p for slots in calendario.values()
               for ps in slots.values() for p in ps]
    assert len(partite) == 6            # tutte le partite presenti
    assert verifica(calendario) == []   # zero partite consecutive
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd fiba-tool && python3 -m pytest tests/test_generator.py -v -k "solver or consecutive"`
Expected: FAIL — `AttributeError: module 'generator' has no attribute 'SOLVER_TIMEOUT'` (e il test consecutive fallisce o per l'attributo o perché senza obiettivo il solver può restituire una soluzione con consecutive)

- [ ] **Step 3: Implement** (in `fiba-tool/generator.py`)

Aggiungi le due costanti subito dopo gli import (dopo la riga `from storage import load_json, save_json`):

```python
# Parametri del solver CP-SAT per la minimizzazione delle partite consecutive.
# Costanti con override via env (stesso pattern di FIBA_PAUSE in fiba_client.py):
# i test usano timeout brevi via monkeypatch/env senza aspettare 5 minuti reali.
SOLVER_TIMEOUT = float(os.environ.get("FIBA_SOLVER_TIMEOUT", "300"))  # 5 min, tetto caso peggiore
SOLVER_GAP = float(os.environ.get("FIBA_SOLVER_GAP", "0.01"))         # 1% di gap relativo tollerato
```

Sostituisci il corpo di `genera_calendario` (righe ~66-98) con questa versione.
Le prime righe (costruzione partite, variabili, `AddAllDifferent`) sono invariate;
la parte nuova è il blocco "Minimizzazione partite consecutive" e i parametri del
solver:

```python
def genera_calendario(squadre, gironi, num_giorni, num_slots):
    from ortools.sat.python import cp_model
    per_id = {s["id"]: s for s in squadre}
    partite = []
    for gi, girone in enumerate(gironi):
        partite += [(a["id"], b["id"], gi + 1) for a, b in combinations(girone, 2)]
    model = cp_model.CpModel()
    variabili = []
    for idx, (s1, s2, _) in enumerate(partite):
        disponibili = [
            giorno * num_slots + slot
            for giorno in range(num_giorni)
            for slot in range(num_slots)
            if per_id[s1]["disponibilita"][giorno][slot]
            and per_id[s2]["disponibilita"][giorno][slot]]
        if not disponibili:
            raise ValueError(
                f"Nessuno slot comune tra {per_id[s1]['nome']} e {per_id[s2]['nome']}: "
                "le disponibilità sono troppo restrittive, servono più aperture")
        variabili.append(model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(disponibili), f"m{idx}"))
    model.AddAllDifferent(variabili)

    # Minimizzazione partite consecutive (OBIETTIVO MORBIDO, non vincolo).
    # Per ogni partita decomponiamo lo slot globale in (giorno, slot_nel_giorno)
    # con una sola uguaglianza lineare: slot_globale = giorno*num_slots + slot,
    # con 0<=slot<num_slots → è la divisione euclidea univoca, niente modulo.
    # Poi, per ogni squadra e ogni coppia delle sue partite, penalizziamo il caso
    # "stesso giorno E slot adiacenti" — stessa definizione usata da verifica().
    # AddAllDifferent resta l'unico vincolo di fattibilità: l'obiettivo sceglie
    # solo QUALE soluzione fattibile, quindi non può mai rendere il problema
    # infeasible (es. con disponibilità strette resta risolvibile, con qualche
    # consecutiva in più).
    giorno_var, slot_var = [], []
    for idx, x in enumerate(variabili):
        d = model.NewIntVar(0, num_giorni - 1, f"g{idx}")
        s = model.NewIntVar(0, num_slots - 1, f"s{idx}")
        model.Add(x == d * num_slots + s)
        giorno_var.append(d)
        slot_var.append(s)
    partite_di = defaultdict(list)
    for idx, (s1, s2, _) in enumerate(partite):
        partite_di[s1].append(idx)
        partite_di[s2].append(idx)
    penalita = []
    for indici in partite_di.values():
        for i, j in combinations(indici, 2):
            stesso_giorno = model.NewBoolVar("")
            model.Add(giorno_var[i] == giorno_var[j]).OnlyEnforceIf(stesso_giorno)
            model.Add(giorno_var[i] != giorno_var[j]).OnlyEnforceIf(stesso_giorno.Not())
            dist = model.NewIntVar(0, num_slots, "")
            model.AddAbsEquality(dist, slot_var[i] - slot_var[j])
            adiacente = model.NewBoolVar("")
            model.Add(dist == 1).OnlyEnforceIf(adiacente)
            model.Add(dist != 1).OnlyEnforceIf(adiacente.Not())
            consec = model.NewBoolVar("")
            model.AddBoolAnd([stesso_giorno, adiacente]).OnlyEnforceIf(consec)
            model.AddBoolOr([stesso_giorno.Not(), adiacente.Not()]).OnlyEnforceIf(consec.Not())
            penalita.append(consec)
    if penalita:
        model.Minimize(sum(penalita))

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = SOLVER_TIMEOUT
    solver.parameters.relative_gap_limit = SOLVER_GAP
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError("Nessuna soluzione trovata: le disponibilità sono troppo "
                         "restrittive, servono più slot o più aperture")
    calendario = {g: {s: [] for s in range(num_slots)} for g in range(num_giorni)}
    for idx, (s1, s2, gi) in enumerate(partite):
        v = solver.Value(variabili[idx])
        calendario[v // num_slots][v % num_slots].append(
            {"girone": gi, "squadre": [per_id[s1]["nome"], per_id[s2]["nome"]]})
    return calendario
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd fiba-tool && python3 -m pytest tests/test_generator.py tests/test_generator_cli.py -v`
Expected: tutti passed (incluso `test_cli_end_to_end`/`test_cli_infeasible` preesistenti, che restano validi: la fattibilità è invariata)

- [ ] **Step 5: Commit**

```bash
git add fiba-tool/generator.py fiba-tool/tests/test_generator.py
git commit -m "feat(fiba-tool): minimizza partite consecutive nel solver (timeout+gap)"
```

---

### Task 3: Fallback a media per giocatori senza ranking FIBA

**Files:**
- Modify: `fiba-tool/app.py` (`_esegui_fetch` + nuova funzione `applica_fallback_medio`)
- Test: `fiba-tool/tests/test_app.py` (append)

**Interfaces:**
- Consumes: `leggi_squadre()`, `save_json`, `SQUADRE` (esistenti in app.py).
- Produces: `applica_fallback_medio(dati: dict) -> int` (helper puro accanto a `ridimensiona`; muta `dati["squadre"]` in place, ritorna il numero di giocatori aggiornati).
- Convenzione `fetch_status`: `"ok"` = punteggio reale >0; `"ok: N/A (0 punti)"` = fetch riuscito ma 0 punti; `"ok: media stimata (N)"` = stima applicata; `"errore: ..."` = fetch fallito (mai stimato).

> **Nota di collocazione (deviazione voluta dalla spec):** la spec indicava la
> marcatura N/A in `fiba_client.py` (`parse_player_payload`). Nel codice reale però
> `fetch_status` viene deciso in `app.py` (`_esegui_fetch`), mentre
> `parse_player_payload` ritorna solo `{id, nome, ranking_points}` e non conosce le
> stringhe di stato di business. Marcare l'N/A in `app.py` (dove `fetch_status` è già
> assegnato) è più coerente e non altera il contratto di `fiba_client`. La convenzione
> di stato resta identica a quella della spec.

- [ ] **Step 1: Write the failing tests** (append a `fiba-tool/tests/test_app.py`)

```python
def test_applica_fallback_medio_pool_vuoto_non_tocca_nulla():
    import app
    dati = {"squadre": [{"giocatori": [
        {"ranking_points": 0, "fetch_status": "ok: N/A (0 punti)"}]}]}
    assert app.applica_fallback_medio(dati) == 0
    assert dati["squadre"][0]["giocatori"][0]["ranking_points"] == 0


def test_applica_fallback_medio_assegna_media_ai_na():
    import app
    dati = {"squadre": [
        {"giocatori": [
            {"ranking_points": 100, "fetch_status": "ok"},
            {"ranking_points": 300, "fetch_status": "ok"}]},
        {"giocatori": [
            {"ranking_points": 0, "fetch_status": "ok: N/A (0 punti)"}]},
    ]}
    aggiornati = app.applica_fallback_medio(dati)
    assert aggiornati == 1
    na = dati["squadre"][1]["giocatori"][0]
    assert na["ranking_points"] == 200            # media di 100 e 300
    assert na["fetch_status"] == "ok: media stimata (200)"


def test_applica_fallback_medio_non_tocca_errori_e_aggiorna_stime_vecchie():
    import app
    dati = {"squadre": [
        {"giocatori": [{"ranking_points": 400, "fetch_status": "ok"}]},
        {"giocatori": [
            {"ranking_points": 999, "fetch_status": "errore: profilo non trovato"},
            {"ranking_points": 50, "fetch_status": "ok: media stimata (50)"}]},
    ]}
    app.applica_fallback_medio(dati)
    errore = dati["squadre"][1]["giocatori"][0]
    stima = dati["squadre"][1]["giocatori"][1]
    assert errore["ranking_points"] == 999        # errore mai toccato
    assert errore["fetch_status"] == "errore: profilo non trovato"
    assert stima["ranking_points"] == 400         # stima vecchia ricalcolata sul pool
    assert stima["fetch_status"] == "ok: media stimata (400)"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd fiba-tool && python3 -m pytest tests/test_app.py -v -k fallback`
Expected: FAIL — `AttributeError: module 'app' has no attribute 'applica_fallback_medio'`

- [ ] **Step 3: Implement** (in `fiba-tool/app.py`)

Aggiungi la funzione `applica_fallback_medio` subito prima di `_esegui_fetch`
(cioè prima della riga `def _esegui_fetch(cartella, ids):`):

```python
def applica_fallback_medio(dati):
    """Passo finale del fetch: calcola la media dei ranking_points REALI (>0)
    su tutto il pool squadre e la riassegna a TUTTI i giocatori marcati N/A o
    già stimati (di qualunque squadra, anche da job precedenti). I giocatori in
    "errore:" non vengono mai toccati. Se il pool non ha ancora punteggi reali,
    non modifica nulla (i N/A restano tali finché un fetch futuro porta almeno un
    punteggio nel pool). Muta `dati` in place; ritorna il numero di aggiornati."""
    reali = [g["ranking_points"]
             for s in dati["squadre"] for g in s["giocatori"]
             if g.get("fetch_status") == "ok" and (g.get("ranking_points") or 0) > 0]
    if not reali:
        return 0
    media = round(sum(reali) / len(reali))
    aggiornati = 0
    for s in dati["squadre"]:
        for g in s["giocatori"]:
            st = g.get("fetch_status") or ""
            if st.startswith("ok: N/A") or st.startswith("ok: media stimata"):
                g["ranking_points"] = media
                g["fetch_status"] = f"ok: media stimata ({media})"
                aggiornati += 1
    return aggiornati
```

Nel loop di `_esegui_fetch`, sostituisci il ramo `if r["ok"]:` (righe ~164-166)
per marcare i 0 punti come N/A invece che come `"ok"` semplice:

```python
                for g, r in zip(squadra["giocatori"], risultati):
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

Aggiungi il passo finale in `_esegui_fetch`, subito prima della scrittura dello
status `"completato"` (prima della riga
`save_json(percorso_status, {"tipo": "fetch", "stato": "completato", ...})`):

```python
        # Passo finale: assegna il punteggio medio del pool ai giocatori N/A
        # (di qualunque squadra, anche marcati in job precedenti).
        dati = leggi_squadre()
        if applica_fallback_medio(dati):
            save_json(SQUADRE, dati)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd fiba-tool && python3 -m pytest tests/test_app.py -v`
Expected: tutti passed (i 3 nuovi + i preesistenti; `test_fetch_job_e_squadra_aggiornata` resta valido perché il fake FIBA restituisce `rankingPoints=1000` > 0, quindi `fetch_status == "ok"`)

- [ ] **Step 5: Commit**

```bash
git add fiba-tool/app.py fiba-tool/tests/test_app.py
git commit -m "feat(fiba-tool): fallback a media per giocatori senza ranking FIBA"
```

---

### Task 4: Badge arancione per punteggio stimato in dashboard

**Files:**
- Modify: `fiba-tool/static/index.html` (`classeBadge` + CSS)

**Interfaces:**
- Consumes: la convenzione `fetch_status` del Task 3 (`"ok: N/A ..."` / `"ok: media stimata ..."`).
- Produces: nessuna nuova interfaccia; solo comportamento visivo.

- [ ] **Step 1: Add the CSS color**

In `fiba-tool/static/index.html`, alla riga della definizione dei colori badge
(`.verde{background:#2e7d32}.giallo{background:#f9a825}.rosso{background:#c62828}`)
aggiungi in coda la classe arancione:

```css
.verde{background:#2e7d32}.giallo{background:#f9a825}.rosso{background:#c62828}.arancione{background:#e67e22}
```

- [ ] **Step 2: Update `classeBadge`**

Sostituisci la funzione `classeBadge` esistente con questa versione (il ramo
arancione va PRIMA degli altri: uno stato `"ok: N/A ..."`/`"ok: media stimata ..."`
non è `"ok"` puro e verrebbe altrimenti classificato rosso):

```javascript
function classeBadge(g) {
  const st = g.fetch_status || '';
  // Arancione = punteggio stimato (media del pool), non confermato da FIBA.
  if (st.startsWith('ok: N/A') || st.startsWith('ok: media stimata')) return 'arancione';
  if (!g.fetched_at || st !== 'ok') return 'rosso';
  return g.fetched_at.slice(0, 10) === new Date().toISOString().slice(0, 10)
    ? 'verde' : 'giallo';
}
```

- [ ] **Step 3: Manual verification**

Run:
```bash
cd fiba-tool
rm -rf /tmp/fiba-badge-check
FIBA_DATA_DIR=/tmp/fiba-badge-check python3 app.py &
sleep 2
# squadra con un giocatore reale e uno N/A (fetch_status impostato a mano)
SID=$(curl -s -X POST http://127.0.0.1:8000/api/squadre -H "Content-Type: application/json" \
  -d '{"nome":"T","giocatori":[{"url":"https://play.fiba3x3.com/players/x1","nome":"R","ranking_points":500,"fetch_status":"ok","fetched_at":"2026-07-21T00:00:00+00:00"},{"url":"https://play.fiba3x3.com/players/x2","nome":"Stimato","ranking_points":500,"fetch_status":"ok: media stimata (500)","fetched_at":"2026-07-21T00:00:00+00:00"}],"disponibilita":[]}' \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['id'])")
echo "creata squadra $SID"
```
Apri `http://127.0.0.1:8000` (vista Squadre): il primo giocatore ha badge verde
(reale), il secondo badge arancione (stimato). Poi:
```bash
lsof -ti:8000 | xargs kill; rm -rf /tmp/fiba-badge-check
```

- [ ] **Step 4: Verify the smoke test still passes**

Run: `cd fiba-tool && python3 -m pytest tests/test_smoke.py -v`
Expected: 1 passed (nessuna regressione UI — lo smoke test usa il fake FIBA con
`rankingPoints=1000`, quindi badge verdi, invariato)

- [ ] **Step 5: Commit**

```bash
git add fiba-tool/static/index.html
git commit -m "feat(fiba-tool): badge arancione per punteggio stimato via media"
```

---

## Verifica finale

1. `cd fiba-tool && python3 -m pytest tests/ -v` → tutti verdi (30 preesistenti + i nuovi)
2. Benchmark manuale di scala (calibra il default 300s con numeri reali):
   ```bash
   cd fiba-tool && python3 -c "
   import json, tempfile, os, time, subprocess, sys
   # 120 squadre, 20 gironi, 15 giorni × 20 slot (caso storico)
   squadre = [{'id': f's{i}', 'nome': f's{i}',
               'giocatori': [{'ranking_points': (i*37) % 5000 + 100}],
               'disponibilita': [[1]*20 for _ in range(15)]} for i in range(120)]
   d = tempfile.mkdtemp()
   json.dump({'squadre': squadre}, open(f'{d}/s.json','w'))
   json.dump({'num_gironi':20,'num_giorni':15,'num_partite_giorno':20}, open(f'{d}/c.json','w'))
   t = time.time()
   r = subprocess.run([sys.executable,'generator.py','--squadre',f'{d}/s.json',
                       '--config',f'{d}/c.json','--output',f'{d}/out'])
   print('secondi:', round(time.time()-t,1), 'exit:', r.returncode)
   print('sbilanciamento/warnings:', {k: json.load(open(f'{d}/out/calendario_finale.json'))[k] for k in ('sbilanciamento',)}, 
         len(json.load(open(f'{d}/out/calendario_finale.json'))['warnings']), 'warning')
   "
   ```
   Atteso: completa entro il tetto di 300s (tipicamente molto meno grazie al gap 1%),
   `exit: 0`. Se sistematicamente troppo lento, valutare l'abbassamento del default o
   un gap più permissivo — ma NON in questo piano, è una calibrazione separata.
3. `git diff main -- copia_di_generazione_squadre.py` → vuoto (mai toccato)
4. `git log --oneline` → un commit per task
