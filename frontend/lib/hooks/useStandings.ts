'use client'
import { useEffect, useState } from 'react'
import { collection, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import type { StandingsEntry } from '@/types/schema'

const DEV_BYPASS = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true'

const DEV_STANDINGS: Record<string, StandingsEntry[]> = {
  A: [
    { team_id: 'team1', team_name: 'Aquile', played: 1, wins: 1, draws: 0, losses: 0, goals_for: 2, goals_against: 1, goal_difference: 1, points: 3, position: 1 },
    { team_id: 'team2', team_name: 'Bisonti', played: 1, wins: 0, draws: 0, losses: 1, goals_for: 1, goals_against: 2, goal_difference: -1, points: 0, position: 2 },
  ],
}

export function useStandings(tournamentId: string) {
  const [standings, setStandings] = useState<Record<string, StandingsEntry[]>>(
    DEV_BYPASS ? DEV_STANDINGS : {}
  )
  const [loading, setLoading] = useState(!DEV_BYPASS)

  useEffect(() => {
    if (DEV_BYPASS) return
    const col = collection(db, 'tournaments', tournamentId, 'standings')
    const unsub = onSnapshot(
      col,
      (snap) => {
        const map: Record<string, StandingsEntry[]> = {}
        snap.docs.forEach((d) => {
          const data = d.data()
          map[d.id] = (data.entries ?? []) as StandingsEntry[]
        })
        setStandings(map)
        setLoading(false)
      },
      () => setLoading(false)
    )
    return unsub
  }, [tournamentId])

  return { standings, loading }
}
