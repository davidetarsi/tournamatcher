'use client'
import { useEffect, useState } from 'react'
import { doc, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import type { Tournament } from '@/types/schema'

const DEV_BYPASS = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true'

const DEV_TOURNAMENT: Tournament = {
  id: 'dev-tournament',
  name: 'Torneo di test (dev)',
  admin_uid: 'dev-bypass',
  public: true,
  status: 'draft',
}

export function useTournament(tournamentId: string) {
  const [data, setData] = useState<Tournament | null>(
    DEV_BYPASS ? DEV_TOURNAMENT : null
  )
  const [loading, setLoading] = useState(!DEV_BYPASS)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    if (DEV_BYPASS) return

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
