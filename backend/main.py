from __future__ import annotations
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from limiter import limiter
from routers import tournaments, teams, schedule, results


def parse_allowed_origins(raw: str) -> list[str]:
    """I browser inviano Origin senza trailing slash: normalizziamo per il match esatto."""
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


app = FastAPI(title="Tournament Manager API")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_allowed_origins(os.getenv("ALLOWED_ORIGINS", "http://localhost:3000")),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(schedule.router)
app.include_router(results.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
