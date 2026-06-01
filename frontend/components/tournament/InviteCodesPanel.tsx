'use client'
import { useTournament } from '@/lib/hooks/useTournament'

interface Props {
  tournamentId: string
}

export function InviteCodesPanel({ tournamentId }: Props) {
  const { data: tournament } = useTournament(tournamentId)

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        La gestione dei codici invito sarà disponibile nella prossima versione (Plan C).
      </p>
      {tournament && (
        <p>
          Modalità accesso:{' '}
          <strong>{tournament.public ? 'Pubblica' : 'Su invito'}</strong>
        </p>
      )}
    </div>
  )
}
