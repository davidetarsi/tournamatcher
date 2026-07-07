'use client'
import { useEffect, useState } from 'react'
import { doc, getDoc } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { updateSchema } from '@/lib/api'
import type { TournamentSchema, SchemaField, PointsSystem, TiebreakerRule } from '@/types/schema'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Badge } from '@/components/ui/badge'

interface Props {
  tournamentId: string
}

export function SchemaEditor({ tournamentId }: Props) {
  const [schema, setSchema] = useState<TournamentSchema | null>(null)
  const [fields, setFields] = useState<SchemaField[]>([])
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const { getToken } = useFirebaseToken()
  const [ps, setPs] = useState<PointsSystem>({ win: 3, draw: 1, loss: 0, draws_allowed: true })
  const [tiebreakerRules, setTiebreakerRules] = useState<TiebreakerRule[]>(['goal_difference', 'goals_for', 'head_to_head'])
  const [numGiorni, setNumGiorni] = useState(1)
  const [numSlotsPerGiorno, setNumSlotsPerGiorno] = useState(1)

  useEffect(() => {
    const ref = doc(db, 'tournaments', tournamentId, 'config', 'schema')
    getDoc(ref).then((snap) => {
      if (snap.exists()) {
        const s = snap.data() as TournamentSchema
        setSchema(s)
        setFields(s.team_fields)
        if (s.points_system) setPs(s.points_system)
        if (s.tiebreaker_rules) setTiebreakerRules(s.tiebreaker_rules as TiebreakerRule[])
        if (s.num_giorni) setNumGiorni(s.num_giorni)
        if (s.num_slots_per_giorno) setNumSlotsPerGiorno(s.num_slots_per_giorno)
      }
    })
  }, [tournamentId])

  const removeField = (key: string) =>
    setFields((prev) => prev.filter((f) => f.key !== key))

  const addField = (field: SchemaField) =>
    setFields((prev) => [...prev, field])

  const handleSave = async () => {
    if (!schema) return
    setSaving(true)
    setSaved(false)
    setSaveError(null)
    try {
      const token = await getToken()
      await updateSchema(tournamentId, { ...schema, team_fields: fields, points_system: ps, tiebreaker_rules: tiebreakerRules, num_giorni: numGiorni, num_slots_per_giorno: numSlotsPerGiorno }, token)
      setSaved(true)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Errore durante il salvataggio')
    } finally {
      setSaving(false)
    }
  }

  if (!schema) return <p>Caricamento schema...</p>

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        {fields.map((f) => (
          <div key={f.key} className="flex items-center gap-3 p-3 border rounded">
            <span className="font-mono font-medium">{f.key}</span>
            <Badge variant="secondary">{f.type}</Badge>
            <span className="text-sm text-gray-500">{f.required ? 'richiesto' : 'opzionale'}</span>
            <Button
              variant="destructive"
              size="sm"
              aria-label={`rimuovi ${f.key}`}
              onClick={() => removeField(f.key)}
              className="ml-auto"
            >
              Rimuovi
            </Button>
          </div>
        ))}
      </div>

      <AddFieldForm onAdd={addField} existingKeys={fields.map((f) => f.key)} />

      <div className="space-y-4 border-t pt-4">
        <h3 className="font-semibold text-sm">Sistema punti</h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Vittoria</label>
            <Input
              type="number"
              min={0}
              className="w-20"
              value={ps.win}
              onChange={(e) => setPs((p) => ({ ...p, win: parseInt(e.target.value) || 0 }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Pareggio</label>
            <Input
              type="number"
              min={0}
              className="w-20"
              value={ps.draw}
              disabled={!ps.draws_allowed}
              onChange={(e) => setPs((p) => ({ ...p, draw: parseInt(e.target.value) || 0 }))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Sconfitta</label>
            <Input
              type="number"
              min={0}
              className="w-20"
              value={ps.loss}
              onChange={(e) => setPs((p) => ({ ...p, loss: parseInt(e.target.value) || 0 }))}
            />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={ps.draws_allowed}
              onChange={(e) => setPs((p) => ({ ...p, draws_allowed: e.target.checked }))}
            />
            Pareggi consentiti
          </label>
        </div>
        <div>
          <h4 className="text-xs text-gray-500 mb-2">Regole spareggio (ordine applicazione)</h4>
          <div className="space-y-1">
            {tiebreakerRules.map((rule, idx) => (
              <div key={rule} className="flex items-center gap-2 text-sm">
                <span className="w-36">{rule.replace(/_/g, ' ')}</span>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={idx === 0}
                  onClick={() =>
                    setTiebreakerRules((r) => {
                      const n = [...r]
                      ;[n[idx - 1], n[idx]] = [n[idx], n[idx - 1]]
                      return n
                    })
                  }
                >
                  ↑
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={idx === tiebreakerRules.length - 1}
                  onClick={() =>
                    setTiebreakerRules((r) => {
                      const n = [...r]
                      ;[n[idx], n[idx + 1]] = [n[idx + 1], n[idx]]
                      return n
                    })
                  }
                >
                  ↓
                </Button>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="space-y-4 border-t pt-4">
        <h3 className="font-semibold text-sm">Disponibilità e Iscrizioni</h3>
        <div className="flex flex-wrap gap-4 items-end">
          <div>
            <label className="text-xs text-gray-500 block mb-1">Giornate</label>
            <Input
              type="number"
              min={1}
              className="w-20"
              value={numGiorni}
              onChange={(e) => setNumGiorni(Math.max(1, parseInt(e.target.value) || 1))}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 block mb-1">Slot per giornata</label>
            <Input
              type="number"
              min={1}
              className="w-20"
              value={numSlotsPerGiorno}
              onChange={(e) => setNumSlotsPerGiorno(Math.max(1, parseInt(e.target.value) || 1))}
            />
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Salvataggio...' : 'Salva Schema'}
        </Button>
        {saved && <span className="text-green-600 text-sm">Salvato!</span>}
      </div>
      {saveError && <p className="text-red-600 text-sm">{saveError}</p>}
    </div>
  )
}

function AddFieldForm({
  onAdd,
  existingKeys,
}: {
  onAdd: (f: SchemaField) => void
  existingKeys: string[]
}) {
  const [key, setKey] = useState('')
  const [type, setType] = useState<SchemaField['type']>('text')
  const [required, setRequired] = useState(true)
  const [maxLength, setMaxLength] = useState(100)

  const isDuplicate = existingKeys.includes(key)

  const handleAdd = () => {
    if (!key || isDuplicate) return
    onAdd({ key, type, required, max_length: type === 'text' ? maxLength : undefined })
    setKey('')
  }

  return (
    <div className="flex flex-wrap gap-2 items-end border-t pt-4">
      <div>
        <label className="text-sm text-gray-600">Chiave</label>
        <Input
          placeholder="es. phone"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          className="w-32"
        />
        {isDuplicate && <p className="text-red-500 text-xs">Chiave già esistente</p>}
      </div>
      <div>
        <label className="text-sm text-gray-600">Tipo</label>
        <Select value={type} onValueChange={(v) => setType(v as SchemaField['type'])}>
          <SelectTrigger className="w-28">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="text">text</SelectItem>
            <SelectItem value="email">email</SelectItem>
            <SelectItem value="number">number</SelectItem>
            <SelectItem value="date">date</SelectItem>
          </SelectContent>
        </Select>
      </div>
      {type === 'text' && (
        <div>
          <label className="text-sm text-gray-600">Max length</label>
          <Input
            type="number"
            value={maxLength}
            onChange={(e) => setMaxLength(Number(e.target.value))}
            className="w-24"
          />
        </div>
      )}
      <Button onClick={handleAdd} disabled={!key || isDuplicate}>
        Aggiungi campo
      </Button>
    </div>
  )
}
