import { ArrowRight, Check, ChevronRight, Clock, ExternalLink } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { track } from '../../lib/context'
import {
  TYPE_LABEL,
  duration,
  fetchItem,
  recordProgress,
  type ItemDetail,
  type LearningStatus,
} from '../../lib/learning'
import { usePersona } from '../../lib/persona'
import { BackButton } from '../BackButton'
import { Markdown } from '../Markdown'
import { NotFound } from '../SimplePages'
import { FeedbackPrompt } from '../marketplace/FeedbackPrompt'
import { ItemCard } from './ItemCard'
import { Player } from './Player'

export function ItemPage() {
  const { id = '' } = useParams()
  const [params] = useSearchParams()
  const { persona } = usePersona()
  const fromAgent = params.get('from') ?? ''
  const [item, setItem] = useState<ItemDetail | null | undefined>(undefined)
  const [status, setStatus] = useState<LearningStatus>('not_started')
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const ctrl = new AbortController()
    setItem(undefined)
    fetchItem(id, ctrl.signal)
      .then((i) => {
        setItem(i)
        setStatus(i.status)
        setProgress(i.progress)
        track('learning', 'learning_view', {
          subject_id: i.id,
          subject_type: i.type,
          persona,
          topics: [...i.topics, ...i.tags],
          meta: { path: i.path, from_agent: fromAgent || undefined },
        })
        // opening an item starts it
        if (i.status === 'not_started') {
          void recordProgress(i.id, 'in_progress', 5)
            .then((r) => {
              setStatus(r.status)
              setProgress(r.progress)
            })
            .catch(() => {})
        }
      })
      .catch((err: unknown) => {
        if (!isAbort(err)) setItem(null)
      })
    return () => ctrl.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function mark(next: LearningStatus, pct?: number) {
    if (!item) return
    try {
      const r = await recordProgress(item.id, next, pct)
      setStatus(r.status)
      setProgress(r.progress)
    } catch {
      /* progress is best-effort */
    }
  }

  if (item === null) return <NotFound />
  if (item === undefined) {
    return (
      <div className="content">
        <div className="skeleton" style={{ height: 24, width: 320, marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 420 }} />
      </div>
    )
  }

  const fromAgentName = fromAgent ? item.related_agent_names[fromAgent] : ''
  const fallback = fromAgent ? `/marketplace/agents/${fromAgent}` : `/learning?path=${item.path}`
  const time = duration(item.duration_seconds)
  const external = item.url && /^https?:\/\//.test(item.url) && item.type !== 'video'

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/learning">Learning</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to={`/learning?path=${item.path}`}>{item.path_title}</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>{item.title}</span>
      </nav>

      <div className="doc__bar">
        <BackButton fallback={fallback} label={fromAgentName ? `Back to ${fromAgentName}` : 'Back'} />
        <div className="doc__bar-right">
          {status === 'completed' ? (
            <span className="item__done">
              <Check size={15} strokeWidth={3} /> Completed
            </span>
          ) : (
            <button type="button" className="btn btn--inline" onClick={() => void mark('completed')}>
              <Check size={16} strokeWidth={2.6} /> Mark as complete
            </button>
          )}
        </div>
      </div>

      <div className="video__layout">
        <div className="video__main">
          {item.type === 'video' && <Player item={item} onProgress={(p) => void mark('in_progress', p)} />}

          <div className="video__head">
            <div className="agent__badges">
              <span className="icard__type">{TYPE_LABEL[item.type]}</span>
              {item.required && <span className="icard__required">Required for your role</span>}
              {item.level && <span className="vcard__level">{item.level}</span>}
              {time && (
                <span className="acard__kicker">
                  <Clock size={13} strokeWidth={2.4} /> {time}
                </span>
              )}
              <span className="acard__kicker">{item.path_title}</span>
            </div>
            <h1 className="video__title">{item.title}</h1>
            <p className="video__desc">{item.description}</p>
            {item.source && (
              <p className="video__source">
                From <strong>{item.source}</strong>
                {item.youtube_id && (
                  <>
                    {' · '}
                    <a href={item.url} target="_blank" rel="noreferrer">
                      Open on YouTube
                    </a>
                  </>
                )}
              </p>
            )}
            {status === 'in_progress' && progress > 0 && (
              <div className="item__progress" aria-label={`${progress}% complete`}>
                <span style={{ width: `${progress}%` }} />
                <em>{progress}% complete</em>
              </div>
            )}
          </div>

          {item.body && (
            <article className="doc__page doc__page--inline">
              <Markdown source={item.body} />
            </article>
          )}

          {external && (
            <section className="panel">
              <h2 className="panel__title">Open the full content</h2>
              <p className="panel__text">
                This item lives in {item.source || 'another system'}. It opens in a new tab; come back here to mark it complete.
              </p>
              <a
                className="btn btn--inline"
                href={item.url}
                target="_blank"
                rel="noreferrer"
                onClick={() => track('learning', 'click', { subject_id: item.id, subject_type: item.type, persona })}
              >
                Open {TYPE_LABEL[item.type].toLowerCase()} <ExternalLink size={15} strokeWidth={2.4} />
              </a>
            </section>
          )}

          <FeedbackPrompt
            pillar="learning"
            context="item"
            subjectId={item.id}
            resetKey={item.id}
            question="Was this useful?"
          />

          {item.related_agents.length > 0 && (
            <section className="panel">
              <h2 className="panel__title">Agents covered</h2>
              <div className="agent__links">
                {item.related_agents.map((aid) => (
                  <Link key={aid} to={`/marketplace/agents/${aid}`} className="linkbtn">
                    {item.related_agent_names[aid] ?? aid} <ArrowRight size={16} strokeWidth={2.4} />
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>

        <aside className="video__side">
          <h2 className="section-title section-title--first">Up next</h2>
          <div className="video-stack">
            {(item.related_items ?? []).map((r) => (
              <ItemCard key={r.id} item={r} fromAgentId={fromAgent || undefined} compact />
            ))}
          </div>
          <Link to={`/learning?path=${item.path}`} className="textlink" style={{ marginTop: 10 }}>
            All {item.path_title.toLowerCase()} content <ArrowRight size={16} strokeWidth={2.4} />
          </Link>
        </aside>
      </div>
    </div>
  )
}
