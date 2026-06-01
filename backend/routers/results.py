from fastapi import APIRouter, Depends, HTTPException, Request
from google.cloud.firestore import SERVER_TIMESTAMP
from auth import verify_token
from db import get_db
from limiter import limiter
from models import MatchResult
from standings import compute_and_cache_standings

router = APIRouter(prefix="/tournaments/{tournament_id}", tags=["results"])


@router.post("/matches/{match_id}/result")
@limiter.limit("30/minute")
async def submit_result(
    request: Request,
    tournament_id: str,
    match_id: str,
    payload: MatchResult,
    user: dict = Depends(verify_token),
    db=Depends(get_db),
):
    t_ref = db.collection("tournaments").document(tournament_id)
    tournament = t_ref.get()
    if not tournament.exists:
        raise HTTPException(404, "Torneo non trovato")
    if tournament.to_dict().get("admin_uid") != user["uid"]:
        raise HTTPException(403, "Non autorizzato")

    schema_doc = t_ref.collection("config").document("schema").get()
    if schema_doc.exists:
        ps = schema_doc.to_dict().get("points_system", {})
        if not ps.get("draws_allowed", True) and payload.home_goals == payload.away_goals:
            raise HTTPException(422, "Pareggi non consentiti per questo sport")

    match_ref = t_ref.collection("matches").document(match_id)
    if not match_ref.get().exists:
        raise HTTPException(404, "Partita non trovata")

    match_ref.update({
        "home_goals": payload.home_goals,
        "away_goals": payload.away_goals,
        "played_at": SERVER_TIMESTAMP,
    })

    compute_and_cache_standings(db, tournament_id)

    return {"status": "ok"}
