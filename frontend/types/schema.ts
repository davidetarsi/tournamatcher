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

export interface TournamentSchema {
  sport: string
  max_teams: number
  teams_per_group: number
  public: boolean
  invite_codes: InviteCodes
  team_fields: SchemaField[]
  player_fields: SchemaField[]
  admin_controls: AdminControls
}

export interface Tournament {
  id: string
  name: string
  admin_uid: string
  public: boolean
  status: 'draft' | 'scheduled'
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
