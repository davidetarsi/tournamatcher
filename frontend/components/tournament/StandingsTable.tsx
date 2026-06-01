import type { StandingsEntry, PointsSystem } from '@/types/schema'

interface Props {
  groupName: string
  entries: StandingsEntry[]
  pointsSystem?: PointsSystem
}

const DEFAULT_PS: PointsSystem = { win: 3, draw: 1, loss: 0, draws_allowed: true }

export function StandingsTable({ groupName, entries, pointsSystem = DEFAULT_PS }: Props) {
  const showDraws = pointsSystem.draws_allowed

  return (
    <div className="mb-6">
      <h3 className="font-semibold mb-2">Girone {groupName}</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="border-b text-gray-500 text-xs uppercase">
              <th className="py-2 pr-3 text-left w-8">Pos</th>
              <th className="py-2 pr-3 text-left">Squadra</th>
              <th className="py-2 px-2 text-center">G</th>
              <th className="py-2 px-2 text-center">V</th>
              {showDraws && <th className="py-2 px-2 text-center">P</th>}
              <th className="py-2 px-2 text-center">S</th>
              <th className="py-2 px-2 text-center">GF</th>
              <th className="py-2 px-2 text-center">GS</th>
              <th className="py-2 px-2 text-center">+/-</th>
              <th className="py-2 pl-2 text-center font-bold">Pt</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((e) => (
              <tr key={e.team_id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-3 text-gray-500">{e.position}</td>
                <td className="py-2 pr-3 font-medium">{e.team_name}</td>
                <td className="py-2 px-2 text-center">{e.played}</td>
                <td className="py-2 px-2 text-center">{e.wins}</td>
                {showDraws && <td className="py-2 px-2 text-center">{e.draws}</td>}
                <td className="py-2 px-2 text-center">{e.losses}</td>
                <td className="py-2 px-2 text-center">{e.goals_for}</td>
                <td className="py-2 px-2 text-center">{e.goals_against}</td>
                <td className="py-2 px-2 text-center">{e.goal_difference > 0 ? `+${e.goal_difference}` : e.goal_difference}</td>
                <td className="py-2 pl-2 text-center font-bold">{e.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
