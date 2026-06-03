'use client'
import { useEffect, useState } from 'react'
import { collection, query, where, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useAuth } from '@/components/auth/AuthProvider'
import type { Tournament } from '@/types/schema'
import Link from 'next/link'
import { Badge } from '@/components/ui/badge'

export function TournamentList() {
  const { user } = useAuth()
  const [tournaments, setTournaments] = useState<Tournament[]>([])
  const [loading, setLoading] = useState(true)

  const uid = user?.uid ?? null

  useEffect(() => {
    if (!uid) return
    const q = query(collection(db, 'tournaments'), where('admin_uid', '==', uid))
    const unsubscribe = onSnapshot(
      q,
      (snap) => {
        setTournaments(snap.docs.map((d) => ({ id: d.id, ...d.data() } as Tournament)))
        setLoading(false)
      },
      () => setLoading(false)
    )
    return unsubscribe
  }, [uid])

  if (loading) return <p>Caricamento tornei...</p>
  if (tournaments.length === 0) return <p>Nessun torneo ancora. Creane uno!</p>

  return (
    <ul className="space-y-2">
      {tournaments.map((t) => (
        <li key={t.id}>
          <Link href={`/admin/${t.id}`} className="flex items-center justify-between p-4 border rounded hover:bg-gray-50">
            <span className="font-medium">{t.name}</span>
            <Badge variant={t.status === 'scheduled' ? 'default' : 'secondary'}>{t.status}</Badge>
          </Link>
        </li>
      ))}
    </ul>
  )
}
