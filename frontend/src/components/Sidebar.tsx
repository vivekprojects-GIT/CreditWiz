import { CircleHelp, Home } from 'lucide-react'
import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { PillarGlyph } from '../lib/icons'
import { pillarBasePath, type Pillar } from '../lib/types'

interface Props {
  pillars: Pillar[]
}

function cls(base: string) {
  return ({ isActive }: { isActive: boolean }) => (isActive ? `${base} is-active` : base)
}

/**
 * Official logo: drop the brand file at frontend/public/mufg-logo.svg (or .png and
 * change the path below). Until that file exists the drawn mark + wordmark is shown.
 */
const LOGO_SRC = '/mufg-logo.svg'

function MufgLogo() {
  const [failed, setFailed] = useState(false)
  if (!failed) {
    return <img className="brand__img" src={LOGO_SRC} alt="MUFG" onError={() => setFailed(true)} />
  }
  return (
    <>
      <svg viewBox="0 0 40 40" aria-hidden="true">
        <circle cx="20" cy="20" r="18" fill="#e60000" />
        <circle cx="20" cy="20" r="9.5" fill="#fff" />
        <circle cx="20" cy="20" r="5.5" fill="#e60000" />
      </svg>
      <span>MUFG</span>
    </>
  )
}

export function Sidebar({ pillars }: Props) {
  return (
    <aside className="sidebar" aria-label="Primary">
      <NavLink to="/" className="brand" aria-label="CreditWiz home">
        <div className="brand__logo">
          <MufgLogo />
        </div>
        <div className="brand__product">
          <div className="brand__wordmark">CreditWiz</div>
          <div className="brand__tagline">Enterprise AI Hub · Americas</div>
        </div>
      </NavLink>

      <nav className="nav">
        <NavLink to="/" end className={cls('nav__item nav__item--home')}>
          <Home className="nav__icon" strokeWidth={2.2} />
          <span className="nav__label">Home</span>
        </NavLink>

        <div className="nav__section">Workspace</div>

        {pillars.map((p) => (
          <NavLink key={p.id} to={pillarBasePath(p)} className={cls('nav__item')}>
            <PillarGlyph icon={p.icon} className="nav__icon" strokeWidth={2} />
            <span className="nav__label">{p.short_title}</span>
          </NavLink>
        ))}

        <div className="nav__spacer" />
        <div className="nav__divider" />

        <NavLink to="/help" className={cls('nav__item nav__item--util')}>
          <CircleHelp className="nav__icon" strokeWidth={2} />
          <span className="nav__label">Help &amp; support</span>
        </NavLink>
      </nav>
    </aside>
  )
}
