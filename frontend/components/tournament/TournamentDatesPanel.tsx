'use client'
import { useEffect, useState } from 'react'
import { getRegistrationConfig, updateTournamentConfig } from '@/lib/api'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

interface Props {
  tournamentId: string
}

export function TournamentDatesPanel({ tournamentId }: Props) {
  const { getToken } = useFirebaseToken()
  const [startDate, setStartDate] = useState('')
  const [editDeadline, setEditDeadline] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getRegistrationConfig(tournamentId)
      .then((cfg) => {
        setStartDate(cfg.start_date ?? '')
        if (cfg.edit_deadline) {
          setEditDeadline(new Date(cfg.edit_deadline).toISOString().slice(0, 16))
        }
      })
      .catch(() => {})
  }, [tournamentId])

  const handleStartDateChange = (val: string) => {
    setStartDate(val)
    if (!editDeadline && val) {
      const [year, month, day] = val.split('-').map(Number)
      const prev = new Date(year, month - 1, day - 1)
      const yyyy = prev.getFullYear()
      const mm = String(prev.getMonth() + 1).padStart(2, '0')
      const dd = String(prev.getDate()).padStart(2, '0')
      setEditDeadline(`${yyyy}-${mm}-${dd}T23:59`)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    setSaved(false)
    try {
      const token = await getToken()
      const payload: { start_date?: string; edit_deadline?: string } = {}
      if (startDate) payload.start_date = startDate
      if (editDeadline) payload.edit_deadline = new Date(editDeadline).toISOString()
      await updateTournamentConfig(tournamentId, payload, token)
      setSaved(true)
    } catch {
      setError('Errore durante il salvataggio.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-4 max-w-md">
      <div>
        <Label htmlFor="start-date">Data inizio torneo</Label>
        <Input
          id="start-date"
          type="date"
          value={startDate}
          onChange={(e) => handleStartDateChange(e.target.value)}
        />
      </div>
      <div>
        <Label htmlFor="edit-deadline">Scadenza modifiche (disponibilità e giocatori)</Label>
        <Input
          id="edit-deadline"
          type="datetime-local"
          value={editDeadline}
          onChange={(e) => setEditDeadline(e.target.value)}
        />
        <p className="text-xs text-gray-500 mt-1">
          Lascia vuoto per usare il default: inizio torneo − 1 giorno alle 23:59
        </p>
      </div>
      <Button onClick={handleSave} disabled={saving}>
        {saving ? 'Salvataggio...' : 'Salva date'}
      </Button>
      {saved && <p className="text-green-600 text-sm">Salvato.</p>}
      {error && <p className="text-red-600 text-sm">{error}</p>}
    </div>
  )
}
