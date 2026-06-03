import { useState, useEffect } from 'react'
import { doc, getDoc } from 'firebase/firestore'
import { db } from '@/lib/firebase'

export function useSlugResolution(slug: string) {
  const [tournamentId, setTournamentId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)

  useEffect(() => {
    let isMounted = true
    getDoc(doc(db, 'tournament_slugs', slug))
      .then((snap) => {
        if (!isMounted) return
        if (snap.exists()) {
          setTournamentId(snap.data().tournament_id)
        } else {
          setNotFound(true)
        }
        setLoading(false)
      })
      .catch(() => {
        if (!isMounted) return
        setNotFound(true)
        setLoading(false)
      })
    return () => { isMounted = false }
  }, [slug])

  return { tournamentId, loading, notFound }
}
