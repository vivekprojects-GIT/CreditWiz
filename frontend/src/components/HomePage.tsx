import { ArrowRight, ArrowUp, Bell, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { fetchNotifications, isAbort } from '../lib/api'
import { useHub } from '../lib/hub'
import { fetchMarketplaceHome, type Agent } from '../lib/marketplace'
import { usePersona } from '../lib/personaContext'
import { pillarBasePath, type Notification } from '../lib/types'

function timeAgo(iso: string): string {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return d === 1 ? 'yesterday' : `${d}d ago`
}

/**
 * The ask box is the hub's front door, not the marketplace's. It is meant to
 * take any request and route it to whichever pillar owns the answer -- that
 * routing is the LangGraph service still to be built, where each pillar is an
 * agent.
 *
 * Until then the starters are honest about where they land. Each carries its
 * pillar's name, and one with a `query` runs a real search there while the
 * rest open the pillar that will own the answer. Every query is checked
 * against the local lexicon -- what the deployment runs when no model key is
 * set -- so no starter can return "no match" in front of an audience.
 */
type Starter = {
  /** Pillar id, so the route is taken from hub data and cannot drift. */
  pillar: string
  text: string
  /** A real query for a live pillar; omitted when the starter just opens it. */
  query?: string
}

const STARTERS: Starter[] = [
  { pillar: 'marketplace', text: 'Screen a client against sanctions lists', query: 'Screen a client against sanctions lists' },
  { pillar: 'marketplace', text: 'Work out who ultimately owns a company', query: 'Work out who ultimately owns a company' },
  { pillar: 'marketplace', text: 'Check W-8 and FATCA classification', query: 'Check W-8 and FATCA classification' },
  { pillar: 'learning', text: 'Start a path for my role' },
  { pillar: 'governance', text: 'How do I get an agent approved?' },
  { pillar: 'intake', text: 'Request a new agent' },
]

export function HomePage() {
  const data = useHub()
  const { persona } = usePersona()
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [picked, setPicked] = useState<Agent[] | null>(null)
  const [error, setError] = useState('')
  const [news, setNews] = useState<Notification[]>([])

  useEffect(() => {
    const ctrl = new AbortController()
    fetchMarketplaceHome(persona, ctrl.signal, 'all')
      .then((h) => {
        setError('')
        setPicked((h.carousels.find((c) => c.id === 'recommended')?.agents ?? []).slice(0, 3))
      })
      .catch((e: unknown) => {
        if (!isAbort(e)) setError(e instanceof Error ? e.message : 'Could not load agents')
      })
    fetchNotifications(ctrl.signal)
      .then((n) => setNews(n.slice(0, 3)))
      .catch((err: unknown) => {
        if (!isAbort(err)) setNews([])
      })
    return () => ctrl.abort()
  }, [persona])

  function ask(q: string) {
    const trimmed = q.trim()
    // Marketplace search is the only engine that understands a sentence today.
    // When the router lands this becomes a single call that decides the pillar.
    if (trimmed) navigate(`/marketplace?q=${encodeURIComponent(trimmed)}`)
  }

  return (
    <div className="content home">
      <section className="ask" aria-labelledby="ask-title">
        <p className="ask__kicker">Enterprise AI Hub</p>
        <h1 className="ask__title" id="ask-title">
          Welcome, {data.user.first_name}. What do you need?
        </h1>
        <p className="ask__lead">
          Ask for an agent, a policy, a learning path or a person. One box for the whole hub.
        </p>

        <form
          className="ask__form"
          onSubmit={(e) => {
            e.preventDefault()
            ask(query)
          }}
          role="search"
        >
          <Sparkles className="ask__spark" size={18} strokeWidth={2.2} aria-hidden="true" />
          <input
            className="ask__input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything across the AI Hub"
            aria-label="Ask anything across the AI Hub"
            autoComplete="off"
          />
          <button
            className="ask__go"
            type="submit"
            disabled={!query.trim()}
            aria-label="Ask"
            title="Ask"
          >
            <ArrowUp size={18} strokeWidth={2.6} />
          </button>
        </form>

        <ul className="starters" aria-label="Example requests">
          {STARTERS.map((s) => {
            const pillar = data.pillars.find((p) => p.id === s.pillar)
            if (!pillar) return null
            const base = pillarBasePath(pillar)
            return (
              <li key={s.text}>
                <Link
                  className="starter"
                  to={s.query ? `${base}?q=${encodeURIComponent(s.query)}` : base}
                >
                  <span className="starter__pillar">{pillar.short_title}</span>
                  {s.text}
                </Link>
              </li>
            )
          })}
        </ul>

        <p className="ask__note">
          Agent search and Learning answer for real. The other pillars open their page until the
          assistant that routes across all nine is connected.
        </p>
      </section>

      <div className="home-cards">
        <section className="panel home-card" aria-labelledby="home-picked">
          <div className="home-card__head">
            <h2 className="home-card__title" id="home-picked">
              Picked for you
            </h2>
            <Link to="/marketplace" className="textlink">
              All agents <ArrowRight size={14} strokeWidth={2.4} />
            </Link>
          </div>
          {error ? (
            <p role="alert">{error}</p>
          ) : picked ? (
            <ul className="home-list">
              {picked.map((a) => (
                <li key={a.id}>
                  <Link className="home-row" to={`/marketplace/agents/${a.id}`}>
                    <span className="home-row__title">{a.name}</span>
                    <span className="home-row__sub">{a.tagline}</span>
                  </Link>
                </li>
              ))}
            </ul>
          ) : (
            <div className="skeleton" style={{ height: 150 }} />
          )}
        </section>

        <section className="panel home-card" aria-labelledby="home-jump">
          <div className="home-card__head">
            <h2 className="home-card__title" id="home-jump">
              Jump back in
            </h2>
          </div>
          <ul className="home-list">
            <li>
              <Link className="home-row" to="/learning/me">
                <span className="home-row__title">My learning</span>
                <span className="home-row__sub">Progress, required steps and saved items.</span>
              </Link>
            </li>
            <li>
              <Link className="home-row" to="/learning/catalog">
                <span className="home-row__title">Learning catalog</span>
                <span className="home-row__sub">Videos, runbooks and quick references.</span>
              </Link>
            </li>
            <li>
              <Link className="home-row" to="/community">
                <span className="home-row__title">Community</span>
                <span className="home-row__sub">Forums, SME directory and FAQs.</span>
              </Link>
            </li>
          </ul>
        </section>

        <section className="panel home-card" aria-labelledby="home-news">
          <div className="home-card__head">
            <h2 className="home-card__title" id="home-news">
              <Bell size={16} strokeWidth={2.4} /> What's new
            </h2>
          </div>
          {news.length === 0 ? (
            <p className="muted">Nothing new right now.</p>
          ) : (
            <ul className="home-list">
              {news.map((n) => (
                <li key={n.id}>
                  <Link className="home-row" to={n.href}>
                    <span className="home-row__title">{n.title}</span>
                    <span className="home-row__sub">{n.body}</span>
                    <span className="home-row__time">{timeAgo(n.created_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  )
}
