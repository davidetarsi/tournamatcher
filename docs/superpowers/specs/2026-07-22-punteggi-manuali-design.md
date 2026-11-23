# Punteggi manuali per giocatori non su FIBA

**Data:** 2026-07-22
**Stato:** approvato in brainstorming, in attesa di piano di implementazione
**Branch:** feature/fiba-tool (continua sullo stesso branch)
**Spec precedenti:** [2026-07-20-fiba-tool-design.md](2026-07-20-fiba-tool-design.md),
[2026-07-21-generator-tiering-anticonsecutive-fallback-design.md](2026-07-21-generator-tiering-anticonsecutive-fallback-design.md)

## Contesto

Oggi la casella "URL profili giocatori" accetta solo link a profili play.fiba3x3.com.
Una riga che non è un URL valido viene trattata come URL rotto: il giocatore finisce
in `fetch_status = "errore: URL profilo non riconosciuto"`, resta a 0 punti, e **non**
riceve nemmeno il fallback a media (che copre solo i giocatori "N/A" con fetch riuscito).
Risultato: la squadra viene penalizzata.

Molte squadre reali hanno però giocatori non registrati su FIBA. L'obiettivo è rendere
il tool utilizzabile per queste squadre permettendo di **mescolare, nella stessa casella
e nella stessa squadra, righe-URL (fetch da FIBA) e righe manuali** con un punteggio
inserito a mano. Il sistema non deve mai rompersi (già garantito: il client non solleva
mai eccezioni complessive) e deve trattare i punteggi manuali come dati di prima classe.

## Decisioni chiave

| Decisione | Scelta |
|---|---|
| Granularità | Per-giocatore: URL e righe manuali si mescolano nella stessa squadra |
| Formato riga manuale | `nome,punteggio` con punteggio **opzionale** |
| Riga senza numero (o numero non valido) | Trattata come "stimalo": riceve la media del pool (come i giocatori N/A) |
| Punteggio manuale nella media del pool | **Sì**: conta come un dato reale, insieme ai punti FIBA |
| Badge dashboard | **Blu** per manuale-con-numero; arancione per manuale-senza-numero (stimato) |
| Dove si fa il parsing | Ibrido (approccio C): split URL/manuale nel JS, validazione punteggio + logica fetch/media nel backend testato |

## 1. Riconoscimento righe e schema

Nella casella di testo, ogni riga viene classificata al salvataggio della squadra:
- contiene la sottostringa `play.fiba3x3.com/players/` → **riga URL** (comportamento
  attuale: fetch da FIBA);
- altrimenti → **riga manuale**, interpretata come `nome,punteggio` (punteggio opzionale).

Lo schema `giocatori` non cambia forma (`{url, nome, ranking_points, fetch_status,
fetched_at}`); cambia solo la convenzione di `fetch_status`, estendendo quella esistente
(`"ok"` / `"ok: N/A (0 punti)"` / `"ok: media stimata (N)"` / `"errore: ..."`):

- `"manuale (N)"` — punteggio inserito a mano, `N` intero **> 0**. `ranking_points = N`,
  `url = ""`. Badge **blu**.
- `"manuale: N/A"` — riga manuale **senza** numero valido (assente, non intero, ≤ 0).
  `ranking_points = None`, `url = ""`. Il passo finale del fetch lo trasforma in
  `"ok: media stimata (N)"` (badge arancione), esattamente come un giocatore N/A.

Un giocatore manuale ha `url` vuoto e viene mostrato in dashboard col suo `nome`.

### Parser (funzione pura, backend, testabile)

Al salvataggio (`POST`/`PUT /api/squadre`), il backend normalizza/valida ogni giocatore
manuale ricevuto dal frontend tramite una funzione pura:

```python
def normalizza_giocatore_manuale(nome, punteggio_raw):
    """Ritorna (ranking_points|None, fetch_status). punteggio_raw è il punteggio
    numerico estratto dalla riga (gruppo 2 della regex del frontend, o None se assente).
    Un punteggio valido è un intero > 0; qualunque altra cosa (assente, non numerico,
    ≤ 0) → None e stato N/A (verrà stimato). Difensiva: valida a prescindere da cosa
    manda il JS."""
```

Regole:
- punteggio intero > 0 → `(N, "manuale (N)")`
- assente / non intero / ≤ 0 → `(None, "manuale: N/A")`

