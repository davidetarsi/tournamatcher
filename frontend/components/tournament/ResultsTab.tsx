'use client'
import { useState } from 'react'
import { useMatches } from '@/lib/hooks/useMatches'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { submitResult } from '@/lib/api'
import type { Match, PointsSystem } from '@/types/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'

interface Props {
  tournamentId: string
  pointsSystem: PointsSystem
}

interface RowState {
  home: string
  away: string
  saving: boolean
  editing: boolean
  error: string | null
}

function groupByGironeThenDay(matches: Match[]): Record<string, Record<number, Match[]>> {
  const result: Record<string, Record<number, Match[]>> = {}
  for (const m of [...matches].sort((a, b) => a.giorno - b.giorno || a.slot - b.slot)) {
    ;(result[m.girone] ??= {})
    ;(result[m.girone][m.giorno] ??= []).push(m)
  }
  return result
}

export function ResultsTab({ tournamentId, pointsSystem }: Props) {
  const { matches, loading } = useMatches(tournamentId)
  const { getToken } = useFirebaseToken()
  const [rowState, setRowState] = useState<Record<string, RowState>>({})

  const getRow = (matchId: string, m: Match): RowState =>
    rowState[matchId] ?? {
      home: m.home_goals?.toString() ?? '',
      away: m.away_goals?.toString() ?? '',
      saving: false,
      editing: false,
      error: null,
    }

  const setRow = (matchId: string, patch: Partial<RowState>) =>
    setRowState((prev) => ({ ...prev, [matchId]: { ...getRow(matchId, {} as Match), ...patch } }))

  const handleSave = async (m: Match) => {
    const row = rowState[m.id] ?? { home: '', away: '', saving: false, editing: false, error: null }
    const hg = parseInt(row.home, 10)
    const ag = parseInt(row.away, 10)
    if (isNaN(hg) || isNaN(ag) || hg < 0 || ag < 0) {
      setRow(m.id, { error: 'Inserisci numeri validi ≥ 0' })
      return
    }
    if (!pointsSystem.draws_allowed && hg === ag) {
      setRow(m.id, { error: 'Pareggi non consentiti' })
      return
    }
    setRow(m.id, { saving: true, error: null })
    try {
      const token = await getToken()
      await submitResult(tournamentId, m.id, { home_goals: hg, away_goals: ag }, token)
      setRow(m.id, { saving: false, editing: false })
    } catch (e) {
      setRow(m.id, { saving: false, error: e instanceof Error ? e.message : 'Errore' })
    }
  }

  if (loading) return <p>Caricamento partite...</p>
  if (matches.length === 0) return <p className="text-sm text-gray-500">Nessuna partita. Genera il calendario prima.</p>

  const grouped = groupByGironeThenDay(matches)
  const gironi = Object.keys(grouped).sort()

  return (
    <div className="space-y-6">
      {gironi.map((girone) => (
        <div key={girone}>
          <h3 className="font-semibold mb-3">Girone {girone}</h3>
          <div className="space-y-4">
            {Object.keys(grouped[girone]).map(Number).sort((a, b) => a - b).map((day) => (
              <div key={day}>
                <h4 className="text-sm text-gray-500 mb-2">Giorno {day}</h4>
                <div className="space-y-2">
                  {grouped[girone][day].map((m) => {
                    const row = getRow(m.id, m)
                    const played = m.home_goals !== null && m.away_goals !== null && !row.editing
                    return (
                      <div key={m.id} className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium w-28 text-right truncate">{m.squadre[0]}</span>
                        {played ? (
                          <>
                            <span className="font-mono font-bold">{m.home_goals} – {m.away_goals}</span>
                            <span className="font-medium w-28 truncate">{m.squadre[1]}</span>
                            <Button size="sm" variant="outline" onClick={() => setRow(m.id, { editing: true, home: m.home_goals!.toString(), away: m.away_goals!.toString() })}>
                              Modifica
                            </Button>
                          </>
                        ) : (
                          <>
                            <Input
                              className="w-14 text-center"
                              value={row.home}
                              onChange={(e) => setRow(m.id, { home: e.target.value })}
                              placeholder="0"
                              type="number"
                              min={0}
                            />
                            <span>–</span>
                            <Input
                              className="w-14 text-center"
                              value={row.away}
                              onChange={(e) => setRow(m.id, { away: e.target.value })}
                              placeholder="0"
                              type="number"
                              min={0}
                            />
                            <span className="font-medium w-28 truncate">{m.squadre[1]}</span>
                            <Button size="sm" onClick={() => handleSave(m)} disabled={row.saving}>
                              {row.saving ? '...' : 'Salva'}
                            </Button>
                          </>
                        )}
                        {row.error && <Badge variant="destructive" className="text-xs">{row.error}</Badge>}
                      </div>
                    )
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}
