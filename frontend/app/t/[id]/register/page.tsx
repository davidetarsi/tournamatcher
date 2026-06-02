'use client'
import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { getRegistrationConfig, registerTeam, loginTeam, ApiError } from '@/lib/api'
import { AvailabilityGrid, initSlots } from '@/components/tournament/AvailabilityGrid'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import type { RegistrationConfig, SchemaField } from '@/types/schema'

type Slot = { slot_id: string; available: boolean }

export default function RegisterPage() {
  const { id: tournamentId } = useParams() as { id: string }
  const router = useRouter()

  const [config, setConfig] = useState<RegistrationConfig | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [fieldValues, setFieldValues] = useState<Record<string, string>>({})
  const [inviteCode, setInviteCode] = useState('')
  const [slots, setSlots] = useState<Slot[]>([])
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [completedPin, setCompletedPin] = useState<string | null>(null)
  const [completedTeamId, setCompletedTeamId] = useState<string | null>(null)
  const [confirmingPin, setConfirmingPin] = useState(false)

  useEffect(() => {
    getRegistrationConfig(tournamentId)
      .then((cfg) => {
        setConfig(cfg)
        setSlots(initSlots(cfg.num_giorni, cfg.num_slots_per_giorno))
      })
      .catch(() => setLoadError('Torneo non trovato o non disponibile.'))
  }, [tournamentId])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!config) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const result = await registerTeam(tournamentId, {
        fields: fieldValues,
        invite_code: inviteCode || undefined,
        availability_slots: slots,
      })
      setCompletedPin(result.team_code_plain)
      setCompletedTeamId(result.team_id)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) setSubmitError('Codice invito non valido o iscrizione su invito.')
        else if (err.status === 409) setSubmitError('Posti esauriti per questa categoria.')
        else if (err.status === 422) setSubmitError('Dati non validi. Controlla i campi.')
        else setSubmitError('Errore durante la registrazione. Riprova.')
      } else {
        setSubmitError('Errore durante la registrazione. Riprova.')
      }
    } finally {
      setSubmitting(false)
    }
  }

  const handleConfirmPin = async () => {
    if (!completedPin || !completedTeamId) return
    setConfirmingPin(true)
    let loginFailed = false
    try {
      const { access_token } = await loginTeam(tournamentId, completedTeamId, completedPin)
      localStorage.setItem(`team_jwt_${completedTeamId}`, access_token)
    } catch {
      loginFailed = true
    } finally {
      setConfirmingPin(false)
      const path = `/t/${tournamentId}/team/${completedTeamId}`
      router.push(loginFailed ? `${path}?message=${encodeURIComponent('Inserisci il codice per accedere alla tua pagina.')}` : path)
    }
  }

  if (!config && !loadError) return <div className="p-6">Caricamento...</div>
  if (loadError) return <div className="p-6 text-red-600">{loadError}</div>

  if (completedPin && completedTeamId) {
    return (
      <main className="container mx-auto p-6 max-w-md">
        <div className="border-2 border-yellow-400 rounded-lg p-6 space-y-4 bg-yellow-50">
          <h2 className="text-xl font-bold">Registrazione completata!</h2>
          <p className="text-sm text-gray-700">
            Salva questo codice segreto. Ti servirà per accedere alla pagina della tua squadra da altri dispositivi. <strong>Non sarà più mostrato.</strong>
          </p>
          <div className="py-4 text-center">
            <span className="text-3xl font-mono font-bold tracking-[0.3em] bg-white border rounded px-4 py-2">
              {completedPin}
            </span>
          </div>
          <Button className="w-full" onClick={handleConfirmPin} disabled={confirmingPin}>
            {confirmingPin ? 'Accesso in corso...' : 'Ho salvato il codice → Vai alla mia pagina'}
          </Button>
        </div>
      </main>
    )
  }

  return (
    <main className="container mx-auto p-6 max-w-md">
      <h1 className="text-2xl font-bold mb-6">Iscriviti a {config!.name}</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        {config!.team_fields.map((f: SchemaField) => (
          <div key={f.key}>
            <label className="text-sm font-medium block mb-1">
              {f.key}
              {f.required && <span className="text-red-500 ml-1">*</span>}
            </label>
            <Input
              type={f.type === 'email' ? 'email' : f.type === 'number' ? 'number' : 'text'}
              required={f.required}
              maxLength={f.max_length}
              value={fieldValues[f.key] ?? ''}
              onChange={(e) => setFieldValues((prev) => ({ ...prev, [f.key]: e.target.value }))}
            />
          </div>
        ))}

        {config!.invite_codes.enabled && (
          <div>
            <label className="text-sm font-medium block mb-1">
              Codice invito
              {!config!.invite_codes.partial && <span className="text-red-500 ml-1">*</span>}
            </label>
            <Input
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              required={!config!.invite_codes.partial}
              placeholder="Es. ABCD1234"
              className="font-mono"
            />
          </div>
        )}

        <div>
          <label className="text-sm font-medium block mb-2">Disponibilità</label>
          <p className="text-xs text-gray-500 mb-2">
            Indica i giorni e gli slot in cui la tua squadra è disponibile a giocare.
          </p>
          <AvailabilityGrid
            numGiorni={config!.num_giorni}
            numSlotsPerGiorno={config!.num_slots_per_giorno}
            value={slots}
            onChange={setSlots}
          />
        </div>

        {submitError && <p className="text-red-600 text-sm">{submitError}</p>}

        <Button type="submit" disabled={submitting} className="w-full">
          {submitting ? 'Registrazione...' : 'Iscriviti'}
        </Button>
      </form>
    </main>
  )
}
