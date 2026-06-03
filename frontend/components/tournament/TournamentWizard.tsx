'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { createTournament } from '@/lib/api'
import type { SchemaField } from '@/types/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

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

export function TournamentWizard() {
  const [step, setStep] = useState(1)
  const [template, setTemplate] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [maxTeams, setMaxTeams] = useState(8)
  const [teamsPerGroup, setTeamsPerGroup] = useState(4)
  const [isPublic, setIsPublic] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [logoFile, setLogoFile] = useState<File | null>(null)
  const [logoError, setLogoError] = useState<string | null>(null)
  const { getToken } = useFirebaseToken()
  const router = useRouter()

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

  const handleSubmit = async () => {
    if (!template) return
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
            num_giorni: 1,
            num_slots_per_giorno: 1,
            max_public_teams: 0,
          },
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

  if (step === 1) {
    return (
      <div className="space-y-6">
        <h2 className="text-xl font-bold">Scegli template</h2>
        <div className="grid grid-cols-3 gap-4">
          {Object.keys(TEMPLATES).map((key) => (
            <button
              key={key}
              className={`p-6 border-2 rounded-lg capitalize font-medium transition-colors ${
                template === key ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-400'
              }`}
              onClick={() => setTemplate(key)}
            >
              {key}
            </button>
          ))}
        </div>
        <Button onClick={() => setStep(2)} disabled={!template}>
          Avanti
        </Button>
      </div>
    )
  }

  return (
    <div className="space-y-4 max-w-md">
      <h2 className="text-xl font-bold">Configura torneo</h2>
      <div>
        <Label htmlFor="name">Nome torneo</Label>
        <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>
      <div>
        <Label htmlFor="max-teams">Max squadre</Label>
        <Input
          id="max-teams"
          type="number"
          value={maxTeams}
          onChange={(e) => setMaxTeams(Number(e.target.value))}
        />
      </div>
      <div>
        <Label htmlFor="teams-per-group">Squadre per girone</Label>
        <Input
          id="teams-per-group"
          type="number"
          value={teamsPerGroup}
          onChange={(e) => setTeamsPerGroup(Number(e.target.value))}
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
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(1)}>
          Indietro
        </Button>
        <Button onClick={handleSubmit} disabled={!name || submitting}>
          {submitting ? 'Creazione...' : 'Crea Torneo'}
        </Button>
      </div>
      {submitError && <p className="text-red-600 text-sm">{submitError}</p>}
    </div>
  )
}
