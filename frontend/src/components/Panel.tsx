import { CircleCheck, Info, StickyNote, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'

export type PanelKind = 'info' | 'note' | 'warning' | 'success'

const ICON = { info: Info, note: StickyNote, warning: TriangleAlert, success: CircleCheck }

/** A Confluence-style panel: a tinted box with an icon and an optional title. */
export function Panel({ kind, title, children }: { kind: PanelKind; title?: string; children: ReactNode }) {
  const Icon = ICON[kind]
  return (
    <aside className={`cf-panel cf-panel--${kind}`} role="note">
      <Icon className="cf-panel__icon" size={18} strokeWidth={2.2} aria-hidden="true" />
      <div className="cf-panel__body">
        {title && <p className="cf-panel__title">{title}</p>}
        {children}
      </div>
    </aside>
  )
}
