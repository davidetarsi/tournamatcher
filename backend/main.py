from __future__ import annotations
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from limiter import limiter
from routers import tournaments, teams, schedule, results

app = FastAPI(title="Tournament Manager API")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(schedule.router)
app.include_router(results.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
