import { render, screen, fireEvent } from '@testing-library/react'
import { GoogleSignInButton } from '@/components/auth/GoogleSignInButton'

jest.mock('@/lib/firebase', () => ({ auth: {} }))
jest.mock('firebase/auth', () => ({
  GoogleAuthProvider: jest.fn().mockImplementation(() => ({})),
  signInWithPopup: jest.fn().mockResolvedValue({ user: {} }),
}))

describe('GoogleSignInButton', () => {
  it('renders a sign-in button', () => {
    render(<GoogleSignInButton />)
    expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument()
  })

  it('calls signInWithPopup on click', async () => {
    const { signInWithPopup } = require('firebase/auth')
    render(<GoogleSignInButton />)
    fireEvent.click(screen.getByRole('button', { name: /google/i }))
    expect(signInWithPopup).toHaveBeenCalled()
  })
})
