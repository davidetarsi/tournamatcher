import pytest

from generator import assegna_fasce, combinazioni_valide, punteggio_squadra, sbilanciamento, snake_draft, valida_parametri


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


def test_combinazioni_valide_120x20():
    # 120 squadre, 20 gironi → 300 slot totali: 15 giorni × 20 slot è il caso storico
    assert (15, 20) in combinazioni_valide(120, 20)


def test_valida_parametri_ok():
    valida_parametri(120, 20, 15, 20)  # non deve sollevare


def test_valida_parametri_capacita_errata():
    with pytest.raises(ValueError, match="Combinazioni valide"):
        valida_parametri(120, 20, 14, 20)


def test_valida_parametri_non_divisibile():
    with pytest.raises(ValueError, match="divisibili"):
        valida_parametri(10, 3, 5, 2)


def test_assegna_fasce_teste_di_serie():
    # 2 gironi → le 2 squadre più forti sono fascia 5 (teste di serie)
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    squadre = [squadra(f"S{p}", [p]) for p in punti]
    fasce = assegna_fasce(squadre, 2)
    cinque = {s["nome"] for s in squadre if fasce[id(s)] == 5}
    assert cinque == {"S800", "S700"}


def test_assegna_fasce_resto_non_divisibile_per_4():
    # 2 teste di serie + 6 resto → dimensione ceil(6/4)=2 → fasce 4,4,3,3,2,2
    punti = [800, 700, 600, 500, 400, 300, 200, 100]
    squadre = [squadra(f"S{p}", [p]) for p in punti]
    fasce = assegna_fasce(squadre, 2)
    per_nome = {s["nome"]: fasce[id(s)] for s in squadre}
    assert [per_nome[f"S{p}"] for p in punti] == [5, 5, 4, 4, 3, 3, 2, 2]


def test_assegna_fasce_meno_di_4_nel_resto():
    # 2 teste di serie + 2 resto: nessuna divisione per zero, fasce valide 1..5
    squadre = [squadra(f"S{p}", [p]) for p in [500, 400, 300, 200]]
    fasce = assegna_fasce(squadre, 2)
    assert sorted(fasce.values(), reverse=True) == [5, 5, 4, 4]


def test_snake_draft_con_chiave_fasce_una_testa_di_serie_per_girone():
    # Con un outlier enorme, il seeding per fascia mette comunque
    # una sola testa di serie (fascia 5) per girone.
    punti = [26009, 7062, 4985, 3883, 3883, 3883, 3883, 3883]
    squadre = [squadra(f"S{i}", [p]) for i, p in enumerate(punti)]
    fasce = assegna_fasce(squadre, 2)
    gironi = snake_draft(squadre, 2, chiave=lambda s: fasce[id(s)])
    # ogni girone ha esattamente una fascia-5
    for g in gironi:
        assert sum(1 for s in g if fasce[id(s)] == 5) == 1
    # e le somme di fascia dei due gironi sono bilanciate (delta piccolo)
    somme_fascia = [sum(fasce[id(s)] for s in g) for g in gironi]
    assert max(somme_fascia) - min(somme_fascia) <= 1
