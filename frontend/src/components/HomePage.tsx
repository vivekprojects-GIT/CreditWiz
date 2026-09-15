import { ArrowRight, Bell } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { fetchNotifications, isAbort, searchHub } from '../lib/api'
import { useHub } from '../lib/hub'
import { matchSections } from '../lib/hubSearch'
import { fetchMarketplaceHome, type Agent } from '../lib/marketplace'
import { usePersona } from '../lib/personaContext'
import type { Notification, SearchResult } from '../lib/types'
import { BandSearch } from './BandSearch'
import { PageBand } from './PageBand'

function timeAgo(iso: string): string {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return d === 1 ? 'yesterday' : `${d}d ago`
}

/**
 * The search bar is the hub's front door, not the marketplace's. It is meant
 * to take any request and route it to whichever pillar owns the answer -- that
 * routing is the LangGraph service still to be built, where each pillar is an
 * agent.
 *
 * Until then a question asked here is answered here, from what is real: agents
 * from Discover's search, items from the learning catalog, and the pages of
 * every pillar that match. It is the same bar every pillar opens with, so
 * search looks and works the same wherever someone starts.
 */
const EXAMPLES = [
  'Screen a client against sanctions lists',
  'Who ultimately owns a company',
  'Summarise a contract',
  'Check W-8 and FATCA classification',
]

const SHOWN = 5

export function HomePage() {
  const data = useHub()
  const { persona } = usePersona()
  const [params, setParams] = useSearchParams()
  const q = (params.get('q') ?? '').trim()
  const [draft, setDraft] = useState(q)
  useEffect(() => setDraft(q), [q])
  const [found, setFound] = useState<{ q: string; results: SearchResult[] } | null>(null)
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

  useEffect(() => {
    if (!q) return
    const ctrl = new AbortController()
    searchHub(q, ctrl.signal)
      .then((results) => setFound({ q, results }))
      .catch((e: unknown) => {
        if (!isAbort(e)) setFound({ q, results: [] })
      })
    return () => ctrl.abort()
  }, [q])

  function ask(value: string) {
    const trimmed = value.trim()
    if (!trimmed) return
    setDraft(trimmed)
    // Pushed, not replaced, so Back returns to the home page as it was.
    setParams({ q: trimmed })
  }

  function clear() {
    setDraft('')
    setParams({}, { replace: true })
  }

  const results = found?.q === q ? found.results : null
  const agents = results?.filter((r) => r.kind === 'agent').slice(0, SHOWN) ?? null
  const learning = results?.filter((r) => r.kind === 'learning').slice(0, SHOWN) ?? null
  const pages = q ? matchSections(data.pillars, q, SHOWN) : []

  return (
    <div className="content home">
      <PageBand
        compact
        kicker="Enterprise AI Hub"
        title={`Welcome, ${data.user.first_name}. What do you need?`}
        lead="Ask for an agent, a policy, a learning path or a person. One search for the whole hub."
      >
        <BandSearch
          value={draft}
          onChange={setDraft}
          onSearch={ask}
          onClear={clear}
          placeholder="Ask anything across the AI Hub"
          label="Ask anything across the AI Hub"
          action="Search"
          examples={q ? [] : EXAMPLES}
          busy={Boolean(q) && results === null}
        />
      </PageBand>

      {q ? (
        <section className="home-results" aria-live="polite" aria-labelledby="home-results-title">
          <div className="home-results__head">
            <div>
              <h2 className="home-results__title" id="home-results-title">
                Results for “{q}”
              </h2>
              <p className="home-results__count">Agents from Discover, the learning catalog and pages across every pillar.</p>
            </div>
          </div>

          <div className="home-cards">
            <section className="panel home-card" aria-labelledby="home-agents">
              <div className="home-card__head">
                <h3 className="home-card__title" id="home-agents">
                  Agents
                </h3>
                <Link to={`/marketplace?q=${encodeURIComponent(q)}`} className="textlink">
                  See all in Discover <ArrowRight size={14} strokeWidth={2.4} />
                </Link>
              </div>
              {agents === null ? (
                <div className="skeleton" style={{ height: 120 }} />
              ) : agents.length ? (
                <ul className="home-list">
                  {agents.map((r) => (
                    <li key={r.href}>
                      <Link className="home-row" to={r.href}>
                        <span className="home-row__title">{r.title}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No agent matches this yet.</p>
              )}
            </section>

            <section className="panel home-card" aria-labelledby="home-learning">
              <div className="home-card__head">
                <h3 className="home-card__title" id="home-learning">
                  Learning
                </h3>
                <Link to="/learning/catalog" className="textlink">
                  Catalog <ArrowRight size={14} strokeWidth={2.4} />
                </Link>
              </div>
              {learning === null ? (
                <div className="skeleton" style={{ height: 120 }} />
              ) : learning.length ? (
                <ul className="home-list">
                  {learning.map((r) => (
                    <li key={r.href}>
                      <Link className="home-row" to={r.href}>
                        <span className="home-row__title">{r.title}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No course or guide matches this yet.</p>
              )}
            </section>

            <section className="panel home-card" aria-labelledby="home-pages">
              <div className="home-card__head">
                <h3 className="home-card__title" id="home-pages">
                  Across the hub
                </h3>
              </div>
              {pages.length ? (
                <ul className="home-list">
                  {pages.map(({ pillar, section }) => (
                    <li key={section.href}>
                      <Link className="home-row" to={section.href}>
                        <span className="home-row__pillar">{pillar.short_title}</span>
                        <span className="home-row__title">{section.title}</span>
                        <span className="home-row__sub">{section.blurb}</span>
                      </Link>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="muted">No hub page matches this yet.</p>
              )}
            </section>
          </div>
        </section>
      ) : (
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
      )}
    </div>
  )
}
