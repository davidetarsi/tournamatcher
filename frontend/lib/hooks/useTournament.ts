'use client'
import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import type { Tournament } from '@/types/schema'

export function useTournament(tournamentId: string) {
  const [data, setData] = useState<Tournament | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    const ref = doc(db, 'tournaments', tournamentId)
    const unsubscribe = onSnapshot(
      ref,
      (snap) => {
        setData(snap.exists() ? ({ id: snap.id, ...snap.data() } as Tournament) : null)
        setLoading(false)
      },
      (err) => {
        setError(err)
        setLoading(false)
      }
    )
    return unsubscribe
  }, [tournamentId])

  return { data, loading, error }
}
