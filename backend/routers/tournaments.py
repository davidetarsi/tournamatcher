from __future__ import annotations
import uuid
from fastapi import APIRouter, Depends
from auth import verify_token
from db import get_db
from models import TournamentCreate

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.post("", status_code=201)
async def create_tournament(
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
