import { AccessRequestForm } from './AccessRequestForm'
import {
  BookOpen,
  Boxes,
  Calendar,
  ChevronRight,
  Cpu,
  ExternalLink,
  Layers,
  MessageSquare,
  Rocket,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { formatDate } from '../../lib/format'
import { fetchAgentLearning, type Item } from '../../lib/learning'
import { track, type EventType } from '../../lib/context'
import { ACCESS_LABEL, STATUS_LABEL, fetchAgent, fetchRelated, type Agent } from '../../lib/marketplace'
import { usePersona } from '../../lib/personaContext'
import { BackButton } from '../BackButton'
import { ItemCard } from '../learning/ItemCard'
import { NotFound } from '../SimplePages'
import { AgentCard } from './AgentCard'
import { FeedbackPrompt } from './FeedbackPrompt'

const PERSONA_LABEL: Record<string, string> = {
  business_user: 'Business users',
  compliance_user: 'Compliance users',
  risk_analyst: 'Risk analysts',
  operations_user: 'Operations users',
  developer: 'Developers',
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
  const [videos, setVideos] = useState<Item[]>([])

  useEffect(() => {
    const ctrl = new AbortController()
    setAgent(undefined)
    setVideos([])
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
    fetchAgentLearning(id, persona, ctrl.signal)
      .then(setVideos)
      .catch(() => setVideos([]))
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
  const canLaunch = !isSample && !!agent.access.launch_url
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
      <header className="agent__head band">
        <div className="agent__head-main">
          <div className="agent__badges">
            <span className={`status status--${agent.status}`}>{STATUS_LABEL[agent.status]}</span>
            <span className="agent__category">{agent.category}</span>
            {agent.version && <span className="agent__version">v{agent.version}</span>}
            {forYou && <span className="acard__foryou">For your persona</span>}
          </div>
          <h1 className="agent__name">{agent.name}</h1>
          <p className="agent__tagline">{agent.tagline}</p>
          <dl className="agent__facts">
            <div>
              <dt>Who it is for</dt>
              <dd>{agent.personas.map((p) => PERSONA_LABEL[p] ?? p).join(', ') || 'Not listed'}</dd>
            </div>
            <div>
              <dt>Business domains</dt>
              <dd>{agent.business_domains.join(', ')}</dd>
            </div>
            <div>
              <dt>Owner</dt>
              {/* A first-pass listing may not have a confirmed owner yet. Say so
                  here rather than carrying placeholder text in the data. */}
              <dd>
                {agent.owner.name || 'To be confirmed'} · {agent.owner.team}
              </dd>
            </div>
            <div>
              <dt>Platform</dt>
              <dd>{agent.platform || 'Not listed'}</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{formatDate(agent.updated_at)}</dd>
            </div>
          </dl>
        </div>

        <div className="agent__actions">
          {access === 'open' &&
            (canLaunch ? (
              <ExtLink href={agent.access.launch_url} event="launch" agent={agent} className="btn btn--inline">
                <Rocket size={18} /> Launch agent
              </ExtLink>
            ) : (
              // No live launch link yet, so the most useful single click is
              // the documentation rather than a disabled button.
              <Link to={`/marketplace/agents/${agent.id}/docs`} className="btn btn--inline">
                <BookOpen size={18} strokeWidth={2.4} /> Read documentation
              </Link>
            ))}

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

          <div className="agent__resources">
            {(access !== 'open' || canLaunch) && (
              <Link to={`/marketplace/agents/${agent.id}/docs`} className="btn-outline">
                <BookOpen size={16} strokeWidth={2.4} /> Documentation
              </Link>
            )}
            <Link to={`/marketplace/agents/${agent.id}/architecture`} className="btn-outline">
              <Layers size={16} strokeWidth={2.4} /> Architecture
            </Link>
          </div>

          {/* Only where launching is the action. On a request listing this
              line talked about launching when the next step is asking. */}
          {access === 'open' && !canLaunch && (
            <span className="agent__note">Launch link coming soon</span>
          )}
        </div>
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

        {(videos?.length ?? 0) > 0 && (
          <section className="panel">
            <div className="section-head section-head--tight">
              <div>
                <h2 className="panel__title" style={{ margin: 0 }}>
                  Learning for this agent
                </h2>
                <p className="section-sub">
                  Related material selected by Learning. Use your account's Learning page for progress and required steps.
                </p>
              </div>
              <Link to="/learning" className="textlink">
                All learning
              </Link>
            </div>
            <div className="video-row">
              {videos.map((v) => (
                <ItemCard key={v.id} item={v} fromAgentId={agent.id} compact />
              ))}
            </div>
          </section>
        )}

        <section className="panel">
          <h2 className="panel__title">Technical details</h2>
          <dl className="techline">
            <div>
              <dt>
                <Cpu size={14} strokeWidth={2.2} /> Models
              </dt>
              <dd>{agent.models.length ? agent.models.join(', ') : 'Not listed'}</dd>
            </div>
            <div>
              <dt>
                <Boxes size={14} strokeWidth={2.2} /> Tools and services
              </dt>
              <dd>{agent.tools_services.length ? agent.tools_services.join(', ') : 'Not listed'}</dd>
            </div>
            {agent.architecture_pattern && (
              <div>
                <dt>
                  <Layers size={14} strokeWidth={2.2} /> Architecture pattern
                </dt>
                <dd>{agent.architecture_pattern}</dd>
              </div>
            )}
            <div>
              <dt>
                <Calendar size={14} strokeWidth={2.2} /> Created
              </dt>
              <dd>{formatDate(agent.created_at)}</dd>
            </div>
            {agent.source_kind === 'enterprise' && agent.documentation_url && (
              <div>
                <dt>
                  <ExternalLink size={14} strokeWidth={2.2} /> Source documentation
                </dt>
                <dd>
                  <ExtLink href={agent.documentation_url} event="documentation_click" agent={agent} className="linkbtn">
                    Open
                  </ExtLink>
                </dd>
              </div>
            )}
          </dl>
        </section>

        {/* Getting access is the last thing about the agent: read first, then
            act. The route, the request and the owner sit in one card, not three. */}
        <section className="panel panel--access" id="request-access">
          <h2 className="panel__title">
            <ShieldCheck size={20} strokeWidth={2.4} /> Get access
          </h2>
          <p className="panel__text">
            <strong>{ACCESS_LABEL[agent.access.type]}.</strong> {agent.access.how}
          </p>
          {/* A request form only makes sense where a request is the route in.
              Open agents need none; restricted ones go through the owner. */}
          {access === 'request' && <AccessRequestForm key={agent.id} agentId={agent.id} />}
          <div className="agent__owner">
            <span>
              <strong>{agent.owner.name || 'Owner to be confirmed'}</strong> · {agent.owner.team}
            </span>
            {agent.source_kind === 'enterprise' && !agent.owner.email ? (
              <span className="muted">Contact details will appear once the owning team confirms the listing.</span>
            ) : agent.source_kind === 'enterprise' ? (
              <a
                className="linkbtn"
                href={`mailto:${agent.owner.email}?subject=${encodeURIComponent(agent.name)}`}
                onClick={() => track('marketplace', 'collaborate', { subject_id: agent.id })}
              >
                <MessageSquare size={16} /> Collaborate with the owner
              </a>
            ) : (
              <details>
                <summary>Collaborate with the owner</summary>
                <p>Sample contact: {agent.owner.email}. Enterprise contact will be enabled when the listing is confirmed.</p>
              </details>
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
