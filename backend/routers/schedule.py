from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from auth import verify_token
from db import get_db
from scheduler import crea_gironi_bilanciati, generate_schedule

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["schedule"])


def _load_teams_from_firestore(db, tournament_id: str) -> dict:
    """
    Carica squadre confermate e converte availability_slots in matrice 2D.
    slot_id format: "giorno_slot" (e.g. "0_1" = day 0, slot 1)
    """
    teams_stream = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .where("confirmed", "==", True)
        .stream()
    )

    teams = {}
    for doc in teams_stream:
        data = doc.to_dict()
        slots_stream = doc.reference.collection("availability_slots").stream()

        slot_map: dict = {}
        for s in slots_stream:
            sd = s.to_dict()
            parts = sd["slot_id"].split("_")
            key = (int(parts[0]), int(parts[1]))
            slot_map[key] = sd["available"]

        if not slot_map:
            continue

        num_giorni = max(k[0] for k in slot_map) + 1
        num_slots = max(k[1] for k in slot_map) + 1
        disponibilita = [
            [int(slot_map.get((g, s), False)) for s in range(num_slots)]
            for g in range(num_giorni)
        ]

        teams[doc.id] = {
            "nome": doc.id,
            "forza": data.get("forza", 1),
            "disponibilita": disponibilita,
        }

    return teams


@router.post("/generate-schedule")
async def generate_schedule_endpoint(
    request: Request,
    tournament_id: str,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    tournament_ref = db.collection("tournaments").document(tournament_id)
    tournament = tournament_ref.get()

    if not tournament.exists:
        raise HTTPException(404, "Torneo non trovato")

    if tournament.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(403, "Non autorizzato")

    schema_doc = tournament_ref.collection("config").document("schema").get()
    if not schema_doc.exists:
        raise HTTPException(404, "Schema non trovato")

    schema = schema_doc.to_dict()
    num_gironi = schema["max_teams"] // schema["teams_per_group"]

    teams = _load_teams_from_firestore(db, tournament_id)
    if not teams:
        raise HTTPException(400, "Nessuna squadra confermata")

    # Gestione squadre dispari: aggiunge BYE
    if len(teams) % schema["teams_per_group"] != 0:
        sample_team = next(iter(teams.values()))
        num_giorni_cal = len(sample_team["disponibilita"])
        num_slots_cal = len(sample_team["disponibilita"][0])
        teams["BYE"] = {
            "nome": "BYE",
            "forza": 0,
            "disponibilita": [[1] * num_slots_cal for _ in range(num_giorni_cal)],
        }

    sample_team = next(iter(teams.values()))
    num_giorni_cal = len(sample_team["disponibilita"])
    num_slots_cal = len(sample_team["disponibilita"][0])

    try:
        gironi = crea_gironi_bilanciati(teams, num_gironi=num_gironi)
    except ValueError as e:
        raise HTTPException(400, str(e))

    calendario = generate_schedule(gironi, teams, num_giorni_cal, num_slots_cal)
    if calendario is None:
        raise HTTPException(400, "Impossibile generare il calendario con i vincoli attuali")

    # Salva su Firestore via Admin SDK
    batch = db.batch()
    matches_col = tournament_ref.collection("matches")
    total_matches = 0
    for giorno, slots in calendario.items():
        for slot, partite in slots.items():
            for partita in partite:
                match_ref = matches_col.document(str(uuid.uuid4()))
                batch.set(match_ref, {
                    "giorno": giorno,
                    "slot": slot,
                    "girone": partita["girone"],
                    "squadre": partita["squadre"],
                })
                total_matches += 1
    batch.commit()

    tournament_ref.update({"status": "scheduled"})

    return {"status": "generated", "matches": total_matches}
