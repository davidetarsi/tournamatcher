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
  const { getToken } = useFirebaseToken()
  const router = useRouter()

  const handleSubmit = async () => {
    if (!template) return
    const tmpl = TEMPLATES[template]
    const token = await getToken()
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
        },
      },
      token
    )
    router.push(`/admin/${result.tournament_id}`)
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
      <div className="flex gap-2">
        <Button variant="outline" onClick={() => setStep(1)}>
          Indietro
        </Button>
        <Button onClick={handleSubmit} disabled={!name}>
          Crea Torneo
        </Button>
      </div>
    </div>
  )
}
