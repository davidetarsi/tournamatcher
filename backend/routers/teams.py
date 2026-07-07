import hmac
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ValidationError
from auth import verify_token
from db import get_db
from dependencies import verify_team_jwt
from limiter import limiter
from models import AvailabilitySlot, TeamPublicRegister, TeamLoginRequest, PlayerUpdate
from schema_engine import build_team_model, sanitize
from google.cloud import firestore as _firestore
from services.auth_service import generate_pin, hash_pin, create_team_token
from services.tournament_service import get_effective_deadline

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["teams"])


class _RegistrationError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail


@_firestore.transactional
def _register_in_transaction(transaction, tournament_ref, sanitized_fields, payload, schema):
    stats_ref = tournament_ref.collection("metadata").document("stats")
    stats_doc = stats_ref.get(transaction=transaction)
    stats_data = (stats_doc.to_dict() if stats_doc.exists else None) or {"public_count": 0, "invite_count": 0}
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
        "players": [],
    })
    transaction.set(stats_ref, new_stats, merge=True)

    return team_id, pin


class TeamUpdate(BaseModel):
    forza: Optional[int] = None       # 1-5, set by admin
    confirmed: Optional[bool] = None  # admin confirms team


@router.put("/teams/{team_id}/availability")
@limiter.limit("30/minute")
async def update_availability(
    request: Request,
    tournament_id: str,
    team_id: str,
    slots: List[AvailabilitySlot],
    team: dict = Depends(verify_team_jwt),
    db=Depends(get_db),
):
    schema_doc = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("config")
        .document("schema")
        .get()
    )
    schema = schema_doc.to_dict() or {}
    deadline = get_effective_deadline(schema)
    if deadline and datetime.now(timezone.utc) > deadline:
        raise HTTPException(403, "Modifiche non più consentite: scadenza superata")

    team_ref = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
    )
    team_ref.update({"availability": [slot.model_dump() for slot in slots]})

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


@router.get("/teams/{team_id}/players")
@limiter.limit("30/minute")
async def get_players(
    request: Request,
    tournament_id: str,
    team_id: str,
    team: dict = Depends(verify_team_jwt),
    db=Depends(get_db),
):
    team_doc = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
        .get()
    )
    if not team_doc.exists:
        raise HTTPException(404, "Squadra non trovata")
    players = (team_doc.to_dict() or {}).get("players", [])
    return {"players": players}


@router.put("/teams/{team_id}/players")
@limiter.limit("20/minute")
async def update_players(
    request: Request,
    tournament_id: str,
    team_id: str,
    payload: PlayerUpdate,
    team: dict = Depends(verify_team_jwt),
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    schema_doc = t_ref.collection("config").document("schema").get()
    schema = schema_doc.to_dict() or {}

    deadline = get_effective_deadline(schema)
    if deadline and datetime.now(timezone.utc) > deadline:
        raise HTTPException(403, "Modifiche non più consentite: scadenza superata")

    player_fields = schema.get("player_fields", [])
    PlayerModel = build_team_model({"team_fields": player_fields})

    sanitized_players = []
    for i, p in enumerate(payload.players):
        try:
            validated = PlayerModel(**p)
        except ValidationError as e:
            raise HTTPException(422, f"Giocatore {i + 1}: {e.errors()}")
        sanitized = {
            k: sanitize(v) if isinstance(v, str) else v
            for k, v in validated.model_dump().items()
        }
        sanitized_players.append(sanitized)

    team_ref = t_ref.collection("teams").document(team_id)
    if not team_ref.get().exists:
        raise HTTPException(404, "Squadra non trovata")
    team_ref.update({"players": sanitized_players})
    return {"updated": len(sanitized_players)}


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
    except ValidationError as e:
        raise HTTPException(422, e.errors())

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


@router.post("/teams/{team_id}/auth")
@limiter.limit("5/minute")
async def team_login(
    request: Request,
    tournament_id: str,
    team_id: str,
    payload: TeamLoginRequest,
    db=Depends(get_db),
):
    team_doc = (
        db.collection("tournaments")
        .document(tournament_id)
        .collection("teams")
        .document(team_id)
        .get()
    )
    if not team_doc.exists:
        raise HTTPException(404, "Squadra non trovata")
    stored_hash = (team_doc.to_dict() or {}).get("team_code_hash") or ""
    if not hmac.compare_digest(hash_pin(payload.team_code), stored_hash):
        raise HTTPException(403, "Codice non valido")
    token = create_team_token(tournament_id, team_id)
    return {"access_token": token, "token_type": "bearer"}
