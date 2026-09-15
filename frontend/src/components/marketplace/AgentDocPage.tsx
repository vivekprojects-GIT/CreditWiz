import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, isAbort } from '../../lib/api'
import { fetchArchitecture, type ArchitecturePage } from '../../lib/architecture'
import { track } from '../../lib/context'
import { formatDate } from '../../lib/format'
import { fetchAgentDocs, type DocPage } from '../../lib/learning'
import { usePersona } from '../../lib/personaContext'
import '../../confluence.css'
import { ConfluencePage } from '../ConfluencePage'
import { Markdown, headingsOf } from '../Markdown'
import { Panel } from '../Panel'
import { NotFound } from '../SimplePages'
import { ArchitectureDiagram } from './ArchitectureDiagram'

type Loaded = { kind: 'docs'; page: DocPage } | { kind: 'architecture'; page: ArchitecturePage }

/** Where a page sits: its space, breadcrumb and the agent's page tree. */
function frame(agentId: string, agentName: string, current: 'docs' | 'architecture') {
  const base = `/marketplace/agents/${agentId}`
  return {
    space: 'Agent documentation',
    crumbs: [
      { label: 'AI Marketplace', to: '/marketplace' },
      { label: agentName, to: base },
      { label: current === 'docs' ? 'Documentation' : 'Architecture' },
    ],
    tree: {
      root: { label: agentName, to: base },
      pages: [
        { label: 'Documentation', to: `${base}/docs`, active: current === 'docs' },
        { label: 'Architecture', to: `${base}/architecture`, active: current === 'architecture' },
      ],
    },
  }
}

export function AgentDocPage({ kind }: { kind: 'docs' | 'architecture' }) {
  const { id = '' } = useParams()
  const { persona } = usePersona()
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const [loaded, setLoaded] = useState<Loaded | null | undefined>(undefined)

  useEffect(() => {
    const ctrl = new AbortController()
    setLoaded(undefined)
    const load: Promise<Loaded> =
      kind === 'docs'
        ? fetchAgentDocs(id, ctrl.signal).then((page) => ({ kind: 'docs' as const, page }))
        : fetchArchitecture(id, ctrl.signal).then((page) => ({ kind: 'architecture' as const, page }))
    load
      .then((l) => {
        setError('')
        setLoaded(l)
        track('marketplace', kind === 'docs' ? 'documentation_click' : 'architecture_click', {
          subject_id: id,
          subject_type: 'agent',
          persona,
          meta: { view: 'in-app' },
        })
      })
      .catch((err: unknown) => {
        if (isAbort(err)) return
        if (err instanceof ApiError && err.status === 404) setLoaded(null)
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
  if (loaded === null) return <NotFound />
  if (loaded === undefined) {
    return (
      <div className="content">
        <div className="skeleton" style={{ height: 24, width: 320, marginBottom: 16 }} />
        <div className="skeleton" style={{ height: 480 }} />
      </div>
    )
  }
  return loaded.kind === 'docs' ? <DocsView page={loaded.page} /> : <ArchitectureView page={loaded.page} />
}

function DocsView({ page }: { page: DocPage }) {
  const properties: [string, string][] = [
    ['Owner', page.owner || 'To be confirmed'],
    ['Team', page.team],
    ['Status', page.status],
    ...(page.version ? ([['Version', page.version]] as [string, string][]) : []),
    ['Last updated', formatDate(page.updated)],
    ['Access', 'Open to all employees'],
  ]
  return (
    <ConfluencePage
      {...frame(page.agent_id, page.agent_name, 'docs')}
      title={page.title}
      status={page.status}
      owner={page.owner}
      team={page.team}
      updated={page.updated}
      readMinutes={page.read_minutes}
      properties={properties}
      toc={headingsOf(page.markdown)}
      labels={page.labels}
    >
      <Markdown source={page.markdown} />
    </ConfluencePage>
  )
}

const SECTIONS = [
  { id: 'diagram', text: 'Architecture diagram' },
  { id: 'flow', text: 'How a request flows' },
  { id: 'components', text: 'Components' },
  { id: 'principles', text: 'Design principles' },
  { id: 'controls', text: 'Security and controls' },
]

function ArchitectureView({ page }: { page: ArchitecturePage }) {
  const properties: [string, string][] = [
    ['Owner', page.owner || 'To be confirmed'],
    ['Team', page.team],
    ['Pattern', page.pattern],
    ['Status', page.status],
    ...(page.version ? ([['Version', page.version]] as [string, string][]) : []),
    ['Last updated', formatDate(page.updated)],
  ]
  const toc = page.related.length ? [...SECTIONS, { id: 'related', text: 'Related agents' }] : SECTIONS
  return (
    <ConfluencePage
      {...frame(page.agent_id, page.agent_name, 'architecture')}
      title={page.title}
      status={page.status}
      owner={page.owner}
      team={page.team}
      updated={page.updated}
      properties={properties}
      toc={toc}
      labels={['architecture', page.pattern.toLowerCase()]}
      wide
    >
      <div className="md">
        <Panel kind="info" title="Summary">
          <p>{page.summary}</p>
        </Panel>
        {!page.confirmed && (
          <Panel kind="note" title="To be confirmed">
            <p>
              Platform and model choices will be added once {page.team} confirms them. Components marked to be
              confirmed stand in for that decision.
            </p>
          </Panel>
        )}

        <h2 id="diagram">Architecture diagram</h2>
        <ArchitectureDiagram
          title={`${page.agent_name} architecture`}
          columns={page.columns}
          edges={page.edges}
          band={page.band}
        />

        <h2 id="flow">How a request flows</h2>
        <ol className="cf-steps">
          {page.steps.map((s) => (
            <li key={s.number}>
              <span className="cf-step" aria-hidden="true">
                {s.number}
              </span>
              <div>
                <strong>{s.title}</strong>
                <p>{s.detail}</p>
              </div>
            </li>
          ))}
        </ol>

        <h2 id="components">Components</h2>
        <table>
          <thead>
            <tr>
              <th>Component</th>
              <th>Type</th>
              <th>Responsibility</th>
            </tr>
          </thead>
          <tbody>
            {page.components.map((c) => (
              <tr key={`${c.type}-${c.name}`}>
                <td>
                  <strong>{c.name}</strong>
                </td>
                <td>{c.type}</td>
                <td>{c.responsibility}</td>
              </tr>
            ))}
          </tbody>
        </table>

        <h2 id="principles">Design principles</h2>
        <ul>
          {page.principles.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>

        <h2 id="controls">Security and controls</h2>
        <table>
          <thead>
            <tr>
              <th>Control</th>
              <th>How it applies</th>
            </tr>
          </thead>
          <tbody>
            {page.band.map((b) => (
              <tr key={b.label}>
                <td>
                  <strong>{b.label}</strong>
                </td>
                <td>{b.detail}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {page.related.length > 0 && (
          <>
            <h2 id="related">Related agents</h2>
            <ul>
              {page.related.map((r) => (
                <li key={r.id}>
                  <Link to={`/marketplace/agents/${r.id}/architecture`}>{r.name}</Link>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </ConfluencePage>
  )
}
