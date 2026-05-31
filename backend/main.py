from __future__ import annotations
from fastapi import FastAPI
from routers import tournaments

app = FastAPI()
app.include_router(tournaments.router)
