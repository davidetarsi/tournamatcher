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


def test_applica_fallback_medio_pool_vuoto_non_tocca_nulla():
    import app
    dati = {"squadre": [{"giocatori": [
        {"ranking_points": 0, "fetch_status": "ok: N/A (0 punti)"}]}]}
    assert app.applica_fallback_medio(dati) == 0
    assert dati["squadre"][0]["giocatori"][0]["ranking_points"] == 0


def test_applica_fallback_medio_assegna_media_ai_na():
    import app
    dati = {"squadre": [
        {"giocatori": [
            {"ranking_points": 100, "fetch_status": "ok"},
            {"ranking_points": 300, "fetch_status": "ok"}]},
        {"giocatori": [
            {"ranking_points": 0, "fetch_status": "ok: N/A (0 punti)"}]},
    ]}
    aggiornati = app.applica_fallback_medio(dati)
    assert aggiornati == 1
    na = dati["squadre"][1]["giocatori"][0]
    assert na["ranking_points"] == 200            # media di 100 e 300
    assert na["fetch_status"] == "ok: media stimata (200)"


def test_applica_fallback_medio_non_tocca_errori_e_aggiorna_stime_vecchie():
    import app
    dati = {"squadre": [
        {"giocatori": [{"ranking_points": 400, "fetch_status": "ok"}]},
        {"giocatori": [
            {"ranking_points": 999, "fetch_status": "errore: profilo non trovato"},
            {"ranking_points": 50, "fetch_status": "ok: media stimata (50)"}]},
    ]}
    app.applica_fallback_medio(dati)
    errore = dati["squadre"][1]["giocatori"][0]
    stima = dati["squadre"][1]["giocatori"][1]
    assert errore["ranking_points"] == 999        # errore mai toccato
    assert errore["fetch_status"] == "errore: profilo non trovato"
    assert stima["ranking_points"] == 400         # stima vecchia ricalcolata sul pool
    assert stima["fetch_status"] == "ok: media stimata (400)"


def test_fetch_0_punti_marcato_na_poi_media(client, monkeypatch):
    """Verifica il ramo 0 punti: fetch → marcato N/A → assegnato media del pool.

    Crea squadra A con giocatore che ha ranking_points=600 (reale),
    squadra B con giocatore che ha ranking_points=0 (non in classifica FIBA).
    Dopo fetch+fallback: A rimane "ok"/600, B diventa "ok: media stimata (600)"/600.
    """
    squadra_a = {
        "nome": "Rossi Leoni",
        "giocatori": [{"url": "https://play.fiba3x3.com/players/a1", "nome": "",
                       "ranking_points": 0, "fetch_status": "mai", "fetched_at": None}],
        "disponibilita": [[1, 0], [0, 1]],
    }
    squadra_b = {
        "nome": "Blu Aquile",
        "giocatori": [{"url": "https://play.fiba3x3.com/players/b1", "nome": "",
                       "ranking_points": 0, "fetch_status": "mai", "fetched_at": None}],
        "disponibilita": [[1, 0], [0, 1]],
    }

    client.post("/api/squadre", json=squadra_a)
    client.post("/api/squadre", json=squadra_b)

    def fetch_team_players_finto(urls, session=None, pausa=None, on_progress=None):
        """Mock che ritorna 600 punti per a1, 0 punti per b1."""
        risultati = []
        for url in urls:
            if "a1" in url:
                risultati.append({
                    "url": url,
                    "ok": True,
                    "dati": {
                        "id": "a1",
                        "nome": "Player A",
                        "ranking_points": 600,
                        "fetched_at": "2026-07-21T00:00:00"
                    }
                })
            elif "b1" in url:
                risultati.append({
                    "url": url,
                    "ok": True,
                    "dati": {
                        "id": "b1",
                        "nome": "Player B",
                        "ranking_points": 0,
                        "fetched_at": "2026-07-21T00:00:00"
                    }
                })
        return risultati

    monkeypatch.setattr(fiba_client, "fetch_team_players", fetch_team_players_finto)

    job_id = client.post("/api/fetch").json()["job_id"]

    # Polling finché completato o errore
    for _ in range(60):  # max ~15s
        st = client.get(f"/api/jobs/{job_id}/status").json()
        if st.get("stato") in ("completato", "errore"):
            break
        time.sleep(0.25)
    assert st["stato"] == "completato"

    # Verifica risultati
    squadre = client.get("/api/squadre").json()["squadre"]
    assert len(squadre) == 2

    # Ordina per nome per averle in ordine
    squadre_sorted = sorted(squadre, key=lambda x: x["nome"])
    giocatore_a = squadre_sorted[0]["giocatori"][0]  # Blu Aquile (b1)
    giocatore_b = squadre_sorted[1]["giocatori"][0]  # Rossi Leoni (a1)

    # Giocatore A (600 punti reali) → fetch_status "ok"
    assert giocatore_b["ranking_points"] == 600
    assert giocatore_b["fetch_status"] == "ok"

    # Giocatore B (0 punti iniziali) → fetch_status "ok: N/A (0 punti)" durante fetch,
    # poi applica_fallback_medio lo trasforma in media del pool (600)
    assert giocatore_a["ranking_points"] == 600
    assert giocatore_a["fetch_status"] == "ok: media stimata (600)"


