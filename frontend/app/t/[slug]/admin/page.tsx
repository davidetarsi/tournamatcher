'use client'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useSlugResolution } from '@/lib/hooks/useSlugResolution'
import { useTournament } from '@/lib/hooks/useTournament'
import { TeamTable } from '@/components/tournament/TeamTable'
import { InviteCodesPanel } from '@/components/tournament/InviteCodesPanel'
import { SchedulePanel } from '@/components/tournament/SchedulePanel'
import { ResultsTab } from '@/components/tournament/ResultsTab'
import { StandingsTab } from '@/components/tournament/StandingsTab'
import { TournamentDatesPanel } from '@/components/tournament/TournamentDatesPanel'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { PointsSystem } from '@/types/schema'

const DEFAULT_PS: PointsSystem = { win: 3, draw: 1, loss: 0, draws_allowed: true }

export default function AdminDashboardPage() {
  const { slug } = useParams() as { slug: string }
  const { tournamentId, loading: slugLoading, notFound: slugNotFound } = useSlugResolution(slug)
  const { data: tournament, loading } = useTournament(tournamentId ?? '')

  if (slugLoading || loading) return <div className="p-6">Caricamento...</div>
  if (slugNotFound || !tournament) return <div className="p-6">Torneo non trovato.</div>

  const ps: PointsSystem = tournament.points_system ?? DEFAULT_PS

  return (
    <main className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{tournament.name}</h1>
        <Link href={`/t/${slug}/admin/schema`}>
          <Button variant="outline">Modifica schema</Button>
        </Link>
      </div>
      <Tabs defaultValue="teams">
        <TabsList>
          <TabsTrigger value="teams">Squadre</TabsTrigger>
          <TabsTrigger value="invite">Invite Codes</TabsTrigger>
          <TabsTrigger value="schedule">Calendario</TabsTrigger>
          <TabsTrigger value="results">Risultati</TabsTrigger>
          <TabsTrigger value="standings">Classifiche</TabsTrigger>
          <TabsTrigger value="dates">Date</TabsTrigger>
        </TabsList>
        <TabsContent value="teams" className="mt-4">
          <TeamTable tournamentId={tournamentId!} />
        </TabsContent>
        <TabsContent value="invite" className="mt-4">
          <InviteCodesPanel tournamentId={tournamentId!} />
        </TabsContent>
        <TabsContent value="schedule" className="mt-4">
          <SchedulePanel tournamentId={tournamentId!} />
        </TabsContent>
        <TabsContent value="results" className="mt-4">
          <ResultsTab tournamentId={tournamentId!} pointsSystem={ps} />
        </TabsContent>
        <TabsContent value="standings" className="mt-4">
          <StandingsTab tournamentId={tournamentId!} pointsSystem={ps} />
        </TabsContent>
        <TabsContent value="dates" className="mt-4">
          <TournamentDatesPanel tournamentId={tournamentId!} />
        </TabsContent>
      </Tabs>
    </main>
  )
}