Il frontend fa lo split riga→(nome, punteggio_raw) e costruisce l'oggetto giocatore con
`url = ""`. **Il discriminatore univoco lato backend è l'URL vuoto**: un giocatore con
`url` vuoto/assente è manuale (i giocatori-URL hanno sempre un `url` non vuoto). Al
salvataggio (`POST`/`PUT /api/squadre`), il backend applica `normalizza_giocatore_manuale`
a ogni giocatore con `url` vuoto, così `ranking_points` e `fetch_status` finiscono sempre
puliti e coerenti (int > 0 → `"manuale (N)"`; altrimenti None → `"manuale: N/A"`)
indipendentemente da cosa manda il JS.

## 2. Fetch e media

**Il fetch salta i giocatori manuali.** In `_esegui_fetch`, per ogni squadra:
- i giocatori il cui `fetch_status` inizia con `"manuale"` vengono **saltati**: non
  interrogati su FIBA, non marcati `errore`, punteggio **non sovrascritto**. Così un
  punteggio manuale con numero resta stabile anche rilanciando "Aggiorna punti".
- le righe-URL della stessa squadra vengono fetchate normalmente.

Questo risolve anche il bug originale: una riga non-URL non diventa più `errore`.

**La media del pool** (`applica_fallback_medio`, passo finale di ogni fetch) cambia in
due punti:
- **cosa entra nella media**: i punteggi "reali noti" ora includono sia i FIBA reali
  (`fetch_status == "ok"`, punti > 0) sia i manuali con numero (`fetch_status` inizia con
  `"manuale"`, punti > 0).
- **cosa riceve la media**: come oggi tutti i `"ok: N/A"` e `"ok: media stimata"`, più i
  manuali-senza-numero (`"manuale: N/A"`), che diventano `"ok: media stimata (N)"`. Se il
  pool non ha ancora alcun punteggio noto (né FIBA né manuale), restano in attesa.

**Scala dei numeri (promemoria in dashboard).** I punti FIBA vanno da poche centinaia a
centinaia di migliaia. Un punteggio manuale deve stare sulla **stessa scala** per dare un
seeding sensato (il sistema lavora sul rango, quindi un numero fuori scala non rompe nulla
ma colloca il giocatore in fondo alla classifica). Nessun vincolo rigido; la dashboard
mostra accanto alla casella un promemoria: *"il punteggio manuale va sulla stessa scala dei
punti FIBA (tipicamente migliaia–decine di migliaia)"*.

## 3. Dashboard

- **Parsing riga** (JS, in `salva-squadra`): ogni riga della textarea → se contiene
  `play.fiba3x3.com/players/` costruisce un giocatore-URL (come oggi); altrimenti usa
  un'espressione regolare per estrarre in modo sicuro l'eventuale punteggio numerico ancorato
  alla FINE della riga: `/^(.*?)(?:\s*,\s*(\d+))?$/`. Il gruppo 1 diventa il `nome`, il gruppo
  2 (se presente) diventa il `punteggio_raw`. Costruisce poi un giocatore manuale (`url = ""`)
  con un marcatore provvisorio, che il backend normalizzerà al salvataggio via
  `normalizza_giocatore_manuale` (rete di sicurezza: il punteggio finisce comunque validato
  a int > 0 o None).
