'use client'
import { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { User, onIdTokenChanged } from 'firebase/auth'
import { auth } from '@/lib/firebase'

const DEV_BYPASS = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true'

interface AuthContextValue {
  user: User | null
  loading: boolean
}

const AuthContext = createContext<AuthContextValue>({ user: null, loading: true })

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(
    DEV_BYPASS ? ({ uid: 'dev-bypass', email: 'dev@local.test' } as unknown as User) : null
  )
  const [loading, setLoading] = useState(!DEV_BYPASS)

  useEffect(() => {
    if (DEV_BYPASS) return

    let unsubscribe: (() => void) | undefined
    try {
      unsubscribe = onIdTokenChanged(auth, async (u) => {
        setUser(u)
        setLoading(false)
        try {
          if (u) {
            const token = await u.getIdToken()
            await fetch('/api/auth/session', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ token }),
            })
          } else {
            await fetch('/api/auth/session', { method: 'DELETE' })
          }
        } catch {
          // Session sync errors don't affect the auth state display
        }
      })
    } catch {
      setLoading(false)
    }
    return () => unsubscribe?.()
  }, [])

  return <AuthContext.Provider value={{ user, loading }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  return useContext(AuthContext)
}
