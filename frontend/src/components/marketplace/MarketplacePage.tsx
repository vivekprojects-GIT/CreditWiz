import { ArrowRight, ChevronRight, Loader2, Search, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { track } from '../../lib/context'
import { fetchMarketplaceHome, searchAgents, type MarketplaceHome, type SearchResponse } from '../../lib/marketplace'
import { usePersona } from '../../lib/persona'
import { AgentCard } from './AgentCard'
import { Carousel } from './Carousel'
import { FeedbackPrompt } from './FeedbackPrompt'
import { PageBand } from '../PageBand'
import { PersonaPreview } from './PersonaPicker'

export function MarketplacePage() {
  const { persona } = usePersona()
  const [params, setParams] = useSearchParams()
  const [home, setHome] = useState<MarketplaceHome | null>(null)
  const [homeError, setHomeError] = useState<string | null>(null)

  const [query, setQuery] = useState(params.get('q') ?? '')
  const [domain, setDomain] = useState(params.get('domain') ?? '')
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Home content (carousels) depends on persona.
  useEffect(() => {
    const ctrl = new AbortController()
    fetchMarketplaceHome(persona, ctrl.signal)
      .then((h) => {
        setHome(h)
        setHomeError(null)
      })
      .catch((err: unknown) => {
        if (!isAbort(err)) setHomeError(err instanceof Error ? err.message : String(err))
      })
    return () => ctrl.abort()
  }, [persona])

  // Run (or re-run) the search when the URL query, persona or domain changes.
  const urlQuery = params.get('q') ?? ''
  useEffect(() => {
    const q = urlQuery.trim()
    if (!q) {
      setResult(null)
      return
    }
    const ctrl = new AbortController()
    setSearching(true)
    setSearchError(null)
    searchAgents(q, persona, domain, ctrl.signal)
      .then((r) => setResult(r))
      .catch((err: unknown) => {
        if (!isAbort(err)) setSearchError(err instanceof Error ? err.message : String(err))
      })
      .finally(() => {
        if (!ctrl.signal.aborted) setSearching(false)
      })
    return () => ctrl.abort()
  }, [urlQuery, persona, domain])

  function runSearch(q: string) {
    const trimmed = q.trim()
    setQuery(trimmed)
    const next = new URLSearchParams(params)
    if (trimmed) next.set('q', trimmed)
    else next.delete('q')
    if (domain) next.set('domain', domain)
    else next.delete('domain')
    setParams(next, { replace: true })
  }

  function clearSearch() {
    setQuery('')
    const next = new URLSearchParams(params)
    next.delete('q')
    setParams(next, { replace: true })
    inputRef.current?.focus()
  }

  return (
    <div className="content mkt">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>AI Marketplace</span>
      </nav>

      <PageBand
        kicker="AI Marketplace"
        title="Find the right agent for the job"
        lead={`Describe what you need in plain language. We match it against ${home?.agent_count ?? '…'} trusted agents.`}
      >
      <form
        className={`gsearch${searching ? ' is-busy' : ''}`}
        onSubmit={(e) => {
          e.preventDefault()
          runSearch(query)
        }}
        role="search"
      >
        <Sparkles className="gsearch__icon" size={22} strokeWidth={2.2} />
        <input
          ref={inputRef}
          className="gsearch__input"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. I need an agent that can review customer onboarding documents"
          aria-label="Describe what you need"
          autoComplete="off"
        />
        {query && (
          <button type="button" className="gsearch__clear" aria-label="Clear search" onClick={clearSearch}>
            <X size={18} strokeWidth={2.4} />
          </button>
        )}
        <select className="gsearch__domain" value={domain} onChange={(e) => setDomain(e.target.value)} aria-label="Limit to business domain">
          <option value="">All domains</option>
          {home?.domains.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <button type="submit" className="gsearch__go" disabled={searching || !query.trim()}>
          {searching ? <Loader2 className="spin" size={20} strokeWidth={2.4} /> : <Search size={20} strokeWidth={2.4} />}
          Find agents
        </button>
      </form>

      {!urlQuery && home && (
        <div className="examples">
          <span className="examples__label">Try</span>
          {home.example_queries.slice(0, 4).map((q) => (
            <button key={q} type="button" className="examples__chip" onClick={() => runSearch(q)}>
              {q}
            </button>
          ))}
        </div>
      )}
      </PageBand>

      {searchError && (
        <div className="state state--error" role="alert">
          <p>Search is unavailable right now. {searchError}</p>
        </div>
      )}

      {urlQuery && result && (
        <section className="results" aria-live="polite">
          <div className="results__head">
            <div>
              <div className="results__intent">
                <Sparkles size={16} strokeWidth={2.4} />
                <span>{result.intent.summary}</span>
                <span className={`engine engine--${result.engine}`} title="How the request was interpreted">
                  {result.engine === 'claude' ? 'Interpreted by Claude' : 'Interpreted locally'}
                </span>
              </div>
              {result.intent.concepts.length > 0 && (
                <div className="results__concepts">
                  {result.intent.concepts.map((c) => (
                    <span key={c} className="concept">
                      {c}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <button type="button" className="results__clear" onClick={clearSearch}>
              Clear results
            </button>
          </div>

          {result.no_match ? (
            <div className="nomatch">
              <h2 className="nomatch__title">No agent matches that yet</h2>
              <p>
                We checked all {home?.agent_count ?? ''} agents. You can request one, learn to build it, or ask the community.
              </p>
              <div className="nomatch__actions">
                {result.next_steps.map((s) => (
                  <Link key={s.href} to={s.href} className="btn btn--blue btn--inline">
                    {s.label} <ArrowRight size={18} strokeWidth={2.4} />
                  </Link>
                ))}
              </div>
            </div>
          ) : (
            <div className="results__grid">
              {result.results.map((m, i) => (
                <div key={m.agent.id} className={`results__item${i === 0 ? ' is-top' : ''}`}>
                  {i === 0 && <span className="results__best">Best match</span>}
                  <AgentCard agent={m.agent} why={m.why} source="search" />
                </div>
              ))}
            </div>
          )}

          <FeedbackPrompt pillar="marketplace" context="search" query={result.query} resetKey={`${result.query}|${persona}|${domain}`} />
        </section>
      )}

      {homeError && (
        <div className="state state--error" role="alert">
          <p>Could not load the marketplace. {homeError}</p>
        </div>
      )}

      {home && (
        <div className={`mkt__browse${urlQuery ? ' mkt__browse--dimmed' : ''}`}>
          <div className="mkt__browse-head">
            <h2 className="section-title">Browse agents</h2>
            <div className="mkt__browse-tools">
              <Link to="/marketplace/agents" className="textlink" onClick={() => track('marketplace', 'click', { persona, meta: { source: 'browse-all' } })}>
                All {home.agent_count} agents <ArrowRight size={16} strokeWidth={2.4} />
              </Link>
            </div>
          </div>
          {home.carousels.map((c) => (
            <Carousel key={c.id} data={c} extra={c.id === 'recommended' ? <PersonaPreview personas={home.personas} /> : undefined} />
          ))}
        </div>
      )}
    </div>
  )
}
