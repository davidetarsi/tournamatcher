"""Generatore gironi e calendario per fiba-tool.

Eseguibile standalone (vedi main() nel Task 4):
    python generator.py --squadre … --config … --output …
"""
import argparse
import json
import os
from collections import defaultdict
from itertools import combinations

from storage import load_json, save_json


def punteggio_squadra(squadra):
    punti = sorted((g.get("ranking_points") or 0 for g in squadra["giocatori"]),
                   reverse=True)
    return sum(punti[:3])


def snake_draft(squadre, num_gironi, chiave=punteggio_squadra):
    """Distribuzione a serpente: 1→N, N→1, 1→N… Le teste di serie (top-N per
    `chiave`) emergono dal primo giro. Euristica greedy, non un ottimo garantito.
    `chiave` di default ordina per punteggio reale; il CLI passa invece la fascia
    (vedi assegna_fasce) per un seeding insensibile agli outlier."""
    ordinate = sorted(squadre, key=chiave, reverse=True)
    gironi = [[] for _ in range(num_gironi)]
    for i, s in enumerate(ordinate):
        giro, pos = divmod(i, num_gironi)
        idx = pos if giro % 2 == 0 else num_gironi - 1 - pos
        gironi[idx].append(s)
    return gironi


def assegna_fasce(squadre, num_gironi):
    """Converte i punteggi reali in fasce 1-5 per RANGO (stile seeding pot, es.
    gironi del Mondiale FIFA). Insensibile agli outlier: guarda la posizione in
    classifica, non il valore assoluto — un punteggio enorme diventa "il numero 1"
    e non trascina più la somma del suo girone. Le prime num_gironi squadre sono
    fascia 5 (una testa di serie per girone); il resto si divide in 4 fasce il più
    possibile uguali per numero, con l'eventuale eccesso alle fasce più forti (ceil).
    Ritorna {id(squadra): fascia}."""
    ordinate = sorted(squadre, key=punteggio_squadra, reverse=True)
    teste_di_serie = ordinate[:num_gironi]
    resto = ordinate[num_gironi:]
    # Se resto < 4, tutte le squadre del resto vanno nella stessa fascia (4);
    # altrimenti dividiamo in 4 fasce uguali per numero (ceil)
    if len(resto) < 4:
        dimensione = len(resto)
    else:
        dimensione = max(1, -(-len(resto) // 4))  # ceil
    fasce = {id(s): 5 for s in teste_di_serie}
    for i, s in enumerate(resto):
        fasce[id(s)] = 4 - min(i // dimensione, 3)  # 4,3,2,1 a cascata
    return fasce


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


def genera_calendario(squadre, gironi, num_giorni, num_slots):
    from ortools.sat.python import cp_model
    per_id = {s["id"]: s for s in squadre}
    partite = []
    for gi, girone in enumerate(gironi):
        partite += [(a["id"], b["id"], gi + 1) for a, b in combinations(girone, 2)]
    model = cp_model.CpModel()
    variabili = []
    for idx, (s1, s2, _) in enumerate(partite):
        disponibili = [
            giorno * num_slots + slot
            for giorno in range(num_giorni)
            for slot in range(num_slots)
            if per_id[s1]["disponibilita"][giorno][slot]
            and per_id[s2]["disponibilita"][giorno][slot]]
        if not disponibili:
            raise ValueError(
                f"Nessuno slot comune tra {per_id[s1]['nome']} e {per_id[s2]['nome']}: "
                "le disponibilità sono troppo restrittive, servono più aperture")
        variabili.append(model.NewIntVarFromDomain(
            cp_model.Domain.FromValues(disponibili), f"m{idx}"))
    model.AddAllDifferent(variabili)
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ValueError("Nessuna soluzione trovata: le disponibilità sono troppo "
                         "restrittive, servono più slot o più aperture")
    calendario = {g: {s: [] for s in range(num_slots)} for g in range(num_giorni)}
    for idx, (s1, s2, gi) in enumerate(partite):
        v = solver.Value(variabili[idx])
        calendario[v // num_slots][v % num_slots].append(
            {"girone": gi, "squadre": [per_id[s1]["nome"], per_id[s2]["nome"]]})
    return calendario


def verifica(calendario):
    """Warning per partite consecutive della stessa squadra nello stesso giorno."""
    avvisi = []
    per_squadra = defaultdict(list)
    for giorno, slots in calendario.items():
        for slot, partite in slots.items():
            for p in partite:
                for nome in p["squadre"]:
                    per_squadra[nome].append((int(giorno), int(slot)))
    for nome, occorrenze in sorted(per_squadra.items()):
        per_giorno = defaultdict(list)
        for g, s in occorrenze:
            per_giorno[g].append(s)
        for g, ss in per_giorno.items():
            ss.sort()
            for a, b in zip(ss, ss[1:]):
                if b - a == 1:
                    avvisi.append(f"{nome}: partite consecutive giorno {g + 1}, "
                                  f"slot {a + 1} e {b + 1}")
    return avvisi


def testo_report(risultato):
    righe = [f"Sbilanciamento gironi: {risultato['sbilanciamento']} punti", "",
             "GIRONI:"]
    for g in risultato["gironi"]:
        righe.append(f"  Girone {g['numero']} ({g['punteggio_totale']} pt): "
                     + ", ".join(g["squadre"]))
    righe += ["", "CALENDARIO:"]
    for giorno in sorted(risultato["calendario"], key=int):
        righe.append(f"  Giorno {int(giorno) + 1}:")
        slots = risultato["calendario"][giorno]
        for slot in sorted(slots, key=int):
            for p in slots[slot]:
                righe.append(f"    Slot {int(slot) + 1}: {p['squadre'][0]} vs "
                             f"{p['squadre'][1]} (Girone {p['girone']})")
    if risultato["warnings"]:
        righe += ["", "WARNING:"] + [f"  - {w}" for w in risultato["warnings"]]
    return "\n".join(righe) + "\n"


def scrivi_status(cartella, **campi):
    save_json(os.path.join(cartella, "status.json"), {"tipo": "genera", **campi})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--squadre", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    os.makedirs(args.output, exist_ok=True)
    fase = "caricamento"
    try:
        scrivi_status(args.output, stato="in_corso", fase=fase)
        try:
            squadre = load_json(args.squadre, {"squadre": []})["squadre"]
            config = load_json(args.config, {})
        except json.JSONDecodeError as e:
            raise ValueError(f"File JSON non valido: {e}") from e
        try:
            valida_parametri(len(squadre), config["num_gironi"],
                             config["num_giorni"], config["num_partite_giorno"])
        except KeyError as e:
            raise ValueError(
                f"Parametro mancante in config.json: {e}") from e
        fase = "gironi"
        scrivi_status(args.output, stato="in_corso", fase=fase)
        # Seeding per fasce di rango: il bilanciamento gironi non usa i punti
        # reali assoluti (un outlier li distorce) ma le fasce 1-5 per rango.
        fasce = assegna_fasce(squadre, config["num_gironi"])
        gironi = snake_draft(squadre, config["num_gironi"],
                             chiave=lambda s: fasce[id(s)])
        fase = "calendario"
        scrivi_status(args.output, stato="in_corso", fase=fase)
        calendario = genera_calendario(squadre, gironi,
                                       config["num_giorni"],
                                       config["num_partite_giorno"])
        fase = "verifica"
        scrivi_status(args.output, stato="in_corso", fase=fase)
        avvisi = verifica(calendario)
        risultato = {
            "gironi": [{"numero": i + 1,
                        "squadre": [s["nome"] for s in g],
                        "punteggio_totale": sum(punteggio_squadra(s) for s in g)}
                       for i, g in enumerate(gironi)],
            "sbilanciamento": sbilanciamento(gironi),
            "calendario": calendario,
            "warnings": avvisi,
            "parametri": config,
        }
        save_json(os.path.join(args.output, "calendario_finale.json"), risultato)
        with open(os.path.join(args.output, "report.txt"), "w",
                  encoding="utf-8") as f:
            f.write(testo_report(risultato))
        scrivi_status(args.output, stato="completato", fase="fine",
                      warnings=len(avvisi))
    except Exception as e:
        scrivi_status(args.output, stato="errore", fase=fase, errore=str(e))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
