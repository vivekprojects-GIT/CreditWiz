import { BookOpen, ChevronRight, ExternalLink, Layers } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, isAbort } from '../../lib/api'
import { fetchAgentArchitecture, fetchAgentDocs, type DocPage } from '../../lib/learning'
import { track } from '../../lib/context'
import { usePersona } from '../../lib/personaContext'
import { BackButton } from '../BackButton'
import { Markdown } from '../Markdown'
import { NotFound } from '../SimplePages'

export function AgentDocPage({ kind }: { kind: 'docs' | 'architecture' }) {
  const { id = '' } = useParams()
  const { persona } = usePersona()
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [page, setPage] = useState<DocPage | null | undefined>(undefined)

  useEffect(() => {
    const ctrl = new AbortController()
    setPage(undefined)
    const load = kind === 'docs' ? fetchAgentDocs : fetchAgentArchitecture
    load(id, ctrl.signal)
      .then((p) => {
        setError('')
        setPage(p)
        track('marketplace', kind === 'docs' ? 'documentation_click' : 'architecture_click', {
          subject_id: id,
          subject_type: 'agent',
          persona,
          meta: { view: 'in-app' },
        })
      })
      .catch((err: unknown) => {
        if (isAbort(err)) return
        if (err instanceof ApiError && err.status === 404) setPage(null)
        else setError(err instanceof Error ? err.message : 'Resource unavailable')
      })
    return () => ctrl.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, kind, persona, attempt])

  if (error)
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
  if (page === null) return <NotFound />
  if (page === undefined) {
    return (
      <div className="content">
        <div className="skeleton" style={{ height: 24, width: 320, marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 480 }} />
      </div>
    )
  }

  const Icon = kind === 'docs' ? BookOpen : Layers
  const agentHref = `/marketplace/agents/${page.agent_id}`

  return (
    <div className="content doc">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to="/marketplace">AI Marketplace</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <Link to={agentHref}>{page.agent_name}</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        <span>{kind === 'docs' ? 'Documentation' : 'Architecture'}</span>
      </nav>

      <div className="doc__bar">
        <BackButton fallback={agentHref} label={`Back to ${page.agent_name}`} />
        <div className="doc__bar-right">
          <Link to={kind === 'docs' ? `${agentHref}/architecture` : `${agentHref}/docs`} className="textlink">
            {kind === 'docs' ? <Layers size={16} strokeWidth={2.4} /> : <BookOpen size={16} strokeWidth={2.4} />}
            {kind === 'docs' ? 'Architecture pattern' : 'Documentation'}
          </Link>
          {page.source_url && (
            <a className="textlink" href={page.source_url} target="_blank" rel="noreferrer">
              Source <ExternalLink size={14} strokeWidth={2.4} />
            </a>
          )}
        </div>
      </div>

      {page.source_kind === 'sample' && (
        <p className="muted">Sample reference documentation for MVP review. Validate against the enterprise implementation before use.</p>
      )}
      <article className="doc__page">
        <div className="doc__kicker">
          <Icon size={16} strokeWidth={2.4} /> {kind === 'docs' ? 'Documentation' : 'Architecture pattern'}
        </div>
        <Markdown source={page.markdown} />
      </article>
    </div>
  )
}
