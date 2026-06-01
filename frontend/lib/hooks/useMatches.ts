'use client'
import { useEffect, useState } from 'react'
import { collection, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import type { Match } from '@/types/schema'

const DEV_BYPASS = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true'

const DEV_MATCHES: Match[] = [
  { id: 'm1', giorno: 1, slot: 0, girone: 'A', squadre: ['team1', 'team2'], home_goals: 2, away_goals: 1, played_at: null },
  { id: 'm2', giorno: 1, slot: 1, girone: 'A', squadre: ['team3', 'team4'], home_goals: null, away_goals: null, played_at: null },
  { id: 'm3', giorno: 2, slot: 0, girone: 'B', squadre: ['team5', 'team6'], home_goals: 0, away_goals: 0, played_at: null },
]

export function useMatches(tournamentId: string) {
  const [matches, setMatches] = useState<Match[]>(DEV_BYPASS ? DEV_MATCHES : [])
  const [loading, setLoading] = useState(!DEV_BYPASS)

  useEffect(() => {
    if (DEV_BYPASS) return
    const col = collection(db, 'tournaments', tournamentId, 'matches')
    const unsub = onSnapshot(
      col,
      (snap) => {
        setMatches(snap.docs.map((d) => ({ id: d.id, ...d.data() } as Match)))
        setLoading(false)
      },
      () => setLoading(false)
    )
    return unsub
  }, [tournamentId])

  return { matches, loading }
}
