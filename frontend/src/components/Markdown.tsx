import type { ReactNode } from 'react'
import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import remarkGfm from 'remark-gfm'
import { Panel, type PanelKind } from './Panel'

type Block = { kind: 'md'; text: string } | { kind: 'panel'; panel: PanelKind; title: string; text: string }

const PANEL = /^> \[!(INFO|NOTE|WARNING|SUCCESS)\][ \t]*(.*)$/

/**
 * Split markdown into ordinary runs and Confluence-style panels.
 *
 * A panel is a blockquote whose first line is `> [!INFO] Title` (or NOTE,
 * WARNING, SUCCESS); the rest of the blockquote is its body. Everything else,
 * including plain blockquotes, renders as ordinary markdown.
 */
function blocks(source: string): Block[] {
  const lines = source.split('\n')
  const out: Block[] = []
  let run: string[] = []
  let fenced = false
  const flush = () => {
    if (run.some((l) => l.trim())) out.push({ kind: 'md', text: run.join('\n') })
    run = []
  }
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.startsWith('```')) fenced = !fenced
    const m = fenced ? null : PANEL.exec(line)
    if (!m) {
      run.push(line)
      continue
    }
    flush()
    const body: string[] = []
    while (i + 1 < lines.length && lines[i + 1].startsWith('>')) body.push(lines[++i].replace(/^> ?/, ''))
    out.push({ kind: 'panel', panel: m[1].toLowerCase() as PanelKind, title: m[2].trim(), text: body.join('\n') })
  }
  flush()
  return out
}

export function slugify(text: string) {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
}

/** The `##` headings of a page, for its "On this page" list. */
export function headingsOf(source: string) {
  const out: { id: string; text: string }[] = []
  let fenced = false
  for (const line of source.split('\n')) {
    if (line.startsWith('```')) fenced = !fenced
    const m = fenced ? null : /^## (.+)$/.exec(line)
    if (m) {
      const text = m[1].replace(/[*_`]/g, '')
      out.push({ id: slugify(text), text })
    }
  }
  return out
}

function textOf(node: ReactNode): string {
  if (node == null || typeof node === 'boolean') return ''
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(textOf).join('')
  if (typeof node === 'object' && 'props' in node) {
    return textOf((node as { props: { children?: ReactNode } }).props.children)
  }
  return ''
}

function Run({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Anchored so the page's table of contents can link to each section.
        h2: ({ children }) => <h2 id={slugify(textOf(children))}>{children}</h2>,
        a: ({ href = '', children }) => {
          if (href.startsWith('/')) return <Link to={href}>{children}</Link>
          const external = /^https?:\/\//.test(href)
          return (
            <a href={href} target={external ? '_blank' : undefined} rel={external ? 'noreferrer' : undefined}>
              {children}
            </a>
          )
        },
      }}
    >
      {text}
    </ReactMarkdown>
  )
}

/** Renders trusted, in-house markdown. Internal links route in-app; external open in a new tab. */
export function Markdown({ source }: { source: string }) {
  return (
    <div className="md">
      {blocks(source).map((b, i) =>
        b.kind === 'md' ? (
          <Run key={i} text={b.text} />
        ) : (
          <Panel key={i} kind={b.panel} title={b.title || undefined}>
            <Run text={b.text} />
          </Panel>
        ),
      )}
    </div>
  )
}
