import type { Match } from '@/types/schema'
import { Badge } from '@/components/ui/badge'

interface Props {
  matches: Match[]
  teamNames?: Record<string, string>
}

function groupByDay(matches: Match[]): Record<number, Match[]> {
  return matches.reduce<Record<number, Match[]>>((acc, m) => {
    ;(acc[m.giorno] ??= []).push(m)
    return acc
  }, {})
}

export function MatchCalendarView({ matches, teamNames = {} }: Props) {
  const byDay = groupByDay([...matches].sort((a, b) => a.giorno - b.giorno || a.slot - b.slot))
  const days = Object.keys(byDay).map(Number).sort((a, b) => a - b)

  if (days.length === 0) return <p className="text-sm text-gray-500">Nessuna partita.</p>

  return (
    <div className="space-y-4">
      {days.map((day) => (
        <div key={day}>
          <h4 className="font-semibold text-sm text-gray-600 mb-2">Giorno {day}</h4>
          <div className="space-y-1">
            {byDay[day].map((m) => {
              const home = teamNames[m.squadre[0]] ?? m.squadre[0]
              const away = teamNames[m.squadre[1]] ?? m.squadre[1]
              const score =
                m.home_goals !== null && m.away_goals !== null
                  ? `${m.home_goals} – ${m.away_goals}`
                  : '– : –'
              return (
                <div key={m.id} className="flex items-center gap-2 text-sm py-1">
                  <Badge variant="outline" className="text-xs shrink-0">
                    {m.girone}
                  </Badge>
                  <span className="flex-1 text-right font-medium">{home}</span>
                  <span className="font-mono font-bold text-center w-12">{score}</span>
                  <span className="flex-1 text-left font-medium">{away}</span>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
