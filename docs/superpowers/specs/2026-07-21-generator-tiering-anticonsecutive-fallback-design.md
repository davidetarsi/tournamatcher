# Generator: fasce per rango, minimizzazione partite consecutive, fallback punteggi N/A

**Data:** 2026-07-21
**Stato:** approvato in brainstorming, in attesa di piano di implementazione
**Branch:** feature/fiba-tool (continua sullo stesso branch dei 10 task precedenti)
**Spec precedente:** [2026-07-20-fiba-tool-design.md](2026-07-20-fiba-tool-design.md)

## Contesto

Dopo la prima esecuzione reale del tool (torneo da 8 squadre, 2 gironi, 1 giorno,
12 slot), sono emersi tre limiti — tutti pre-esistenti allo script originale o
inerenti alle scelte di design iniziali, nessuno un bug di regressione:

1. **Gironi sbilanciati per outlier di punteggio.** Lo `snake_draft` distribuisce
   le squadre ordinandole per punteggio reale assoluto (somma migliori 3
   giocatori). Con i punti FIBA reali il range è enorme (una squadra a 26009 punti
   contro altre a 3883): un singolo outlier trascina il proprio girone, producendo
   uno sbilanciamento di 18604 punti. Lo snake draft non può spezzare una squadra
   tra due gironi, quindi lavorare sul valore assoluto è la causa.
2. **Partite consecutive per la stessa squadra.** Il modello CP-SAT attuale è di
   pura soddisfacibilità (`AddAllDifferent` + stop alla prima soluzione fattibile).
   Nulla scoraggia due partite della stessa squadra in slot adiacenti: `verifica()`
   le segnala solo a posteriori, non le evita. Stesso comportamento nello script
   originale `copia_di_generazione_squadre.py`.
3. **Giocatori senza punteggio FIBA.** Un giocatore che esiste su FIBA ma non è in
   classifica restituisce `rankingPoints: 0`, che penalizza la squadra come se il
   giocatore non contasse nulla.

Questa iterazione risolve tutti e tre alla radice, mantenendo il vincolo di
progetto già stabilito: **niente retry-loop con soglia** (rischio di non
convergenza con punteggi ad ampio range), tempo di generazione contenuto anche su
tornei grandi.

## Vincolo di velocità (requisito guida)

Benchmark storico dello script originale: ~2 minuti per 120 squadre / 20 gironi
con `forza` 1-5 nativa. Obiettivo: mantenere tempi simili anche con la
minimizzazione attiva. Tetto massimo accettabile nel caso peggiore (torneo grande):
**5 minuti**. I tornei piccoli (16-32 squadre) devono restare nell'ordine dei
secondi — garantito dalla tolleranza di gap relativo (vedi sezione 2).

## Decisioni chiave

| Decisione | Scelta |
|---|---|
| Bilanciamento gironi | Discretizzazione per rango in 5 fasce (stile seeding pot FIFA), poi snake draft esistente sulle fasce |
| Resto fasce non divisibile per 4 | La/le squadra/e in eccesso vanno alle fasce più forti (ceil) |
| Minimizzazione consecutive | Obiettivo morbido nel CP-SAT (mai vincolo rigido → mai infeasible) |
| Limite tempo solver | 300s (5 min), costante con override env `FIBA_SOLVER_TIMEOUT` |
| Gap relativo solver | 1% (0.01), costante con override env `FIBA_SOLVER_GAP` |
| Fallback punteggi N/A | Solo per fetch riuscito con 0 punti confermati; media del pool, riassegnata come passo finale di ogni job di fetch |
| Fetch fallito (errore) | NON riceve fallback: resta dato mancante, badge rosso |
| Configurabilità | Costanti nel codice + override env per i test (stesso pattern di `FIBA_PAUSE`) |

## 1. Fasce per rango (`generator.py`)

Nuova funzione pura:

```python
def assegna_fasce(squadre, num_gironi):
    """Converte punteggi reali in fasce 1-5 per rango (stile seeding pot,
    es. gironi Mondiale FIFA). Insensibile agli outlier: lavora sulla
    posizione in classifica, non sul valore assoluto — un singolo punteggio
    enorme diventa "il numero 1", non trascina la somma del suo girone.
    Ritorna un dict {id(squadra): fascia_1_5}."""
    ordinate = sorted(squadre, key=punteggio_squadra, reverse=True)
    teste_di_serie = ordinate[:num_gironi]        # fascia 5, una per girone
    resto = ordinate[num_gironi:]
    dimensione = max(1, -(-len(resto) // 4))       # ceil: eccesso alle fasce forti
    fasce = {id(s): 5 for s in teste_di_serie}
    for i, s in enumerate(resto):
        fasce[id(s)] = 4 - min(i // dimensione, 3)  # 4,3,2,1 a cascata
    return fasce
```

