'use client'
import { useStandings } from '@/lib/hooks/useStandings'
import { useMatches } from '@/lib/hooks/useMatches'
import { StandingsTable } from './StandingsTable'
import { MatchCalendarView } from './MatchCalendarView'
import type { PointsSystem } from '@/types/schema'

interface Props {
  tournamentId: string
  pointsSystem: PointsSystem
}

export function StandingsTab({ tournamentId, pointsSystem }: Props) {
  const { standings, loading: standingsLoading } = useStandings(tournamentId)
  const { matches, loading: matchesLoading } = useMatches(tournamentId)

  if (standingsLoading || matchesLoading) return <p>Caricamento...</p>

  const groupIds = Object.keys(standings).sort()

  return (
    <div className="space-y-8">
      {groupIds.length === 0 ? (
        <p className="text-sm text-gray-500">Nessuna classifica ancora. Inserisci qualche risultato.</p>
      ) : (
        groupIds.map((g) => (
          <StandingsTable key={g} groupName={g} entries={standings[g]} pointsSystem={pointsSystem} />
        ))
      )}
      <div>
        <h3 className="font-semibold mb-3">Calendario partite</h3>
        <MatchCalendarView matches={matches} />
      </div>
    </div>
  )
}
