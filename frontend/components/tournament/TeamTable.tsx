'use client'
import { useEffect, useState } from 'react'
import { collection, onSnapshot } from 'firebase/firestore'
import { db } from '@/lib/firebase'
import { useFirebaseToken } from '@/lib/hooks/useFirebaseToken'
import { patchTeam } from '@/lib/api'
import type { Team } from '@/types/schema'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Props {
  tournamentId: string
}

export function TeamTable({ tournamentId }: Props) {
  const [teams, setTeams] = useState<Team[]>([])
  const { getToken } = useFirebaseToken()

  useEffect(() => {
    const ref = collection(db, 'tournaments', tournamentId, 'teams')
    const unsubscribe = onSnapshot(ref, (snap) => {
      setTeams(snap.docs.map((d) => ({ id: d.id, ...d.data() } as Team)))
    })
    return unsubscribe
  }, [tournamentId])

  const handlePatch = async (teamId: string, data: { forza?: number; confirmed?: boolean }) => {
    const token = await getToken()
    await patchTeam(tournamentId, teamId, data, token)
  }

  if (teams.length === 0) return <p>Nessuna squadra registrata.</p>

  return (
    <table className="w-full">
      <thead>
        <tr className="text-left border-b">
          <th className="p-2">Nome</th>
          <th className="p-2">Strength</th>
          <th className="p-2">Confermata</th>
        </tr>
      </thead>
      <tbody>
        {teams.map((team) => (
          <tr key={team.id} className="border-b">
            <td className="p-2">{team.nome}</td>
            <td className="p-2">
              <Select
                value={String(team.forza)}
                onValueChange={(v) => handlePatch(team.id, { forza: Number(v) })}
              >
                <SelectTrigger className="w-20">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {[1, 2, 3, 4, 5].map((n) => (
                    <SelectItem key={n} value={String(n)}>
                      {n}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </td>
            <td className="p-2">
              <Switch
                checked={team.confirmed}
                onCheckedChange={(checked) => handlePatch(team.id, { confirmed: checked })}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}
