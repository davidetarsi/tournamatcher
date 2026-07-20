# FIBA Tool — dashboard locale con punteggi reali FIBA 3x3

**Data:** 2026-07-20
**Stato:** approvato in brainstorming, in attesa di piano di implementazione
**Stima:** ≈3 giorni di lavoro effettivo (2.5–3.5)

## Obiettivo

Sostituire la "forza" fittizia 1–5 dello script di generazione calendario con i ranking
points reali FIBA 3x3, presi dai profili giocatore su play.fiba3x3.com. Attorno a questo,
una mini-app locale (dashboard nel browser + backend Python) per: caricare le squadre,
fetchare i punti, lanciare la generazione del calendario e consultare i risultati.

## Decisioni chiave

| Decisione | Scelta |
|---|---|
| Identificazione giocatori | URL del profilo play.fiba3x3.com incollato a mano (zero ambiguità) |
| Punteggio squadra | Somma dei ranking points dei migliori 3 giocatori (metodo di seeding ufficiale FIBA) |
| Posizionamento | Standalone, separato dalla piattaforma esistente (`backend/`/`frontend/` non si toccano) |
| Deploy | Tutto locale (`python app.py` → `http://localhost:8000`); deploy futuro possibile ma fuori scope |
| Disponibilità squadre | Griglia giorni × slot compilata a mano nella dashboard |
| Script originale | `copia_di_generazione_squadre.py` resta intatto come versione "dati random" |

## Architettura

```
fiba-tool/
├── app.py              # FastAPI: serve la dashboard + API
├── fiba_client.py      # Fetch dati FIBA (riusabile anche fuori dal tool)
├── generator.py        # Generazione gironi + calendario, eseguibile standalone
├── static/
│   └── index.html      # Dashboard: HTML + JS vanilla, un solo file, zero build
└── data/
    ├── squadre.json    # Squadre, giocatori, punti, disponibilità
    ├── config.json     # Parametri torneo (num_gironi, num_giorni, num_partite_giorno)
    └── output/         # Una cartella per esecuzione: 2026-07-20_1530/
```

I tre moduli sono indipendenti: `fiba_client.py` non sa nulla di calendari, `generator.py`
non sa nulla di FIBA (riceve squadre con un punteggio numerico). `fiba_client.py` è
pensato per essere riusato in futuro dalla piattaforma grande senza modifiche.

### Flusso dati

```
Dashboard → aggiungi squadra (nome + URL profili + griglia disponibilità) → squadre.json
Dashboard → "Fetch FIBA"  → job in background → fiba_client → punti in squadre.json
Dashboard → "Genera"      → generator.py in subprocess → output/<run>/ → risultati
```

## Storage (`squadre.json`, `config.json`)

- **Scrittura atomica**: file temporaneo + `os.replace()`. Il file non può mai trovarsi
  troncato o corrotto, nemmeno se aperto a mano nel momento sbagliato.
- **`threading.Lock` in-process** per serializzare le scritture tra richieste concorrenti.
  Niente lock a livello OS: il server è un singolo processo; caso peggiore con due tab,
  vince l'ultimo salvataggio (accettabile per un tool mono-utente).
- Schema giocatore in `squadre.json`:

```json
{
  "url": "https://play.fiba3x3.com/players/abc123",
  "nome": "Mario Rossi",
  "ranking_points": 45230,
  "fetch_status": "ok",
  "fetched_at": "2026-07-20T15:30:00"
}
```

## Fetch FIBA (`fiba_client.py`)

- **Via primaria: endpoint JSON interni** del sito (verificato: le pagine sono
  server-rendered ma i dati giocatore viaggiano via XHR, riferimento `api/ws` nel markup).
  Il parsing HTML è un'eventualità da valutare durante l'investigazione iniziale, non un
  fallback promesso.
- **Prima attività del progetto**: ~mezza giornata di reverse-engineering degli endpoint
  con i DevTools. Le risposte JSON reali vengono salvate come fixture per i test.
- **`requests.Session`** riusata (keep-alive) con header da browser realistici.
  Verificato: il sito risponde **403 ai client non-browser**; con User-Agent da browser
  passa. Filtro anti-bot leggero, oggi aggirabile con gli header giusti — è il principale
  rischio residuo del progetto.
- **Cortesia**: una richiesta alla volta, ~1s di pausa tra giocatori, timeout 10s, un solo
  retry. Fetch completo di ~120 squadre ≈ qualche minuto → gira come job in background.
- **Per giocatore, mai tutto-o-niente**: ogni giocatore ha il suo `fetch_status` e
  `fetched_at`; un profilo irraggiungibile non scarta i punti degli altri. In caso di
  errore restano i punti dell'ultimo fetch buono.
- API del modulo: `fetch_player(url)`, `fetch_team_players(urls)` — quest'ultima
  restituisce risultati per giocatore e non solleva mai un'eccezione complessiva.

## Generatore (`generator.py`)

- **Input reale**: `squadre.json` + `config.json`. Il vincolo di capacità
  (`giorni × slot × 2 == num_squadre × (num_squadre/num_gironi − 1)`) è verificato subito;
  se non torna, il messaggio elenca le combinazioni valide (riuso di `calcola_combinazioni`).
- **Punteggio squadra** = somma dei migliori 3 giocatori.
- **Distribuzione gironi: snake draft deterministico.** Squadre ordinate per punteggio
  decrescente, distribuite 1→N, N→1, 1→N… Le teste di serie emergono dal primo giro
  (top-N squadre, una per girone). Sostituisce il retry loop random con soglia: O(N log N),
  nessun ciclo, nessun crash possibile. Nota: è un'euristica greedy, non un ottimo
  garantito — lo **sbilanciamento ottenuto** (differenza max-min tra gironi) viene
  riportato nel risultato a titolo informativo, non come vincolo.
