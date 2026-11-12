import { AccessRequestForm } from './AccessRequestForm'
import {
  ChevronRight,
  Clock,
  ExternalLink,
  FileText,
  MessageSquare,
  Rocket,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { formatDate } from '../../lib/format'
import { track, type EventType } from '../../lib/context'
import { ACCESS_LABEL, STATUS_LABEL, fetchAgent, fetchRelated, launchLink, type Agent } from '../../lib/marketplace'
import { usePersona } from '../../lib/personaContext'
import { BackButton } from '../BackButton'
import { NotFound } from '../SimplePages'
import { AgentCard } from './AgentCard'
import { FeedbackPrompt } from './FeedbackPrompt'
import '../../agent-documents.css'

const PERSONA_LABEL: Record<string, string> = {
  business_user: 'Business users',
  compliance_user: 'Compliance users',
  risk_analyst: 'Risk analysts',
  operations_user: 'Operations users',
  developer: 'Developers',
}

/** "Hannah Weiss" -> "HW"; a team name when no person is confirmed. */
/** A value the owning team has not confirmed says so, rather than being guessed. */
function Unconfirmed({ text = 'To be confirmed' }: { text?: string }) {
  return <span className="tbc">{text}</span>
}

function initials(name: string) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0].toUpperCase())
    .join('')
}

function ExtLink({
  href,
  event,
  agent,
  className,
  children,
}: {
  href: string
  event: EventType
  agent: Agent
  className: string
  children: React.ReactNode
}) {
  const { persona } = usePersona()
  return (
    <a
      className={className}
      href={href}
      target="_blank"
      rel="noreferrer"
      onClick={() =>
        track('marketplace', event, {
          subject_id: agent.id,
          subject_type: 'agent',
          persona,
          topics: [...agent.business_domains, ...agent.capabilities],
        })
      }
    >
      {children}
    </a>
  )
}

