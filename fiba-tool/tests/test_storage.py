import json
import threading

from storage import load_json, save_json


def test_default_se_file_mancante(tmp_path):
    assert load_json(str(tmp_path / "niente.json"), {"squadre": []}) == {"squadre": []}


def test_roundtrip(tmp_path):
    percorso = str(tmp_path / "sub" / "dati.json")
    save_json(percorso, {"nome": "Rossi Leoni", "punti": 45230})
    assert load_json(percorso, None) == {"nome": "Rossi Leoni", "punti": 45230}


def test_scritture_concorrenti_mai_corrotte(tmp_path):
    percorso = str(tmp_path / "dati.json")

    def scrivi(n):
        for i in range(50):
            save_json(percorso, {"scrittore": n, "iterazione": i})

    threads = [threading.Thread(target=scrivi, args=(n,)) for n in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # il file deve essere JSON valido e completo (mai troncato)
    dati = load_json(percorso, None)
    assert set(dati) == {"scrittore", "iterazione"}
