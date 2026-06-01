'use client'
import { useCallback } from 'react'
import { auth } from '@/lib/firebase'

export function useFirebaseToken() {
  const getToken = useCallback(async (): Promise<string> => {
    const user = auth.currentUser
    if (!user) throw new Error('Not authenticated')
    return user.getIdToken()
  }, [])

  return { getToken }
}
