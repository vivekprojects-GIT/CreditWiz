import { Bookmark, BookmarkCheck, Check, ChevronRight, Clapperboard, Copy, ShieldCheck, Star } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, isAbort } from '../../lib/api'
import { track } from '../../lib/context'
import { formatDate } from '../../lib/format'
import { RELATION_LABEL, fetchPrompt, setSaved, type PromptDetail } from '../../lib/prompts'
import { BackButton } from '../BackButton'
import { NotFound } from '../SimplePages'
import { PromptTile, RiskPill, formatCount } from './PromptTile'

type Tab = 'prompt' | 'output' | 'guide'
const TABS: [Tab, string][] = [
  ['prompt', 'Prompt'],
  ['output', 'Sample output'],
  ['guide', 'Inputs and guidelines'],
]

export function PromptPage() {
  const { id = '' } = useParams()
  return <PromptContent key={id} id={id} />
}

function PromptContent({ id }: { id: string }) {
  const [p, setP] = useState<PromptDetail | null | undefined>(undefined)
  const [error, setError] = useState('')
  const [tab, setTab] = useState<Tab>('prompt')
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    const ctrl = new AbortController()
    fetchPrompt(id, ctrl.signal)
      .then((found) => {
        setP(found)
        track('prompts', 'view', { subject_id: found.id, subject_type: 'prompt', topics: found.tags })
      })
      .catch((e: unknown) => {
        if (isAbort(e)) return
        if (e instanceof ApiError && e.status === 404) setP(null)
        else setError(e instanceof Error ? e.message : 'This prompt could not load.')
      })
    return () => ctrl.abort()
  }, [id])

  if (p === null) return <NotFound />
  if (p === undefined)
    return (
      <div className="content">
        {error ? (
          <p className="state state--error" role="alert">
            {error}
          </p>
        ) : (
          <div className="skeleton" style={{ height: 420 }} />
        )}
      </div>
    )

  function toggleSave() {
    if (!p) return
    const next = !p.saved
    setP({ ...p, saved: next })
    setSaved(p.id, next).catch(() => setP((cur) => (cur ? { ...cur, saved: !next } : cur)))
  }

  function copy() {
    if (!p) return
    void navigator.clipboard?.writeText(p.body).then(() => setCopied(true)).catch(() => undefined)
    track('prompts', 'click', { subject_id: p.id, subject_type: 'prompt', meta: { action: 'copy' } })
  }

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/library">Prompts &amp; Skills</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>{p.title}</span>
      </nav>
      <div className="doc__bar">
        <BackButton fallback="/library" label="Back" />
      </div>

      <div className="pdoc">
        <div className="pdoc__main">
          <div className="pdoc__badges">
            {p.validated && (
              <span className="pdoc__validated">
                <Check size={13} strokeWidth={3} aria-hidden="true" /> Validated
              </span>
            )}
            <RiskPill risk={p.risk} />
            <span className="pdoc__cat">
              {p.desk.label} · {p.category}
            </span>
            {p.source_kind === 'sample' && <span className="asset__sample">Sample</span>}
          </div>
          <h1 className="pdoc__title">{p.title}</h1>
          <p className="pdoc__lead">{p.description}</p>

          <dl className="pdoc__stats">
            <div>
              <dt>Rating</dt>
              <dd>
                <Star className="star" size={16} strokeWidth={2.4} aria-hidden="true" /> {p.rating}{' '}
                <span className="muted">({p.ratings})</span>
              </dd>
            </div>
            <div>
              <dt>Uses</dt>
              <dd>{formatCount(p.uses)}</dd>
            </div>
            <div>
              <dt>Views</dt>
              <dd>{formatCount(p.views)}</dd>
            </div>
            <div>
              <dt>Saved per use</dt>
              <dd>{p.hours_saved}h</dd>
            </div>
            <div>
              <dt>Updated</dt>
              <dd>{formatDate(p.updated)}</dd>
            </div>
          </dl>

          <div className="pdoc__acts">
            <button type="button" className="btn btn--inline" onClick={copy}>
              <Copy size={16} strokeWidth={2.2} /> {copied ? 'Copied' : 'Copy the prompt'}
            </button>
            <button type="button" className="btn-outline" aria-pressed={p.saved} onClick={toggleSave}>
              {p.saved ? <BookmarkCheck size={16} strokeWidth={2.2} /> : <Bookmark size={16} strokeWidth={2.2} />}
              {p.saved ? 'Saved to My library' : 'Save'}
            </button>
          </div>

          <p className="impact">
            <b>{p.narrative}</b>
            <span>{p.repetition}.</span>
          </p>

          <div className="ptabs" role="tablist" aria-label="Prompt">
            {TABS.map(([value, label]) => (
              <button
                key={value}
                type="button"
                role="tab"
                id={`tab-${value}`}
                aria-selected={tab === value}
                aria-controls={`panel-${value}`}
                onClick={() => setTab(value)}
              >
                {label}
              </button>
            ))}
          </div>
          <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
            {tab === 'prompt' && <pre className="codeblock">{p.body}</pre>}
            {tab === 'output' && <pre className="codeblock codeblock--light">{p.sample_output}</pre>}
            {tab === 'guide' && (
              <>
                <h2 className="section-title section-title--first">What to supply</h2>
                <div className="table-wrap">
                  <table className="inputs">
                    <thead>
                      <tr>
                        <th scope="col">Input</th>
                        <th scope="col">Type</th>
                        <th scope="col">Notes</th>
                      </tr>
                    </thead>
                    <tbody>
                      {p.inputs.map((i) => (
                        <tr key={i.label}>
                          <td>
                            {i.label}
                            {!i.required && <span className="muted"> (optional)</span>}
                          </td>
                          <td>{i.type}</td>
                          <td>{i.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <h2 className="section-title">Usage guidelines</h2>
                <ul className="guidelines">
                  {p.guidelines.map((g) => (
                    <li key={g}>
                      <ShieldCheck size={16} strokeWidth={2.2} aria-hidden="true" /> {g}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          {p.reviews.length > 0 && (
            <>
              <h2 className="section-title">What colleagues say</h2>
              <ul className="reviews">
                {p.reviews.map((r) => (
                  <li key={r.name + r.when} className="review">
                    <span className="pavatar" aria-hidden="true">
                      {r.initials}
                    </span>
                    <div>
                      <p className="review__who">
                        <b>{r.name}</b> <span className="muted">· {r.team} · {r.when}</span>
                        <span className="review__stars" aria-label={`${r.stars} out of 5`}>
                          {'★'.repeat(r.stars)}
                        </span>
                      </p>
                      <p className="review__text">{r.comment}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <aside className="pside">
          <section className="panel">
            <h2 className="panel__title">
              <ShieldCheck size={18} strokeWidth={2.2} /> {p.risk} risk
            </h2>
            <p className="panel__text">{p.risk_note}</p>
          </section>
          <section className="panel">
            <h2 className="panel__title">People</h2>
            <ul className="people">
              <li>
                <span className="pavatar" aria-hidden="true">
                  {p.contributor.initials}
                </span>
                <span>
                  <b>{p.contributor.name}</b>
                  <span className="muted">
                    Contributor · {p.contributor.team} · {RELATION_LABEL[p.relation]}
                  </span>
                </span>
              </li>
              {p.collaborators
                .filter((c) => c.name !== p.contributor.name)
                .map((c) => (
                  <li key={c.name}>
                    <span className="pavatar" aria-hidden="true">
                      {c.initials}
                    </span>
                    <span>
                      <b>{c.name}</b>
                      <span className="muted">{c.role}</span>
                    </span>
                  </li>
                ))}
            </ul>
          </section>
          {p.tutorial && (
            <section className="panel">
              <h2 className="panel__title">
                <Clapperboard size={18} strokeWidth={2.2} /> Tutorial
              </h2>
              <p className="panel__text">
                {p.tutorial.title} · {p.tutorial.duration} · {p.tutorial.views} views
              </p>
            </section>
          )}
          <p className="muted small">
            Added {formatDate(p.created)}. Sample data from the design reference.
          </p>
        </aside>
      </div>

      {p.related.length > 0 && (
        <>
          <h2 className="section-title">More {p.category.toLowerCase()} prompts</h2>
          <div className="lib-grid">
            {p.related.map((r) => (
              <PromptTile key={r.id} p={r} />
            ))}
          </div>
        </>
      )}
    </div>
  )
}
