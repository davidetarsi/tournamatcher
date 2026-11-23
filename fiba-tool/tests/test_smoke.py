"""Unico smoke test E2E del percorso felice (FIBA finto via FIBA_FAKE).
Copre la parte asincrona fragile del vanilla JS: form, fetch job, polling, risultati."""
import os
import socket
import subprocess
import sys
import tempfile
import time

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORTA = 8123
URL = f"http://127.0.0.1:{PORTA}"

NAV_SQUADRE = 'header button[data-vista="squadre"]'
NAV_PARAMETRI = 'header button[data-vista="parametri"]'


@pytest.fixture(scope="module")
def server():
    with tempfile.TemporaryDirectory() as dati:
        env = {**os.environ,
               "FIBA_DATA_DIR": dati,
               "FIBA_FAKE": "1",
               "FIBA_API_BASE": f"{URL}/fake-fiba",
               "FIBA_PAUSE": "0"}
        proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app:app", "--port", str(PORTA)],
            cwd=BASE, env=env)
        try:
            for _ in range(50):
                try:
                    socket.create_connection(("127.0.0.1", PORTA), 0.2).close()
                    break
                except OSError:
                    time.sleep(0.2)
            else:
                raise RuntimeError("Server non partito")
            yield URL
        finally:
            proc.terminate()
            proc.wait()


def test_percorso_felice(server, page):
    page.goto(server)

    # parametri: 1 girone, 2 giorni, 3 slot (per 4 squadre)
    page.click(NAV_PARAMETRI)
    for campo, valore in [("num_gironi", "1"), ("num_giorni", "2"),
                          ("num_partite_giorno", "3")]:
        page.fill(f"#{campo}", valore)
    page.click("#salva-config")

    # 4 squadre, 3 giocatori l'una, tutte disponibili
    for i in range(1, 5):
        page.click(NAV_SQUADRE)
        page.fill("#nome-squadra", f"Squadra {i}")
        page.fill("#urls-giocatori", "\n".join(
            f"https://play.fiba3x3.com/players/s{i}g{j}" for j in range(1, 4)))
        page.click("#tutto-disponibile")
        page.click("#salva-squadra")
        page.wait_for_selector(f"text=Squadra {i}")

    # fetch di tutte (FIBA finto) → badge verdi
    page.click(NAV_PARAMETRI)
    page.click("#btn-fetch-tutti")
    page.wait_for_selector("#stato-job:has-text('completato')", timeout=30000)
    page.click(NAV_SQUADRE)
    assert page.locator(".badge.verde").count() == 12

    # genera → risultati
    page.click(NAV_PARAMETRI)
    page.click("#btn-genera")
    page.wait_for_selector("#lista-runs", timeout=60000)
    page.wait_for_selector("#lista-runs :text('completato')", timeout=60000)
    page.click("#lista-runs button")
    page.wait_for_selector("text=Sbilanciamento")
    assert page.locator("#dettaglio-run tr:has-text('vs')").count() == 6
