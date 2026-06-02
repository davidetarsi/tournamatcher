'use client'
import { useMemo } from 'react'

interface Slot {
  slot_id: string
  available: boolean
}

interface Props {
  numGiorni: number
  numSlotsPerGiorno: number
  value: Slot[]
  onChange: (slots: Slot[]) => void
}

export function AvailabilityGrid({ numGiorni, numSlotsPerGiorno, value, onChange }: Props) {
  const slotMap = useMemo(
    () => Object.fromEntries(value.map((s) => [s.slot_id, s.available])),
    [value]
  )

  const toggle = (slot_id: string, available: boolean) => {
    onChange(value.map((s) => (s.slot_id === slot_id ? { slot_id, available } : s)))
  }

  return (
    <div className="overflow-x-auto">
      <table className="text-sm border-collapse">
        <thead>
          <tr>
            <th className="p-2" />
            {Array.from({ length: numSlotsPerGiorno }, (_, i) => (
              <th key={i} className="p-2 font-medium text-gray-600 text-center">
                Slot {i + 1}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: numGiorni }, (_, gi) => (
            <tr key={gi} className="border-t">
              <td className="p-2 pr-4 font-medium text-gray-600 whitespace-nowrap">
                Giorno {gi + 1}
              </td>
              {Array.from({ length: numSlotsPerGiorno }, (_, si) => {
                const slot_id = `g${gi + 1}_s${si + 1}`
                return (
                  <td key={si} className="p-2 text-center">
                    <input
                      type="checkbox"
                      checked={slotMap[slot_id] ?? false}
                      onChange={(e) => toggle(slot_id, e.target.checked)}
                      className="w-4 h-4 cursor-pointer"
                    />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function initSlots(numGiorni: number, numSlotsPerGiorno: number): Slot[] {
  return Array.from({ length: numGiorni }, (_, gi) =>
    Array.from({ length: numSlotsPerGiorno }, (_, si) => ({
      slot_id: `g${gi + 1}_s${si + 1}`,
      available: false,
    }))
  ).flat()
}
