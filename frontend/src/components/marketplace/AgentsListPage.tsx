import { ChevronRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { fetchAgents, fetchMarketplaceHome, type Agent, type Persona } from '../../lib/marketplace'
import { usePersona } from '../../lib/persona'
import { PageBand } from '../PageBand'
import { AgentCard } from './AgentCard'

const CATEGORIES = ['Compliance & Risk', 'Document Intelligence', 'Customer Operations', 'Knowledge & Policy', 'Developer Tools']

export function AgentsListPage() {
  const { persona } = usePersona()
  const [params, setParams] = useSearchParams()
  const [agents, setAgents] = useState<Agent[] | null>(null)
  const [domains, setDomains] = useState<string[]>([])
  const [personas, setPersonas] = useState<Persona[]>([])
  const [error, setError] = useState<string | null>(null)

  const domain = params.get('domain') ?? ''
  const category = params.get('category') ?? ''
  const onlyMine = params.get('mine') === '1'

  useEffect(() => {
    const ctrl = new AbortController()
    fetchMarketplaceHome('', ctrl.signal)
      .then((h) => {
        setDomains(h.domains)
        setPersonas(h.personas)
      })
      .catch(() => {})
    return () => ctrl.abort()
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    fetchAgents({ domain, category, persona: onlyMine ? persona : '' }, ctrl.signal)
      .then((a) => {
        setAgents(a)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!isAbort(err)) setError(err instanceof Error ? err.message : String(err))
      })
    return () => ctrl.abort()
  }, [domain, category, onlyMine, persona])

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next, { replace: true })
  }

  const personaLabel = personas.find((p) => p.id === persona)?.label ?? 'my persona'

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/marketplace">AI Marketplace</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>All agents</span>
      </nav>
      <PageBand
        kicker="AI Marketplace"
        title="All agents"
        lead="Every agent registered in the hub, with its owner, status and how to get access."
        aside={agents ? <span className="band__count">{agents.length} shown</span> : undefined}
        compact
      />

      <div className="filters">
        <select className="filters__select" value={domain} onChange={(e) => setFilter('domain', e.target.value)} aria-label="Business domain">
          <option value="">All domains</option>
          {domains.map((d) => (
            <option key={d} value={d}>
              {d}
            </option>
          ))}
        </select>
        <select className="filters__select" value={category} onChange={(e) => setFilter('category', e.target.value)} aria-label="Category">
          <option value="">All categories</option>
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <label className="filters__check">
          <input type="checkbox" checked={onlyMine} onChange={(e) => setFilter('mine', e.target.checked ? '1' : '')} />
          Only agents for {personaLabel.toLowerCase()}s
        </label>
        {(domain || category || onlyMine) && (
          <button type="button" className="results__clear" onClick={() => setParams({}, { replace: true })}>
            Clear filters
          </button>
        )}
      </div>

      {error && (
        <div className="state state--error" role="alert">
          <p>Could not load agents. {error}</p>
        </div>
      )}
      {agents && agents.length === 0 && <div className="state">No agents match those filters.</div>}
      {agents && agents.length > 0 && (
        <div className="agent-grid">
          {agents.map((a) => (
            <AgentCard key={a.id} agent={a} source="list" />
          ))}
        </div>
      )}
    </div>
  )
}
