'use client'
import { useState } from 'react'
import { loginTeam, ApiError } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

interface Props {
  tournamentId: string
  teamId: string
  onSuccess: (jwt: string) => void
}

export function TeamCodeEntry({ tournamentId, teamId, onSuccess }: Props) {
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const { access_token } = await loginTeam(tournamentId, teamId, code)
      localStorage.setItem(`team_jwt_${teamId}`, access_token)
      onSuccess(access_token)
    } catch (err) {
      setError(err instanceof ApiError && err.status === 403 ? 'Codice non valido' : 'Errore di rete, riprova')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container mx-auto p-6 max-w-sm">
      <div className="border rounded-lg p-6 space-y-4">
        <h2 className="text-lg font-semibold">Accedi alla pagina della tua squadra</h2>
        <p className="text-sm text-gray-600">
          Inserisci il codice segreto ricevuto alla registrazione.
        </p>
        <form onSubmit={handleSubmit} className="space-y-3">
          <Input
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            placeholder="Es. ABCD1234"
            maxLength={8}
            className="font-mono text-lg tracking-widest"
          />
          {error && <p className="text-red-600 text-sm">{error}</p>}
          <Button type="submit" disabled={loading || code.length < 8} className="w-full">
            {loading ? 'Verifica...' : 'Accedi'}
          </Button>
        </form>
      </div>
    </main>
  )
}
