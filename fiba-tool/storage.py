"""Storage JSON atomico. Scritture serializzate in-process; os.replace garantisce
che il file non sia mai visibile troncato o corrotto."""
import json
import os
import tempfile
import threading

_lock = threading.Lock()


def load_json(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with _lock:
        cartella = os.path.dirname(os.path.abspath(path))
        os.makedirs(cartella, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=cartella, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.unlink(tmp)
            raise
