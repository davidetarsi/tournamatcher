"""FastAPI: dashboard statica + API del fiba-tool. Avvio: python app.py"""
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import fiba_client
from generator import punteggio_squadra, valida_parametri
from storage import load_json, save_json

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.environ.get("FIBA_DATA_DIR", os.path.join(BASE, "data"))
SQUADRE = os.path.join(DATA, "squadre.json")
CONFIG = os.path.join(DATA, "config.json")
OUTPUT = os.path.join(DATA, "output")
DEFAULT_CONFIG = {"num_gironi": 2, "num_giorni": 2, "num_partite_giorno": 3}

app = FastAPI()


class SquadraIn(BaseModel):
    nome: str
    giocatori: list[dict]
    disponibilita: list[list[int]]


class ConfigIn(BaseModel):
    num_gironi: int
    num_giorni: int
    num_partite_giorno: int


def leggi_squadre():
    return load_json(SQUADRE, {"squadre": []})


def ridimensiona(griglia, giorni, slot):
    """Adatta la griglia ai nuovi parametri. Celle nuove = 0 (opt-in rigoroso:
    mai assumere disponibilità non confermata). Ritorna (griglia, cresciuta)."""
    cresciuta = giorni > len(griglia) or any(slot > len(r) for r in griglia)
    nuova = [[griglia[g][s] if g < len(griglia) and s < len(griglia[g]) else 0
              for s in range(slot)] for g in range(giorni)]
    return nuova, cresciuta


@app.get("/api/squadre")
def lista_squadre():
    dati = leggi_squadre()
    for s in dati["squadre"]:
        s["punteggio"] = punteggio_squadra(s)
    return dati


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


@app.delete("/api/squadre/{sid}")
def elimina_squadra(sid: str):
    dati = leggi_squadre()
    prima = len(dati["squadre"])
    dati["squadre"] = [s for s in dati["squadre"] if s["id"] != sid]
    if len(dati["squadre"]) == prima:
        raise HTTPException(404, "Squadra non trovata")
    save_json(SQUADRE, dati)
    return {"ok": True}


@app.get("/api/config")
def leggi_config():
    return load_json(CONFIG, DEFAULT_CONFIG)


@app.put("/api/config")
def salva_config(cfg: ConfigIn):
    nuovo = cfg.model_dump()
    dati = leggi_squadre()
    for s in dati["squadre"]:
        s["disponibilita"], cresciuta = ridimensiona(
            s["disponibilita"], nuovo["num_giorni"], nuovo["num_partite_giorno"])
        if cresciuta:
            s["da_riconfermare"] = True
    save_json(SQUADRE, dati)
    save_json(CONFIG, nuovo)
    return nuovo


def nuovo_job(tipo):
    job_id = datetime.now().strftime("%Y-%m-%d_%H%M%S") + f"-{tipo}"
    cartella = os.path.join(OUTPUT, job_id)
    os.makedirs(cartella, exist_ok=True)
    return job_id, cartella


@app.post("/api/genera")
def genera():
    dati = leggi_squadre()
    cfg = load_json(CONFIG, DEFAULT_CONFIG)
    try:
        valida_parametri(len(dati["squadre"]), cfg["num_gironi"],
                         cfg["num_giorni"], cfg["num_partite_giorno"])
    except ValueError as e:
        raise HTTPException(400, str(e))
    job_id, cartella = nuovo_job("genera")
    subprocess.Popen([sys.executable, os.path.join(BASE, "generator.py"),
                      "--squadre", SQUADRE, "--config", CONFIG,
                      "--output", cartella])
    return {"job_id": job_id}


@app.post("/api/fetch")
def avvia_fetch(squadra: Optional[str] = None):
    dati = leggi_squadre()
    ids = [s["id"] for s in dati["squadre"] if squadra in (None, s["id"])]
    if not ids:
        raise HTTPException(404, "Nessuna squadra da aggiornare")
    job_id, cartella = nuovo_job("fetch")
    threading.Thread(target=_esegui_fetch, args=(cartella, ids),
                     daemon=True).start()
    return {"job_id": job_id}


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


def _esegui_fetch(cartella, ids):
    percorso_status = os.path.join(cartella, "status.json")
    save_json(percorso_status, {"tipo": "fetch", "stato": "in_corso",
                                "fatti": 0, "totale": len(ids)})
    n = 0
    try:
        sessione = fiba_client.nuova_sessione()
        for n, sid in enumerate(ids, 1):
            dati = leggi_squadre()  # riletto a ogni giro: minimizza le finestre di conflitto
            squadra = next((s for s in dati["squadre"] if s["id"] == sid), None)
            if squadra:
                risultati = fiba_client.fetch_team_players(
                    [g["url"] for g in squadra["giocatori"]], sessione)
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
            save_json(percorso_status, {"tipo": "fetch", "stato": "in_corso",
                                        "fatti": n, "totale": len(ids)})
        # Passo finale: assegna il punteggio medio del pool ai giocatori N/A
        # (di qualunque squadra, anche marcati in job precedenti).
        dati = leggi_squadre()
        if applica_fallback_medio(dati):
            save_json(SQUADRE, dati)
        save_json(percorso_status, {"tipo": "fetch", "stato": "completato",
                                    "fatti": len(ids), "totale": len(ids)})
    except Exception as e:
        save_json(percorso_status, {"tipo": "fetch", "stato": "errore",
                                    "errore": str(e), "fatti": n, "totale": len(ids)})


def _percorso_job(job_id, nome_file):
    if "/" in job_id or ".." in job_id:
        raise HTTPException(400, "Id job non valido")
    return os.path.join(OUTPUT, job_id, nome_file)


@app.get("/api/jobs/{job_id}/status")
def stato_job(job_id: str):
    st = load_json(_percorso_job(job_id, "status.json"), None)
    if st is None:
        raise HTTPException(404, "Job non trovato")
    return st


@app.get("/api/runs")
def elenco_runs():
    out = []
    if os.path.isdir(OUTPUT):
        for nome in sorted(os.listdir(OUTPUT), reverse=True):
            st = load_json(os.path.join(OUTPUT, nome, "status.json"), None)
            if st and st.get("tipo") == "genera":
                out.append({"id": nome, **st})
    return out


@app.get("/api/runs/{run_id}/calendario")
def run_calendario(run_id: str):
    cal = load_json(_percorso_job(run_id, "calendario_finale.json"), None)
    if cal is None:
        raise HTTPException(404, "Calendario non trovato")
    return cal


@app.get("/api/runs/{run_id}/report", response_class=PlainTextResponse)
def run_report(run_id: str):
    percorso = _percorso_job(run_id, "report.txt")
    if not os.path.exists(percorso):
        raise HTTPException(404, "Report non trovato")
    with open(percorso, encoding="utf-8") as f:
        return f.read()


if os.environ.get("FIBA_FAKE"):
    @app.get("/fake-fiba/api/v2/player/{player_id}")
    def fake_player(player_id: str):
        # stesso schema del payload reale (vedi ENDPOINTS.md / fiba_client.parse_player_payload)
        return {"id": player_id, "firstName": "Giocatore", "lastName": player_id,
                "rankingPoints": 1000}


app.mount("/", StaticFiles(directory=os.path.join(BASE, "static"), html=True))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
