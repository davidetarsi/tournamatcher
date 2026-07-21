import importlib

import pytest
from fastapi.testclient import TestClient

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
