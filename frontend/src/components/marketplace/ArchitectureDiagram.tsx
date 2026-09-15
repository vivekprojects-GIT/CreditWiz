import { useId } from 'react'
import type { ArchBandItem, ArchColumn, ArchEdge, NodeKind } from '../../lib/architecture'

// Drawing units. The SVG scales to its container, so these are proportions.
const W = 1120
const PAD = 20
const GAP = 64 // between columns: room for connectors and step markers
const HEAD = 48 // column title and sublabel
const INSET = 12 // node inset inside its column
const NODE_GAP = 14
const GROUP_HEAD = 24
const GROUP_GAP = 8
const BAND_GAP = 28
const BAND_H = 78
const CHAR = 6.7 // average glyph width at 12.5px semibold, for wrapping

export const KIND_STYLE: Record<NodeKind, { color: string; label: string }> = {
  person: { color: '#3d404a', label: 'Person' },
  external: { color: '#767b88', label: 'External' },
  channel: { color: '#1a56c4', label: 'Channel' },
  agent: { color: '#e60000', label: 'Agent' },
  model: { color: '#7c3aed', label: 'Model' },
  tool: { color: '#0f766e', label: 'Tool' },
  store: { color: '#b45309', label: 'System of record' },
}

function wrap(text: string, max: number): string[] {
  const lines: string[] = []
  let line = ''
  for (const word of text.split(/\s+/)) {
    const next = line ? `${line} ${word}` : word
    if (next.length > max && line) {
      lines.push(line)
      line = word
    } else line = next
  }
  if (line) lines.push(line)
  return lines
}

function clip(text: string, max: number) {
  return text.length > max ? `${text.slice(0, max - 1).trimEnd()}…` : text
}

type Box = {
  id: string
  x: number
  y: number
  w: number
  h: number
  col: number
  lines: string[]
  detail: string[]
  kind: NodeKind
  highlight: boolean
}

interface Props {
  title: string
  columns: ArchColumn[]
  edges: ArchEdge[]
  band: ArchBandItem[]
}

/**
 * A layered architecture diagram: columns left to right, the agent this page
 * describes highlighted, numbered connectors that match the steps table, and a
 * band of platform services and controls that apply to everything above it.
 */
