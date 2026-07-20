"""Generatore gironi e calendario per fiba-tool.

Eseguibile standalone (vedi main() nel Task 4):
    python generator.py --squadre … --config … --output …
"""


def punteggio_squadra(squadra):
    punti = sorted((g.get("ranking_points") or 0 for g in squadra["giocatori"]),
                   reverse=True)
    return sum(punti[:3])


def snake_draft(squadre, num_gironi):
    """Distribuzione a serpente: 1→N, N→1, 1→N… Le teste di serie (top-N)
    emergono dal primo giro. Euristica greedy, non un ottimo garantito."""
    ordinate = sorted(squadre, key=punteggio_squadra, reverse=True)
    gironi = [[] for _ in range(num_gironi)]
    for i, s in enumerate(ordinate):
        giro, pos = divmod(i, num_gironi)
        idx = pos if giro % 2 == 0 else num_gironi - 1 - pos
        gironi[idx].append(s)
    return gironi


def sbilanciamento(gironi):
    somme = [sum(punteggio_squadra(s) for s in g) for g in gironi]
    return max(somme) - min(somme)
