import { ArrowRight, ChevronRight, Clock, PenLine, Plus } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { useCreate } from '../../lib/create'
import { formatDate } from '../../lib/format'
import {
  AUDIENCE_LABEL,
  KIND_NAME,
  fetchLibrary,
  fetchMyContributions,
  setSaved,
  type Contribution,
  type PromptCard,
} from '../../lib/prompts'
import { PageBand } from '../PageBand'
import { PromptTile, RiskPill } from './PromptTile'

const STATUS: Record<Contribution['status'], string> = {
  in_review: 'In review',
  live: 'Live',
  returned: 'Returned to you',
}

export function MyLibraryPage() {
  const { open } = useCreate()
  const [mine, setMine] = useState<Contribution[] | null>(null)
  const [saved, setSavedList] = useState<PromptCard[] | null>(null)
  const [error, setError] = useState('')
  // Bumped when something is submitted from Create while this page is open.
  const [version, setVersion] = useState(0)

  useEffect(() => {
    const bump = () => setVersion((v) => v + 1)
    window.addEventListener('creditwiz:contributed', bump)
    return () => window.removeEventListener('creditwiz:contributed', bump)
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    Promise.all([fetchMyContributions(ctrl.signal), fetchLibrary('all', ctrl.signal)])
      .then(([contributions, lib]) => {
        setMine(contributions)
        setSavedList(lib.prompts.filter((p) => p.saved))
      })
      .catch((e: unknown) => {
        if (!isAbort(e)) setError(e instanceof Error ? e.message : 'My library could not load.')
      })
    return () => ctrl.abort()
  }, [version])

  function unsave(p: PromptCard) {
    setSavedList((list) => list?.filter((x) => x.id !== p.id) ?? list)
    setSaved(p.id, false).catch(() => setSavedList((list) => (list ? [p, ...list] : list)))
  }

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/library">Prompts &amp; Skills</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>My library</span>
      </nav>
      <PageBand
        kicker="Prompts & Skills"
        title="My library"
        compact
        lead="What you saved, and what you submitted for review."
        aside={
          <button type="button" className="btn btn--inline" onClick={() => open({ kind: 'choose' })}>
            <Plus size={16} strokeWidth={2.4} /> Create new
          </button>
        }
      />

      {error && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}

      <h2 className="section-title section-title--first">
        Submitted by you{mine && mine.length > 0 ? ` (${mine.length})` : ''}
      </h2>
      {mine === null && !error && <div className="skeleton" style={{ height: 120 }} />}
      {mine?.length === 0 && (
        <section className="panel lib-empty">
          <h3 className="panel__title">
            <PenLine size={18} strokeWidth={2.2} /> You have not submitted anything yet
          </h3>
          <p className="panel__text">
            If you have rewritten the same analysis three times this month, that is a prompt worth sharing.
          </p>
          <button type="button" className="btn btn--inline" onClick={() => open({ kind: 'prompt' })}>
            <Plus size={16} strokeWidth={2.4} /> Draft your first prompt
          </button>
        </section>
      )}
      {mine && mine.length > 0 && (
        <ul className="contribs">
          {mine.map((c) => (
            <li key={c.id} className="contrib">
              <div className="contrib__main">
                <p className="contrib__meta">
                  <span className="contrib__kind">{KIND_NAME[c.kind]}</span>
                  <span className={`contrib__status contrib__status--${c.status}`}>
                    <Clock size={13} strokeWidth={2.4} aria-hidden="true" /> {STATUS[c.status]}
                  </span>
                  {c.risk && <RiskPill risk={c.risk} />}
                </p>
                <h3 className="contrib__title">{c.title}</h3>
                {c.description && <p className="contrib__desc">{c.description}</p>}
                <p className="contrib__review">{c.review}</p>
                <p className="contrib__review">
                  {c.status === 'returned'
                    ? 'Not in search while it is with you.'
                    : c.status === 'live'
                      ? `Found in search by you and ${AUDIENCE_LABEL[c.audience]}.`
                      : `Found in search by you now, and by ${AUDIENCE_LABEL[c.audience]} once approved.`}
                </p>
              </div>
              <span className="contrib__date">Submitted {formatDate(c.created_at)}</span>
            </li>
          ))}
        </ul>
      )}

      <h2 className="section-title">Saved{saved ? ` (${saved.length})` : ''}</h2>
      {saved === null && !error && <div className="skeleton" style={{ height: 120 }} />}
      {saved?.length === 0 && (
        <section className="panel lib-empty">
          <h3 className="panel__title">Nothing saved yet</h3>
          <p className="panel__text">Save a prompt with its bookmark to keep it here.</p>
          <Link className="textlink" to="/library">
            Browse the library <ArrowRight size={14} strokeWidth={2.4} />
          </Link>
        </section>
      )}
      {saved && saved.length > 0 && (
        <div className="lib-grid">
          {saved.map((p) => (
            <PromptTile key={p.id} p={p} onToggleSave={unsave} />
          ))}
        </div>
      )}

      <h2 className="section-title">My learning</h2>
      <p>
        <Link className="textlink" to="/learning/me">
          Progress, required steps and courses you started <ArrowRight size={14} strokeWidth={2.4} />
        </Link>
      </p>
    </div>
  )
}
