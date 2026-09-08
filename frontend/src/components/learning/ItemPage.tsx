import { ArrowRight, Check, ChevronRight, Clock, ExternalLink } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { ApiError, isAbort } from '../../lib/api'
import { track } from '../../lib/context'
import {
  TYPE_LABEL,
  duration,
  fetchItem,
  rateItem,
  recordProgress,
  type ItemDetail,
  type LearningStatus,
} from '../../lib/learning'
import { usePersona } from '../../lib/personaContext'
import { BackButton } from '../BackButton'
import { Markdown } from '../Markdown'
import { NotFound } from '../SimplePages'
import { FeedbackPrompt } from '../marketplace/FeedbackPrompt'
import { ItemCard } from './ItemCard'
import { RatingInput, RatingSummary } from './StarRating'
import { Player } from './Player'

export function ItemPage() {
  const { id = '' } = useParams()
  return <ItemContent key={id} />
}
function ItemContent() {
  const { id = '' } = useParams()
  const [params] = useSearchParams()
  const { derived } = usePersona()
  const persona = derived.id
  const activeId = useRef(id)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const fromAgent = params.get('from') ?? ''
  const [item, setItem] = useState<ItemDetail | null | undefined>(undefined)
  const [rating, setRating] = useState(false)
  const [status, setStatus] = useState<LearningStatus>('not_started')
  const [progress, setProgress] = useState(0)

  useEffect(() => {
    const ctrl = new AbortController()
    activeId.current = id
    setItem(undefined)
    fetchItem(id, ctrl.signal)
      .then((i) => {
        setError('')
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
        if (i.status === 'not_started' && !i.blocked_by.length && !i.prerequisite_unavailable) {
          void recordProgress(i.id, 'in_progress', 0)
            .then((r) => {
              if (ctrl.signal.aborted) return
              setStatus(r.status)
              setProgress(r.progress)
            })
            .catch((e: unknown) => {
              if (!ctrl.signal.aborted) setError(e instanceof Error ? e.message : 'Could not save progress')
            })
        }
      })
      .catch((err: unknown) => {
        if (isAbort(err)) return
        if (err instanceof ApiError && err.status === 404) setItem(null)
        else setError(err instanceof Error ? err.message : 'Could not load this item')
      })
    return () => ctrl.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, persona, fromAgent, attempt])

  async function mark(next: LearningStatus, pct?: number) {
    if (!item) return
    setBusy(true)
    setError('')
    try {
      const r = await recordProgress(item.id, next, pct)
      if (activeId.current !== item.id) return
      setStatus(r.status)
      setProgress(r.progress)
    } catch (e) {
      if (activeId.current === item.id) setError(e instanceof Error ? e.message : 'Could not save progress')
    } finally {
      if (activeId.current === item.id) setBusy(false)
    }
  }

  if (item === null) return <NotFound />
  if (item === undefined && error)
    return (
      <div className="content" role="alert">
        {error}{' '}
        <button
          onClick={() => {
            setError('')
            setAttempt((a) => a + 1)
          }}
        >
          Retry
        </button>
      </div>
    )
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
            <button
              type="button"
              className="btn btn--inline"
              disabled={busy || item.blocked_by.length > 0 || item.prerequisite_unavailable}
              onClick={() => void mark('completed')}
            >
              <Check size={16} strokeWidth={2.6} /> Mark as complete
            </button>
          )}
        </div>
      </div>

      {error && (
        <p role="alert" className="state state--error">
          {error}
        </p>
      )}
      {(item.blocked_by.length > 0 || item.prerequisite_unavailable) && (
        <section className="panel">
          <h2 className="panel__title">Complete prerequisites first</h2>
          {item.blocked_by.map((dep) => (
            <p key={dep}>
              <Link to={`/learning/items/${dep}`}>{dep.replaceAll('-', ' ')}</Link>
            </p>
          ))}
          {item.prerequisite_unavailable && <p>A prerequisite is unavailable for your account. Contact the content owner.</p>}
        </section>
      )}
      <p className="muted">
        {item.source_kind === 'sample' ? 'Sample content · ' : ''}Owner: {item.owner}. Completion is self-reported; it does not certify
        proficiency.
      </p>
      <div className="video__layout">
        <div className="video__main">
          {item.type === 'video' && (
            <Player
              key={item.id}
              item={item}
              onProgress={(p) => {
                if (!item.blocked_by.length && !item.prerequisite_unavailable) void mark('in_progress', p)
              }}
            />
          )}

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

          {item.url.startsWith('/') && !item.url.startsWith('//') && (
            <Link className="btn btn--inline" to={item.url}>
              Open linked resource
            </Link>
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

          <section className="panel rate">
            <div>
              <h2 className="panel__title">Rate this {TYPE_LABEL[item.type].toLowerCase()}</h2>
              <p className="panel__text">
                {item.status === 'not_started'
                  ? 'Open it first, then tell other people in your role whether it was worth their time.'
                  : 'Tell other people in your role whether this was worth their time.'}
              </p>
            </div>
            <div className="rate__right">
              <RatingInput
                value={item.my_rating}
                disabled={item.status === 'not_started' || rating}
                onRate={(stars) => {
                  setRating(true)
                  rateItem(item.id, stars)
                    .then((updated) => setItem((prev) => (prev ? { ...prev, ...updated } : prev)))
                    .catch(() => undefined)
                    .finally(() => setRating(false))
                }}
              />
              <RatingSummary average={item.rating_average} count={item.rating_count} />
            </div>
          </section>

          <FeedbackPrompt pillar="learning" context="item" subjectId={item.id} resetKey={item.id} question="Was this useful?" />

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
