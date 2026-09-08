import { ChevronRight, GraduationCap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { track } from '../../lib/context'
import { fetchItems, fetchLearningHome, type Item, type LearningHome } from '../../lib/learning'
import { usePersona } from '../../lib/persona'
import { PageBand } from '../PageBand'
import { ItemCard } from './ItemCard'

export function LearningPage() {
  const { persona } = usePersona()
  const [params, setParams] = useSearchParams()
  const [home, setHome] = useState<LearningHome | null>(null)
  const [pathItems, setPathItems] = useState<Item[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const pathId = params.get('path') ?? ''

  useEffect(() => {
    const ctrl = new AbortController()
    fetchLearningHome(persona, ctrl.signal)
      .then((h) => {
        setHome(h)
        setError(null)
      })
      .catch((err: unknown) => {
        if (!isAbort(err)) setError(err instanceof Error ? err.message : String(err))
      })
    return () => ctrl.abort()
  }, [persona])

  useEffect(() => {
    if (!pathId) {
      setPathItems(null)
      return
    }
    const ctrl = new AbortController()
    fetchItems({ path: pathId }, ctrl.signal)
      .then(setPathItems)
      .catch(() => setPathItems([]))
    return () => ctrl.abort()
  }, [pathId])

  const currentPath = home?.paths.find((p) => p.id === pathId)

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>Learning</span>
      </nav>

      <PageBand
        kicker="Enablement"
        title="Learning"
        lead="The right learning for your role, and where you are with it. Every agent in the marketplace links to the content that teaches it."
        aside={
          <>
            <Link to="/learning/me" className="band__action">
              <GraduationCap size={16} strokeWidth={2.2} /> My learning
            </Link>
            {home && <span className="band__count">{home.item_count} items</span>}
          </>
        }
      >
        {home && (
          <div className="pathbar pathbar--onband" role="tablist" aria-label="Learning paths">
            <button
              type="button"
              role="tab"
              aria-selected={!pathId}
              className={`pathbar__item${!pathId ? ' is-active' : ''}`}
              onClick={() => setParams({}, { replace: true })}
            >
              For you
            </button>
            {(home.paths ?? []).map((p) => (
              <button
                key={p.id}
                type="button"
                role="tab"
                aria-selected={pathId === p.id}
                className={`pathbar__item${pathId === p.id ? ' is-active' : ''}`}
                onClick={() => {
                  setParams({ path: p.id }, { replace: true })
                  track('learning', 'click', { subject_id: p.id, subject_type: 'path', topics: [p.title] })
                }}
                title={p.blurb}
              >
                {p.title}
              </button>
            ))}
          </div>
        )}
      </PageBand>

      {error && (
        <div className="state state--error" role="alert">
          <p>Could not load the learning catalogue. {error}</p>
        </div>
      )}

      {/* a single path selected */}
      {pathId && (
        <>
          <div className="section-head">
            <div>
              <h2 className="section-title section-title--first">{currentPath?.title ?? pathId}</h2>
              <p className="section-sub">{currentPath?.blurb}</p>
            </div>
          </div>
          {pathItems === null ? (
            <div className="item-grid">
              {[0, 1, 2].map((i) => (
                <div key={i} className="skeleton" style={{ height: 150 }} />
              ))}
            </div>
          ) : pathItems.length === 0 ? (
            <div className="state">Nothing in this path yet.</div>
          ) : (
            <div className="item-grid">
              {pathItems.map((i) => (
                <ItemCard key={i.id} item={i} />
              ))}
            </div>
          )}
        </>
      )}

      {/* role-based landing */}
      {!pathId &&
        (home?.sections ?? []).map((s, idx) => (
          <section key={s.id} aria-labelledby={`sec-${s.id}`} className={`lsection lsection--${s.id}`}>
            <div className="section-head">
              <div>
                <h2 className={`section-title${idx === 0 ? ' section-title--first' : ''}`} id={`sec-${s.id}`}>
                  {s.title}
                  {s.id === 'required' && <span className="sec-count">{s.items.length} outstanding</span>}
                </h2>
                <p className="section-sub">{s.subtitle}</p>
              </div>
            </div>
            <div className="item-grid">
              {s.items.map((i) => (
                <ItemCard key={i.id} item={i} />
              ))}
            </div>
          </section>
        ))}
    </div>
  )
}
