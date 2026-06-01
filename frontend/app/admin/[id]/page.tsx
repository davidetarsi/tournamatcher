'use client'
import Link from 'next/link'
import { useTournament } from '@/lib/hooks/useTournament'
import { TeamTable } from '@/components/tournament/TeamTable'
import { InviteCodesPanel } from '@/components/tournament/InviteCodesPanel'
import { SchedulePanel } from '@/components/tournament/SchedulePanel'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

export default function DashboardPage({ params }: { params: { id: string } }) {
  const { data: tournament, loading } = useTournament(params.id)

  if (loading) return <div className="p-6">Caricamento...</div>
  if (!tournament) return <div className="p-6">Torneo non trovato.</div>

  return (
    <main className="container mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{tournament.name}</h1>
        <Link href={`/admin/${params.id}/schema`}>
          <Button variant="outline">Modifica schema</Button>
        </Link>
      </div>
      <Tabs defaultValue="teams">
        <TabsList>
          <TabsTrigger value="teams">Squadre</TabsTrigger>
          <TabsTrigger value="invite">Invite Codes</TabsTrigger>
          <TabsTrigger value="schedule">Calendario</TabsTrigger>
        </TabsList>
        <TabsContent value="teams" className="mt-4">
          <TeamTable tournamentId={params.id} />
        </TabsContent>
        <TabsContent value="invite" className="mt-4">
          <InviteCodesPanel tournamentId={params.id} />
        </TabsContent>
        <TabsContent value="schedule" className="mt-4">
          <SchedulePanel tournamentId={params.id} />
        </TabsContent>
      </Tabs>
    </main>
  )
}
