import { ArrowRight, Bell, ChevronDown, Sparkles } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchNotifications, isAbort } from '../lib/api'
import { useHub } from '../lib/hub'
import { fetchMarketplaceHome, type Agent } from '../lib/marketplace'
import { usePersona } from '../lib/persona'
import type { Notification } from '../lib/types'
import { AgentCard } from './marketplace/AgentCard'
import { ModuleCard } from './ModuleCard'
import { PageBand } from './PageBand'
import { PriorityCard } from './PriorityCard'

function timeAgo(iso: string): string {
  const h = Math.floor((Date.now() - new Date(iso).getTime()) / 3_600_000)
  if (h < 1) return 'just now'
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return d === 1 ? 'yesterday' : `${d}d ago`
}

export function HomePage() {
  const data = useHub()
  const { persona } = usePersona()
  const [domainId, setDomainId] = useState(data.domains[0]?.id ?? 'all')
  const [featured, setFeatured] = useState<Agent[]>([])
  const [personaLabel, setPersonaLabel] = useState('')
  const [news, setNews] = useState<Notification[]>([])

  const priority = data.pillars.filter((p) => p.priority)
  const others = data.pillars.filter((p) => !p.priority)

  useEffect(() => {
    const ctrl = new AbortController()
    fetchMarketplaceHome(persona, ctrl.signal)
      .then((h) => {
        const recommended = h.carousels.find((c) => c.id === 'recommended')?.agents ?? []
        setFeatured(recommended.slice(0, 3))
        setPersonaLabel(h.personas.find((p) => p.id === persona)?.label ?? '')
      })
      .catch(() => {})
    fetchNotifications(ctrl.signal)
      .then((n) => setNews(n.slice(0, 4)))
      .catch((err: unknown) => {
        if (!isAbort(err)) setNews([])
      })
    return () => ctrl.abort()
  }, [persona])

  return (
    <div className="content">
      <PageBand
        kicker="Enterprise AI Hub"
        title={`Welcome, ${data.user.first_name}`}
        lead="Discover AI. Build your skills. Connect with experts."
        aside={
          <div className="domain">
            <select
              className="domain__select"
              value={domainId}
              onChange={(e) => setDomainId(e.target.value)}
              aria-label="Business domain"
            >
              {data.domains.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.id === 'all' ? 'All business domains' : d.name}
                </option>
              ))}
            </select>
            <ChevronDown className="domain__chev" size={18} strokeWidth={2.2} />
          </div>
        }
      />

      <h2 className="section-title section-title--first">Start here</h2>
      <section className="priority-grid" aria-label="Priority modules">
        {priority.map((p) => (
          <PriorityCard key={p.id} pillar={p} />
        ))}
      </section>

      <div className="home-split">
        <section className="home-featured" aria-labelledby="home-featured-title">
          <div className="section-head">
            <div>
              <h2 className="section-title" id="home-featured-title">
                <Sparkles size={18} strokeWidth={2.4} className="section-title__icon" />
                Agents picked for {personaLabel ? `${personaLabel.toLowerCase()}s` : 'you'}
              </h2>
              <p className="section-sub">Based on your persona. Change it on the marketplace page.</p>
            </div>
            <Link to="/marketplace" className="textlink">
              Open marketplace <ArrowRight size={16} strokeWidth={2.4} />
            </Link>
          </div>
          {featured.length > 0 ? (
            <div className="featured-grid">
              {featured.map((a) => (
                <AgentCard key={a.id} agent={a} source="home-featured" compact hideForYou />
              ))}
            </div>
          ) : (
            <div className="featured-grid">
              {[0, 1, 2].map((i) => (
                <div key={i} className="skeleton" style={{ height: 168 }} />
              ))}
            </div>
          )}
        </section>

        <section className="home-news panel" aria-labelledby="home-news-title">
          <div className="section-head section-head--tight">
            <h2 className="section-title" id="home-news-title">
              <Bell size={18} strokeWidth={2.4} className="section-title__icon" />
              What's new
            </h2>
          </div>
          {news.length === 0 ? (
            <p className="muted">Nothing new right now.</p>
          ) : (
            <ul className="newslist">
              {news.map((n) => (
                <li key={n.id}>
                  <Link to={n.href} className="newsitem">
                    <span className="newsitem__title">{n.title}</span>
                    <span className="newsitem__body">{n.body}</span>
                    <span className="newsitem__time">{timeAgo(n.created_at)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <h2 className="section-title">More across your AI Hub</h2>
      <section className="more-grid" aria-label="Supporting modules">
        {others.map((p) => (
          <ModuleCard key={p.id} pillar={p} />
        ))}
      </section>
    </div>
  )
}