- **Re-serializzazione in modifica (context-aware, preserva l'intento).** Quando si riapre
  una squadra in modifica, il popolamento della textarea deve preservare l'intento originale,
  non il valore momentaneo:
  - giocatore con `url` non vuoto → ri-serializzato come il suo **URL** (giocatore FIBA, anche
    se attualmente stimato: ha un URL, quindi resta URL e verrà rifetchato);
  - giocatore con `url` vuoto e `fetch_status` che inizia con `"manuale ("` (punteggio fisso
    inserito a mano) → ri-serializzato come `"nome,punteggio"`;
  - giocatore con `url` vuoto e `fetch_status` `"manuale: N/A"` **o** `"ok: media stimata (N)"`
    (intento originale: "stimalo") → ri-serializzato come **solo `"nome"`**, omettendo il
    punteggio stimato momentaneo, così al salvataggio successivo torna `"manuale: N/A"` e
    continua a fluttuare con la media del pool.

  Senza questa distinzione, un giocatore salvato "da stimare" verrebbe silenziosamente
  congelato al valore stimato corrente la prima volta che si riapre e si risalva la squadra
  (per un motivo qualsiasi, es. aggiungere un altro giocatore), perdendo l'intento dinamico.
- **Badge** (`classeBadge`): nuovo ramo **blu** per `fetch_status` che inizia con
  `"manuale"` (con numero). I manuali-senza-numero diventano `"ok: media stimata"` → restano
  arancioni. Ordine dei rami: blu prima del controllo rosso (come già fatto per l'arancione).
- **CSS**: nuova classe `.blu`.
- **Promemoria di scala**: testo statico accanto alla casella URL/manuale.

## Cosa NON cambia

- Forma dello schema `giocatori`, API (firme invariate), formato `squadre.json`/`config.json`.
- `punteggio_squadra` (somma migliori 3): un manuale con numero vi contribuisce come
  qualunque altro punteggio.
- Generatore (fasce, CP-SAT), `copia_di_generazione_squadre.py` (mai toccato).
- Scritture atomiche, stato per-job, messaggi in italiano.

## Testing

**Unit (backend):**
- `normalizza_giocatore_manuale`: `"1500"` → `(1500, "manuale (1500)")`; assente/`""` →
  `(None, "manuale: N/A")`; `"abc"` / `"-5"` / `"0"` → `(None, "manuale: N/A")`.
- regex di parsing riga (se la si testa anche in isolamento, es. portata in una piccola
  utility condivisa): `"Mario Rossi,1500"` → (`"Mario Rossi"`, `"1500"`);
  `"Rossi, Mario"` → (`"Rossi, Mario"`, assente); `"Rossi, Mario, 1500"` →
  (`"Rossi, Mario"`, `"1500"`); `"Team USA 2024"` → (`"Team USA 2024"`, assente).
- riconoscimento URL vs manuale (una riga con `play.fiba3x3.com/players/` non è manuale).
- `_esegui_fetch` salta i manuali: squadra con un manuale + un URL → il manuale conserva
  `fetch_status`/punteggio (non `errore`, non fetchato), l'URL viene fetchato (via mock).
- `applica_fallback_medio`: un manuale-con-numero entra nella media insieme ai FIBA reali;
  un manuale-senza-numero riceve la media; valore calcolato corretto.
- stabilità: un secondo fetch non altera un manuale-con-numero.

**Verifica UI (controller, browser reale):** squadra con tre righe — un URL FIBA, un
`Nome,1500`, un `Nome` senza numero — mostra badge verde/arancione (a seconda del fetch),
blu, arancione (stimato). Promemoria di scala presente.

**Verifica round-trip (controller, browser reale) — preservazione dell'intento:** salvare
un giocatore manuale-senza-numero (che diventa `"ok: media stimata (N)"`), riaprire la
squadra in modifica e risalvarla senza toccare quel giocatore → il giocatore resta stimato
(`"manuale: N/A"` → rifluttua), NON diventa `"manuale (N)"` hardcoded. Verificabile anche
lato dato: dopo il ciclo modifica→salva, il suo `fetch_status` non inizia con `"manuale ("`.
Viceversa, un manuale-con-numero (`"manuale (1500)"`) risalvato resta a 1500.

**Smoke test Playwright esistente:** resta verde (nessuna regressione sul percorso felice).

## Rischi

1. **Punteggi manuali fuori scala** → seeding poco sensato. Mitigazione: promemoria in
   dashboard; il sistema è rank-based, quindi non si rompe, al più colloca male il giocatore.
2. **Parsing nel JS meno testato** del backend. Mitigazione: la validazione del punteggio
   (la parte che può sbagliare i numeri) è una funzione pura Python testata; il JS fa solo
   lo split, coperto dallo smoke test e dalla verifica UI manuale.
3. **Ambiguità virgole nel nome** (es. "Rossi, Mario"): risolto alla radice dalla regex
   nel JS. La virgola separa il punteggio SOLO se si trova alla fine della riga ed è seguita
   esclusivamente da cifre numeriche (es. "Rossi, Mario, 1500" → Nome: "Rossi, Mario", Punti:
   1500). In tutti gli altri casi — inclusa la presenza di spazi e altre parole dopo la
   virgola — l'intera riga viene preservata integralmente come nome del giocatore. Il backend
   `normalizza_giocatore_manuale` resta comunque la rete di sicurezza finale.
