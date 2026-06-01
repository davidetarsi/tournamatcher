import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TeamTable } from '@/components/tournament/TeamTable'
import * as api from '@/lib/api'

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('@/components/ui/switch', () => ({
  Switch: ({ checked, onCheckedChange }: { checked: boolean; onCheckedChange: (v: boolean) => void }) => (
    <input
      type="checkbox"
      role="switch"
      checked={checked}
      onChange={(e) => onCheckedChange(e.target.checked)}
    />
  ),
}))
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  onSnapshot: jest.fn((_ref, cb) => {
    cb({
      docs: [
        { id: 'team-1', data: () => ({ nome: 'Leoni', forza: 5, confirmed: false, owner_uid: 'u1' }) },
      ],
    })
    return jest.fn()
  }),
}))

describe('TeamTable', () => {
  it('renders team names from Firestore', () => {
    render(<TeamTable tournamentId="t-123" />)
    expect(screen.getByText('Leoni')).toBeInTheDocument()
  })

  it('shows empty state when no teams', () => {
    const { onSnapshot } = require('firebase/firestore')
    onSnapshot.mockImplementationOnce((_r: any, cb: any) => { cb({ docs: [] }); return jest.fn() })
    render(<TeamTable tournamentId="t-123" />)
    expect(screen.getByText(/nessuna squadra/i)).toBeInTheDocument()
  })

  it('calls patchTeam when confirm toggle is clicked', async () => {
    const mockPatch = jest.spyOn(api, 'patchTeam').mockResolvedValue({ status: 'ok' })
    render(<TeamTable tournamentId="t-123" />)
    fireEvent.click(screen.getByRole('switch'))
    await waitFor(() => {
      expect(mockPatch).toHaveBeenCalledWith('t-123', 'team-1', { confirmed: true }, 'fake-token')
    })
  })
})
