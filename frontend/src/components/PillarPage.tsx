import { ArrowRight, ChevronRight } from 'lucide-react'
import { Link, useLocation } from 'react-router-dom'
import { useHub } from '../lib/hub'
import { pillarBasePath } from '../lib/types'
import { PageBand } from './PageBand'
import { NotFound } from './SimplePages'

export function PillarPage() {
  const { pillars } = useHub()
  const { pathname } = useLocation()
  const base = '/' + (pathname.split('/')[1] ?? '')
  const pillar = pillars.find((p) => pillarBasePath(p) === base)
  if (!pillar) return <NotFound />

  const current = pillar.sections.find((s) => s.href === pathname)

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} strokeWidth={2.2} />
        {current ? <Link to={base}>{pillar.short_title}</Link> : <span>{pillar.short_title}</span>}
        {current && (
          <>
            <ChevronRight size={16} strokeWidth={2.2} />
            <span>{current.title}</span>
          </>
        )}
      </nav>

      <PageBand
        kicker={current ? pillar.short_title : undefined}
        title={current ? current.title : pillar.short_title}
        lead={current ? current.blurb : pillar.description}
        compact
      />

      <p className="state">Planned pillar · Outside the Marketplace + Learning MVP.</p>
      {current ? (
        <section className="panel">
          <h2 className="panel__title">{current.title}</h2>
          <p className="panel__text">
            This area is outside the Marketplace + Learning MVP. It shows the planned hub structure; its workflows are not implemented.
          </p>
          <Link className="mcard__link" to={base}>
            Back to {pillar.short_title} <ArrowRight strokeWidth={2.4} />
          </Link>
        </section>
      ) : null}

      <h2 className="section-title">{current ? `More in ${pillar.short_title}` : 'Planned capabilities'}</h2>
      <section className="more-grid" aria-label={`${pillar.short_title} sections`}>
        {pillar.sections
          .filter((s) => s.href !== current?.href)
          .map((s) => (
            <Link key={s.href} to={s.href} className={`scard scard--${pillar.tone}`}>
              <span className="scard__title">{s.title}</span>
              <span className="scard__blurb">{s.blurb}</span>
              <span className="scard__go">
                Open <ArrowRight size={18} strokeWidth={2.4} />
              </span>
            </Link>
          ))}
      </section>
    </div>
  )
}
