from generator import punteggio_squadra, sbilanciamento, snake_draft


def squadra(nome, punti_giocatori):
    return {
        "id": nome,
        "nome": nome,
        "giocatori": [{"url": f"https://play.fiba3x3.com/players/{nome}{i}",
                       "nome": f"g{i}", "ranking_points": p,
                       "fetch_status": "ok", "fetched_at": None}
                      for i, p in enumerate(punti_giocatori)],
        "disponibilita": [],
        "da_riconfermare": False,
    }


def test_punteggio_somma_migliori_3():
    s = squadra("A", [100, 400, 200, 300])  # 4 giocatori: i 3 migliori sono 400+300+200
    assert punteggio_squadra(s) == 900


def test_punteggio_con_dati_incompleti():
    assert punteggio_squadra(squadra("A", [100, None])) == 100
    assert punteggio_squadra(squadra("A", [])) == 0


def test_snake_draft_pattern():
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    squadre = [squadra(f"S{p}", [p]) for p in punti]
    gironi = snake_draft(squadre, 2)
    nomi = [[s["nome"] for s in g] for g in gironi]
    # andata 1-2, ritorno 2-1: girone0 = 1°,4°,5°,8° ; girone1 = 2°,3°,6°,7°
    assert nomi[0] == ["S800", "S500", "S400", "S100"]
    assert nomi[1] == ["S700", "S600", "S300", "S200"]


def test_teste_di_serie_una_per_girone():
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    squadre = [squadra(f"S{p}", [p]) for p in punti]
    gironi = snake_draft(squadre, 4)
    prime = {g[0]["nome"] for g in gironi}
    assert prime == {"S800", "S700", "S600", "S500"}


def test_sbilanciamento():
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    gironi = snake_draft([squadra(f"S{p}", [p]) for p in punti], 2)
    assert sbilanciamento(gironi) == 0  # 800+500+400+100 == 700+600+300+200
