import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TournamentWizard } from '@/components/tournament/TournamentWizard'
import * as api from '@/lib/api'

jest.mock('@/lib/api')
jest.mock('@/lib/hooks/useFirebaseToken', () => ({
  useFirebaseToken: () => ({ getToken: jest.fn().mockResolvedValue('fake-token') }),
}))
jest.mock('next/navigation', () => ({ useRouter: () => ({ push: jest.fn() }) }))

describe('TournamentWizard', () => {
  it('shows template options on step 1', () => {
    render(<TournamentWizard />)
    expect(screen.getByText(/calcetto/i)).toBeInTheDocument()
    expect(screen.getByText(/basket/i)).toBeInTheDocument()
    expect(screen.getByText(/personalizzato/i)).toBeInTheDocument()
  })

  it('disables Avanti button until a template is selected', () => {
    render(<TournamentWizard />)
    expect(screen.getByRole('button', { name: /avanti/i })).toBeDisabled()
  })

  it('advances to step 2 after selecting a template', async () => {
    render(<TournamentWizard />)
    fireEvent.click(screen.getByText(/calcetto/i))
    fireEvent.click(screen.getByRole('button', { name: /avanti/i }))
    await waitFor(() => {
      expect(screen.getByLabelText(/nome torneo/i)).toBeInTheDocument()
    })
  })

  it('calls createTournament and redirects on submit', async () => {
    const mockCreate = jest.spyOn(api, 'createTournament').mockResolvedValue({ tournament_id: 't-new', slug: 'torneo-2026' })
    const { push } = require('next/navigation').useRouter()
    render(<TournamentWizard />)
    fireEvent.click(screen.getByText(/calcetto/i))
    fireEvent.click(screen.getByRole('button', { name: /avanti/i }))
    await waitFor(() => screen.getByLabelText(/nome torneo/i))
    fireEvent.change(screen.getByLabelText(/nome torneo/i), { target: { value: 'Torneo 2026' } })
    fireEvent.click(screen.getByRole('button', { name: /crea torneo/i }))
    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        expect.objectContaining({ name: 'Torneo 2026' }),
        'fake-token'
      )
    })
  })
})
