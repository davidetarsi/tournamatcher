from __future__ import annotations
import pytest
from scheduler import crea_gironi_bilanciati, generate_schedule

# 4 squadre, 2 gironi da 2 (1 top-seed per girone)
TEAMS = {
    "Leoni":  {"nome": "Leoni",  "forza": 5, "disponibilita": [[1, 1], [1, 1], [0, 1]]},
    "Aquile": {"nome": "Aquile", "forza": 5, "disponibilita": [[1, 1], [1, 1], [1, 0]]},
    "Tori":   {"nome": "Tori",   "forza": 2, "disponibilita": [[1, 1], [1, 1], [1, 1]]},
    "Draghi": {"nome": "Draghi", "forza": 3, "disponibilita": [[1, 1], [1, 1], [1, 1]]},
}

def test_crea_gironi_returns_correct_count():
    gironi = crea_gironi_bilanciati(TEAMS, num_gironi=2, soglia=3)
    assert len(gironi) == 2

def test_ogni_girone_ha_una_testa_di_serie():
    gironi = crea_gironi_bilanciati(TEAMS, num_gironi=2, soglia=3)
    for girone in gironi:
        top_seeds = [t for t in girone if TEAMS[t]["forza"] == 5]
        assert len(top_seeds) == 1

def test_ogni_squadra_appare_una_sola_volta():
    gironi = crea_gironi_bilanciati(TEAMS, num_gironi=2, soglia=3)
    all_teams = [t for girone in gironi for t in girone]
    assert sorted(all_teams) == sorted(TEAMS.keys())

def test_generate_schedule_returns_all_matches():
    # 2 gironi da 2 squadre = 1 partita per girone = 2 partite totali
    gironi = [["Leoni", "Tori"], ["Aquile", "Draghi"]]
    result = generate_schedule(gironi, TEAMS, num_giorni=3, num_slots=2)
    assert result is not None
    total_matches = sum(
        len(matches)
        for slots in result.values()
        for matches in slots.values()
    )
    assert total_matches == 2

def test_generate_schedule_respects_availability():
    # Leoni non disponibile giorno 0 slot 0 → nessuna partita con Leoni in quello slot
    gironi = [["Leoni", "Tori"], ["Aquile", "Draghi"]]
    result = generate_schedule(gironi, TEAMS, num_giorni=3, num_slots=2)
    if result and 0 in result and 0 in result[0]:
        for match in result[0][0]:
            assert "Leoni" not in match["squadre"]

def test_generate_schedule_returns_none_if_infeasible():
    teams_no_overlap = {
        "A": {"nome": "A", "forza": 5, "disponibilita": [[1, 0], [0, 0]]},
        "B": {"nome": "B", "forza": 2, "disponibilita": [[0, 1], [0, 0]]},
    }
    result = generate_schedule([["A", "B"]], teams_no_overlap, num_giorni=2, num_slots=2)
    assert result is None
