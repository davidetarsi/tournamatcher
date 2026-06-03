import type { Metadata } from 'next'
import { getTournamentBySlug } from '@/lib/api'
import TournamentPublicClient from './TournamentPublicClient'

type Props = { params: { slug: string } }

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const data = await getTournamentBySlug(params.slug)
    const image = data.logo_url || process.env.NEXT_PUBLIC_DEFAULT_LOGO_URL || ''
    return {
      title: `${data.name} | Tournament Manager`,
      openGraph: {
        title: data.name,
        description: 'Iscrizioni aperte, risultati e classifiche in tempo reale.',
        ...(image ? { images: [image] } : {}),
      },
    }
  } catch {
    return { title: 'Tournament Manager' }
  }
}

export default function TournamentPage({ params }: Props) {
  return <TournamentPublicClient slug={params.slug} />
}
