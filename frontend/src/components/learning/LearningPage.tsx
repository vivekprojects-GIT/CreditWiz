import { ChevronRight, GraduationCap } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useLocation, useSearchParams } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { fetchItems, fetchLearningHome, itemHref, TYPE_LABEL, type Item, type LearningHome } from '../../lib/learning'
import { usePersona } from '../../lib/personaContext'
import { PageBand } from '../PageBand'
import { ItemCard } from './ItemCard'

export function LearningPage() {
  const { derived } = usePersona()
  const [params, setParams] = useSearchParams()
  const { pathname } = useLocation()
  const [data, setData] = useState<{ key: string; home: LearningHome; items: Item[] } | null>(null)
  const [failure, setFailure] = useState<{ key: string; message: string } | null>(null)
  const [attempt, setAttempt] = useState(0)
  const pathId = params.get('path') ?? ''
  const mode = pathname.split('/')[2] ?? ''
  const type =
    mode === 'best-practices'
      ? 'best-practice'
      : mode === 'docs'
        ? 'docs'
        : mode === 'quick-reference'
          ? 'quick-reference'
          : (params.get('type') ?? '')
  const q = params.get('q') ?? ''
  const status = params.get('status') ?? ''
  const key = [derived.id, pathId, mode, type, q, status, attempt].join('|')
  useEffect(() => {
    const ctrl = new AbortController()
    const timer = setTimeout(
      () => {
        Promise.all([fetchLearningHome(derived.id, ctrl.signal), fetchItems({ path: pathId, type, q, status }, ctrl.signal)])
          .then(([home, items]) => setData({ key, home, items }))
          .catch((e: unknown) => {
            if (!isAbort(e)) setFailure({ key, message: e instanceof Error ? e.message : 'Could not load learning' })
          })
      },
      q ? 180 : 0,
    )
    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [key, derived.id, pathId, type, q, status])
  const current = data?.key === key ? data : null
  const error = failure?.key === key ? failure.message : ''
  const home = current?.home
  const selectedPath = home?.paths.find((p) => p.id === pathId)
  const browse = !!pathId || (!!mode && mode !== 'paths')
  const title = pathId
    ? (selectedPath?.title ?? 'Learning path')
    : mode === 'paths'
      ? 'Role-based paths'
      : mode === 'catalog'
        ? 'Learning catalog'
        : mode === 'docs'
          ? 'Product documentation'
          : mode === 'best-practices'
            ? 'Best practices'
            : mode === 'quick-reference'
              ? 'Quick references'
              : 'Learning'
  function filter(name: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) next.set(name, value)
    else next.delete(name)
    setParams(next, { replace: name === 'q' })
  }
  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} />
        <Link to="/learning">Learning</Link>
        {mode && (
          <>
            <ChevronRight size={16} />
            <span>{title}</span>
          </>
        )}
      </nav>
      <PageBand
        kicker={derived.label}
        title={title}
        lead={
          selectedPath?.blurb ?? 'Approved sample materials, selected by your role and explicit content rules. Completion is self-reported.'
        }
        aside={
          <Link to="/learning/me" className="band__action">
            <GraduationCap size={16} /> My learning
          </Link>
        }
      >
        <nav className="pathbar pathbar--onband" aria-label="Learning views">
          {[
            ['', 'For you'],
            ['paths', 'Role-based paths'],
            ['catalog', 'Catalog'],
            ['best-practices', 'Best practices'],
            ['docs', 'Product docs'],
            ['quick-reference', 'Quick references'],
          ].map(([p, label]) => (
            <Link key={p} className={`pathbar__item${mode === p && !pathId ? ' is-active' : ''}`} to={`/learning${p ? '/' + p : ''}`}>
              {label}
            </Link>
          ))}
        </nav>
      </PageBand>
      {browse && (
        <div className="catalog-filters">
          <label className="field">
            Search learning
            <input type="search" value={q} onChange={(e) => filter('q', e.target.value)} placeholder="Title, topic, or keyword" />
          </label>
          {!pathId && mode === 'catalog' && (
            <label className="field">
              Content type
              <select value={type} onChange={(e) => filter('type', e.target.value)}>
                <option value="">All types</option>
                {Object.entries(TYPE_LABEL).map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </select>
            </label>
          )}
          <label className="field">
            Progress
            <select value={status} onChange={(e) => filter('status', e.target.value)}>
              <option value="">All progress</option>
              <option value="not_started">Not started</option>
              <option value="in_progress">In progress</option>
              <option value="completed">Completed</option>
            </select>
          </label>
        </div>
      )}
      {error ? (
        <div className="state state--error" role="alert">
          {error} <button onClick={() => setAttempt((a) => a + 1)}>Retry</button>
        </div>
      ) : !current ? (
        <div className="state" role="status">
          Loading learning…
        </div>
      ) : (
        <>
          {(!mode || mode === 'paths') && !pathId && (
            <section>
              <h2 className="section-title">Paths for {home?.persona_label}</h2>
              <div className="path-grid">
                {home?.role_paths.map((p) => (
                  <article className="pathcard" key={p.id}>
                    <h3 className="pathcard__title">{p.title}</h3>
                    <p className="pathcard__blurb">{p.blurb}</p>
                    <div className="pathcard__progress">
                      <span className="pathcard__bar" aria-hidden="true">
                        <span style={{ width: `${p.total_steps ? (p.completed_steps / p.total_steps) * 100 : 0}%` }} />
                      </span>
                      <span className="pathcard__count">
                        {p.completed_steps} of {p.total_steps} steps
                      </span>
                    </div>
                    <div className="pathcard__actions">
                      {p.next_item_id && (
                        <Link className="btn btn--inline" to={itemHref(p.next_item_id)}>
                          Continue path
                        </Link>
                      )}
                      <Link className="textlink" to={`/learning/paths?path=${p.id}`}>
                        View steps
                      </Link>
                    </div>
                  </article>
                ))}
              </div>
              {mode === 'paths' && (
                <>
                  <h2 className="section-title">All available paths</h2>
                  <div className="pathbar">
                    {home?.paths.map((p) => (
                      <Link className="pathbar__item" key={p.id} to={`/learning/paths?path=${p.id}`}>
                        {p.title}
                      </Link>
                    ))}
                  </div>
                </>
              )}
            </section>
          )}
          {browse && (
            <>
              {selectedPath && (
                <p>
                  {selectedPath.completed_steps} / {selectedPath.total_steps} completed · Follow the numbered sequence. Prerequisites are
                  shown on each item.
                </p>
              )}
              {current.items.length ? (
                <div className="item-grid">
                  {current.items.map((i) => (
                    <ItemCard key={i.id} item={i} />
                  ))}
                </div>
              ) : (
                <div className="state">No learning matches these filters.</div>
              )}
            </>
          )}
          {!mode &&
            !pathId &&
            home?.sections.map((s) => (
              <section key={s.id} className={`lsection lsection--${s.id}`}>
                <h2 className="section-title">{s.title}</h2>
                <p className="section-sub">{s.subtitle}</p>
                {s.items.length ? (
                  <div className="item-grid">
                    {s.items.map((i) => (
                      <ItemCard key={i.id} item={i} />
                    ))}
                  </div>
                ) : (
                  <p className="muted">You're up to date.</p>
                )}
              </section>
            ))}
        </>
      )}
    </div>
  )
}
