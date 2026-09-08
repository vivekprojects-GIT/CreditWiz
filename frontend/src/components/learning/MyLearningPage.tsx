import { ChevronRight, Info } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { fetchMyLearning, type MyLearning } from '../../lib/learning'
import { PageBand } from '../PageBand'
import { ItemCard } from './ItemCard'

export function MyLearningPage() {
  const [data, setData] = useState<MyLearning | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    fetchMyLearning(ctrl.signal)
      .then(setData)
      .catch((err: unknown) => {
        if (!isAbort(err)) setError(err instanceof Error ? err.message : String(err))
      })
    return () => ctrl.abort()
  }, [])

  const inProgress = (data?.items ?? []).filter((i) => i.status === 'in_progress')
  const notStarted = (data?.items ?? []).filter((i) => i.status === 'not_started')
  const completed = (data?.items ?? []).filter((i) => i.status === 'completed')

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/learning">Learning</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>My learning</span>
      </nav>

      <PageBand
        kicker={data?.persona_label}
        title="My learning"
        lead="Where you are with the learning relevant to your role."
        aside={
          data && data.required_total > 0 ? (
            <span className="band__count">
              Required: {data.required_completed} of {data.required_total}
            </span>
          ) : undefined
        }
        compact
      />

      {error && (
        <div className="state state--error" role="alert">
          <p>Could not load your learning. {error}</p>
        </div>
      )}

      {data && (
        <>
          <div className="stats">
            <div className="stat">
              <span className="stat__n">{data.completed}</span>
              <span className="stat__l">Completed</span>
            </div>
            <div className="stat">
              <span className="stat__n">{data.in_progress}</span>
              <span className="stat__l">In progress</span>
            </div>
            <div className="stat">
              <span className="stat__n">{data.not_started}</span>
              <span className="stat__l">Not started</span>
            </div>
            <div className="stat stat--required">
              <span className="stat__n">
                {data.required_completed}<span className="stat__of">/{data.required_total}</span>
              </span>
              <span className="stat__l">Required for your role</span>
            </div>
          </div>

          <section className="panel">
            <h2 className="panel__title">Topic coverage</h2>
            <p className="panel__text">
              How much of the learning relevant to your role you have completed, by topic.
            </p>
            <ul className="coverage">
              {data.coverage.map((c) => (
                <li key={c.topic}>
                  <span className="coverage__topic">{c.topic}</span>
                  <span className="coverage__bar" aria-hidden="true">
                    <span style={{ width: `${c.total ? (c.completed / c.total) * 100 : 0}%` }} />
                  </span>
                  <span className="coverage__count">
                    {c.completed} of {c.total}
                  </span>
                </li>
              ))}
            </ul>
            <p className="coverage__note">
              <Info size={14} strokeWidth={2.4} /> {data.proficiency_note}
            </p>
          </section>

          {inProgress.length > 0 && (
            <>
              <h2 className="section-title">Continue learning</h2>
              <div className="item-grid">
                {inProgress.map((i) => (
                  <ItemCard key={i.id} item={i} />
                ))}
              </div>
            </>
          )}

          {notStarted.length > 0 && (
            <>
              <h2 className="section-title">Not started</h2>
              <div className="item-grid">
                {notStarted.map((i) => (
                  <ItemCard key={i.id} item={i} />
                ))}
              </div>
            </>
          )}

          {completed.length > 0 && (
            <>
              <h2 className="section-title">Completed</h2>
              <div className="item-grid">
                {completed.map((i) => (
                  <ItemCard key={i.id} item={i} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  )
}
