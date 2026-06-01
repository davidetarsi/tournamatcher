import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from auth import verify_token
from db import get_db
from limiter import limiter
from models import TournamentCreate, SchemaConfig

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.post("", status_code=201)
@limiter.limit("10/minute")
async def create_tournament(
    request: Request,
    payload: TournamentCreate,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    tournament_id = str(uuid.uuid4())
    ref = db.collection("tournaments").document(tournament_id)

    ref.set({
        "name": payload.name,
        "admin_uid": user["uid"],
        "public": payload.schema_config.public,
        "status": "draft",
    })

    ref.collection("config").document("schema").set(
        payload.schema_config.model_dump()
    )

    return {"tournament_id": tournament_id}


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
