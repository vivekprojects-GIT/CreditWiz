import { ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { fetchJourneys, type JourneysHome } from '../../lib/journeys'
import { usePersona } from '../../lib/personaContext'
import '../../journeys.css'
import { PageBand } from '../PageBand'
import { JourneyGrid } from './JourneyGrid'

/** Every job the signed-in persona does. */
export function JourneysPage() {
  const { persona } = usePersona()
  const [home, setHome] = useState<JourneysHome | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const ctrl = new AbortController()
    fetchJourneys(persona, ctrl.signal)
      .then((h) => {
        setError('')
        setHome(h)
      })
      .catch((e: unknown) => {
        if (!isAbort(e)) setError(e instanceof Error ? e.message : 'Could not load your work')
      })
    return () => ctrl.abort()
  }, [persona])

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>Your work</span>
      </nav>
      <PageBand
        compact
        kicker={home?.persona_label}
        title="Your work"
        lead="The jobs you do, and what helps at each one: systems, data, prompts, agents, learning and people."
      />
      {error ? (
        <p role="alert">{error}</p>
      ) : !home ? (
        <div className="skeleton" style={{ height: 280 }} />
      ) : home.journeys.length ? (
        <JourneyGrid journeys={home.journeys} />
      ) : (
        <section className="panel">
          <h2 className="panel__title">No journeys for your role yet</h2>
          <p className="panel__text">
            Journeys start with Relationship Managers. Other roles follow as the client confirms which personas come
            next.
          </p>
        </section>
      )}
    </div>
  )
}
