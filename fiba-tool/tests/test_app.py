import importlib
import time

import pytest
from fastapi.testclient import TestClient

import fiba_client

SQUADRA = {
    "nome": "Rossi Leoni",
    "giocatori": [{"url": "https://play.fiba3x3.com/players/a1", "nome": "",
                   "ranking_points": 300, "fetch_status": "mai", "fetched_at": None},
                  {"url": "https://play.fiba3x3.com/players/a2", "nome": "",
                   "ranking_points": 200, "fetch_status": "mai", "fetched_at": None}],
    "disponibilita": [[1, 0], [0, 1]],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("FIBA_DATA_DIR", str(tmp_path))
    import app as modulo
    importlib.reload(modulo)
    return TestClient(modulo.app)


def test_crud_squadre(client):
    r = client.post("/api/squadre", json=SQUADRA)
    assert r.status_code == 200
    sid = r.json()["id"]

    lista = client.get("/api/squadre").json()["squadre"]
    assert len(lista) == 1
    assert lista[0]["punteggio"] == 500  # somma top 3 (qui 2 giocatori)

    r = client.put(f"/api/squadre/{sid}", json={**SQUADRA, "nome": "Blu Aquile"})
    assert r.status_code == 200
    assert client.get("/api/squadre").json()["squadre"][0]["nome"] == "Blu Aquile"

    assert client.delete(f"/api/squadre/{sid}").status_code == 200
    assert client.get("/api/squadre").json()["squadre"] == []


def test_config_espansione_opt_in(client):
    client.post("/api/squadre", json=SQUADRA)  # griglia 2×2
    r = client.put("/api/config",
                   json={"num_gironi": 1, "num_giorni": 3, "num_partite_giorno": 3})
    assert r.status_code == 200
    s = client.get("/api/squadre").json()["squadre"][0]
    # celle nuove a 0, squadra da riconfermare
    assert s["disponibilita"] == [[1, 0, 0], [0, 1, 0], [0, 0, 0]]
    assert s["da_riconfermare"] is True


def test_riconferma_al_salvataggio(client):
    sid = client.post("/api/squadre", json=SQUADRA).json()["id"]
    client.put("/api/config",
               json={"num_gironi": 1, "num_giorni": 3, "num_partite_giorno": 3})
    aggiornata = {**SQUADRA,
                  "disponibilita": [[1, 0, 1], [0, 1, 1], [1, 1, 1]]}
    client.put(f"/api/squadre/{sid}", json=aggiornata)
    assert client.get("/api/squadre").json()["squadre"][0]["da_riconfermare"] is False


def test_genera_job_e_runs(client):
    for n, p in [("A", 400), ("B", 300), ("C", 200), ("D", 100)]:
        client.post("/api/squadre", json={
            "nome": n,
            "giocatori": [{"url": f"https://play.fiba3x3.com/players/{n}",
                           "nome": n, "ranking_points": p,
                           "fetch_status": "ok", "fetched_at": None}],
            "disponibilita": [[1, 1, 1], [1, 1, 1]]})
    client.put("/api/config",
               json={"num_gironi": 1, "num_giorni": 2, "num_partite_giorno": 3})
    job_id = client.post("/api/genera").json()["job_id"]

    for _ in range(60):  # max ~15s
        st = client.get(f"/api/jobs/{job_id}/status").json()
        # .get(): appena dopo il POST il sottoprocesso potrebbe non aver
        # ancora scritto status.json (404 -> {"detail": ...}, niente "stato")
        if st.get("stato") in ("completato", "errore"):
            break
        time.sleep(0.25)
    assert st["stato"] == "completato"

    runs = client.get("/api/runs").json()
    assert runs[0]["id"] == job_id
    cal = client.get(f"/api/runs/{job_id}/calendario").json()
    assert cal["gironi"][0]["punteggio_totale"] == 1000
    assert "GIRONI" in client.get(f"/api/runs/{job_id}/report").text


def test_genera_parametri_invalidi(client):
    client.put("/api/config",
               json={"num_gironi": 1, "num_giorni": 5, "num_partite_giorno": 5})
    assert client.post("/api/genera").status_code == 400


def test_job_inesistente(client):
    assert client.get("/api/jobs/finto/status").status_code == 404


def test_fetch_job_e_squadra_aggiornata(client, monkeypatch):
    squadra = {
        "nome": "Verdi Falchi",
        "giocatori": [{"url": "https://play.fiba3x3.com/players/x1", "nome": "",
                       "ranking_points": 0, "fetch_status": "mai", "fetched_at": None}],
        "disponibilita": [[1, 0], [0, 1]],
    }
    client.post("/api/squadre", json=squadra)

    def fetch_team_players_finto(urls, session=None, pausa=None, on_progress=None):
        return [{"url": url, "ok": True,
                 "dati": {"id": "x1", "nome": "Test Player",
                          "ranking_points": 500, "fetched_at": "2026-07-21T00:00:00"}}
                for url in urls]

    monkeypatch.setattr(fiba_client, "fetch_team_players", fetch_team_players_finto)

    job_id = client.post("/api/fetch").json()["job_id"]

    for _ in range(60):  # max ~15s
        st = client.get(f"/api/jobs/{job_id}/status").json()
        if st.get("stato") in ("completato", "errore"):
            break
        time.sleep(0.25)
    assert st["stato"] == "completato"

    giocatore = client.get("/api/squadre").json()["squadre"][0]["giocatori"][0]
    assert giocatore["ranking_points"] == 500
    assert giocatore["fetch_status"] == "ok"
