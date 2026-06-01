'use client'
import { useEffect, useState } from 'react'
import { collection, query, where, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import type { Match } from '@/types/schema'

export function useTeamMatches(tournamentId: string, teamId: string) {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!tournamentId || !teamId) return
    const q = query(
      collection(db, 'tournaments', tournamentId, 'matches'),
      where('squadre', 'array-contains', teamId)
    )
    const unsub = onSnapshot(
      q,
      (snap) => {
        const docs = snap.docs
          .map((d) => ({ id: d.id, ...d.data() } as Match))
          .sort((a, b) => a.giorno - b.giorno || a.slot - b.slot)
        setMatches(docs)
        setLoading(false)
      },
      () => setLoading(false)
    )
    return unsub
  }, [tournamentId, teamId])

  return { matches, loading }
}