`snake_draft` viene esteso con un parametro `chiave` opzionale (default
`punteggio_squadra`, così i test esistenti dei Task 2-3 restano invariati):

```python
def snake_draft(squadre, num_gironi, chiave=punteggio_squadra):
    ordinate = sorted(squadre, key=chiave, reverse=True)
    ...  # resto invariato
```

Il CLI (`main()`) calcola le fasce e le passa come chiave:

```python
fasce = assegna_fasce(squadre, config["num_gironi"])
gironi = snake_draft(squadre, config["num_gironi"], chiave=lambda s: fasce[id(s)])
```

**Conseguenza di design esplicita:** i punti reali totali per girone non saranno
più quasi-uguali (l'obiettivo diventa "stesso mix di fasce", non "stessa somma di
punti") — esattamente come nei gironi del Mondiale. Il totale punti reale resta nel
report a titolo informativo; il criterio di bilanciamento usa le fasce. Lo
`sbilanciamento` nel report continua a misurare la differenza di somme di punteggio
reale (utile come indicatore), ma non è più il criterio ottimizzato.

## 2. Minimizzazione partite consecutive (`generator.py`, `genera_calendario`)

Costanti (override env per i test):

```python
SOLVER_TIMEOUT = float(os.environ.get("FIBA_SOLVER_TIMEOUT", "300"))  # 5 min
SOLVER_GAP = float(os.environ.get("FIBA_SOLVER_GAP", "0.01"))         # 1%
```

Nel modello, dopo `AddAllDifferent(variabili)` e prima del solve: per ogni squadra,
per ogni coppia (i, j) delle sue partite, una variabile booleana reificata
`consec[i,j]` vera sse le due partite cadono in slot adiacenti dello stesso giorno.
La definizione di "adiacenti stesso giorno" replica esattamente quella già usata da
`verifica()` (stesso `giorno = slot // num_slots`, `abs(slotA - slotB) == 1`), così
l'obiettivo minimizza esattamente ciò che oggi viene solo segnalato.

```python
model.Minimize(sum(tutte_le_consec))
solver.parameters.max_time_in_seconds = SOLVER_TIMEOUT
solver.parameters.relative_gap_limit = SOLVER_GAP
```

**Garanzie:**
- `AddAllDifferent` resta il vincolo rigido → il problema è fattibile esattamente
  quando lo era prima; l'obiettivo sceglie solo *quale* soluzione fattibile.
- `max_time_in_seconds`: CP-SAT ritorna sempre la migliore soluzione trovata finora
  se il tempo scade → mai un run bloccato indefinitamente.
- `relative_gap_limit`: il solver si ferma appena la soluzione è entro l'1%
  dall'ottimo teorico → i tornei piccoli finiscono in secondi (non consumano il
  tetto di 5 min), i grandi degradano in qualità (non in tempo).
- `status` OPTIMAL **o** FEASIBLE resta accettato (come oggi); solo INFEASIBLE/
  UNKNOWN produce l'errore in italiano già esistente.

Il numero di variabili di penalità cresce come
`num_squadre × (partite_per_squadra)² / 2`: ~1200 per 120 squadre/20 gironi —
gestibile. Il rischio non è la dimensione del modello ma il tempo di ricerca
dell'ottimo, coperto da timeout + gap.

## 3. Fallback a media per giocatori N/A

**Marcatura (`fiba_client.py`, `parse_player_payload`):** quando
`rankingPoints == 0`, il giocatore ottiene un `fetch_status` distinto
`"ok: N/A (0 punti)"` (invece del normale `"ok"`), ma `ranking_points` resta 0 —
nessun valore stimato viene assegnato in questa fase.

**Passo finale (`app.py`, in coda a `_esegui_fetch`, dopo il loop per-giocatore):**
nuova funzione pura in `app.py` (stesso livello di `ridimensiona` del Task 7 —
helper puro senza dipendenze HTTP, testabile importandolo direttamente in
`test_app.py`):

```python
def applica_fallback_medio(dati):
    """Passo finale di ogni job di fetch: calcola la media dei ranking_points
    reali (>0) su TUTTO il pool squadre e la riassegna a TUTTI i giocatori
    marcati N/A (di qualunque squadra, anche marcati in job precedenti).
    Se il pool non ha ancora punteggi reali, non tocca nulla (i giocatori N/A
    restano tali finché un fetch futuro porta almeno un punteggio nel pool).
    Muta `dati` in place. Ritorna il numero di giocatori aggiornati."""
```

