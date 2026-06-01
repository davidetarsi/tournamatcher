export type FieldType = 'text' | 'email' | 'number' | 'date'

export interface SchemaField {
  key: string
  type: FieldType
  required: boolean
  max_length?: number
}

export interface InviteCodes {
  enabled: boolean
  partial: boolean
}

export interface AdminControls {
  can_set_strength: boolean
  max_teams: number
}

export interface PointsSystem {
  win: number
  draw: number
  loss: number
  draws_allowed: boolean
}

export type TiebreakerRule = 'goal_difference' | 'goals_for' | 'head_to_head'

export interface TournamentSchema {
  sport: string
  max_teams: number
  teams_per_group: number
  public: boolean
  invite_codes: InviteCodes
  team_fields: SchemaField[]
  player_fields: SchemaField[]
  admin_controls: AdminControls
  points_system: PointsSystem
  tiebreaker_rules: TiebreakerRule[]
}

export interface Tournament {
  id: string
  name: string
  admin_uid: string
  public: boolean
  status: 'draft' | 'scheduled'
  points_system?: PointsSystem
}

export interface Team {
  id: string
  nome: string
  forza: number
  confirmed: boolean
  owner_uid: string
}

export interface TournamentCreate {
  name: string
  schema_config: TournamentSchema
}

export interface TeamUpdate {
  forza?: number
  confirmed?: boolean
}

export interface StandingsEntry {
  team_id: string
  team_name: string
  played: number
  wins: number
  draws: number
  losses: number
  goals_for: number
  goals_against: number
  goal_difference: number
  points: number
  position: number
}

export interface Match {
  id: string
  giorno: number
  slot: number
  girone: string
  squadre: [string, string]
  home_goals: number | null
  away_goals: number | null
  played_at: string | null
}
