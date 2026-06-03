'use client'
import { useParams } from 'next/navigation'
import { useSlugResolution } from '@/lib/hooks/useSlugResolution'
import { SchemaEditor } from '@/components/tournament/SchemaEditor'

export default function SchemaPage() {
  const { slug } = useParams() as { slug: string }
  const { tournamentId, loading, notFound } = useSlugResolution(slug)

  if (loading) return <div className="p-6">Caricamento...</div>
  if (notFound || !tournamentId) return <div className="p-6">Torneo non trovato.</div>

  return (
    <main className="container mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Editor Schema Campi</h1>
      <SchemaEditor tournamentId={tournamentId} />
    </main>
  )
}
