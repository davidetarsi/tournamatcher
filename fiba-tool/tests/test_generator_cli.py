import json
import os
import subprocess
import sys

from storage import load_json, save_json

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def squadra(nome, punti):
    return {"id": nome, "nome": nome,
            "giocatori": [{"url": f"https://play.fiba3x3.com/players/{nome}",
                           "nome": nome, "ranking_points": punti,
                           "fetch_status": "ok", "fetched_at": None}],
            "disponibilita": [[1, 1, 1], [1, 1, 1]],  # 2 giorni × 3 slot
            "da_riconfermare": False}


def test_cli_end_to_end(tmp_path):
    # 4 squadre, 1 girone → 6 partite → 2 giorni × 3 slot
    save_json(str(tmp_path / "squadre.json"),
              {"squadre": [squadra(n, p) for n, p in
                           [("A", 400), ("B", 300), ("C", 200), ("D", 100)]]})
    save_json(str(tmp_path / "config.json"),
              {"num_gironi": 1, "num_giorni": 2, "num_partite_giorno": 3})
    out = tmp_path / "run1"
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "generator.py"),
         "--squadre", str(tmp_path / "squadre.json"),
         "--config", str(tmp_path / "config.json"),
         "--output", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    status = load_json(str(out / "status.json"), None)
    assert status["stato"] == "completato"
    risultato = load_json(str(out / "calendario_finale.json"), None)
    partite = [p for slots in risultato["calendario"].values()
               for ps in slots.values() for p in ps]
    assert len(partite) == 6
    assert risultato["gironi"][0]["punteggio_totale"] == 1000
    assert os.path.exists(out / "report.txt")


def test_cli_infeasible(tmp_path):
    # nessuna disponibilità comune → errore umano in status.json
    squadre = [squadra(n, p) for n, p in
               [("A", 400), ("B", 300), ("C", 200), ("D", 100)]]
    for s in squadre:
        s["disponibilita"] = [[0, 0, 0], [0, 0, 0]]
    save_json(str(tmp_path / "squadre.json"), {"squadre": squadre})
    save_json(str(tmp_path / "config.json"),
              {"num_gironi": 1, "num_giorni": 2, "num_partite_giorno": 3})
    out = tmp_path / "run2"
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "generator.py"),
         "--squadre", str(tmp_path / "squadre.json"),
         "--config", str(tmp_path / "config.json"),
         "--output", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 1
    status = load_json(str(out / "status.json"), None)
    assert status["stato"] == "errore"
    assert "slot" in status["errore"].lower()


def test_cli_error_status_include_fase(tmp_path):
    # capacità errata (num_giorni * num_partite_giorno != slot totali) →
    # fallisce durante il caricamento/validazione parametri: lo status di
    # errore deve comunque riportare in quale fase è avvenuto il fallimento.
    squadre = [squadra(n, p) for n, p in
               [("A", 400), ("B", 300), ("C", 200), ("D", 100)]]
    save_json(str(tmp_path / "squadre.json"), {"squadre": squadre})
    save_json(str(tmp_path / "config.json"),
              {"num_gironi": 1, "num_giorni": 2, "num_partite_giorno": 1})
    out = tmp_path / "run3"
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "generator.py"),
         "--squadre", str(tmp_path / "squadre.json"),
         "--config", str(tmp_path / "config.json"),
         "--output", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 1
    status = load_json(str(out / "status.json"), None)
    assert status["stato"] == "errore"
    assert status.get("fase")


def test_cli_missing_config_key_gives_italian_message(tmp_path):
    # config.json senza "num_partite_giorno" → non deve finire il KeyError
    # grezzo (es. "'num_partite_giorno'") in status.json, ma un messaggio
    # italiano leggibile.
    squadre = [squadra(n, p) for n, p in
               [("A", 400), ("B", 300), ("C", 200), ("D", 100)]]
    save_json(str(tmp_path / "squadre.json"), {"squadre": squadre})
    save_json(str(tmp_path / "config.json"),
              {"num_gironi": 1, "num_giorni": 2})
    out = tmp_path / "run4"
    r = subprocess.run(
        [sys.executable, os.path.join(BASE, "generator.py"),
         "--squadre", str(tmp_path / "squadre.json"),
         "--config", str(tmp_path / "config.json"),
         "--output", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 1
    status = load_json(str(out / "status.json"), None)
    assert status["stato"] == "errore"
    errore = status["errore"]
    assert errore.strip() != "'num_partite_giorno'"
    assert "mancante" in errore.lower() or "config" in errore.lower()
