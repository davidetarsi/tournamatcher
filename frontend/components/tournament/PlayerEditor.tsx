'use client'
import { useEffect, useState } from 'react'
import { getTeamPlayers, updatePlayers } from '@/lib/api'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import type { SchemaField } from '@/types/schema'

interface Props {
  tournamentId: string
  teamId: string
  teamJwt: string
  playerFields: SchemaField[]
  deadline: string | null  // ISO datetime or null (null = no deadline)
}

export function PlayerEditor({ tournamentId, teamId, teamJwt, playerFields, deadline }: Props) {
  const [players, setPlayers] = useState<Record<string, string>[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const isPastDeadline = deadline ? new Date() > new Date(deadline) : false
  const canEdit = !isPastDeadline

  useEffect(() => {
    getTeamPlayers(tournamentId, teamId, teamJwt)
      .then((data) => {
        setPlayers(data.players as Record<string, string>[])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [tournamentId, teamId, teamJwt])

  const handleAdd = () => {
    const empty: Record<string, string> = {}
    playerFields.forEach((f) => { empty[f.key] = '' })
    setPlayers((prev) => [...prev, empty])
  }

  const handleChange = (idx: number, key: string, val: string) => {
    setPlayers((prev) => prev.map((p, i) => i === idx ? { ...p, [key]: val } : p))
  }

  const handleRemove = (idx: number) => {
    setPlayers((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      await updatePlayers(tournamentId, teamId, players, teamJwt)
      setSaved(true)
    } catch {
      setError('Errore durante il salvataggio.')
    } finally {
      setSaving(false)
    }
  }

  if (playerFields.length === 0) return null

  return (
    <div className="mt-8">
      <h2 className="text-lg font-semibold mb-1">Giocatori</h2>

      {isPastDeadline && (
        <p className="text-sm text-amber-700 bg-amber-50 border rounded px-3 py-2 mb-3">
          Le modifiche sono chiuse
          {deadline
            ? ` (scadenza: ${new Date(deadline).toLocaleDateString('it-IT')})`
            : ''}.
        </p>
      )}
      {canEdit && deadline && (
        <p className="text-xs text-gray-500 mb-3">
          Modifiche aperte fino al{' '}
          {new Date(deadline).toLocaleDateString('it-IT', {
            day: '2-digit', month: 'long', year: 'numeric',
          })}
        </p>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Caricamento giocatori...</p>
      ) : players.length === 0 ? (
        <p className="text-sm text-gray-500 mb-3">Nessun giocatore inserito.</p>
      ) : (
        <div className="space-y-2 mb-3">
          {players.map((p, i) => (
            <div key={i} className="flex gap-2 items-center">
              {playerFields.map((f) => (
                <Input
                  key={f.key}
                  placeholder={f.key}
                  value={p[f.key] ?? ''}
                  disabled={!canEdit}
                  maxLength={f.max_length}
                  onChange={(e) => handleChange(i, f.key, e.target.value)}
                  className="flex-1"
                />
              ))}
              {canEdit && (
                <button
                  type="button"
                  onClick={() => handleRemove(i)}
                  className="text-red-500 hover:text-red-700 text-sm shrink-0 px-1"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {canEdit && (
        <div className="space-y-2">
          <Button type="button" variant="outline" onClick={handleAdd} className="w-full">
            + Aggiungi giocatore
          </Button>
          <Button type="button" onClick={handleSave} disabled={saving} className="w-full">
            {saving ? 'Salvataggio...' : 'Salva giocatori'}
          </Button>
          {saved && <p className="text-green-600 text-sm">Salvato.</p>}
          {error && <p className="text-red-600 text-sm">{error}</p>}
        </div>
      )}
    </div>
  )
}
