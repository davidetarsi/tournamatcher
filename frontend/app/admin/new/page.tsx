import { TournamentWizard } from '@/components/tournament/TournamentWizard'

export default function NewTournamentPage() {
  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Nuovo torneo</h1>
      <TournamentWizard />
    </main>
  )
}
