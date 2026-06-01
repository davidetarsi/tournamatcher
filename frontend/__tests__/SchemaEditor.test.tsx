import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { SchemaEditor } from '@/components/tournament/SchemaEditor'
import * as api from '@/lib/api'

const mockSchema = {
  sport: 'calcetto',
  max_teams: 8,
  teams_per_group: 4,
  public: false,
  invite_codes: { enabled: false, partial: false },
  team_fields: [{ key: 'nome', type: 'text', required: true, max_length: 100 }],
  player_fields: [],
  admin_controls: { can_set_strength: true, max_teams: 8 },
}

jest.mock('@/lib/firebase', () => ({ db: {} }))
jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('firebase/firestore', () => ({
  doc: jest.fn(),
  getDoc: jest.fn().mockResolvedValue({
    exists: () => true,
    data: () => mockSchema,
  }),
}))

describe('SchemaEditor', () => {
  it('renders existing fields after load', async () => {
    render(<SchemaEditor tournamentId="t-123" />)
    await waitFor(() => {
      expect(screen.getByText('nome')).toBeInTheDocument()
    })
  })

  it('removes a field when the remove button is clicked', async () => {
    render(<SchemaEditor tournamentId="t-123" />)
    await waitFor(() => screen.getByText('nome'))
    fireEvent.click(screen.getByRole('button', { name: /rimuovi nome/i }))
    expect(screen.queryByText('nome')).not.toBeInTheDocument()
  })

  it('calls updateSchema on save', async () => {
    const mockUpdate = jest.spyOn(api, 'updateSchema').mockResolvedValue({ status: 'updated' })
    render(<SchemaEditor tournamentId="t-123" />)
    await waitFor(() => screen.getByText('nome'))
    fireEvent.click(screen.getByRole('button', { name: /salva schema/i }))
    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith('t-123', expect.objectContaining({ sport: 'calcetto' }), 'fake-token')
    })
  })
})