- Media su `ranking_points > 0` di tutti i giocatori con `fetch_status` reale
  (`"ok"`), escludendo quelli già stimati e quelli in errore.
- Ai giocatori N/A: `ranking_points = round(media)`,
  `fetch_status = f"ok: media stimata ({round(media)})"`.
- Idempotente: un giocatore già "media stimata" viene riconsiderato ad ogni job
  (torna nel set N/A per il ricalcolo), così la stima si aggiorna quando il pool
  cresce. Distinzione: `"ok"` = reale (entra nella media), `"ok: N/A ..."` /
  `"ok: media stimata ..."` = da (ri)stimare, `"errore: ..."` = mai toccato.
- Chiamata dopo il salvataggio dei risultati per-giocatore, con un ultimo
  `save_json(SQUADRE, dati)` atomico.

**Dashboard (`static/index.html`, `classeBadge`):** nuovo stato visivo. Tre colori
diventano quattro:
- verde: fetch reale oggi (`fetch_status == "ok"`, fetchato oggi)
- **arancione (nuovo): punteggio stimato via media** (`fetch_status` inizia con
  `"ok: media stimata"` o `"ok: N/A"`)
- giallo: dato reale ma vecchio (fetchato in un giorno precedente)
- rosso: mai fetchato o errore

L'ordine di precedenza in `classeBadge` va definito così che "media stimata" non
venga confuso con "reale ma vecchio".

## Cosa NON cambia

- `combinazioni_valide` / `valida_parametri` (validazione capacità)
- Interfaccia CLI (`--squadre/--config/--output`), formato `status.json`,
  `calendario_finale.json`, `report.txt`
- API (`/api/genera`, `/api/fetch`, ecc.) — firme invariate
- `snake_draft` come algoritmo di distribuzione (cambia solo il suo input/chiave)
- `copia_di_generazione_squadre.py` (mai toccato)
- Scritture atomiche via `storage.save_json`, stato per-job, messaggi in italiano

## Testing

**Unit (`assegna_fasce`):**
- teste di serie esatte (num_gironi squadre in fascia 5, una per girone dopo lo
  snake draft)
- resto non divisibile per 4 → eccesso alle fasce forti (es. 6 squadre resto →
  fasce 4,3,2,1 di dimensioni 2,2,1,1)
- caso reale "prova 7": sbilanciamento su punteggio reale scende da ~18604 a poche
  unità di fascia rispetto allo snake draft su punti grezzi
- meno di 4 squadre nel resto (dimensione clampata a ≥1, nessuna divisione per 0)

**Unit (minimizzazione consecutive):**
- con timeout ridotto via `FIBA_SOLVER_TIMEOUT` (test veloci, mai 5 min reali)
- un caso costruito dove esiste una soluzione a zero consecutive → il solver la
  trova (verifica che l'obiettivo funzioni, non solo che non crashi)
- un caso stretto (poche disponibilità) dove zero consecutive è impossibile → il
  solver ritorna comunque una soluzione fattibile (obiettivo morbido, non infeasible)
- infeasible reale (nessuno slot comune) → errore in italiano invariato

**Unit (`applica_fallback_medio`):**
- pool vuoto (nessun punteggio reale) → nessuna modifica, N/A restano
- pool con punteggi reali → media corretta e arrotondata, assegnata ai soli N/A
- giocatori N/A di squadre diverse → tutti aggiornati (non solo la squadra fetchata)
- giocatori in `errore:` → mai toccati
- idempotenza: un giocatore già "media stimata" si aggiorna se il pool cresce

**Integrazione:**
- benchmark manuale a scala realistica (120 squadre/20 gironi sintetiche) per
  validare che il tetto di 5 minuti sia adeguato e calibrare il default
- lo smoke test Playwright esistente resta verde (nessuna regressione UI)

## Rischi

1. **Tempo di solve su tornei grandi.** Mitigazione: timeout + gap garantiscono un
   caso peggiore limitato; il benchmark di integrazione calibra il default prima
   del rilascio.
2. **Media come stima "opinabile".** Mitigazione: badge arancione distinto rende
   sempre esplicito quali punteggi sono reali e quali stimati; l'organizzatore
   decide se accettarli.
3. **Fasce cambiano la semantica di "sbilanciamento" nel report.** Mitigazione:
   documentato sopra; il valore resta come indicatore informativo, non come
   criterio ottimizzato.
