'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { createTournament } from '@/lib/api'
import type { SchemaField, CampoGiornoSlots } from '@/types/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { SlotOrariStep } from './SlotOrariStep'

const TEMPLATES: Record<string, { sport: string; team_fields: SchemaField[] }> = {
  calcetto: {
    sport: 'calcetto',
    team_fields: [
      { key: 'nome', type: 'text', required: true, max_length: 100 },
      { key: 'contact_email', type: 'email', required: true },
      { key: 'city', type: 'text', required: false, max_length: 80 },
    ],
  },
  basket: {
    sport: 'basket',
    team_fields: [
      { key: 'nome', type: 'text', required: true, max_length: 100 },
      { key: 'contact_email', type: 'email', required: true },
      { key: 'jersey_number', type: 'number', required: false },
    ],
  },
  personalizzato: { sport: '', team_fields: [] },
}

function computeNumGiorni(
  maxTeams: number,
  teamsPerGroup: number,
  numSlotsPerGiorno: number,
  numCampi: number
): number | null {
  if (maxTeams <= 0 || teamsPerGroup <= 0 || numSlotsPerGiorno <= 0 || numCampi <= 0) return null
  if (maxTeams % teamsPerGroup !== 0) return null
  const numerator = maxTeams * (teamsPerGroup - 1)
  const denominator = numSlotsPerGiorno * numCampi * 2
  if (numerator % denominator !== 0) return null
  return numerator / denominator
}

function initSlotOrari(
  numCampi: number,
  numGiorni: number,
  numSlotsPerGiorno: number,
  existing: CampoGiornoSlots[]
): CampoGiornoSlots[] {
  const result: CampoGiornoSlots[] = []
  for (let c = 1; c <= numCampi; c++) {
    for (let g = 1; g <= numGiorni; g++) {
      const prev = existing.find((e) => e.campo === c && e.giorno === g)
      result.push({
        campo: c,
        giorno: g,
        slots:
          prev && prev.slots.length === numSlotsPerGiorno
            ? prev.slots
            : Array(numSlotsPerGiorno).fill(''),
      })
    }
  }
  return result
}

function allSlotsValid(slotOrari: CampoGiornoSlots[]): boolean {
  for (const entry of slotOrari) {
    for (let i = 0; i < entry.slots.length; i++) {
      if (!entry.slots[i]) return false
      if (i > 0) {
        const prev = entry.slots[i - 1]
        const curr = entry.slots[i]
        const toMin = (t: string) => {
          const [h, m] = t.split(':').map(Number)
          return h * 60 + m
        }
        if (toMin(curr) < toMin(prev) + 5) return false
      }
    }
  }
  return true
}

const STEP_LABELS = ['Template', 'Formato', 'Orari', 'Riepilogo']

