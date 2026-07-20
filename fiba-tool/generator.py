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


def combinazioni_valide(num_squadre, num_gironi):
    """Coppie (giorni, slot_al_giorno) che soddisfano la capacità esatta."""
    per_girone = num_squadre // num_gironi
    slot_totali = num_squadre * (per_girone - 1) // 2
    out = []
    for giorni in range(1, slot_totali + 1):
        slot, resto = divmod(slot_totali, giorni)
        if resto == 0:
            out.append((giorni, slot))
    return out


def valida_parametri(num_squadre, num_gironi, num_giorni, num_partite_giorno):
    if num_gironi < 1 or num_squadre < 2:
        raise ValueError("Servono almeno 2 squadre e 1 girone")
    if num_squadre % num_gironi != 0:
        raise ValueError(
            f"{num_squadre} squadre non divisibili in {num_gironi} gironi uguali")
    per_girone = num_squadre // num_gironi
    slot_totali = num_squadre * (per_girone - 1) // 2
    if num_giorni * num_partite_giorno != slot_totali:
        valide = ", ".join(f"{g} giorni × {s} slot"
                           for g, s in combinazioni_valide(num_squadre, num_gironi))
        raise ValueError(
            f"Capacità errata: servono {slot_totali} slot totali, "
            f"ne hai {num_giorni * num_partite_giorno}. Combinazioni valide: {valide}")
