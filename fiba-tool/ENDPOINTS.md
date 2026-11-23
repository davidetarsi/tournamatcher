# Endpoint FIBA 3x3 (non documentati — verificati il 2026-07-20)

Nessuna API pubblica ufficiale (la FIBA 3x3 Premium API è stata dismessa). Questi sono gli
endpoint JSON interni usati dal sito play.fiba3x3.com per popolare le proprie pagine,
individuati via DevTools → Network e riprodotti da terminale con curl.

## Profilo giocatore

- **URL profilo pubblico (da incollare nella dashboard):**
  `https://play.fiba3x3.com/players/<player-id>` — `<player-id>` è un UUID
  (es. `f20a6ede-97d4-4575-8f20-fb51cd19f87d`).
- **Endpoint dati:** `GET https://play.fiba3x3.com/api/v2/player/<player-id>`
- **Header richiesti:** `User-Agent` da browser reale. Verificato con curl:
  - Senza header browser → `403 Forbidden`
  - Con `User-Agent: Mozilla/5.0 (...) Chrome/126.0.0.0 Safari/537.36` → `200 OK`
  - Nessun cookie/sessione necessario per questo endpoint (dati pubblici).
- **Campi usati:**
  - Nome: `firstName` + `lastName` (stringhe separate, non un unico campo `name`)
  - Punti ranking: `rankingPoints` (intero — es. `628536` per un giocatore attivo
    in top-25 mondiale, `0` per un giocatore non attualmente in ranking)
  - Id: `id` (stesso UUID presente nell'URL del profilo)
- **Fixture:** `tests/fixtures/player_response.json` (risposta reale salvata per
  Nauris Miezis, giocatore lettone allora #25 nel ranking mondiale maschile).

## Ricerca giocatori per nome (scoperto durante l'investigazione, non usato dal tool)

- `GET https://play.fiba3x3.com/api/v2/search/players?name=<query>` — stesso
  `User-Agent` richiesto. Ritorna `{"results": [...], "totalCount": N}` dove
  ogni risultato ha già `id`, `firstName`, `lastName`, `nationality`,
  `rankingPoints` inline (utile in futuro per una ricerca-per-nome, ma il design
  attuale usa solo URL profilo incollati a mano — vedi spec).

## Nota sul rendering

La pagina profilo (`https://play.fiba3x3.com/players/<player-id>`) è **server-rendered**,
non un guscio SPA vuoto — i dati compaiono anche nell'HTML della pagina (tabella "Info"
con "Ranking Points"). Il parsing HTML resta comunque una via secondaria non implementata:
l'endpoint JSON sopra è sufficiente e più stabile.
