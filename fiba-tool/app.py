"""FastAPI: dashboard statica + API del fiba-tool. Avvio: python app.py"""
import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from generator import punteggio_squadra
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
            dati["squadre"][i] = {**squadra.model_dump(), "id": sid,
                                  "da_riconfermare": False}
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


app.mount("/", StaticFiles(directory=os.path.join(BASE, "static"), html=True))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
