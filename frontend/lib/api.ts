import type { TournamentCreate, TournamentSchema, TeamUpdate, RegistrationConfig } from '@/types/schema'

const BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL!

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message)
    this.name = 'ApiError'
  }
}

async function apiFetch<T = unknown>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json() as Promise<T>
}

async function publicFetch<T = unknown>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options.headers },
  })
  if (!res.ok) throw new ApiError(res.status, await res.text())
  return res.json() as Promise<T>
}

export async function createTournament(data: TournamentCreate, token: string): Promise<{ tournament_id: string; slug: string }> {
  return apiFetch<{ tournament_id: string; slug: string }>('/tournaments', token, { method: 'POST', body: JSON.stringify(data) })
}

export async function patchTeam(tId: string, teamId: string, data: TeamUpdate, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/tournaments/${tId}/teams/${teamId}`, token, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function generateSchedule(tId: string, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/tournaments/${tId}/generate-schedule`, token, { method: 'POST' })
}

export async function updateSchema(tId: string, schema: TournamentSchema, token: string): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/tournaments/${tId}/schema`, token, {
    method: 'PUT',
    body: JSON.stringify(schema),
  })
}

export async function submitResult(
  tournamentId: string,
  matchId: string,
  data: { home_goals: number; away_goals: number },
  token: string
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(
    `/tournaments/${tournamentId}/matches/${matchId}/result`,
    token,
    { method: 'POST', body: JSON.stringify(data) }
  )
}

export async function getRegistrationConfig(tournamentId: string): Promise<RegistrationConfig> {
  return publicFetch<RegistrationConfig>(`/tournaments/${tournamentId}/registration-config`)
}

export async function registerTeam(
  tournamentId: string,
  data: {
    fields: Record<string, unknown>
    invite_code?: string
    availability_slots: { slot_id: string; available: boolean }[]
  }
): Promise<{ team_id: string; team_code_plain: string }> {
  return publicFetch<{ team_id: string; team_code_plain: string }>(
    `/tournaments/${tournamentId}/register`,
    { method: 'POST', body: JSON.stringify(data) }
  )
}

export async function loginTeam(
  tournamentId: string,
  teamId: string,
  teamCode: string
): Promise<{ access_token: string; token_type: string }> {
  return publicFetch<{ access_token: string; token_type: string }>(
    `/tournaments/${tournamentId}/teams/${teamId}/auth`,
    { method: 'POST', body: JSON.stringify({ team_code: teamCode }) }
  )
}

export async function updateTournamentConfig(
  tId: string,
  data: { start_date?: string; edit_deadline?: string },
  token: string
): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/tournaments/${tId}/config`, token, {
    method: 'PATCH',
    body: JSON.stringify(data),
  })
}

export async function getTeamPlayers(
  tId: string,
  teamId: string,
  teamJwt: string
): Promise<{ players: Record<string, unknown>[] }> {
  return apiFetch<{ players: Record<string, unknown>[] }>(
    `/tournaments/${tId}/teams/${teamId}/players`,
    teamJwt
  )
}

export async function updatePlayers(
  tId: string,
  teamId: string,
  players: Record<string, unknown>[],
  teamJwt: string
): Promise<{ updated: number }> {
  return apiFetch<{ updated: number }>(
    `/tournaments/${tId}/teams/${teamId}/players`,
    teamJwt,
    { method: 'PUT', body: JSON.stringify({ players }) }
  )
}

export async function getTournamentBySlug(slug: string): Promise<{ tournament_id: string; name: string; logo_url: string | null }> {
  const apiUrl = process.env.RAILWAY_API_URL || process.env.NEXT_PUBLIC_RAILWAY_API_URL || 'http://localhost:8000'
  const res = await fetch(`${apiUrl}/tournaments/by-slug/${slug}`, { next: { revalidate: 60 } } as RequestInit)
  if (!res.ok) throw new Error(`Tournament not found: ${slug}`)
  return res.json()
}
