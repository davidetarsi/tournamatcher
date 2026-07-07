from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class TeamField(BaseModel):
    key: str
    type: Literal["text", "email", "number", "date"]
    required: bool = True
    max_length: Optional[int] = None


class AdminControls(BaseModel):
    can_set_strength: bool = True
    max_teams: int


class PointsSystem(BaseModel):
    win: int = 3
    draw: int = 1
    loss: int = 0
    draws_allowed: bool = True


class CampoGiornoSlots(BaseModel):
    campo: int
    giorno: int
    slots: List[str]  # ["15:00", "16:30", ...]


class SchemaConfig(BaseModel):
    sport: str
    max_teams: int
    teams_per_group: int
    public: bool = False
    team_fields: list[TeamField]
    player_fields: list[TeamField]
    admin_controls: AdminControls
    points_system: PointsSystem = Field(default_factory=PointsSystem)
    tiebreaker_rules: list[str] = Field(
        default_factory=lambda: ["goal_difference", "goals_for", "head_to_head"]
    )
    num_giorni: int = 1
    num_slots_per_giorno: int = 1
    num_campi: int = 1
    slot_orari: List[CampoGiornoSlots] = Field(default_factory=list)


class TournamentCreate(BaseModel):
    name: str
    schema_config: SchemaConfig
    start_date: Optional[str] = None   # ISO date "2026-07-15", used only for slug
    logo_base64: Optional[str] = None


class TeamPublicRegister(BaseModel):
    fields: dict
    availability_slots: list[AvailabilitySlot] = Field(default_factory=list)


class TeamLoginRequest(BaseModel):
    team_code: str


class AvailabilitySlot(BaseModel):
    slot_id: str
    available: bool


class ScheduleRequest(BaseModel):
    tournament_id: str


class MatchResult(BaseModel):
    home_goals: int = Field(ge=0)
    away_goals: int = Field(ge=0)


class StandingsEntry(BaseModel):
    team_id: str
    team_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    position: int


class TournamentConfigUpdate(BaseModel):
    start_date: Optional[str] = None     # ISO date "2026-07-15"
    edit_deadline: Optional[str] = None  # ISO datetime "2026-07-14T21:59:00Z"


class PlayerUpdate(BaseModel):
    players: list[dict]
