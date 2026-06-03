'use client'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/components/auth/AuthProvider'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'
import { TournamentList } from '@/components/tournament/TournamentList'
import { Button } from '@/components/ui/button'

export default function AdminPage() {
  const { user, loading } = useAuth()
  const router = useRouter()

  if (loading) return <div className="flex min-h-screen items-center justify-center">Caricamento...</div>

  if (!user) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <div className="text-center space-y-4">
          <h1 className="text-2xl font-bold">Tournament Manager</h1>
          <GoogleSignInButton />
        </div>
      </main>
    )
  }

  const isDev = process.env.NEXT_PUBLIC_DEV_BYPASS_AUTH === 'true'

  return (
    <main className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">I tuoi tornei</h1>
        <div className="flex gap-2">
          {isDev && (
            <Button variant="outline" onClick={() => router.push('/admin/dev-tournament')}>
              [Dev] Apri dashboard
            </Button>
          )}
          <Button onClick={() => router.push('/admin/new')}>Nuovo torneo</Button>
        </div>
      </div>
      <TournamentList />
    </main>
  )
}
