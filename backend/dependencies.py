# backend/dependencies.py
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.auth_service import SECRET_KEY, ALGORITHM
import jwt

security = HTTPBearer()


async def verify_team_jwt(
    tournament_id: str,
    team_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("sub") != team_id or payload.get("tournament_id") != tournament_id:
            raise HTTPException(403, "Token non valido per questa risorsa")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token scaduto")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token non valido")