export function AgentDetailPage() {
  const { id = '' } = useParams()
  const { persona } = usePersona()
  const [agent, setAgent] = useState<Agent | null | undefined>(undefined)
  const [related, setRelated] = useState<Agent[]>([])

  useEffect(() => {
    const ctrl = new AbortController()
    setAgent(undefined)
    fetchAgent(id, ctrl.signal)
      .then((a) => {
        setAgent(a)
        track('marketplace', 'view', {
          subject_id: a.id,
          subject_type: 'agent',
          persona,
          topics: [...a.business_domains, ...a.capabilities],
        })
      })
      .catch((err: unknown) => {
        if (!isAbort(err)) setAgent(null)
      })
    fetchRelated(id, ctrl.signal)
      .then(setRelated)
      .catch(() => setRelated([]))
    return () => ctrl.abort()
    // persona intentionally excluded: viewing is logged once per agent load
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, persona])

  if (agent === null) return <NotFound />
  if (agent === undefined) {
    return (
      <div className="content">
        <div className="skeleton" style={{ height: 24, width: 320, marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 160, marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 320 }} />
      </div>
    )
  }

  const forYou = agent.personas.includes(persona)
  // The primary action follows the agent's declared access type. It used to
  // collapse to "Request access" for every sample listing -- so an agent whose
  // card said "Open" asked the user to request it on the next page.
  const access = agent.access.type
  const isSample = agent.source_kind === 'sample'
  const launchUrl = launchLink(agent)
  const canLaunch = !!launchUrl
  // The header's action column is shown only when there is something to do.
  // Open agents without a live link still get the column, to say the link is coming.
  const hasAction = access === 'open' || access === 'request' || access === 'restricted'
  const ownerMail = agent.owner.email
    ? `mailto:${agent.owner.email}?subject=${encodeURIComponent(`Access to ${agent.name}`)}`
    : undefined

  // One click to act. The hero's Request access button brings the Get access
  // card into view and puts the cursor in the reason box, so the request is
  // typed straight away rather than scrolled to and then clicked into.
  function goToRequest(e: React.MouseEvent) {
    const card = document.getElementById('request-access')
    if (!card) return
    e.preventDefault()
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    card.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' })
    card.querySelector<HTMLTextAreaElement>('textarea')?.focus({ preventScroll: true })
  }

  return (
    <div className="content agent">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/marketplace">AI Marketplace</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>{agent.name}</span>
      </nav>

      <div className="doc__bar">
        <BackButton fallback="/marketplace" label="Back to marketplace" />
      </div>

      {/* The first screen holds the whole decision: what it is, who it is for,
          who owns it, and every action -- each one click from here. It used to
          take two and a half screens of cards and a sidebar to learn the same. */}
      <header className="agent__head">
        <div className="agent__head-top">
          <div className="agent__head-main">
            <div className="agent__badges">
              <span className={`status status--${agent.status}`}>{STATUS_LABEL[agent.status]}</span>
              <span className="agent__category">{agent.category}</span>
              {agent.version && <span className="agent__version">v{agent.version}</span>}
              {forYou && <span className="acard__foryou">For you</span>}
            </div>
            <h1 className="agent__name">{agent.name}</h1>
            <p className="agent__tagline">{agent.tagline}</p>
          </div>

          {/* An empty action column kept a third of the header blank. */}
          {hasAction && (
            <div className="agent__actions">
              {/* Where launching is the action but no link is live yet, say so where the button will be. */}
              {access === 'open' && !canLaunch && (
                <p className="agent__pending">
                  <Clock size={14} strokeWidth={2.2} aria-hidden="true" /> Launch link coming soon
                </p>
              )}
              {access === 'open' && canLaunch && (
                <ExtLink href={launchUrl} event="launch" agent={agent} className="btn btn--inline">
                  <Rocket size={18} /> Launch agent
                </ExtLink>
              )}

              {access === 'request' && (
                <>
                  <a className="btn btn--inline" href="#request-access" onClick={goToRequest}>
                    Request access
                  </a>
                  {!isSample && agent.access.request_url && (
                    <ExtLink href={agent.access.request_url} event="request_access" agent={agent} className="btn-outline">
                      Open enterprise access portal
                    </ExtLink>
                  )}
                </>
              )}

              {access === 'restricted' && (
                <a className="btn-outline" href={ownerMail} aria-disabled={!ownerMail}>
                  Contact the owner for access
                </a>
              )}
            </div>
          )}
        </div>

        {/* The facts a reader checks before opening it, in one row under the name. */}
        <dl className="agent__facts">
          <div>
            <dt>Used by</dt>
            <dd>{agent.personas.map((p) => PERSONA_LABEL[p] ?? p).join(', ') || <Unconfirmed />}</dd>
          </div>
          <div>
            <dt>Domains</dt>
            <dd>{agent.business_domains.join(', ') || <Unconfirmed />}</dd>
          </div>
          <div>
            <dt>Owner</dt>
            {/* A first-pass listing may not have a named owner yet: the team is
                shown, and the person says it is to be confirmed. */}
            <dd>
              {agent.owner.team || <Unconfirmed />}
              <span className="agent__fact-sub">{agent.owner.name || <Unconfirmed text="Contact to be confirmed" />}</span>
            </dd>
          </div>
          <div>
            <dt>Platform</dt>
            <dd>{agent.platform || <Unconfirmed />}</dd>
          </div>
          <div>
            <dt>Updated</dt>
            <dd>{formatDate(agent.updated_at)}</dd>
          </div>
        </dl>
      </header>

      <div className="agent__body">
        <div className="agent__overview">
          {/* What it does and why it was built are read together, so they sit together. */}
          <section className="panel">
            <h2 className="panel__title">What it does</h2>
            <p className="panel__text">{agent.description}</p>
            {agent.problem_solved && (
              <>
                <h3 className="panel__subtitle">Why it exists</h3>
                <p className="panel__text">{agent.problem_solved}</p>
              </>
            )}
          </section>

          <section className="panel">
            <h2 className="panel__title">What you can ask it to do</h2>
            <ul className="usecases">
              {(agent.use_cases ?? []).map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
            {(agent.example_tasks?.length ?? 0) > 0 && (
              <div className="examples-inline">
                <span className="examples__label">Example prompts</span>
                {agent.example_tasks.map((t) => (
                  <span key={t} className="examples__chip examples__chip--static">
                    {t}
                  </span>
                ))}
              </div>
            )}
            <h3 className="panel__subtitle">Capabilities</h3>
            <div className="pills">
              {(agent.capabilities ?? []).map((c) => (
                <span key={c} className="pill">
                  {c}
                </span>
              ))}
            </div>
          </section>
        </div>

        {/* Documents stay where the owning team keeps them: Nexus lists each
            with what it covers and a link to open it there, and holds no copy. */}
        <section className="panel" id="documents">
          <h2 className="panel__title">
            <FileText size={20} strokeWidth={2.2} /> Documentation
          </h2>
          {agent.documents.length ? (
            <div className="doc-table-wrap">
              <table className="doc-table">
                <thead>
                  <tr>
                    <th scope="col">Document</th>
                    <th scope="col">What it covers</th>
                    <th scope="col">Open it</th>
                  </tr>
                </thead>
                <tbody>
                  {agent.documents.map((doc) => (
                    <tr key={doc.url}>
                      <th scope="row">{doc.label}</th>
                      <td data-label="What it covers">{doc.description || <span className="tbc">To be confirmed</span>}</td>
                      <td data-label="Open it">
                        <ExtLink href={doc.url} event="documentation_click" agent={agent} className="linkbtn">
                          <ExternalLink size={14} strokeWidth={2.2} /> Open {doc.label}
                        </ExtLink>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="tbc">Document links to be confirmed</p>
          )}
        </section>

        {/* How to get it, and who owns it: two plain halves of one card. */}
        <section className="panel access" id="request-access">
          <div className="access__route">
            <h2 className="panel__title">
              <ShieldCheck size={20} strokeWidth={2.2} /> Get access
            </h2>
            <span className={`access__type access__type--${access}`}>{ACCESS_LABEL[agent.access.type]}</span>
            <p className="panel__text">{agent.access.how}</p>
            {/* A request form only makes sense where a request is the route in.
                Open agents need none; restricted ones go through the owner. */}
            {access === 'request' && <AccessRequestForm key={agent.id} agentId={agent.id} />}
          </div>
          <div className="access__owner">
            <h3 className="access__label">Owner</h3>
            <div className="access__person">
              <span className="access__avatar" aria-hidden="true">
                {initials(agent.owner.name || agent.owner.team)}
              </span>
              <div>
                <p className="access__name">{agent.owner.name || 'To be confirmed'}</p>
                <p className="access__team">{agent.owner.team}</p>
              </div>
            </div>
            {agent.source_kind === 'enterprise' && agent.owner.email ? (
              <a
                className="btn-outline access__contact"
                href={`mailto:${agent.owner.email}?subject=${encodeURIComponent(agent.name)}`}
                onClick={() => track('marketplace', 'collaborate', { subject_id: agent.id })}
              >
                <MessageSquare size={16} strokeWidth={2.2} /> Contact the owner
              </a>
            ) : (
              <p className="access__pending">Contact details appear once the owning team confirms this listing.</p>
            )}
          </div>
        </section>

        {related.length > 0 && (
          <section>
            <h2 className="section-title">Related agents</h2>
            <div className="agent-grid">
              {related.map((a) => (
                <AgentCard key={a.id} agent={a} source="related" compact />
              ))}
            </div>
          </section>
        )}

        <FeedbackPrompt pillar="marketplace" context="agent" subjectId={agent.id} resetKey={agent.id} question="Was this page useful?" />
      </div>
    </div>
  )
}
