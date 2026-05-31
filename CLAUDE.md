# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the script

```bash
pip install ortools numpy PyQt5
python copia_di_generazione_squadre.py
```

The script runs top-to-bottom as a pipeline: it generates teams, creates a calendar, then verifies it — all in one execution.

## Architecture

The entire project lives in a single Python file (`copia_di_generazione_squadre.py`), originally exported from a Google Colab notebook. It runs as a sequential pipeline across four phases:

1. **Team generation** — `genera_squadre(num)` creates N teams with random Italian-style names, a strength rating (1–5), and a binary availability matrix `[num_giorni][num_partite_giorno]`. One team per group is forced to strength 5 (top-seed).

2. **Group (girone) creation** — `crea_gironi_bilanciati(squadre)` randomly assigns teams to groups, ensuring each group has exactly one top-seed and that the total strength across groups differs by at most `soglia=2`. Uses a retry loop up to 10M attempts.

3. **Schedule generation** — Uses **OR-Tools CP-SAT** (`ortools.sat.python.cp_model`) to assign each match a time slot. Slots are encoded as `giorno * num_slots_giorno + slot`. The key constraint is `AddAllDifferent` across all match variables, ensuring no two matches share a slot. Match variables are initialized only from slots where both teams are available.

4. **Verification** — `verifica_calendario_avanzato('calendario_finale.json')` checks for scheduling errors (duplicate team assignments) and warnings (consecutive slots for the same team), then writes a full report to `{NxM}-report_calendario.txt`.

## Data flow

```
Parameters → genera_squadre() → {NxM}-campionato.txt
                                        ↓
                            crea_gironi_bilanciati()
                                        ↓
                            CP-SAT solver → calendario_finale.json
                                        ↓
                            verifica_calendario_avanzato() → report .txt
```

## Key constraint

The parameters must satisfy: `num_giorni × num_partite_giorno × 2 == num_squadre × ((num_squadre / num_gironi) - 1)`. This ensures total match capacity exactly equals the number of matches needed. The file name `{num_squadre}x{num_gironi}-campionato.txt` encodes these parameters and is parsed at runtime to recover `num_gironi`.

## Commented-out GUI

A PyQt5 `TeamCreator` widget (lines 19–96) is commented out — it was an early attempt at a UI for manually entering teams. The current approach uses random generation instead.
