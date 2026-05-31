from __future__ import annotations
import random
from itertools import combinations
from ortools.sat.python import cp_model


def crea_gironi_bilanciati(
    teams: dict,
    num_gironi: int,
    soglia: int = 2,
    max_tentativi: int = 1_000_000,
) -> list[list[str]]:
    """
    Distribuisce le squadre in gironi bilanciati (differenza forza totale <= soglia).
    Ogni girone ha esattamente una testa di serie (forza == 5).
    """
    lista = list(teams.values())
    top_seeds = [s for s in lista if s["forza"] == 5]

    if len(top_seeds) < num_gironi:
        raise ValueError(f"Teste di serie insufficienti: {len(top_seeds)} < {num_gironi}")

    for _ in range(max_tentativi):
        random.shuffle(lista)
        seeds_sample = random.sample(top_seeds, num_gironi)
        gironi: list[list] = [[s] for s in seeds_sample]
        altri = [s for s in lista if s not in seeds_sample]

        for i, s in enumerate(altri):
            gironi[i % num_gironi].append(s)

        somme = [sum(s["forza"] for s in g) for g in gironi]
        if max(somme) - min(somme) <= soglia:
            return [[s["nome"] for s in g] for g in gironi]

    raise ValueError(f"Nessun girone bilanciato trovato dopo {max_tentativi} tentativi")


def generate_schedule(
    gironi: list[list[str]],
    teams: dict,
    num_giorni: int,
    num_slots: int,
) -> dict | None:
    """
    Genera un calendario ottimizzato con OR-Tools CP-SAT.

    Args:
        gironi: lista di gironi, ognuno lista di nomi squadra
        teams: {nome: {forza, disponibilita: list[list[int]]}}
        num_giorni: numero di giorni
        num_slots: slot per giorno

    Returns:
        {giorno: {slot: [{girone, squadre}]}} oppure None se infeasible
    """
    model = cp_model.CpModel()
    matches = []

    for i, girone in enumerate(gironi):
        matches += [(a, b, i + 1) for a, b in combinations(girone, 2)]

    vars_ = []
    for s1, s2, _ in matches:
        disponibili = [
            g * num_slots + s
            for g in range(num_giorni)
            for s in range(num_slots)
            if teams[s1]["disponibilita"][g][s] and teams[s2]["disponibilita"][g][s]
        ]
        if not disponibili:
            return None  # nessuno slot comune → infeasible

        var = model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(disponibili), f"m_{s1}_{s2}"
        )
        vars_.append(var)

    model.AddAllDifferent(vars_)

    solver = cp_model.CpSolver()
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return None

    calendario: dict = {g: {s: [] for s in range(num_slots)} for g in range(num_giorni)}
    for idx, (s1, s2, g) in enumerate(matches):
        encoded = solver.Value(vars_[idx])
        giorno = encoded // num_slots
        slot = encoded % num_slots
        calendario[giorno][slot].append({"girone": g, "squadre": [s1, s2]})

    return calendario
