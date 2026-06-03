'use client'
import { useState, useEffect } from 'react'
import { GoogleAuthProvider, signInWithPopup, signOut } from 'firebase/auth'
import Image from 'next/image'
import Link from 'next/link'
import { auth } from '@/lib/firebase'
import { useAuth } from '@/components/auth/AuthProvider'
import { getMyTournaments } from '@/lib/api'

type Tournament = { name: string; slug: string; status: string }

export default function AuthButton() {
  const { user, loading } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const [tournaments, setTournaments] = useState<Tournament[] | null>(null)
  const [loadingTournaments, setLoadingTournaments] = useState(false)
  const [fetchError, setFetchError] = useState(false)

  // Fetch tournaments whenever the drawer opens and user is authenticated
  useEffect(() => {
    if (!isOpen || !user) return
    setFetchError(false)
    setLoadingTournaments(true)
    user
      .getIdToken()
      .then((token) => getMyTournaments(token))
      .then((data) => setTournaments(data))
      .catch(() => { setFetchError(true); setTournaments([]) })
      .finally(() => setLoadingTournaments(false))
  }, [isOpen, user])

  const handleSignIn = async () => {
    try {
      const provider = new GoogleAuthProvider()
      await signInWithPopup(auth, provider)
    } catch {
      // user cancelled or network error — no action needed
    }
  }

  const handleSignOut = async () => {
    setIsOpen(false)
    await signOut(auth)
  }

  // While auth is resolving, show a fixed-size skeleton to avoid layout shift
  if (loading) return <div className="w-9 h-9 rounded-full bg-gray-200 animate-pulse" />

  if (!user) {
    return (
      <button
        onClick={handleSignIn}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
      >
        Accedi
      </button>
    )
  }

  return (
    <>
      {/* Avatar button */}
      <button
        onClick={() => setIsOpen((prev) => !prev)}
        className="rounded-full overflow-hidden w-9 h-9 border-2 border-gray-200 hover:border-blue-400 transition-colors focus:outline-none"
        aria-label="Apri menu utente"
      >
        {user.photoURL ? (
          <Image
            src={user.photoURL}
            alt={user.displayName ?? 'Avatar'}
            width={36}
            height={36}
            className="object-cover"
          />
        ) : (
          <div className="w-full h-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
            {(user.displayName ?? user.email ?? 'U')[0].toUpperCase()}
          </div>
        )}
      </button>

      {/* Drawer */}
      {isOpen && (
        <div className="fixed inset-0 z-50">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/40"
            onClick={() => setIsOpen(false)}
          />

          {/* Panel */}
          <div className="absolute right-0 top-0 h-full w-80 bg-white shadow-xl flex flex-col">
            {/* User info */}
            <div className="p-4 border-b">
              <p className="font-semibold text-gray-900 truncate">
                {user.displayName ?? 'Utente'}
              </p>
              <p className="text-sm text-gray-500 truncate">{user.email}</p>
            </div>

            {/* Tournament list */}
            <div className="flex-1 overflow-y-auto p-4">
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                I tuoi tornei
              </p>

              {loadingTournaments && (
                <div className="space-y-3">
                  {[1, 2, 3].map((i) => (
                    <div
                      key={i}
                      className="h-9 rounded-lg bg-gray-100 animate-pulse"
                    />
                  ))}
                </div>
              )}

              {!loadingTournaments && tournaments !== null && (
                fetchError ? (
                  <p className="text-sm text-red-500 py-4 text-center">Errore nel caricamento</p>
                ) : tournaments.length === 0 ? (
                  <p className="text-sm text-gray-500 py-4 text-center">Nessun torneo</p>
                ) : (
                  <ul className="space-y-1">
                    {tournaments.map((t) => (
                      <li key={t.slug}>
                        <Link
                          href={`/t/${t.slug}/admin`}
                          onClick={() => setIsOpen(false)}
                          className="flex items-center justify-between px-3 py-2 rounded-lg hover:bg-gray-50 transition-colors text-sm text-gray-800"
                        >
                          <span className="truncate">{t.name}</span>
                          <span className="ml-2 text-xs text-gray-400 shrink-0">{t.status}</span>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )
              )}
            </div>

            {/* Logout */}
            <div className="p-4 border-t">
              <button
                onClick={handleSignOut}
                className="w-full text-sm text-red-600 hover:text-red-700 font-medium py-2 rounded-lg hover:bg-red-50 transition-colors"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
