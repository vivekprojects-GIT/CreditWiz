import { ChevronRight, LayoutTemplate } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { useCreate } from '../../lib/create'
import { fetchTemplates, type Template } from '../../lib/prompts'
import { PageBand } from '../PageBand'

export function TemplatesPage() {
  const { open } = useCreate()
  const [templates, setTemplates] = useState<Template[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const ctrl = new AbortController()
    fetchTemplates(ctrl.signal)
      .then(setTemplates)
      .catch((e: unknown) => {
        if (!isAbort(e)) setError(e instanceof Error ? e.message : 'Templates could not load.')
      })
    return () => ctrl.abort()
  }, [])

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/library">Prompts &amp; Skills</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>Prompt templates</span>
      </nav>
      <PageBand
        kicker="Prompts & Skills"
        title="Prompt templates"
        compact
        lead="Four scaffolds cover most banking work. Each already carries the constraints that get prompts through validation."
      />
      {error && (
        <p className="state state--error" role="alert">
          {error}
        </p>
      )}
      {!templates && !error && <div className="skeleton" style={{ height: 320 }} />}
      <div className="tpl-list">
        {templates?.map((t) => (
          <section key={t.id} className="panel tpl-card">
            <div className="tpl-card__head">
              <span className="pick__icon" aria-hidden="true">
                <LayoutTemplate size={18} strokeWidth={2} />
              </span>
              <div className="tpl__body">
                <h2 className="panel__title">{t.name}</h2>
                <p className="panel__text">{t.use}</p>
                <p className="tpl__when">Used for: {t.when}</p>
              </div>
              <button type="button" className="btn btn--inline" onClick={() => open({ kind: 'prompt', body: t.body })}>
                Use this
              </button>
            </div>
            <details className="tpl-card__body">
              <summary>Show the scaffold</summary>
              <pre className="codeblock">{t.body}</pre>
            </details>
          </section>
        ))}
      </div>
    </div>
  )
}
