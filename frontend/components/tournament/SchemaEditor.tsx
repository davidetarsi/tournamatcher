'use client'
import { useEffect, useState } from 'react'
import { doc, getDoc } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { updateSchema } from '@/lib/api'
import type { TournamentSchema, SchemaField } from '@/types/schema'
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
  const { getToken } = useFirebaseToken()

  useEffect(() => {
    const ref = doc(db, 'tournaments', tournamentId, 'config', 'schema')
    getDoc(ref).then((snap) => {
      if (snap.exists()) {
        const s = snap.data() as TournamentSchema
        setSchema(s)
        setFields(s.team_fields)
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
    try {
      const token = await getToken()
      await updateSchema(tournamentId, { ...schema, team_fields: fields }, token)
      setSaved(true)
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

      <div className="flex items-center gap-3">
        <Button onClick={handleSave} disabled={saving}>
          {saving ? 'Salvataggio...' : 'Salva Schema'}
        </Button>
        {saved && <span className="text-green-600 text-sm">Salvato!</span>}
      </div>
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
