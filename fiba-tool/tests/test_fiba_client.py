import json
import os

import pytest

import fiba_client
from fiba_client import (extract_player_id, fetch_team_players,
                         parse_player_payload)

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures",
                       "player_response.json")


def test_extract_player_id():
    assert extract_player_id(
        "https://play.fiba3x3.com/players/abc-123") == "abc-123"


def test_extract_player_id_url_invalido():
    with pytest.raises(ValueError, match="non riconosciuto"):
        extract_player_id("https://esempio.com/giocatore/9")


def test_parse_fixture_reale():
    with open(FIXTURE, encoding="utf-8") as f:
        dati = parse_player_payload(json.load(f))
    assert set(dati) == {"id", "nome", "ranking_points"}
    assert isinstance(dati["ranking_points"], int)
    assert dati["nome"]


def test_fetch_team_players_mai_tutto_o_niente(monkeypatch):
    def finto_fetch(url, session=None, timeout=10):
        if "rotto" in url:
            raise RuntimeError("profilo non trovato")
        return {"id": "x", "nome": "X", "ranking_points": 10,
                "fetched_at": "2026-07-20T00:00:00+00:00"}

    monkeypatch.setattr(fiba_client, "fetch_player", finto_fetch)
    urls = ["https://play.fiba3x3.com/players/ok1",
            "https://play.fiba3x3.com/players/rotto",
            "https://play.fiba3x3.com/players/ok2"]
    r = fetch_team_players(urls, pausa=0)
    assert [x["ok"] for x in r] == [True, False, True]
    assert "profilo non trovato" in r[1]["errore"]
