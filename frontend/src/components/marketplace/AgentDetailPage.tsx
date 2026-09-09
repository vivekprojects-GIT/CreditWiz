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
  Server,
  ShieldCheck,
  Users,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
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
          <p className="agent__meta">
            <span>{agent.owner.team}</span>
            <span>{agent.platform}</span>
            <span>{ACCESS_LABEL[agent.access.type]}</span>
            <span>Updated {agent.updated_at}</span>
          </p>
        </div>

        <div className="agent__actions">
          {access === 'open' &&
            (canLaunch ? (
              <ExtLink href={agent.access.launch_url} event="launch" agent={agent} className="btn btn--inline">
                <Rocket size={18} /> Launch agent
              </ExtLink>
            ) : (
              <button
                type="button"
                className="btn btn--inline"
                disabled
                title="Open to all employees. This sample listing has no live destination yet."
              >
                <Rocket size={18} /> Open agent
              </button>
            ))}

          {access === 'request' && (
            <>
              {!isSample && agent.access.request_url && (
                <ExtLink href={agent.access.request_url} event="request_access" agent={agent} className="btn-outline">
                  Open enterprise access portal
                </ExtLink>
              )}
              <a className="btn btn--inline" href="#request-access">
                Request access
              </a>
            </>
          )}

          {access === 'restricted' && (
            <a className="btn-outline" href={ownerMail} aria-disabled={!ownerMail}>
              Contact the owner for access
            </a>
          )}

          {isSample && <span>Sample listing · Live launch is not configured.</span>}
        </div>
      </header>

      {/* A request form only makes sense where a request is the route in.
          Open agents need none; restricted ones go through the owner. */}
      {access === 'request' && <AccessRequestForm key={agent.id} agentId={agent.id} />}
      <div className="agent__layout">
        <div className="agent__main">
          <section className="panel">
            <h2 className="panel__title">What it does</h2>
            <p className="panel__text">{agent.description}</p>
          </section>

          {agent.problem_solved && (
            <section className="panel">
              <h2 className="panel__title">Why it exists</h2>
              <p className="panel__text">{agent.problem_solved}</p>
            </section>
          )}

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
          </section>

          <section className="panel">
            <h2 className="panel__title">Capabilities</h2>
            <div className="pills">
              {(agent.capabilities ?? []).map((c) => (
                <span key={c} className="pill">
                  {c}
                </span>
              ))}
            </div>
          </section>

          <section className="panel panel--access">
            <h2 className="panel__title">
              <ShieldCheck size={20} strokeWidth={2.4} /> How to get access
            </h2>
            <p className="panel__text">
              <strong>{ACCESS_LABEL[agent.access.type]}.</strong> {agent.access.how}
            </p>
          </section>

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

          <FeedbackPrompt pillar="marketplace" context="agent" subjectId={agent.id} resetKey={agent.id} question="Was this page useful?" />
        </div>

        <aside className="agent__side">
          <section className="panel">
            <h2 className="panel__title">At a glance</h2>
            <dl className="facts">
              <dt>
                <Users size={16} strokeWidth={2.2} /> Who it is for
              </dt>
              <dd>{agent.personas.map((p) => PERSONA_LABEL[p] ?? p).join(', ')}</dd>
              <dt>
                <Layers size={16} strokeWidth={2.2} /> Business domains
              </dt>
              <dd>{agent.business_domains.join(', ')}</dd>
              <dt>
                <Server size={16} strokeWidth={2.2} /> Platform
              </dt>
              <dd>{agent.platform}</dd>
              <dt>
                <Cpu size={16} strokeWidth={2.2} /> Models
              </dt>
              <dd>{agent.models.length ? agent.models.join(', ') : 'Not listed'}</dd>
              <dt>
                <Boxes size={16} strokeWidth={2.2} /> Tools and services
              </dt>
              <dd>{agent.tools_services.length ? agent.tools_services.join(', ') : 'Not listed'}</dd>
              {agent.architecture_pattern && (
                <>
                  <dt>
                    <Layers size={16} strokeWidth={2.2} /> Architecture pattern
                  </dt>
                  <dd>{agent.architecture_pattern}</dd>
                </>
              )}
              <dt>
                <Calendar size={16} strokeWidth={2.2} /> Updated
              </dt>
              <dd>
                {agent.updated_at} <span className="muted">(created {agent.created_at})</span>
              </dd>
            </dl>
          </section>

          <section className="panel">
            <h2 className="panel__title">Owner</h2>
            <p className="owner__name">{agent.owner.name}</p>
            <p className="owner__team">{agent.owner.team}</p>
            <div className="agent__links">
              {agent.source_kind === 'enterprise' ? (
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

          <section className="panel">
            <h2 className="panel__title">Resources</h2>
            <div className="agent__links">
              <Link to={`/marketplace/agents/${agent.id}/docs`} className="linkbtn">
                <BookOpen size={16} strokeWidth={2.4} /> Documentation
              </Link>
              <Link to={`/marketplace/agents/${agent.id}/architecture`} className="linkbtn">
                <Layers size={16} strokeWidth={2.4} /> Architecture pattern
                {agent.architecture_pattern ? `: ${agent.architecture_pattern}` : ''}
              </Link>
              {agent.source_kind === 'enterprise' && agent.documentation_url && (
                <ExtLink href={agent.documentation_url} event="documentation_click" agent={agent} className="linkbtn linkbtn--muted">
                  Source documentation <ExternalLink size={13} strokeWidth={2.4} />
                </ExtLink>
              )}
            </div>
          </section>
        </aside>
      </div>

      {related.length > 0 && (
        <>
          <h2 className="section-title">Related agents</h2>
          <div className="agent-grid">
            {related.map((a) => (
              <AgentCard key={a.id} agent={a} source="related" compact />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
