import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from auth import verify_token
from db import get_db
from limiter import limiter
from models import TeamRegister, AvailabilitySlot, TeamPublicRegister
from schema_engine import build_team_model, sanitize
from google.cloud import firestore as _firestore
from services.auth_service import generate_pin, hash_pin

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["teams"])


class _RegistrationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


@_firestore.transactional
def _register_in_transaction(transaction, tournament_ref, sanitized_fields, payload, schema):
    stats_ref = tournament_ref.collection("metadata").document("stats")
    stats_doc = stats_ref.get(transaction=transaction)
    stats_data = stats_doc.to_dict() if stats_doc.exists else {"public_count": 0, "invite_count": 0}
    public_count = stats_data.get("public_count", 0)
    invite_count = stats_data.get("invite_count", 0)
    total_count = public_count + invite_count

    invite_cfg = schema.get("invite_codes", {"enabled": False, "partial": False})
    max_teams = schema.get("max_teams", 0)
    max_public = schema.get("max_public_teams", 0)

    if payload.invite_code:
        code_doc = (
            tournament_ref.collection("config")
            .document("invite_codes")
            .collection("codes")
            .document(payload.invite_code)
            .get(transaction=transaction)
        )
        if not code_doc.exists:
            raise _RegistrationError(403, "Invite code non valido")
        via = "invite"
        if invite_count >= (max_teams - max_public):
            raise _RegistrationError(409, "Posti su invito esauriti")
        new_stats = {"invite_count": invite_count + 1}
    else:
        if invite_cfg.get("enabled") and not invite_cfg.get("partial"):
            raise _RegistrationError(403, "Iscrizione solo su invito")
        via = "public"
        if invite_cfg.get("partial") and public_count >= max_public:
            raise _RegistrationError(409, "Posti pubblici esauriti")
        if not invite_cfg.get("enabled") and total_count >= max_teams:
            raise _RegistrationError(409, "Iscrizioni chiuse")
        new_stats = {"public_count": public_count + 1}

    pin = generate_pin()
    pin_hash = hash_pin(pin)
    team_id = str(uuid.uuid4())
    team_ref = tournament_ref.collection("teams").document(team_id)

    transaction.set(team_ref, {
        **sanitized_fields,
        "owner_uid": None,
        "confirmed": False,
        "team_code_hash": pin_hash,
        "registered_via": via,
        "availability": [slot.model_dump() for slot in payload.availability_slots],
    })
    transaction.set(stats_ref, new_stats, merge=True)

    return team_id, pin


class TeamUpdate(BaseModel):
    forza: Optional[int] = None       # 1-5, set by admin
    confirmed: Optional[bool] = None  # admin confirms team


@router.post("/teams", status_code=201)
@limiter.limit("5/minute")
async def register_team(
    request: Request,
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
@limiter.limit("30/minute")
async def update_availability(
    request: Request,
    tournament_id: str,
    team_id: str,
    slots: List[AvailabilitySlot],
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


@router.patch("/teams/{team_id}")
@limiter.limit("20/minute")
async def update_team(
    request: Request,
    tournament_id: str,
    team_id: str,
    payload: TeamUpdate,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    """Admin-only: set forza and/or confirmed status for a team."""
    tournament_ref = (
        db.collection("tournaments").document(tournament_id)
    )
    tournament = tournament_ref.get()
    if not tournament.exists or tournament.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(403, "Solo l'admin può aggiornare la squadra")

    update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(400, "Nessun campo da aggiornare")

    (
        tournament_ref.collection("teams").document(team_id).update(update_data)
    )
    return {"updated": list(update_data.keys())}


@router.post("/register", status_code=201)
@limiter.limit("10/minute")
async def public_register_team(
    request: Request,
    tournament_id: str,
    payload: TeamPublicRegister,
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    t = t_ref.get()
    if not t.exists:
        raise HTTPException(404, "Torneo non trovato")

    schema_doc = t_ref.collection("config").document("schema").get()
    if not schema_doc.exists:
        raise HTTPException(404, "Schema non trovato")

    schema = schema_doc.to_dict() or {}
    TeamModel = build_team_model(schema)
    try:
        validated = TeamModel(**payload.fields)
    except Exception as e:
        raise HTTPException(422, str(e))

    sanitized_data = {
        k: sanitize(v) if isinstance(v, str) else v
        for k, v in validated.model_dump().items()
    }

    try:
        team_id, pin = _register_in_transaction(
            db.transaction(), t_ref, sanitized_data, payload, schema
        )
    except _RegistrationError as e:
        raise HTTPException(e.status_code, e.detail)

    return {"team_id": team_id, "team_code_plain": pin}