- **CP-SAT invariato**: codifica slot `giorno × num_slots + slot`, domini dalle
  disponibilità incrociate, `AddAllDifferent`. La verifica finale
  (`verifica_calendario_avanzato`) è portata dentro così com'è, report incluso.
- **Esecuzione in subprocess** (mai in-process: il GIL affamerebbe il server durante il
  solve). `python generator.py --input … --output …`, lanciato da `app.py` con
  `subprocess.Popen`.
- **Status per-job**: ogni esecuzione ha la sua cartella `output/<timestamp>/` con dentro
  `status.json` (fase, avanzamento, esito, errori), calendario, report e parametri usati.
  Nessun file di stato globale: esecuzioni concorrenti non si pestano.
- **Errori del solver in linguaggio umano**: infeasible → "le disponibilità sono troppo
  restrittive, servono più slot o più aperture", scritto in `status.json`.

## Dashboard e API

Tre viste in `index.html`:

1. **Squadre** — elenco con punteggio, badge per giocatore (verde = fetchato oggi,
   giallo = dato vecchio, rosso = mai riuscito), marcatura "dati incompleti" (< 3
   giocatori con punti). Form: nome, URL giocatori, griglia disponibilità. Bottoni
   "Aggiorna punti squadra" / "Aggiorna tutti".
2. **Parametri e generazione** — campi con validazione live del vincolo di capacità e
   suggerimento delle combinazioni valide. "Genera" attivo solo a vincolo soddisfatto.
   Squadre con dati incompleti → avviso, ma non blocca (un giocatore nuovo può avere
   legittimamente zero punti).
3. **Risultati** — elenco esecuzioni; per ciascuna: gironi con punteggi e sbilanciamento,
   calendario per giorno/slot, report di verifica, download dei file.

**Disponibilità e cambio parametri (opt-in rigoroso).** La griglia si disegna dai
parametri in `config.json`. Se i parametri crescono (es. da 2 a 3 giorni), i nuovi slot
nascono **non disponibili** (`false`): assumere la disponibilità è un anti-pattern da
no-show. Le squadre coinvolte passano in stato "da riconfermare" con avviso ben visibile;
finché l'admin non aggiorna le griglie, il solver semplicemente non può usare quegli slot
per quelle squadre. Slot rimossi: si ignorano.

**Endpoint** (tutti sotto `/api`, JSON):

| Endpoint | Cosa fa |
|---|---|
| `GET/POST/PUT/DELETE /api/squadre` | CRUD squadre (scrittura atomica + lock) |
| `GET/PUT /api/config` | Parametri torneo |
| `POST /api/fetch` (tutte o `?squadra=`) | Lancia job di fetch → `job_id` |
| `POST /api/genera` | Lancia `generator.py` in subprocess → `job_id` |
| `GET /api/jobs/{id}/status` | Polling dal `status.json` per-job |
| `GET /api/runs`, `GET /api/runs/{id}/…` | Elenco esecuzioni, calendario, report |

Il JS fa polling di `/api/jobs/{id}/status` ogni 2s fino a fine job: nessuna richiesta
HTTP lunga, nessun timeout browser.

## Test

- **Unit test** su ciò che ha logica: snake draft (distribuzione, teste di serie,
  calcolo sbilanciamento), validazione capacità, scrittura atomica dello storage.
- **`fiba_client`** testato contro fixture JSON registrate durante l'investigazione
  iniziale: i test non toccano la rete e documentano il formato degli endpoint FIBA.
- **Un singolo smoke test Playwright** del percorso felice: aggiungi squadra → fetch (con
  FIBA finto servito dalle fixture) → genera → polling → il calendario appare. Un file,
  non una suite: copre la parte asincrona fragile del vanilla JS senza introdurre
  TypeScript o bundler.

## Rischi dichiarati

1. **FIBA cambia il sito / inasprisce l'anti-bot** (oggi: 403 su UA non-browser, aggirato
   con header realistici). Mitigazione: i punti già fetchati restano in `squadre.json`;
   tutto il resto del tool funziona anche a fetch rotto.
2. **Endpoint interni non documentati** = nessun contratto di stabilità. Mitigazione:
   fixture salvate + modulo isolato da aggiornare in un punto solo.
3. **Giocatori senza punti** (nuovi, profilo vuoto): gestiti come "dati incompleti",
   avviso ma nessun blocco.

## Stima per componente

| Componente | Tempo | Difficoltà |
|---|---|---|
| Investigazione endpoint FIBA + `fiba_client.py` | 0.5–1 giorno | Media-alta (unico pezzo rischioso) |
| `generator.py` (snake draft, subprocess, status per-job) | ~0.5 giorno | Bassa |
| `app.py` + storage | ~0.5 giorno | Bassa |
| Dashboard | ~1 giorno | Bassa-media |
| Smoke test Playwright | ~0.5 giorno | Bassa |
| **Totale** | **≈3 giorni (2.5–3.5)** | |

## Fuori scope (esplicito)

- Deploy (Cloudflare Pages + Railway possibile in futuro: la dashboard è statica e il
  backend è FastAPI, ma non ora).
- Integrazione con la piattaforma esistente (solo riuso futuro di `fiba_client.py`).
- Ricerca giocatori per nome, disambiguazione, autocomplete.
- Passata di scambi migliorativi post-snake-draft (YAGNI finché lo sbilanciamento
  riportato non risulta insoddisfacente nella pratica).
