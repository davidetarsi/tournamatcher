# FIBA Tool

Strumento locale per generare **gironi e calendari di tornei di basket 3x3**
usando i punteggi ranking reali dei giocatori presi da
[play.fiba3x3.com](https://play.fiba3x3.com), con una dashboard nel browser.

Nasce come evoluzione di uno script a riga di comando (`copia_di_generazione_squadre.py`,
che usava una "forza" fittizia 1–5): qui le squadre vengono seminate nei gironi in base
ai punti FIBA reali dei loro giocatori, e il calendario è prodotto con un solver a vincoli.

Gira **tutto in locale**: nessun account, nessun deploy, nessun database — i dati stanno
in file JSON sul tuo computer.

---

## Cosa fa

- **Carica le squadre** da una dashboard: per ogni squadra incolli gli URL dei profili
  FIBA dei giocatori (oppure inserisci punteggi a mano — vedi sotto), e spunti la griglia
  di disponibilità (in quali giorni/slot la squadra può giocare).
- **Pesca i punteggi reali** dei giocatori da FIBA con un job in background. Il punteggio
  squadra è la somma dei ranking points dei suoi 3 giocatori migliori (criterio di seeding
  ufficiale FIBA).
- **Forma i gironi bilanciati** con un *seeding a fasce per rango* (stile "pot" del Mondiale):
  le squadre più forti diventano teste di serie, una per girone, e le altre si distribuiscono
  in fasce di forza — un metodo insensibile agli outlier di punteggio.
- **Genera il calendario** con il solver **OR-Tools CP-SAT**: ogni partita ottiene uno slot,
  rispettando le disponibilità, senza sovrapposizioni, e **minimizzando le partite consecutive**
  della stessa squadra.
- **Mostra i risultati**: gironi, calendario per giorno/slot, e un report scaricabile.

### Punteggi manuali (giocatori non su FIBA)

Non tutti i giocatori sono registrati su FIBA. Nella casella dei profili puoi mescolare,
riga per riga:

- un **URL FIBA** (`https://play.fiba3x3.com/players/<id>`) → il punteggio viene pescato online;
- una riga **manuale** `Nome,punteggio` (es. `Mario Rossi,15000`) → punteggio inserito a mano;
- una riga **manuale senza punteggio** `Nome` → il giocatore riceve automaticamente la
  **media** dei punteggi noti nel torneo (stima).

I badge colorati accanto a ogni giocatore indicano la provenienza del punteggio:
🟢 verde = reale da FIBA · 🔵 blu = inserito a mano · 🟠 arancione = stimato dalla media ·
🔴 rosso = mancante o errore di fetch.

> Il punteggio manuale va inserito **sulla stessa scala** dei punti FIBA (tipicamente
> migliaia–decine di migliaia), altrimenti il giocatore risulterebbe molto più debole del reale.

---

## Come è strutturato

Tutto vive nella cartella `fiba-tool/`. Tre moduli Python indipendenti, orchestrati da un
server FastAPI che serve anche la dashboard:

```
fiba-tool/
├── app.py            # server FastAPI: serve la dashboard + le API REST (CRUD squadre,
│                     #   config, job di fetch/generazione, stato job, risultati)
├── generator.py      # motore: punteggio squadra, fasce, snake draft, solver CP-SAT del
│                     #   calendario, verifica. Eseguibile anche standalone via CLI.
├── fiba_client.py    # client per gli endpoint (non ufficiali) di play.fiba3x3.com
├── storage.py        # lettura/scrittura JSON atomica (temp file + os.replace)
├── static/
│   └── index.html    # dashboard: un unico file HTML + JS vanilla (nessun build step)
├── ENDPOINTS.md      # documentazione degli endpoint FIBA usati (reverse-engineered)
├── requirements.txt
├── data/             # (creata al primo avvio, non versionata) squadre.json, config.json,
│                     #   e output/<timestamp>/ per ogni generazione
└── tests/            # 50 test (pytest) + 1 smoke test end-to-end (Playwright)
```

**Flusso dei dati:**

```
Dashboard ──(aggiungi squadra)──▶ data/squadre.json
Dashboard ──(Aggiorna punti)────▶ fiba_client → punti scritti in squadre.json
Dashboard ──(Genera calendario)─▶ generator.py (subprocess) → data/output/<run>/
```

I moduli sono disaccoppiati: `fiba_client` non sa nulla di calendari, `generator` non sa
nulla di FIBA (riceve solo squadre con un numero). Questo rende `fiba_client` riutilizzabile
e ogni pezzo testabile in isolamento.

---

## Requisiti

- **Python 3.9 o superiore**
- Le dipendenze in `requirements.txt` (la più pesante è `ortools`, il solver di Google).

`pytest`, `pytest-playwright` e `httpx` servono solo per eseguire i test; per usare il tool
bastano `fastapi`, `uvicorn`, `requests`, `ortools`.

---

## Installazione e avvio

```bash
# 1. clona il repository e entra nella cartella del tool
git clone <URL-del-repository>
cd <repository>/fiba-tool

# 2. (consigliato) crea un ambiente virtuale
python3 -m venv .venv
source .venv/bin/activate        # su Windows: .venv\Scripts\activate

# 3. installa le dipendenze
pip install -r requirements.txt

# 4. avvia il server
python3 app.py
```

Poi apri **http://127.0.0.1:8000** nel browser. Al primo avvio la cartella `data/` viene
creata vuota: parti da una dashboard senza squadre.

Per fermare il server: `Ctrl+C` nel terminale.

---

## Come si usa (flusso tipico)

1. **Parametri** (scheda *Parametri e generazione*): imposta numero di gironi, giorni e
   partite al giorno. La dashboard valida al volo che i numeri siano coerenti con il numero
   di squadre e ti suggerisce le combinazioni valide.
2. **Squadre** (scheda *Squadre*): per ogni squadra inserisci nome, i profili dei giocatori
   (URL FIBA e/o righe manuali) e spunta la griglia di disponibilità.
3. **Aggiorna punti**: clicca *Aggiorna punti di tutte le squadre* per pescare i ranking da
   FIBA (job in background con barra di avanzamento). I giocatori senza punteggio reale
   ricevono la stima a media.
4. **Genera calendario**: attivo solo quando i parametri sono validi. La generazione gira in
   un processo separato (il solver può impegnare la CPU) e i risultati compaiono nella scheda
   *Risultati*, con gironi, calendario e report scaricabile.

> **Nota FIBA:** il tool interroga endpoint *non ufficiali* di play.fiba3x3.com (vedi
> `ENDPOINTS.md`). Non essendo un'API pubblica con contratto di stabilità, se FIBA cambia il
> sito il fetch potrebbe rompersi; in quel caso i punteggi già salvati restano, e si aggiorna
> `fiba_client.py`. Il fetch è volutamente educato (una richiesta alla volta, con pausa).

### Uso da riga di comando (senza dashboard)

Il generatore è eseguibile anche da solo, leggendo i JSON prodotti dalla dashboard:

```bash
python3 generator.py --squadre data/squadre.json --config data/config.json --output data/output/manuale
```

---

## Test

```bash
cd fiba-tool
python3 -m pytest tests/ -v
```

Sono 50 test (logica di generazione, client FIBA, storage, API) più uno **smoke test
end-to-end** con Playwright che guida la dashboard in un browser reale. Per quest'ultimo
serve installare il browser una volta:

```bash
python3 -m playwright install chromium
```

---

## Licenza

Distribuito con la **PolyForm Noncommercial License 1.0.0**, come tutto il repository:
uso, modifica e condivisione consentiti solo per **scopi non commerciali**. Per un uso
commerciale serve un accordo scritto con l'autore. Termini completi nel file
[`LICENSE`](../LICENSE) alla radice del repository.
