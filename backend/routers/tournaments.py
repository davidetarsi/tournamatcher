import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from firebase_admin import firestore as fa_firestore
from auth import verify_token
from db import get_db
from limiter import limiter
from models import TournamentCreate, SchemaConfig, TournamentConfigUpdate
from services.tournament_service import generate_slug, reserve_slug_in_transaction

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("/by-slug/{slug}")
@limiter.limit("30/minute")
async def get_tournament_by_slug(
    request: Request,
    slug: str,
    db=Depends(get_db),
):
    slug_doc = db.collection("tournament_slugs").document(slug).get()
    if not slug_doc.exists:
        raise HTTPException(status_code=404, detail="Torneo non trovato")
    tournament_id = slug_doc.to_dict()["tournament_id"]
    t_doc = db.collection("tournaments").document(tournament_id).get()
    if not t_doc.exists:
        raise HTTPException(status_code=404, detail="Torneo non trovato")
    t_data = t_doc.to_dict()
    return {
        "tournament_id": tournament_id,
        "name": t_data["name"],
        "logo_url": t_data.get("logo_url"),
    }


@router.get("/my-tournaments")
@limiter.limit("20/minute")
async def get_my_tournaments(
    request: Request,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    tournaments = (
        db.collection("tournaments")
        .where("admin_uid", "==", user["uid"])
        .order_by("created_at", direction="DESCENDING")
        .stream()
    )
    result = []
    for t in tournaments:
        d = t.to_dict()
        result.append({
            "name": d["name"],
            "slug": d.get("slug", ""),
            "status": d.get("status", "draft"),
        })
    return result


@router.post("", status_code=201)
@limiter.limit("10/minute")
async def create_tournament(
    request: Request,
    payload: TournamentCreate,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    tournament_id = str(uuid.uuid4())
    base_slug = generate_slug(payload.name, payload.start_date)

    slugs_ref = db.collection("tournament_slugs")
    t_ref = db.collection("tournaments").document(tournament_id)
    doc_data = {
        "name": payload.name,
        "admin_uid": user["uid"],
        "public": payload.schema_config.public,
        "status": "draft",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    @fa_firestore.transactional
    def _txn(transaction):
        return reserve_slug_in_transaction(
            transaction, slugs_ref, base_slug, tournament_id, t_ref, doc_data
        )

    slug = _txn(db.transaction())

    t_ref.collection("config").document("schema").set(
        payload.schema_config.model_dump()
    )

    return {"tournament_id": tournament_id, "slug": slug}


@router.put("/{tournament_id}/schema")
@limiter.limit("10/minute")
async def update_schema(
    request: Request,
    tournament_id: str,
    schema: SchemaConfig,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    t = t_ref.get()
    if not t.exists:
        raise HTTPException(status_code=404, detail="Torneo non trovato")
    if t.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(status_code=403, detail="Non autorizzato")
    t_ref.collection("config").document("schema").set(schema.model_dump())
    return {"status": "updated"}


@router.patch("/{tournament_id}/config")
@limiter.limit("20/minute")
async def update_tournament_config(
    request: Request,
    tournament_id: str,
    payload: TournamentConfigUpdate,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    t = t_ref.get()
    if not t.exists:
        raise HTTPException(status_code=404, detail="Torneo non trovato")
    if t.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(status_code=403, detail="Non autorizzato")

    update_data: dict = {}
    if payload.start_date is not None:
        try:
            datetime.fromisoformat(payload.start_date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato data non valido")
        update_data["start_date"] = payload.start_date
    if payload.edit_deadline is not None:
        try:
            datetime.fromisoformat(payload.edit_deadline.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato data non valido")
        update_data["edit_deadline"] = payload.edit_deadline

    if not update_data:
        raise HTTPException(status_code=400, detail="Nessun campo da aggiornare")
    t_ref.collection("config").document("schema").set(update_data, merge=True)
    return {"status": "updated"}


@router.get("/{tournament_id}/registration-config")
@limiter.limit("30/minute")
async def get_registration_config(
    request: Request,
    tournament_id: str,
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    t = t_ref.get()
    if not t.exists:
        raise HTTPException(status_code=404, detail="Torneo non trovato")

    schema_doc = t_ref.collection("config").document("schema").get()
    if not schema_doc.exists:
        raise HTTPException(status_code=404, detail="Schema non trovato")

    schema = schema_doc.to_dict() or {}
    t_data = t.to_dict()

    return {
        "name": t_data["name"],
        "sport": schema.get("sport", ""),
        "invite_codes": schema.get("invite_codes", {"enabled": False, "partial": False}),
        "team_fields": schema.get("team_fields", []),
        "player_fields": schema.get("player_fields", []),
        "num_giorni": schema.get("num_giorni", 1),
        "num_slots_per_giorno": schema.get("num_slots_per_giorno", 1),
        "max_public_teams": schema.get("max_public_teams", 0),
        "max_teams": schema.get("max_teams", 0),
        "start_date": schema.get("start_date"),
        "edit_deadline": schema.get("edit_deadline"),
    }
