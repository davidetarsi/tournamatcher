'use client'
import { useEffect, useState } from 'react'
import { collection, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useTeamMatches } from '@/lib/hooks/useTeamMatches'
import { TeamCodeEntry } from '@/components/tournament/TeamCodeEntry'
import { getRegistrationConfig } from '@/lib/api'
import { PlayerEditor } from '@/components/tournament/PlayerEditor'
import type { Match, StandingsEntry, RegistrationConfig } from '@/types/schema'

interface Props {
  params: { id: string; teamId: string }
}

function matchOutcome(m: Match, teamId: string): 'V' | 'P' | 'S' | null {
  if (m.home_goals === null || m.away_goals === null) return null
  const isHome = m.squadre[0] === teamId
  const myGoals = isHome ? m.home_goals : m.away_goals
  const oppGoals = isHome ? m.away_goals : m.home_goals
  if (myGoals > oppGoals) return 'V'
  if (myGoals < oppGoals) return 'S'
  return 'P'
}

const outcomeStyle: Record<string, string> = {
  V: 'bg-green-100 text-green-800',
  P: 'bg-yellow-100 text-yellow-800',
  S: 'bg-red-100 text-red-800',
}

function effectiveDeadline(cfg: RegistrationConfig): string | null {
  if (cfg.edit_deadline) return cfg.edit_deadline
  if (cfg.start_date) {
    // start_date is "YYYY-MM-DD"; compute midnight UTC, subtract 1 day, set 23:59 UTC
    const d = new Date(cfg.start_date + 'T00:00:00Z')
    d.setUTCDate(d.getUTCDate() - 1)
    d.setUTCHours(23, 59, 0, 0)
    return d.toISOString()
  }
  return null
}

export default function TeamPage({ params }: Props) {
  const { id: tournamentId, teamId } = params
  const { matches, loading } = useTeamMatches(tournamentId, teamId)
  const [teamNames, setTeamNames] = useState<Record<string, string>>({})
  const [teamName, setTeamName] = useState<string>(teamId)
  const [jwt, setJwt] = useState<string | null | undefined>(undefined)
  const [config, setConfig] = useState<RegistrationConfig | null>(null)

  useEffect(() => {
    // localStorage not available during SSR; undefined = not-yet-checked, null = checked+absent
    const stored = localStorage.getItem(`team_jwt_${teamId}`)
    setJwt(stored)
  }, [teamId])

  useEffect(() => {
    getRegistrationConfig(tournamentId)
      .then(setConfig)
      .catch(() => {})
  }, [tournamentId])

  useEffect(() => {
    const unsub = onSnapshot(
      collection(db, 'tournaments', tournamentId, 'standings'),
      (snap) => {
        const names: Record<string, string> = {}
        snap.docs.forEach((d) => {
          const entries: StandingsEntry[] = d.data().entries ?? []
          entries.forEach((e) => { names[e.team_id] = e.team_name })
        })
        setTeamNames(names)
        if (names[teamId]) setTeamName(names[teamId])
      },
      () => {}
    )
    return unsub
  }, [tournamentId, teamId])

  if (jwt === undefined) return <div className="p-6">Caricamento...</div>

  const searchParams = typeof window !== 'undefined'
    ? new URLSearchParams(window.location.search)
    : new URLSearchParams()
  const message = searchParams.get('message')

  if (jwt === null) {
    return (
      <div>
        {message && <p className="p-4 text-sm text-amber-700 bg-amber-50 border-b">{decodeURIComponent(message)}</p>}
        <TeamCodeEntry
          tournamentId={tournamentId}
          teamId={teamId}
          onSuccess={(token) => setJwt(token)}
        />
      </div>
    )
  }

  if (loading) return <div className="p-6">Caricamento partite...</div>

  const wins = matches.filter((m) => matchOutcome(m, teamId) === 'V').length
  const draws = matches.filter((m) => matchOutcome(m, teamId) === 'P').length
  const losses = matches.filter((m) => matchOutcome(m, teamId) === 'S').length

  return (
    <main className="container mx-auto p-6 max-w-lg">
      <h1 className="text-2xl font-bold mb-1">{teamName}</h1>
      <div className="flex gap-3 mb-6 text-sm text-gray-600">
        <span className="text-green-700 font-semibold">{wins}V</span>
        <span className="text-yellow-700 font-semibold">{draws}P</span>
        <span className="text-red-700 font-semibold">{losses}S</span>
      </div>
      <div className="space-y-2">
        {matches.map((m) => {
          const isHome = m.squadre[0] === teamId
          const opponentId = isHome ? m.squadre[1] : m.squadre[0]
          const opponent = teamNames[opponentId] ?? opponentId
          const myGoals = isHome ? m.home_goals : m.away_goals
          const oppGoals = isHome ? m.away_goals : m.home_goals
          const outcome = matchOutcome(m, teamId)
          return (
            <div key={m.id} className="flex items-center gap-3 p-3 border rounded text-sm">
              <span className="text-gray-400 w-16 shrink-0">Giorno {m.giorno}</span>
              <span className="flex-1 font-medium">vs {opponent}</span>
              {myGoals !== null && oppGoals !== null ? (
                <span className="font-mono">{myGoals} – {oppGoals}</span>
              ) : (
                <span className="text-gray-400">– · –</span>
              )}
              {outcome && (
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${outcomeStyle[outcome]}`}>
                  {outcome}
                </span>
              )}
            </div>
          )
        })}
        {matches.length === 0 && <p className="text-gray-500 text-sm">Nessuna partita trovata.</p>}
      </div>
      {jwt && config && config.player_fields.length > 0 && (
        <PlayerEditor
          tournamentId={tournamentId}
          teamId={teamId}
          teamJwt={jwt}
          playerFields={config.player_fields}
          deadline={effectiveDeadline(config)}
        />
      )}
    </main>
  )
}
