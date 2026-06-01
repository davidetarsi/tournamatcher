from __future__ import annotations
import pytest
from standings import compute_standings
from models import StandingsEntry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _match(home, away, hg=None, ag=None, girone="A"):
    return {"girone": girone, "squadre": [home, away], "home_goals": hg, "away_goals": ag}

TEAMS = {"A": "Aquile", "B": "Bisonti", "C": "Condor", "D": "Draghi"}

PS_CALCIO = {"win": 3, "draw": 1, "loss": 0, "draws_allowed": True}
PS_BASKET = {"win": 2, "draw": 0, "loss": 0, "draws_allowed": False}
TR_DEFAULT = ["goal_difference", "goals_for", "head_to_head"]

# ---------------------------------------------------------------------------
# test_standings_computation_calcio
# ---------------------------------------------------------------------------

def test_standings_computation_calcio():
    matches = [
        _match("A", "B", 2, 1),   # A wins
        _match("A", "C", 1, 1),   # draw
        _match("B", "C", 0, 2),   # C wins
    ]
    result = compute_standings(matches, TEAMS, PS_CALCIO, TR_DEFAULT)
    assert "A" in result
    entries = result["A"]
    by_id = {e.team_id: e for e in entries}

    assert by_id["A"].points == 4   # 3 + 1
    assert by_id["C"].points == 4   # 3 + 1
    assert by_id["B"].points == 0
    assert by_id["A"].played == 2
    assert by_id["B"].played == 2
    assert by_id["C"].played == 2
    assert by_id["A"].goals_for == 3
    assert by_id["A"].goals_against == 2

# ---------------------------------------------------------------------------
# test_standings_computation_basket
# ---------------------------------------------------------------------------

def test_standings_computation_basket():
    matches = [
        _match("A", "B", 80, 70),  # A wins
        _match("C", "D", 60, 75),  # D wins
        _match("A", "C", 90, 80),  # A wins
        _match("B", "D", 70, 80),  # D wins
    ]
    result = compute_standings(matches, TEAMS, PS_BASKET, TR_DEFAULT)
    entries = result["A"]
    by_id = {e.team_id: e for e in entries}

    assert by_id["A"].wins == 2
    assert by_id["A"].draws == 0
    assert by_id["D"].wins == 2
    assert by_id["B"].wins == 0
    assert by_id["A"].points == 4
    assert by_id["D"].points == 4

# ---------------------------------------------------------------------------
# test_tiebreaker_goal_difference
# ---------------------------------------------------------------------------

def test_tiebreaker_goal_difference():
    # A and C both 4 pts; A has better GD (+3 vs +1) → A first
    matches = [
        _match("A", "B", 3, 0),   # A +3
        _match("A", "C", 1, 1),   # draw
        _match("B", "C", 0, 2),   # C +2 but after losing 0-3, ga=3
    ]
    result = compute_standings(matches, TEAMS, PS_CALCIO, TR_DEFAULT)
    entries = result["A"]
    assert entries[0].team_id == "A"
    assert entries[1].team_id == "C"
    assert entries[2].team_id == "B"
    assert entries[0].position == 1
    assert entries[1].position == 2
    assert entries[2].position == 3

# ---------------------------------------------------------------------------
# test_tiebreaker_head_to_head (3-way tie resolved by mini-standings)
# ---------------------------------------------------------------------------

def test_tiebreaker_head_to_head():
    # All three teams have 3 pts, same GD (0), same GF (1)
    # Circular: A beat B, B beat C, C beat A — all 1-0
    # Mini-standings: each team 1W 1L → same pts in h2h
    # Order should be stable (no crash); positions 1-3 assigned
    matches = [
        _match("A", "B", 1, 0),
        _match("B", "C", 1, 0),
        _match("C", "A", 1, 0),
    ]
    result = compute_standings(matches, TEAMS, PS_CALCIO, TR_DEFAULT)
    entries = result["A"]
    positions = {e.team_id: e.position for e in entries}
    assert set(positions.values()) == {1, 2, 3}  # all unique, no crash
    assert all(e.points == 3 for e in entries)

# ---------------------------------------------------------------------------
# test_unplayed_matches_ignored
# ---------------------------------------------------------------------------

def test_unplayed_matches_ignored():
    matches = [
        _match("A", "B", 2, 0),
        _match("A", "C"),         # not yet played
        _match("B", "C"),         # not yet played
    ]
    result = compute_standings(matches, TEAMS, PS_CALCIO, TR_DEFAULT)
    entries = result["A"]
    by_id = {e.team_id: e for e in entries}
    assert by_id["A"].played == 1
    assert by_id["B"].played == 1
    assert by_id["C"].played == 0

# ---------------------------------------------------------------------------
# test_multiple_groups
# ---------------------------------------------------------------------------

def test_multiple_groups():
    matches = [
        _match("A", "B", 1, 0, girone="A"),
        _match("C", "D", 2, 1, girone="B"),
    ]
    result = compute_standings(matches, TEAMS, PS_CALCIO, TR_DEFAULT)
    assert "A" in result and "B" in result
    assert {e.team_id for e in result["A"]} == {"A", "B"}
    assert {e.team_id for e in result["B"]} == {"C", "D"}
