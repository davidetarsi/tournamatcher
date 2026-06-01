import type { TournamentCreate, TournamentSchema, TeamUpdate } from '@/types/schema'

const BASE = process.env.NEXT_PUBLIC_RAILWAY_API_URL!

async function apiFetch<T = unknown>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  })
  if (!res.ok) throw new Error(await res.text())
  return res.json() as Promise<T>
}

export async function createTournament(data: TournamentCreate, token: string): Promise<{ tournament_id: string }> {
  return apiFetch<{ tournament_id: string }>('/tournaments', token, { method: 'POST', body: JSON.stringify(data) })
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
