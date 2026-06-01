'use client'
import { useEffect, useState } from 'react'
import { collection, query, where, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useTournament } from '@/lib/hooks/useTournament'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { generateSchedule } from '@/lib/api'
import { Button } from '@/components/ui/button'

interface Props {
  tournamentId: string
}

export function SchedulePanel({ tournamentId }: Props) {
  const { data: tournament } = useTournament(tournamentId)
  const { getToken } = useFirebaseToken()
  const [confirmedCount, setConfirmedCount] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  useEffect(() => {
    const q = query(
      collection(db, 'tournaments', tournamentId, 'teams'),
      where('confirmed', '==', true)
    )
    return onSnapshot(q, (snap) => setConfirmedCount(snap.size))
  }, [tournamentId])

  const handleGenerate = async () => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const token = await getToken()
      await generateSchedule(tournamentId, token)
      setResult('Calendario generato con successo')
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }

  const isScheduled = tournament?.status === 'scheduled'

  return (
    <div className="space-y-4">
      <p>
        Stato: <strong>{tournament?.status ?? '—'}</strong>
      </p>
      <p className="text-sm text-gray-600">
        Squadre confermate: {confirmedCount}
      </p>
      {error && <p className="text-red-600">{error}</p>}
      {result && <p className="text-green-600">{result}</p>}
      <Button
        onClick={handleGenerate}
        disabled={loading || confirmedCount < 2 || isScheduled}
      >
        {loading ? 'Generazione...' : 'Genera Gironi'}
      </Button>
    </div>
  )
}