export function TournamentWizard() {
  const [step, setStep] = useState(1)

  // Step 1
  const [template, setTemplate] = useState<string | null>(null)

  // Step 2 — formato
  const [name, setName] = useState('')
  const [maxTeams, setMaxTeams] = useState(8)
  const [teamsPerGroup, setTeamsPerGroup] = useState(4)
  const [numCampi, setNumCampi] = useState(1)
  const [numSlotsPerGiorno, setNumSlotsPerGiorno] = useState(3)

  // Step 3 — slot orari
  const [slotOrari, setSlotOrari] = useState<CampoGiornoSlots[]>([])

  // Step 4 — dettagli extra + submit
  const [isPublic, setIsPublic] = useState(false)
  const [startDate, setStartDate] = useState('')
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoError, setLogoError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  const { getToken } = useFirebaseToken()
  const router = useRouter()

  const numGiorni = computeNumGiorni(maxTeams, teamsPerGroup, numSlotsPerGiorno, numCampi)
  const numGironi = maxTeams > 0 && teamsPerGroup > 0 && maxTeams % teamsPerGroup === 0
    ? maxTeams / teamsPerGroup
    : null

  const handleLogoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null
    setLogoError(null)
    if (file && file.size > 2 * 1024 * 1024) {
      setLogoError('Il logo non può superare 2MB.')
      setLogoFile(null)
      return
    }
    setLogoFile(file)
  }

  const goToStep3 = () => {
    if (numGiorni === null) return
    setSlotOrari(initSlotOrari(numCampi, numGiorni, numSlotsPerGiorno, slotOrari))
    setStep(3)
  }

  const handleSubmit = async () => {
    if (!template || numGiorni === null) return
    setSubmitting(true)
    setSubmitError(null)
    try {
      const tmpl = TEMPLATES[template]
      const token = await getToken()

      let logo_base64: string | undefined
      if (logoFile) {
        logo_base64 = await new Promise<string>((resolve, reject) => {
          const reader = new FileReader()
          reader.onload = () => resolve(reader.result as string)
          reader.onerror = reject
          reader.readAsDataURL(logoFile)
        })
      }

      const result = await createTournament(
        {
          name,
          schema_config: {
            sport: tmpl.sport,
            max_teams: maxTeams,
            teams_per_group: teamsPerGroup,
            public: isPublic,
            invite_codes: { enabled: false, partial: false },
            team_fields: tmpl.team_fields,
            player_fields: [],
            admin_controls: { can_set_strength: true, max_teams: maxTeams },
            points_system: { win: 3, draw: 1, loss: 0, draws_allowed: true },
            tiebreaker_rules: ['goal_difference', 'goals_for', 'head_to_head'],
            num_giorni: numGiorni,
            num_slots_per_giorno: numSlotsPerGiorno,
            num_campi: numCampi,
            slot_orari: slotOrari,
            max_public_teams: 0,
          },
          start_date: startDate || undefined,
          ...(logo_base64 ? { logo_base64 } : {}),
        },
        token
      )
      router.push(`/t/${result.slug}/admin`)
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : 'Errore durante la creazione del torneo')
    } finally {
      setSubmitting(false)
    }
  }

  // ── Step indicator ──────────────────────────────────────────────────────────
  const StepIndicator = () => (
    <div className="flex items-center gap-2 mb-8">
      {STEP_LABELS.map((label, i) => {
        const n = i + 1
        const active = n === step
        const done = n < step
        return (
          <div key={n} className="flex items-center gap-2">
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                done
                  ? 'bg-green-500 border-green-500 text-white'
                  : active
                  ? 'border-blue-600 text-blue-600'
                  : 'border-gray-300 text-gray-400'
              }`}
            >
              {done ? '✓' : n}
            </div>
            <span
              className={`text-xs font-medium hidden sm:block ${
                active ? 'text-blue-600' : done ? 'text-green-600' : 'text-gray-400'
              }`}
            >
              {label}
            </span>
            {i < STEP_LABELS.length - 1 && (
              <div className={`h-px w-6 ${done ? 'bg-green-400' : 'bg-gray-200'}`} />
            )}
          </div>
        )
      })}
    </div>
  )

  // ── Step 1: Template ────────────────────────────────────────────────────────
  if (step === 1) {
    return (
      <div className="space-y-6 max-w-lg">
        <StepIndicator />
        <h2 className="text-xl font-bold">Scegli il template</h2>
        <div className="grid grid-cols-3 gap-4">
          {Object.keys(TEMPLATES).map((key) => (
            <button
              key={key}
              className={`p-6 border-2 rounded-lg capitalize font-medium transition-colors ${
                template === key
                  ? 'border-blue-500 bg-blue-50 text-blue-700'
                  : 'border-gray-200 hover:border-gray-400'
              }`}
              onClick={() => setTemplate(key)}
            >
              {key}
            </button>
          ))}
        </div>
        <Button onClick={() => setStep(2)} disabled={!template}>
          Avanti →
        </Button>
      </div>
    )
  }

  // ── Step 2: Formato ─────────────────────────────────────────────────────────
  if (step === 2) {
    const gironiError =
      maxTeams > 0 && teamsPerGroup > 0 && maxTeams % teamsPerGroup !== 0
        ? 'Le squadre non si dividono equamente nei gironi.'
        : null
    const formulaError =
      !gironiError && numGiorni === null && maxTeams > 0 && teamsPerGroup > 0
        ? 'Combinazione non valida: le partite totali non si dividono esattamente. Prova a cambiare il numero di slot o di campi.'
        : null

    const canProceed =
      name.trim().length > 0 && numGiorni !== null && !gironiError

    return (
      <div className="space-y-5 max-w-md">
        <StepIndicator />
        <h2 className="text-xl font-bold">Formato del torneo</h2>

        <div>
          <Label htmlFor="name">Nome torneo</Label>
          <Input
            id="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Es. Torneo Estivo 2026"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="max-teams">Squadre totali</Label>
            <Input
              id="max-teams"
              type="number"
              min={2}
              value={maxTeams}
              onChange={(e) => setMaxTeams(Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="teams-per-group">Squadre per girone</Label>
            <Input
              id="teams-per-group"
              type="number"
              min={2}
              value={teamsPerGroup}
              onChange={(e) => setTeamsPerGroup(Number(e.target.value))}
            />
            {numGironi !== null && !gironiError && (
              <p className="text-xs text-gray-500 mt-1">{numGironi} gironi</p>
            )}
          </div>
        </div>

        {gironiError && <p className="text-sm text-red-600">{gironiError}</p>}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <Label htmlFor="num-campi">Campi da gioco</Label>
            <Input
              id="num-campi"
              type="number"
              min={1}
              value={numCampi}
              onChange={(e) => setNumCampi(Number(e.target.value))}
            />
          </div>
          <div>
            <Label htmlFor="slots-per-giorno">Slot per giorno / campo</Label>
            <Input
              id="slots-per-giorno"
              type="number"
              min={1}
              value={numSlotsPerGiorno}
              onChange={(e) => setNumSlotsPerGiorno(Number(e.target.value))}
            />
          </div>
        </div>

        {formulaError && <p className="text-sm text-red-600">{formulaError}</p>}

        {numGiorni !== null && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3 text-sm">
            <span className="font-semibold text-blue-800">
              Giornate necessarie: {numGiorni}
            </span>
            <span className="text-blue-600 ml-2">
              ({maxTeams * (teamsPerGroup - 1) / 2} partite totali
              {numCampi > 1 ? `, ${numCampi} campi in parallelo` : ''})
            </span>
          </div>
        )}

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setStep(1)}>
            ← Indietro
          </Button>
          <Button onClick={goToStep3} disabled={!canProceed}>
            Avanti →
          </Button>
        </div>
      </div>
    )
  }

  // ── Step 3: Slot orari ──────────────────────────────────────────────────────
  if (step === 3) {
    const canProceed = allSlotsValid(slotOrari)
    return (
      <div className="space-y-5 max-w-2xl">
        <StepIndicator />
        <div>
          <h2 className="text-xl font-bold">Orari delle partite</h2>
          <p className="text-sm text-gray-500 mt-1">
            Definisci gli orari di inizio per ogni slot, per ogni giorno
            {numCampi > 1 ? ' e per ogni campo' : ''}.
          </p>
        </div>

        <SlotOrariStep
          numCampi={numCampi}
          numGiorni={numGiorni!}
          numSlotsPerGiorno={numSlotsPerGiorno}
          value={slotOrari}
          onChange={setSlotOrari}
        />

        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setStep(2)}>
            ← Indietro
          </Button>
          <Button onClick={() => setStep(4)} disabled={!canProceed}>
            Avanti →
          </Button>
        </div>
      </div>
    )
  }

  // ── Step 4: Riepilogo + submit ───────────────────────────────────────────────
  return (
    <div className="space-y-6 max-w-lg">
      <StepIndicator />
      <h2 className="text-xl font-bold">Riepilogo e dettagli finali</h2>

      {/* Riepilogo formato */}
      <div className="bg-gray-50 rounded-lg p-4 space-y-2 text-sm">
        <div className="flex justify-between">
          <span className="text-gray-600">Torneo</span>
          <span className="font-medium">{name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Squadre</span>
          <span className="font-medium">
            {maxTeams} in {numGironi} gironi da {teamsPerGroup}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Giornate</span>
          <span className="font-medium">{numGiorni}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Slot per giornata</span>
          <span className="font-medium">
            {numSlotsPerGiorno} × {numCampi} {numCampi > 1 ? 'campi' : 'campo'}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-600">Partite totali</span>
          <span className="font-medium">{maxTeams * (teamsPerGroup - 1) / 2}</span>
        </div>

        {/* Orari compatti */}
        <div className="border-t pt-2 mt-2">
          <span className="text-gray-600 block mb-1">Orari configurati</span>
          {Array.from({ length: numCampi }, (_, ci) => (
            <div key={ci} className="text-xs text-gray-500">
              {numCampi > 1 && <span className="font-medium">Campo {ci + 1}: </span>}
              {Array.from({ length: numGiorni! }, (_, gi) => {
                const entry = slotOrari.find((e) => e.campo === ci + 1 && e.giorno === gi + 1)
                return (
                  <span key={gi} className="mr-3">
                    G{gi + 1}: {entry?.slots.join(', ') ?? '—'}
                  </span>
                )
              })}
            </div>
          ))}
        </div>
      </div>

      {/* Opzioni aggiuntive */}
      <div className="space-y-4">
        <div>
          <Label htmlFor="start-date">Data di inizio (opzionale)</Label>
          <Input
            id="start-date"
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
          />
        </div>

        <div className="flex items-center gap-2">
          <Switch id="public" checked={isPublic} onCheckedChange={setIsPublic} />
          <Label htmlFor="public">Torneo pubblico</Label>
        </div>

        <div>
          <Label htmlFor="logo">Logo torneo (opzionale, max 2MB)</Label>
          <input
            id="logo"
            type="file"
            accept="image/png,image/jpeg,image/webp"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-gray-50 file:text-gray-700 hover:file:bg-gray-100 mt-1"
            onChange={handleLogoChange}
          />
          {logoError && <p className="text-red-600 text-xs mt-1">{logoError}</p>}
        </div>
      </div>

      {submitError && <p className="text-red-600 text-sm">{submitError}</p>}

      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(3)}>
          ← Indietro
        </Button>
        <Button onClick={handleSubmit} disabled={submitting}>
          {submitting ? 'Creazione in corso...' : '✓ Crea Torneo'}
        </Button>
      </div>
    </div>
  )
}
