import { ArrowRight, ChevronRight, Lock } from 'lucide-react'
import { Link } from 'react-router-dom'
import { PillarGlyph } from '../lib/icons'
import type { Pillar } from '../lib/types'

export function ModuleCard({ pillar }: { pillar: Pillar }) {
  return (
    <article className={`mcard mcard--${pillar.tone}`}>
      <div className="mcard__glyph" aria-hidden="true">
        <PillarGlyph icon={pillar.icon} strokeWidth={2.2} />
      </div>
      <div>
        <h3 className="mcard__title">
          <Link to={pillar.cta_href} className="plain">
            {pillar.title}
          </Link>
        </h3>
        <p className="mcard__desc">{pillar.description}</p>
        {pillar.admin_only && (
          <div>
            <span className="chip">
              <Lock strokeWidth={2.4} />
              Admin
            </span>
          </div>
        )}
        <Link className="mcard__link" to={pillar.cta_href}>
          {pillar.cta_label}
          <ArrowRight strokeWidth={2.4} />
        </Link>
      </div>
      <Link className="mcard__chev" to={pillar.cta_href} aria-label={pillar.cta_label}>
        <ChevronRight strokeWidth={2.6} />
      </Link>
    </article>
  )
}
