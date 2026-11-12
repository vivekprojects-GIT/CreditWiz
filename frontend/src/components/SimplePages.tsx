import { Preferences } from './Preferences'
import { ArrowRight, ChevronRight } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useHub } from '../lib/hub'
import { PageBand } from './PageBand'

/** An empty directory field says so, rather than leaving a blank row. */
const NOT_PROVIDED = <span className="tbc">Not provided</span>

function Crumbs({ title }: { title: string }) {
  return (
    <nav className="crumbs" aria-label="Breadcrumb">
      <Link to="/">Home</Link>
      <ChevronRight size={16} strokeWidth={2.2} />
      <span>{title}</span>
    </nav>
  )
}

export function SettingsPage() {
  const { user } = useHub()
  return (
    <div className="content">
      <Crumbs title="Profile" />
      <PageBand
        kicker={user.job_title}
        title={user.display_name}
        aside={<span className="band__count">{user.persona.label}</span>}
        compact
      />

      <section className="panel">
        <h2 className="panel__title">Profile</h2>
        <dl className="kv">
          <dt>Name</dt>
          <dd>{user.display_name}</dd>
          <dt>Job title</dt>
          <dd>{user.job_title || NOT_PROVIDED}</dd>
          <dt>Department</dt>
          <dd>{user.department || NOT_PROVIDED}</dd>
          <dt>Business unit</dt>
          <dd>{user.business_unit || NOT_PROVIDED}</dd>
          <dt>Location</dt>
          <dd>{user.location || NOT_PROVIDED}</dd>
          <dt>Manager</dt>
          <dd>{user.manager || NOT_PROVIDED}</dd>
          <dt>Nexus access</dt>
          <dd>{user.is_admin ? 'Hub administrator' : 'Employee'}</dd>
          <dt>Employee ID</dt>
          <dd>{user.id}</dd>
        </dl>
      </section>

      <section className="panel">
        <h2 className="panel__title">Persona</h2>
        <p className="panel__text">
          <strong>{user.persona.label}</strong>. Derived by Nexus from your directory profile ({user.persona.rule}); it is not stored on
          your profile. It shapes which agents and learning are recommended to you.
        </p>
      </section>

      <Preferences />
    </div>
  )
}

export function NotFound() {
  return (
    <div className="content">
      <Crumbs title="Not found" />
      <PageBand title="We couldn't find that page" lead="The link may be out of date, or you may not have access to it." compact />
      <Link className="mcard__link" to="/">
        Back to home <ArrowRight strokeWidth={2.2} />
      </Link>
    </div>
  )
}
