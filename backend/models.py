from __future__ import annotations
from pydantic import BaseModel
from typing import Literal, Optional


class TeamField(BaseModel):
    key: str
    type: Literal["text", "email", "number", "date"]
    required: bool = True
    max_length: Optional[int] = None


class InviteCodes(BaseModel):
    enabled: bool = False
    partial: bool = False


class AdminControls(BaseModel):
    can_set_strength: bool = True
    max_teams: int


class SchemaConfig(BaseModel):
    sport: str
    max_teams: int
    teams_per_group: int
    public: bool = False
    invite_codes: InviteCodes
    team_fields: list[TeamField]
    player_fields: list[TeamField]
    admin_controls: AdminControls


class TournamentCreate(BaseModel):
    name: str
    schema_config: SchemaConfig


class TeamRegister(BaseModel):
    # Campi base sempre presenti; i campi dinamici vengono validati separatamente
    invite_code: Optional[str] = None
    fields: dict  # validato con build_team_model a runtime


class AvailabilitySlot(BaseModel):
    slot_id: str  # formato: "YYYY-MM-DD_HH" oppure indice numerico come stringa
    available: bool


class ScheduleRequest(BaseModel):
    tournament_id: str
