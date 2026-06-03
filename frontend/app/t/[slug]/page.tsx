import type { Metadata } from 'next'
import TournamentPublicClient from './TournamentPublicClient'

type Props = { params: { slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const apiUrl = process.env.RAILWAY_API_URL
  try {
    const res = await fetch(`${apiUrl}/tournaments/by-slug/${params.slug}`, {
      next: { revalidate: 60 },
    })
    if (!res.ok) return { title: 'Torneo non trovato' }
    const data = await res.json()
    const image = data.logo_url || process.env.NEXT_PUBLIC_DEFAULT_LOGO_URL || ''
    return {
      title: `${data.name} | Tournament Manager`,
      openGraph: {
        title: data.name,
        description: 'Iscrizioni aperte, risultati e classifiche in tempo reale.',
        images: [image],
      },
    }
  } catch {
    return { title: 'Tournament Manager' }
  }
}

export default function TournamentPage({ params }: Props) {
  return <TournamentPublicClient slug={params.slug} />
}