export function ArchitectureDiagram({ title, columns, edges, band }: Props) {
  const uid = useId().replace(/:/g, '')
  const n = columns.length
  const colW = (W - PAD * 2 - GAP * (n - 1)) / n
  const colX = (i: number) => PAD + i * (colW + GAP)
  const nodeW = colW - INSET * 2
  const labelChars = Math.floor((nodeW - 24) / CHAR)
  const detailChars = Math.floor((nodeW - 24) / 6.1)

  // Measure each column's content.
  type Item = { kind: 'group'; label: string } | { kind: 'node'; box: Omit<Box, 'x' | 'y'> } | { kind: 'space'; h: number }
  const measured = columns.map((c, ci) => {
    const items: Item[] = []
    c.groups.forEach((g, gi) => {
      if (gi > 0) items.push({ kind: 'space', h: GROUP_GAP })
      if (g.label) items.push({ kind: 'group', label: g.label })
      g.nodes.forEach((nd, ni) => {
        if (ni > 0) items.push({ kind: 'space', h: NODE_GAP })
        const lines = wrap(nd.label, labelChars)
        const detail = nd.detail ? wrap(nd.detail, detailChars) : []
        const h = 12 + 14 + lines.length * 16 + detail.length * 14 + 10
        items.push({ kind: 'node', box: { id: nd.id, w: nodeW, h, col: ci, lines, detail, kind: nd.kind, highlight: nd.highlight } })
      })
    })
    const h = items.reduce((sum, it) => sum + (it.kind === 'group' ? GROUP_HEAD : it.kind === 'space' ? it.h : it.box.h), 0)
    return { items, h }
  })
  const contentH = Math.max(...measured.map((m) => m.h))
  const colH = HEAD + INSET + contentH + INSET
  const bandY = PAD + colH + BAND_GAP
  const H = bandY + BAND_H + PAD

  // Place nodes, centred vertically so single nodes line up with the flow.
  const boxes = new Map<string, Box>()
  const groupLabels: { x: number; y: number; label: string }[] = []
  measured.forEach((m, ci) => {
    let y = PAD + HEAD + INSET + (contentH - m.h) / 2
    const x = colX(ci) + INSET
    for (const it of m.items) {
      if (it.kind === 'space') y += it.h
      else if (it.kind === 'group') {
        groupLabels.push({ x, y: y + 15, label: it.label })
        y += GROUP_HEAD
      } else {
        boxes.set(it.box.id, { ...it.box, x, y })
        y += it.box.h
      }
    }
  })

  // Route connectors. Each crosses one gap on its own vertical rail, offset
  // so flows in opposite directions, or from different sources, never share a
  // line. Edges from the same source share a rail, drawing a clean trunk.
  const hot = new Set([...boxes.values()].filter((b) => b.highlight).map((b) => b.id))
  const rails = new Map<string, number>()
  const railCount = new Map<string, number>()
  const badgeSeen = new Set<string>()
  const paths = edges.flatMap((e, i) => {
    const s = boxes.get(e.source)
    const t = boxes.get(e.target)
    if (!s || !t) return []
    const isHot = hot.has(e.source) || hot.has(e.target)
    let d: string
    let badge: { x: number; y: number } | null = null
    if (s.col === t.col) {
      const x = s.x + s.w / 2
      const down = t.y > s.y
      const y1 = down ? s.y + s.h : s.y
      const y2 = down ? t.y : t.y + t.h
      d = `M ${x} ${y1} V ${y2}`
      badge = { x: x + 15, y: (y1 + y2) / 2 }
    } else {
      const dir = t.col > s.col ? 1 : -1
      const gap = dir > 0 ? s.col : s.col - 1
      const gapKey = `${gap}:${dir}`
      const railKey = `${gapKey}:${e.source}`
      if (!rails.has(railKey)) {
        const k = railCount.get(gapKey) ?? 0
        railCount.set(gapKey, k + 1)
        const mid = colX(gap) + colW + GAP / 2
        rails.set(railKey, mid + (dir > 0 ? -6 - 6 * k : 6 + 6 * k))
      }
      const bx = rails.get(railKey)!
      const sx = dir > 0 ? s.x + s.w : s.x
      const tx = dir > 0 ? t.x : t.x + t.w
      const sy = s.y + s.h / 2
      const ty = t.y + t.h / 2
      d = `M ${sx} ${sy} H ${bx} V ${ty} H ${tx}`
      badge = { x: (bx + tx) / 2, y: ty }
    }
    const badgeKey = `${e.source}:${e.step}`
    const showBadge = e.step != null && !badgeSeen.has(badgeKey)
    if (showBadge) badgeSeen.add(badgeKey)
    return [{ key: `${e.source}-${e.target}-${i}`, d, isHot, dashed: e.dashed, step: showBadge ? e.step : null, badge }]
  })
  // Highlighted flows are drawn last so they sit on top.
  paths.sort((a, b) => Number(a.isHot) - Number(b.isHot))

  const kinds = [...new Set([...boxes.values()].map((b) => b.kind))]
  const itemW = (W - PAD * 2 - 28 - (band.length - 1) * 10) / Math.max(band.length, 1)

  return (
    <figure className="cf-diagram">
      <div className="cf-diagram__scroll">
        <svg
          className="cf-diagram__svg"
          viewBox={`0 0 ${W} ${H}`}
          role="img"
          aria-labelledby={`${uid}-title`}
        >
          <title id={`${uid}-title`}>{title}</title>
          <defs>
            <marker id={`${uid}-arrow`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#767b88" />
            </marker>
            <marker id={`${uid}-arrow-hot`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto">
              <path d="M0,0 L10,5 L0,10 z" fill="#e60000" />
            </marker>
          </defs>

          {columns.map((c, ci) => (
            <g key={c.id}>
              <rect x={colX(ci)} y={PAD} width={colW} height={colH} rx={10} fill="#f6f7f9" stroke="#e3e5ea" />
              <text x={colX(ci) + 14} y={PAD + 21} fontSize={11} fontWeight={700} letterSpacing={0.9} fill="#3d404a">
                {c.label.toUpperCase()}
              </text>
              {c.sublabel && (
                <text x={colX(ci) + 14} y={PAD + 37} fontSize={11} fill="#767b88">
                  {clip(c.sublabel, Math.floor((colW - 28) / 6))}
                </text>
              )}
            </g>
          ))}

          {groupLabels.map((g, i) => (
            <text key={i} x={g.x + 2} y={g.y} fontSize={10} fontWeight={700} letterSpacing={0.7} fill="#767b88">
              {g.label.toUpperCase()}
            </text>
          ))}

          {paths.map((p) => (
            <path
              key={p.key}
              d={p.d}
              fill="none"
              stroke={p.isHot ? '#e60000' : '#9a9ea9'}
              strokeWidth={p.isHot ? 1.8 : 1.3}
              strokeDasharray={p.dashed ? '5 4' : undefined}
              markerEnd={`url(#${uid}-${p.isHot ? 'arrow-hot' : 'arrow'})`}
            />
          ))}

          {[...boxes.values()].map((b) => {
            const style = KIND_STYLE[b.kind]
            return (
              <g key={b.id}>
                <rect
                  x={b.x}
                  y={b.y}
                  width={b.w}
                  height={b.h}
                  rx={8}
                  fill={b.highlight ? '#fdecec' : '#ffffff'}
                  stroke={b.highlight ? '#e60000' : '#d2d5dc'}
                  strokeWidth={b.highlight ? 2 : 1}
                />
                <rect x={b.x + 1} y={b.y + 9} width={3} height={b.h - 18} rx={1.5} fill={style.color} />
                <text x={b.x + 14} y={b.y + 21} fontSize={9.5} fontWeight={700} letterSpacing={0.7} fill={style.color}>
                  {b.highlight ? 'THIS AGENT' : style.label.toUpperCase()}
                </text>
                {b.lines.map((l, i) => (
                  <text key={i} x={b.x + 14} y={b.y + 38 + i * 16} fontSize={12.5} fontWeight={650} fill="#17181c">
                    {l}
                  </text>
                ))}
                {b.detail.map((l, i) => (
                  <text key={`d${i}`} x={b.x + 14} y={b.y + 36 + b.lines.length * 16 + i * 14} fontSize={11} fill="#5a5e6b">
                    {l}
                  </text>
                ))}
              </g>
            )
          })}

          {paths
            .filter((p) => p.step != null && p.badge)
            .map((p) => (
              <g key={`b-${p.key}`}>
                <circle cx={p.badge!.x} cy={p.badge!.y} r={9.5} fill={p.isHot ? '#e60000' : '#17181c'} stroke="#ffffff" strokeWidth={2} />
                <text x={p.badge!.x} y={p.badge!.y + 3.8} fontSize={10.5} fontWeight={700} fill="#ffffff" textAnchor="middle">
                  {p.step}
                </text>
              </g>
            ))}

          <rect x={PAD} y={bandY} width={W - PAD * 2} height={BAND_H} rx={10} fill="#ffffff" stroke="#c3c6ce" strokeDasharray="5 4" />
          <text x={PAD + 14} y={bandY + 21} fontSize={11} fontWeight={700} letterSpacing={0.9} fill="#3d404a">
            PLATFORM SERVICES AND CONTROLS
          </text>
          {band.map((item, i) => {
            const x = PAD + 14 + i * (itemW + 10)
            return (
              <g key={item.label}>
                <rect x={x} y={bandY + 32} width={itemW} height={36} rx={6} fill="#f6f7f9" stroke="#e3e5ea" />
                <text x={x + 10} y={bandY + 47} fontSize={11.5} fontWeight={650} fill="#17181c">
                  {clip(item.label, Math.floor((itemW - 20) / 6.4))}
                </text>
                {item.detail && (
                  <text x={x + 10} y={bandY + 61} fontSize={10.5} fill="#5a5e6b">
                    {clip(item.detail, Math.floor((itemW - 20) / 5.6))}
                  </text>
                )}
              </g>
            )
          })}
        </svg>
      </div>
      <figcaption className="cf-legend">
        {kinds.map((k) => (
          <span key={k} className="cf-legend__item">
            <span className="cf-legend__swatch" style={{ background: KIND_STYLE[k].color }} />
            {KIND_STYLE[k].label}
          </span>
        ))}
        <span className="cf-legend__item">
          <span className="cf-legend__step">1</span>
          Numbered connectors follow the steps below
        </span>
      </figcaption>
    </figure>
  )
}
