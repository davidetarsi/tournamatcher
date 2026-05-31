from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends, HTTPException
from auth import verify_token
from db import get_db
from models import TeamRegister, AvailabilitySlot
from schema_engine import build_team_model, sanitize

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["teams"])


@router.post("/teams", status_code=201)
async def register_team(
    tournament_id: str,
    payload: TeamRegister,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    schema_doc = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("config")
        .document("schema")
        .get()
    )
    if not schema_doc.exists:
        raise HTTPException(404, "Torneo non trovato")

    schema = schema_doc.to_dict()
    TeamModel = build_team_model(schema)

    try:
        validated = TeamModel(**payload.fields)
    except Exception as e:
        raise HTTPException(422, str(e))

    sanitized_data = {
        k: sanitize(v) if isinstance(v, str) else v
        for k, v in validated.model_dump().items()
    }

    team_id = str(uuid.uuid4())
    ref = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
    )
    ref.set({
        **sanitized_data,
        "owner_uid": user["uid"],
        "confirmed": False,
    })

    return {"team_id": team_id}


@router.put("/teams/{team_id}/availability")
async def update_availability(
    tournament_id: str,
    team_id: str,
    slots: list[AvailabilitySlot],
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    team_ref = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
    )
    team_doc = team_ref.get()
    if not team_doc.exists or team_doc.get("owner_uid") != user["uid"]:
        raise HTTPException(403, "Non autorizzato")

    slots_col = team_ref.collection("availability_slots")

    # Delete all existing slots first (replace-all semantics for PUT)
    existing = slots_col.stream()
    delete_batch = db.batch()
    for doc in existing:
        delete_batch.delete(doc.reference)
    delete_batch.commit()

    # Write new slots
    write_batch = db.batch()
    for slot in slots:
        write_batch.set(slots_col.document(slot.slot_id), slot.model_dump())
    write_batch.commit()

    return {"updated": len(slots)}
