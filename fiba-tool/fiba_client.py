"""Client dati FIBA 3x3, riusabile anche fuori dal tool.

Gli endpoint non sono documentati da FIBA: URL e parsing sono confinati in
PLAYER_API_URL e parse_player_payload — se FIBA cambia il sito si aggiorna qui
(riferimento: ENDPOINTS.md, fixture in tests/fixtures/)."""
import os
import re
import time
from datetime import datetime, timezone

import requests

PLAYER_ID_RE = re.compile(r"play\.fiba3x3\.com/players/([A-Za-z0-9\-]+)")
API_BASE = os.environ.get("FIBA_API_BASE", "https://play.fiba3x3.com")
PLAYER_API_URL = API_BASE + "/api/v2/player/{player_id}"
PAUSA_DEFAULT = float(os.environ.get("FIBA_PAUSE", "1.0"))

BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/126.0.0.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def nuova_sessione():
    s = requests.Session()
    s.headers.update(BROWSER_HEADERS)
    return s


def extract_player_id(url):
    m = PLAYER_ID_RE.search(url)
    if not m:
        raise ValueError(f"URL profilo non riconosciuto: {url}")
    return m.group(1)


def parse_player_payload(payload):
    # Percorsi campi verificati in ENDPOINTS.md: la risposta reale non ha
    # un campo "name" unico, ma firstName + lastName separati.
    return {"id": payload["id"],
            "nome": f"{payload['firstName']} {payload['lastName']}",
            "ranking_points": int(payload["rankingPoints"])}


def fetch_player(url, session=None, timeout=10):
    session = session or nuova_sessione()
    player_id = extract_player_id(url)
    ultimo_errore = None
    for _ in range(2):  # un solo retry
        try:
            r = session.get(PLAYER_API_URL.format(player_id=player_id),
                            timeout=timeout)
            r.raise_for_status()
            dati = parse_player_payload(r.json())
            dati["fetched_at"] = datetime.now(timezone.utc).isoformat()
            return dati
        except Exception as e:
            ultimo_errore = e
    raise RuntimeError(f"Fetch fallito per {url}: {ultimo_errore}")


def fetch_team_players(urls, session=None, pausa=None, on_progress=None):
    """Un risultato per giocatore, mai un'eccezione complessiva."""
    session = session or nuova_sessione()
    if pausa is None:
        pausa = PAUSA_DEFAULT
    risultati = []
    for i, url in enumerate(urls):
        try:
            risultati.append({"url": url, "ok": True,
                              "dati": fetch_player(url, session)})
        except Exception as e:
            risultati.append({"url": url, "ok": False, "errore": str(e)})
        if on_progress:
            on_progress(i + 1, len(urls))
        if i < len(urls) - 1:
            time.sleep(pausa)
    return risultati
