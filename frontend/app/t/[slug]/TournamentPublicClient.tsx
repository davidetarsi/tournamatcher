'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useStandings } from '@/lib/hooks/useStandings'
import { useMatches } from '@/lib/hooks/useMatches'
import { useSlugResolution } from '@/lib/hooks/useSlugResolution'
import { MatchCalendarView } from '@/components/tournament/MatchCalendarView'
import { getRegistrationConfig } from '@/lib/api'
import type { StandingsEntry } from '@/types/schema'

export default function TournamentPublicClient({ slug }: { slug: string }) {
  const { tournamentId, loading: slugLoading, notFound: slugNotFound } = useSlugResolution(slug)
  const { standings, loading: standingsLoading } = useStandings(tournamentId ?? '')
  const { matches, loading: matchesLoading } = useMatches(tournamentId ?? '')
  const [tournamentName, setTournamentName] = useState<string | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [activeTab, setActiveTab] = useState<'standings' | 'calendar'>('standings')

  useEffect(() => {
    if (!tournamentId) return
    getRegistrationConfig(tournamentId)
      .then((cfg) => setTournamentName(cfg.name))
      .catch(() => setNotFound(true))
  }, [tournamentId])

  const teamNames: Record<string, string> = {}
  Object.values(standings).forEach((entries: StandingsEntry[]) => {
    entries.forEach((e) => { teamNames[e.team_id] = e.team_name })
  })

  if (slugLoading) return <div className="p-6">Caricamento...</div>
  if (slugNotFound || notFound) return <div className="p-6 text-red-600">Torneo non trovato.</div>
  if (tournamentName === null) return <div className="p-6">Caricamento...</div>

  const groupNames = Object.keys(standings).sort()
  const hasStandings = groupNames.length > 0

  return (
    <main className="container mx-auto p-6 max-w-2xl">
      <h1 className="text-2xl font-bold mb-6">{tournamentName}</h1>

      <div className="flex gap-2 mb-6 border-b">
        {(['standings', 'calendar'] as const).map((tab) => (
          <button
            key={tab}
            className={`pb-2 px-1 text-sm font-medium border-b-2 transition-colors ${
              activeTab === tab
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'standings' ? 'Gironi & Classifica' : 'Calendario'}
          </button>
        ))}
      </div>

      {activeTab === 'standings' && (
        standingsLoading ? (
          <p className="text-sm text-gray-500">Caricamento classifica...</p>
        ) : !hasStandings ? (
          <p className="text-sm text-gray-500">Il torneo non è ancora iniziato.</p>
        ) : (
          groupNames.map((g) => (
            <div key={g} className="mb-8">
              <h3 className="font-semibold mb-2">Girone {g}</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead>
                    <tr className="border-b text-gray-500 text-xs uppercase">
                      <th className="py-2 pr-3 text-left w-8">Pos</th>
                      <th className="py-2 pr-3 text-left">Squadra</th>
                      <th className="py-2 px-2 text-center">G</th>
                      <th className="py-2 px-2 text-center">V</th>
                      <th className="py-2 px-2 text-center">P</th>
                      <th className="py-2 px-2 text-center">S</th>
                      <th className="py-2 px-2 text-center">GF</th>
                      <th className="py-2 px-2 text-center">GS</th>
                      <th className="py-2 px-2 text-center">+/-</th>
                      <th className="py-2 pl-2 text-center font-bold">Pt</th>
                    </tr>
                  </thead>
                  <tbody>
                    {standings[g].map((e: StandingsEntry) => (
                      <tr key={e.team_id} className="border-b hover:bg-gray-50">
                        <td className="py-2 pr-3 text-gray-500">{e.position}</td>
                        <td className="py-2 pr-3 font-medium">
                          <Link
                            href={`/t/${slug}/team/${e.team_id}`}
                            className="hover:text-blue-600 hover:underline"
                          >
                            {e.team_name}
                          </Link>
                        </td>
                        <td className="py-2 px-2 text-center">{e.played}</td>
                        <td className="py-2 px-2 text-center">{e.wins}</td>
                        <td className="py-2 px-2 text-center">{e.draws}</td>
                        <td className="py-2 px-2 text-center">{e.losses}</td>
                        <td className="py-2 px-2 text-center">{e.goals_for}</td>
                        <td className="py-2 px-2 text-center">{e.goals_against}</td>
                        <td className="py-2 px-2 text-center">
                          {e.goal_difference > 0 ? `+${e.goal_difference}` : e.goal_difference}
                        </td>
                        <td className="py-2 pl-2 text-center font-bold">{e.points}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))
        )
      )}

      {activeTab === 'calendar' && (
        matchesLoading ? (
          <p className="text-sm text-gray-500">Caricamento calendario...</p>
        ) : (
          <MatchCalendarView matches={matches} teamNames={teamNames} />
        )
      )}
    </main>
  )
}
