import AuthButton from '@/components/auth/AuthButton'
import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b">
        <Link href="/" className="text-xl font-bold">Tournament Manager</Link>
        <nav className="flex items-center gap-4">
          <AuthButton />
        </nav>
      </header>

      {/* Hero */}
      <main className="flex-1">
        <section className="py-24 px-6 text-center max-w-3xl mx-auto">
          <h1 className="text-5xl font-bold mb-6">Organizza il tuo torneo in pochi minuti</h1>
          <p className="text-xl text-gray-600 mb-10">Gironi automatici, iscrizioni squadre, classifiche in tempo reale. Tutto gratis.</p>
          <Link href="/admin/new" className="inline-block bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors">
            Crea il tuo torneo
          </Link>
        </section>

        {/* Feature Grid */}
        <section className="py-16 px-6 bg-gray-50">
          <div className="max-w-5xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8">
            {[
              { title: 'Gironi e calendario automatico', desc: 'Inserisci le squadre e il sistema genera gironi bilanciati e il calendario completo.' },
              { title: 'Iscrizione squadre con codice', desc: 'Ogni torneo ha un link unico. Le squadre si iscrivono in autonomia.' },
              { title: 'Pagina pubblica real-time', desc: "Classifiche e risultati aggiornati in tempo reale, visibili a tutti senza login." },
              { title: 'Gestione giocatori con deadline', desc: 'Le squadre gestiscono i propri giocatori entro la scadenza impostata.' },
            ].map((f) => (
              <div key={f.title} className="bg-white rounded-xl p-6 shadow-sm">
                <h3 className="text-lg font-semibold mb-2">{f.title}</h3>
                <p className="text-gray-600">{f.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Final CTA */}
        <section className="py-24 px-6 text-center">
          <h2 className="text-3xl font-bold mb-6">Pronto a iniziare?</h2>
          <Link href="/admin/new" className="inline-block bg-blue-600 text-white px-8 py-4 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors">
            Inizia gratis
          </Link>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t px-6 py-4 text-sm text-gray-500 flex gap-4">
        <a href="#">Privacy policy</a>
        <a href="#">Termini di servizio</a>
        <a href="#">Contatti</a>
      </footer>
    </div>
  )
}
