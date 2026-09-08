import { ArrowRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PillarGlyph } from '../lib/icons'
import type { Pillar } from '../lib/types'

export function PriorityCard({ pillar }: { pillar: Pillar }) {
  return (
    <article className={`pcard pcard--${pillar.tone}`}>
      <div className="pcard__head">
        <div className="pcard__glyph" aria-hidden="true">
          <PillarGlyph icon={pillar.icon} strokeWidth={2.4} />
        </div>
        <div>
          <h2 className="pcard__title">
            <Link to={pillar.cta_href} className="plain">
              {pillar.card_title || pillar.title}
            </Link>
          </h2>
          <p className="pcard__desc">{pillar.description}</p>
        </div>
      </div>

      {pillar.primary_links.length > 0 && (
        <ul className="linkrow linkrow--primary">
          {pillar.primary_links.map((l) => (
            <li key={l.href}>
              <Link to={l.href}>{l.label}</Link>
            </li>
          ))}
        </ul>
      )}

      {pillar.secondary_links.length > 0 && (
        <ul className="linkrow linkrow--secondary">
          {pillar.secondary_links.map((l) => (
            <li key={l.href}>
              <Link to={l.href}>{l.label}</Link>
            </li>
          ))}
        </ul>
      )}

      <div className="pcard__cta">
        <Link className={`btn btn--${pillar.tone}`} to={pillar.cta_href}>
          {pillar.cta_label}
          <ArrowRight size={20} strokeWidth={2.4} />
        </Link>
      </div>
    </article>
  )
}
