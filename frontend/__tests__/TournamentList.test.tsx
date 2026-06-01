import { render, screen } from '@testing-library/react'
import { TournamentList } from '@/components/tournament/TournamentList'

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/components/auth/AuthProvider', () => ({
  useAuth: () => ({ user: { uid: 'admin-uid-123' }, loading: false }),
}))
jest.mock('firebase/firestore', () => ({
  collection: jest.fn(),
  query: jest.fn(),
  where: jest.fn(),
  onSnapshot: jest.fn((_q, cb) => {
    cb({
      docs: [
        { id: 't-1', data: () => ({ name: 'Torneo Test', status: 'draft', public: false, admin_uid: 'admin-uid-123' }) },
      ],
    })
    return jest.fn()
  }),
}))

describe('TournamentList', () => {
  it('renders tournament names', () => {
    render(<TournamentList />)
    expect(screen.getByText('Torneo Test')).toBeInTheDocument()
  })

  it('shows empty message when no tournaments', () => {
    const { onSnapshot } = require('firebase/firestore')
    onSnapshot.mockImplementationOnce((_q: any, cb: any) => { cb({ docs: [] }); return jest.fn() })
    render(<TournamentList />)
    expect(screen.getByText(/nessun torneo/i)).toBeInTheDocument()
  })
})
