import { ArrowRight, ChevronRight, Loader2, Search, Sparkles, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { track } from '../../lib/context'
import { fetchMarketplaceHome, searchAgents, type MarketplaceHome, type SearchResponse } from '../../lib/marketplace'
import { usePersona } from '../../lib/personaContext'
import { AgentCard } from './AgentCard'
import { Carousel } from './Carousel'
import { FeedbackPrompt } from './FeedbackPrompt'
import { PageBand } from '../PageBand'
import { PersonaPreview } from './PersonaPicker'

export function MarketplacePage() {
  // No key here. Keying on the URL remounted the whole page on every search
  // and every clear: carousels vanished and refetched, the input reset, and
  // the results panel replayed its entrance -- the flicker users reported.
  // The effects below already re-run on query, persona and domain changes.
  return <MarketplaceContent />
}
function MarketplaceContent() {
  const { persona } = usePersona()
  const [params, setParams] = useSearchParams()
  const [home, setHome] = useState<MarketplaceHome | null>(null)
  const [homeError, setHomeError] = useState<string | null>(null)

  const [query, setQuery] = useState(params.get('q') ?? '')
  // No longer a control on this page, but a ?domain= link from the browse list
  // still narrows the search, so the parameter is still honoured.
  const domain = params.get('domain') ?? ''
  const [result, setResult] = useState<SearchResponse | null>(null)
  const [searching, setSearching] = useState(!!params.get('q')?.trim())
  const [searchError, setSearchError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Home content (carousels) depends on persona.
  useEffect(() => {
    const ctrl = new AbortController()
    fetchMarketplaceHome(persona, ctrl.signal, domain)
      .then((h) => {
        setHome(h)
        setHomeError(null)
      })
      .catch((err: unknown) => {
        if (!isAbort(err)) setHomeError(err instanceof Error ? err.message : String(err))
      })
    return () => ctrl.abort()
  }, [persona, domain])

  // Run (or re-run) the search when the URL query, persona or domain changes.
  const urlQuery = params.get('q') ?? ''
  // Back/forward changes the URL without going through runSearch; keep the
  // input in step with it now that the component survives navigation.
  useEffect(() => {
    setQuery(urlQuery)
  }, [urlQuery])
  useEffect(() => {
    const q = urlQuery.trim()
    if (!q) return
    const ctrl = new AbortController()
    // Keep the previous results on screen, dimmed, until the new ones land.
    // Unmounting them first blanked the panel and replayed its entrance
    // animation on every search, which read as flicker.
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
    // Drop the result too. Leaving it in state meant the next search mounted
    // the panel instantly with the OLD query's results, then swapped them.
    setResult(null)
    setSearchError(null)
    setSearching(false)
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
        // Product copy, not prototype status. The catalogue size and the
        // sample/enterprise distinction are stated where they matter: on each
        // listing, and in the "All N agents" link below.
        lead="Describe what you need in plain language and we'll find the agents that fit."
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
        <section className={`results${searching ? ' is-refreshing' : ''}`} aria-live="polite" aria-busy={searching}>
          <div className="results__head">
            <div>
              {/* What we understood, in the user's own terms. The engine badge
                  and the extracted concept chips were plumbing on display: which
                  model read the sentence is not the user's problem, and the
                  concepts restate the query they just typed. Each result still
                  explains itself from the metadata that matched. */}
              <div className="results__intent">
                <Sparkles size={16} strokeWidth={2.4} />
                <span>{result.intent.summary}</span>
              </div>
            </div>
            <button type="button" className="results__clear" onClick={clearSearch}>
              Clear results
            </button>
          </div>

          {result.no_match ? (
            <div className="nomatch">
              <h2 className="nomatch__title">No agent matches that yet</h2>
              <p>No matching authorized listing was found. Broaden your search or explore the learning catalog.</p>
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
                  {i === 0 && (
                    <span className="results__best">
                      Best match
                      {/* Share of the extracted domains and capabilities this
                          agent covers. Absent when nothing structured was
                          extracted, rather than showing an invented number. */}
                      {m.coverage !== null && m.coverage !== undefined && (
                        <span className="results__pct" title="Covers this share of what we understood you needed">
                          {m.coverage}% match
                        </span>
                      )}
                    </span>
                  )}
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
              <Link
                to="/marketplace/agents"
                className="textlink"
                onClick={() => track('marketplace', 'click', { persona, meta: { source: 'browse-all' } })}
              >
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
