import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SchedulePanel } from '@/components/tournament/SchedulePanel'
import * as api from '@/lib/api'

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('@/lib/hooks/useTournament', () => ({
  useTournament: () => ({ data: { id: 't-123', status: 'draft' }, loading: false }),
}))
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  query: jest.fn(),
  where: jest.fn(),
  onSnapshot: jest.fn((_q, cb) => { cb({ size: 3 }); return jest.fn() }),
}))

describe('SchedulePanel', () => {
  it('shows current status', () => {
    render(<SchedulePanel tournamentId="t-123" />)
    expect(screen.getByText(/draft/i)).toBeInTheDocument()
  })

  it('enables generate button when confirmed teams >= 2', () => {
    render(<SchedulePanel tournamentId="t-123" />)
    expect(screen.getByRole('button', { name: /genera gironi/i })).not.toBeDisabled()
  })

  it('calls generateSchedule on button click', async () => {
    const mockGenerate = jest.spyOn(api, 'generateSchedule').mockResolvedValue({ status: 'generated' })
    render(<SchedulePanel tournamentId="t-123" />)
    fireEvent.click(screen.getByRole('button', { name: /genera gironi/i }))
    await waitFor(() => {
      expect(mockGenerate).toHaveBeenCalledWith('t-123', 'fake-token')
    })
  })

  it('shows error message on failure', async () => {
    jest.spyOn(api, 'generateSchedule').mockRejectedValue(new Error('Infeasible'))
    render(<SchedulePanel tournamentId="t-123" />)
    fireEvent.click(screen.getByRole('button', { name: /genera gironi/i }))
    await waitFor(() => {
      expect(screen.getByText(/infeasible/i)).toBeInTheDocument()
    })
  })
})