def test_normalizza_manuale_con_numero():
    import app
    g = {"url": "", "nome": "Mario", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": "vecchio"}
    app.normalizza_giocatore_manuale(g)
    assert g["ranking_points"] == 1500
    assert g["fetch_status"] == "manuale (1500)"
    assert g["fetched_at"] is None


def test_normalizza_manuale_senza_numero_valido():
    import app
    for raw in [None, "", "abc", -5, 0, "12x"]:
        g = {"url": "", "nome": "Mario", "ranking_points": raw,
             "fetch_status": "manuale", "fetched_at": None}
        app.normalizza_giocatore_manuale(g)
        assert g["ranking_points"] is None, raw
        assert g["fetch_status"] == "manuale: N/A", raw


def test_normalizza_manuale_accetta_stringa_di_cifre():
    import app
    g = {"url": "", "nome": "M", "ranking_points": "1500",
         "fetch_status": "manuale", "fetched_at": None}
    app.normalizza_giocatore_manuale(g)
    assert g["ranking_points"] == 1500
    assert g["fetch_status"] == "manuale (1500)"


def test_normalizza_manuali_lascia_intatti_i_fiba():
    import app
    giocatori = [
        {"url": "https://play.fiba3x3.com/players/x", "nome": "F",
         "ranking_points": 900, "fetch_status": "ok", "fetched_at": "t"},
        {"url": "", "nome": "M", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": None},
    ]
    app.normalizza_manuali(giocatori)
    assert giocatori[0]["fetch_status"] == "ok"       # FIBA intatto
    assert giocatori[0]["ranking_points"] == 900
    assert giocatori[1]["fetch_status"] == "manuale (1500)"


def test_crea_e_modifica_squadra_normalizzano_i_manuali(client):
    corpo = {"nome": "T", "disponibilita": [], "giocatori": [
        {"url": "", "nome": "Mario", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": None}]}
    sid = client.post("/api/squadre", json=corpo).json()["id"]
    g = client.get("/api/squadre").json()["squadre"][0]["giocatori"][0]
    assert g["fetch_status"] == "manuale (1500)" and g["ranking_points"] == 1500

    # in modifica un manuale senza numero torna N/A
    corpo2 = {"nome": "T", "disponibilita": [], "giocatori": [
        {"url": "", "nome": "Mario", "ranking_points": None,
         "fetch_status": "manuale", "fetched_at": None}]}
    client.put(f"/api/squadre/{sid}", json=corpo2)
    g = client.get("/api/squadre").json()["squadre"][0]["giocatori"][0]
    assert g["fetch_status"] == "manuale: N/A" and g["ranking_points"] is None


def test_media_conta_i_manuali_con_numero():
    import app
    dati = {"squadre": [
        {"giocatori": [{"ranking_points": 1000, "fetch_status": "manuale (1000)"}]},
        {"giocatori": [{"ranking_points": None, "fetch_status": "manuale: N/A"}]},
    ]}
    aggiornati = app.applica_fallback_medio(dati)
    assert aggiornati == 1
    stimato = dati["squadre"][1]["giocatori"][0]
    assert stimato["ranking_points"] == 1000            # media = solo il 1000 manuale
    assert stimato["fetch_status"] == "ok: media stimata (1000)"


def test_media_non_ristima_i_manuali_con_numero():
    import app
    dati = {"squadre": [
        {"giocatori": [{"ranking_points": 500, "fetch_status": "ok"}]},
        {"giocatori": [{"ranking_points": 1500, "fetch_status": "manuale (1500)"}]},
    ]}
    aggiornati = app.applica_fallback_medio(dati)
    manuale = dati["squadre"][1]["giocatori"][0]
    assert manuale["ranking_points"] == 1500            # NON ristimato
    assert manuale["fetch_status"] == "manuale (1500)"
    assert aggiornati == 0                              # nessun giocatore ri-stimato


def test_fetch_salta_i_giocatori_manuali(client, monkeypatch):
    import fiba_client
    client.post("/api/squadre", json={"nome": "Mix", "disponibilita": [], "giocatori": [
        {"url": "https://play.fiba3x3.com/players/u1", "nome": "", "ranking_points": None,
         "fetch_status": "mai", "fetched_at": None},
        {"url": "", "nome": "Manuale", "ranking_points": 1500,
         "fetch_status": "manuale", "fetched_at": None}]})
    urls_fetchate = []

    def finto(urls, session=None, pausa=None, on_progress=None):
        urls_fetchate.extend(urls)
        return [{"url": u, "ok": True,
                 "dati": {"id": "x", "nome": "R", "ranking_points": 800,
                          "fetched_at": "2026-07-22T00:00:00+00:00"}} for u in urls]

    monkeypatch.setattr(fiba_client, "fetch_team_players", finto)
    job = client.post("/api/fetch").json()["job_id"]
    for _ in range(60):
        st = client.get(f"/api/jobs/{job}/status").json()
        if st.get("stato") in ("completato", "errore"):
            break
        time.sleep(0.25)
    assert st["stato"] == "completato"
    # solo l'URL è stato interrogato, il manuale è stato saltato
    assert urls_fetchate == ["https://play.fiba3x3.com/players/u1"]
    giocatori = client.get("/api/squadre").json()["squadre"][0]["giocatori"]
    manuale = [g for g in giocatori if g["nome"] == "Manuale"][0]
    assert manuale["fetch_status"] == "manuale (1500)"  # intatto, non errore
    assert manuale["ranking_points"] == 1500
