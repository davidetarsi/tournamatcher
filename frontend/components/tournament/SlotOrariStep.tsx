'use client'
import type { CampoGiornoSlots } from '@/types/schema'

interface Props {
  numCampi: number
  numGiorni: number
  numSlotsPerGiorno: number
  value: CampoGiornoSlots[]
  onChange: (value: CampoGiornoSlots[]) => void
}

function toMinutes(time: string): number {
  const [h, m] = time.split(':').map(Number)
  return h * 60 + m
}

function addMinutes(time: string, minutes: number): string {
  const total = toMinutes(time) + minutes
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`
}

export function SlotOrariStep({ numCampi, numGiorni, numSlotsPerGiorno, value, onChange }: Props) {
  const getEntry = (campo: number, giorno: number) =>
    value.find((e) => e.campo === campo && e.giorno === giorno)

  const updateSlot = (campo: number, giorno: number, slotIdx: number, orario: string) => {
    onChange(
      value.map((entry) => {
        if (entry.campo !== campo || entry.giorno !== giorno) return entry
        const newSlots = [...entry.slots]
        newSlots[slotIdx] = orario
        return { ...entry, slots: newSlots }
      })
    )
  }

  const minTime = (campo: number, giorno: number, slotIdx: number): string => {
    if (slotIdx === 0) return '00:00'
    const prev = getEntry(campo, giorno)?.slots[slotIdx - 1]
    return prev ? addMinutes(prev, 5) : '00:00'
  }

  const isInvalid = (campo: number, giorno: number, slotIdx: number, orario: string): boolean => {
    if (!orario || slotIdx === 0) return false
    const prev = getEntry(campo, giorno)?.slots[slotIdx - 1]
    if (!prev) return false
    return toMinutes(orario) < toMinutes(prev) + 5
  }

  return (
    <div className="space-y-6">
      {Array.from({ length: numCampi }, (_, ci) => (
        <div key={ci} className="border rounded-lg p-4">
          <h3 className="font-semibold mb-4 text-sm">
            {numCampi > 1 ? `Campo ${ci + 1}` : 'Orari partite'}
          </h3>
          <div className="space-y-4">
            {Array.from({ length: numGiorni }, (_, gi) => {
              const entry = getEntry(ci + 1, gi + 1)
              return (
                <div key={gi}>
                  <p className="text-xs font-medium text-gray-500 mb-2">Giorno {gi + 1}</p>
                  <div className="flex flex-wrap gap-3">
                    {Array.from({ length: numSlotsPerGiorno }, (_, si) => {
                      const val = entry?.slots[si] ?? ''
                      const invalid = isInvalid(ci + 1, gi + 1, si, val)
                      const min = minTime(ci + 1, gi + 1, si)
                      return (
                        <div key={si} className="flex flex-col items-center gap-0.5">
                          <span className="text-xs text-gray-400">Slot {si + 1}</span>
                          <input
                            type="time"
                            step="300"
                            value={val}
                            min={min}
                            onChange={(e) => updateSlot(ci + 1, gi + 1, si, e.target.value)}
                            className={`border rounded px-2 py-1 text-sm w-28 focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                              invalid ? 'border-red-400 bg-red-50' : 'border-gray-300 bg-white'
                            }`}
                          />
                          {invalid && (
                            <span className="text-xs text-red-500">min {min}</span>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      ))}
    </div>
  )
}
