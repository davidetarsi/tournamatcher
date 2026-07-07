from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from google.cloud import firestore as _firestore
from auth import verify_token
from db import get_db
from limiter import limiter
from scheduler import crea_gironi_bilanciati, generate_schedule, parse_slot_id
from standings import compute_standings, DEFAULT_POINTS_SYSTEM, DEFAULT_TIEBREAKER_RULES

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["schedule"])


def _load_teams_from_firestore(
    db, tournament_id: str, num_giorni: int, num_slots: int
) -> tuple[dict, list[str]]:
    """
    Carica le squadre confermate leggendo il campo array `availability`
    del documento squadra (formato slot_id: 'g1_s1', scritto da POST /register).

    Returns:
        (teams, senza_disponibilita) dove teams è
        {team_id: {nome, display_name, forza, disponibilita: list[list[int]]}}
        — `nome` è il team_id (chiave usata da gironi e scheduler),
        `display_name` è il nome leggibile per le classifiche —
        e senza_disponibilita è la lista dei nomi delle squadre confermate
        che non hanno nessuno slot disponibile.
    """
    teams_stream = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .where("confirmed", "==", True)
        .stream()
    )

    teams: dict = {}
    senza_disponibilita: list[str] = []
    for doc in teams_stream:
        data = doc.to_dict()
        matrix = [[0] * num_slots for _ in range(num_giorni)]
        has_available = False
        for entry in data.get("availability", []):
            try:
                g, s = parse_slot_id(entry["slot_id"])
            except (ValueError, KeyError, TypeError):
                continue  # slot malformato: lo ignoriamo, non blocca le altre squadre
            if g < num_giorni and s < num_slots and entry.get("available"):
                matrix[g][s] = 1
                has_available = True

        if not has_available:
            senza_disponibilita.append(data.get("nome", doc.id))
            continue

        teams[doc.id] = {
            "nome": doc.id,
            "display_name": data.get("nome", doc.id),
            "forza": data.get("forza", 1),
            "disponibilita": matrix,
        }

    return teams, senza_disponibilita


@router.post("/generate-schedule")
@limiter.limit("3/minute")
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

    if tournament.to_dict().get("status") == "scheduled":
        raise HTTPException(409, "Calendario già generato per questo torneo")

    schema_doc = tournament_ref.collection("config").document("schema").get()
    if not schema_doc.exists:
        raise HTTPException(404, "Schema non trovato")

    schema = schema_doc.to_dict()
    num_gironi = schema["max_teams"] // schema["teams_per_group"]
    num_giorni_cal = schema.get("num_giorni", 1)
    num_slots_cal = schema.get("num_slots_per_giorno", 1)

    teams, senza_disponibilita = _load_teams_from_firestore(
        db, tournament_id, num_giorni_cal, num_slots_cal
    )
    if senza_disponibilita:
        raise HTTPException(
            400,
            "Squadre confermate senza slot di disponibilità: "
            + ", ".join(sorted(senza_disponibilita)),
        )
    if not teams:
        raise HTTPException(400, "Nessuna squadra confermata")

    # Gestione squadre dispari: aggiunge BYE
    if len(teams) % schema["teams_per_group"] != 0:
        teams["BYE"] = {
            "nome": "BYE",
            "display_name": "BYE",
            "forza": 0,
            "disponibilita": [[1] * num_slots_cal for _ in range(num_giorni_cal)],
        }

    try:
        gironi = crea_gironi_bilanciati(teams, num_gironi=num_gironi)
    except ValueError as e:
        raise HTTPException(400, str(e))

    calendario = generate_schedule(gironi, teams, num_giorni_cal, num_slots_cal)
    if calendario is None:
        raise HTTPException(400, "Impossibile generare il calendario con i vincoli attuali")

    # Scrittura ATOMICA: partite + classifiche azzerate + stato in un solo batch.
    # Le classifiche si calcolano in memoria dalle partite appena generate
    # (compute_standings è pura): zero letture Firestore aggiuntive.
    batch = db.batch()
    matches_col = tournament_ref.collection("matches")
    match_dicts: list[dict] = []
    for giorno, slots in calendario.items():
        for slot, partite in slots.items():
            for partita in partite:
                match_data = {
                    "giorno": giorno,
                    "slot": slot,
                    "girone": partita["girone"],
                    "squadre": partita["squadre"],
                    "home_goals": None,
                    "away_goals": None,
                }
                batch.set(matches_col.document(str(uuid.uuid4())), match_data)
                match_dicts.append(match_data)

    team_names = {tid: t["display_name"] for tid, t in teams.items()}
    standings = compute_standings(
        match_dicts,
        team_names,
        schema.get("points_system", DEFAULT_POINTS_SYSTEM),
        schema.get("tiebreaker_rules", list(DEFAULT_TIEBREAKER_RULES)),
    )
    standings_col = tournament_ref.collection("standings")
    for group_id, entries in standings.items():
        batch.set(
            standings_col.document(str(group_id)),
            {
                "group_name": str(group_id),
                "computed_at": _firestore.SERVER_TIMESTAMP,
                "entries": [e.model_dump() for e in entries],
            },
        )

    batch.update(tournament_ref, {"status": "scheduled"})
    batch.commit()

    return {"status": "generated", "matches": len(match_dicts)}
