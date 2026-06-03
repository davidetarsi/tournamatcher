'use client'
import { useEffect } from 'react'

export default function AdminError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error('Admin page error:', error)
  }, [error])

  return (
    <div style={{ padding: '2rem', fontFamily: 'monospace' }}>
      <h2 style={{ color: 'red' }}>Errore pagina admin</h2>
      <pre style={{ background: '#f5f5f5', padding: '1rem', overflow: 'auto', fontSize: '0.85rem' }}>
        {error.message}
        {error.stack && '\n\n' + error.stack}
      </pre>
      <button onClick={reset} style={{ marginTop: '1rem', padding: '0.5rem 1rem', cursor: 'pointer' }}>
        Riprova
      </button>
    </div>
  )
}
