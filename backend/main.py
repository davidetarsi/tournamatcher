from __future__ import annotations
from fastapi import FastAPI
from routers import tournaments, teams, schedule

app = FastAPI()
app.include_router(tournaments.router)
app.include_router(teams.router)
app.include_router(schedule.router)
