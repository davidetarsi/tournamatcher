import { SchemaEditor } from '@/components/tournament/SchemaEditor'

export default function SchemaPage({ params }: { params: { id: string } }) {
  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Editor Schema Campi</h1>
      <SchemaEditor tournamentId={params.id} />
    </main>
  )
}
