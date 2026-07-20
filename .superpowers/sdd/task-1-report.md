# Task 1 Report: Scaffold + Storage Atomico

## Riepilogo

Implementato lo scaffold iniziale per il progetto `fiba-tool` e un modulo di storage JSON atomico con supporto a scritture concorrenti serializzate.

## Cosa è stato fatto

### Step 1: Scaffold
Creato lo scaffold del progetto con le seguenti strutture:
- Directory `fiba-tool/` come radice del progetto
- Directory `fiba-tool/tests/` per i test
- File `fiba-tool/.gitignore` con esclusioni per `data/` e `__pycache__/`
- File `fiba-tool/requirements.txt` con dipendenze (fastapi, uvicorn, requests, ortools, httpx, pytest, pytest-playwright)

### Step 2-3: Test-Driven Development
Scritti i test in `fiba-tool/tests/test_storage.py` e conftest.py:
- Aggiunto conftest.py per rendere importabili i moduli dal parent directory
- Creati 3 test case coprenti:
  1. `test_default_se_file_mancante`: verifica che `load_json()` ritorni il default se il file non esiste
  2. `test_roundtrip`: verifica che `save_json()` crei le cartelle mancanti e che `load_json()` rilegga i dati correttamente
  3. `test_scritture_concorrenti_mai_corrotte`: test di stress con 4 thread che scrivono 50 iterazioni ciascuno, verificando che il JSON risultante sia sempre valido e completo

Test iniziale: FAIL (ModuleNotFoundError: No module named 'storage')

### Step 4: Implementazione
Implementato `fiba-tool/storage.py`:
- `load_json(path, default)`: legge JSON da file, ritorna `default` se il file non esiste
- `save_json(path, data)`: scrive JSON in modo atomico usando:
  - Lock threading (`_lock`) per serializzare le scritture in-process
  - tempfile.mkstemp() per creare file temporaneo nella stessa cartella
  - os.replace() per swap atomico (garantisce che il file non sia mai visibile troncato)
  - Creazione automatica delle cartelle mancanti con os.makedirs()
  - Cleanup del file temporaneo in caso di errore

### Step 5: Verifica
Eseguiti i test: **3/3 PASSED** ✓

## Output dei Comandi

### Test fallimento (Step 3)
```
ERROR collecting tests/test_storage.py
ModuleNotFoundError: No module named 'storage'
```

### Test passaggio (Step 5)
```
============================= test session starts ==============================
tests/test_storage.py::test_default_se_file_mancante PASSED              [ 33%]
tests/test_storage.py::test_roundtrip PASSED                             [ 66%]
tests/test_storage.py::test_scritture_concorrenti_mai_corrotte PASSED    [100%]

============================== 3 passed in 0.06s ===============================
```

### Commit
```
[feature/fiba-tool e006bf5] feat(fiba-tool): scaffold + storage JSON atomico con lock
 5 files changed, 74 insertions(+)
 create mode 100644 fiba-tool/.gitignore
 create mode 100644 fiba-tool/requirements.txt
 create mode 100644 fiba-tool/storage.py
 create mode 100644 fiba-tool/tests/conftest.py
 create mode 100644 fiba-tool/tests/test_storage.py
```

## Deviazioni dal Brief

Nessuna deviazione dal brief. Implementazione esatta come specificato, incluso:
- Stessa struttura di directory e nomi di file
- Stesso codice di storage.py con lock e atomicità garantita da os.replace
- Stesso approccio TDD (test prima, verifica fallimento, implementa, verifica successo)
- Stesso formato di commit message

## Hash Commit

- `e006bf5` - feat(fiba-tool): scaffold + storage JSON atomico con lock

## Note Tecniche

La soluzione usa il pattern classico per atomic file writes:
1. Scritture serializzate in-process con `threading.Lock()`
2. Creazione di file temporaneo nella stessa directory (stesso filesystem)
3. `os.replace()` per swap atomico (garantisce che il file non sia mai visibile incompleto)
4. Cleanup automatico del temporary file in caso di eccezione

Questo garantisce:
- Nessun file troncato visibile dai lettori
- Nessuna coruzione di JSON anche con accessi concorrenti
- Atomicità della write su filesystem POSIX

