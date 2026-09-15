import {
  Bot,
  ChartColumn,
  ChevronRight,
  Database,
  GraduationCap,
  Layers,
  Lightbulb,
  MessageSquareText,
  ShieldCheck,
  UserRound,
  Users,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { track } from '../../lib/context'
import { formatDate } from '../../lib/format'
import { KIND_LABEL, type AssetCard } from '../../lib/journeys'

const TBC = 'To be confirmed'

export const KIND_ICON: Record<string, LucideIcon> = {
  agent: Bot,
  learning: GraduationCap,
  system: Database,
  data_product: ChartColumn,
  prompt: MessageSquareText,
  expert: UserRound,
  community: Users,
  use_case: Lightbulb,
}

function Value({ children }: { children: ReactNode }) {
  return children ? <>{children}</> : <span className="is-tbc">{TBC}</span>
}

/**
 * What helps with a job, one row per asset, each carrying its trust card:
 * owner, purpose, approval, who may use it, how to get it, guardrails and
 * where feedback goes. Anything the owning team has not confirmed says so.
 *
 * `cards` sets each asset as a bordered card with its kind's icon, for the
 * home conversation; `rows` is the plain list the journey page uses.
 */
export function AssetList({
  assets,
  journeyId,
  variant = 'rows',
  onOpen,
}: {
  assets: AssetCard[]
  journeyId: string
  variant?: 'rows' | 'cards'
  /** Told which asset was opened, e.g. for the answer that recommended it. */
  onOpen?: (ref: string) => void
}) {
  return (
    <ul className={`assets${variant === 'cards' ? ' assets--cards' : ''}`}>
      {assets.map((a) => (
        <AssetRow key={a.ref} asset={a} journeyId={journeyId} withIcon={variant === 'cards'} onOpen={onOpen} />
      ))}
    </ul>
  )
}

function AssetRow({
  asset,
  journeyId,
  withIcon,
  onOpen,
}: {
  asset: AssetCard
  journeyId: string
  withIcon: boolean
  onOpen?: (ref: string) => void
}) {
  const owner = [asset.trust.owner_name, asset.trust.owner_team].filter(Boolean).join(', ')
  const agentId = asset.kind === 'agent' ? asset.ref.split(':')[1] : ''
  const Icon = KIND_ICON[asset.kind] ?? Layers
  const opened = () => {
    onOpen?.(asset.ref)
    track('hub', 'click', {
      subject_id: asset.ref,
      subject_type: asset.kind,
      meta: { journey: journeyId, intent: asset.intent },
    })
  }

  return (
    <li className="asset">
      {withIcon && (
        <span className={`asset__icon asset__icon--${asset.kind}`} aria-hidden="true">
          <Icon size={18} strokeWidth={2.2} />
        </span>
      )}
      <div className="asset__main">
        <div className="asset__meta">
          <span className={`asset__kind asset__kind--${asset.kind}`}>{KIND_LABEL[asset.kind] ?? asset.kind}</span>
          {asset.status && <span className="asset__status">{asset.status}</span>}
          {asset.source_kind === 'sample' && <span className="asset__sample">Sample</span>}
        </div>
        <h3 className="asset__title">{asset.title}</h3>
        <p className="asset__why">{asset.why}</p>
        <p className="asset__facts">
          {asset.provided_by && (
            <span>
              Work happens in <strong>{asset.provided_by}</strong>
            </span>
          )}
          <span>
            Owner <strong>{owner || TBC}</strong>
          </span>
        </p>
      </div>

      <div className="asset__action">
        {!asset.action_url ? (
          <span className="asset__pending">Link to be confirmed</span>
        ) : asset.action_url.startsWith('/') ? (
          <Link className="btn-outline" to={asset.action_url} onClick={opened}>
            {asset.action_label}
          </Link>
        ) : (
          <a className="btn-outline" href={asset.action_url} target="_blank" rel="noreferrer" onClick={opened}>
            {asset.action_label}
          </a>
        )}
      </div>

      <details className="asset__trust">
        <summary>
          <ChevronRight className="asset__chev" size={16} strokeWidth={2.4} aria-hidden="true" />
          <ShieldCheck size={16} strokeWidth={2.2} aria-hidden="true" /> Trust and access
        </summary>
        <dl className="trust">
          <dt>Owner</dt>
          <dd>
            <Value>{owner}</Value>
          </dd>
          <dt>Purpose</dt>
          <dd>
            <Value>{asset.trust.purpose}</Value>
          </dd>
          <dt>Approved by</dt>
          <dd>
            <Value>{asset.trust.approved_by}</Value>
          </dd>
          <dt>Approved on</dt>
          <dd>
            <Value>{asset.trust.approved_on && formatDate(asset.trust.approved_on)}</Value>
          </dd>
          <dt>Who can use it</dt>
          <dd>
            <Value>{asset.trust.who_can_use}</Value>
          </dd>
          <dt>How to get access</dt>
          <dd>
            <Value>{asset.trust.how_to_access}</Value>
          </dd>
          <dt>Guardrails</dt>
          <dd>
            {asset.trust.guardrails.length ? (
              <ul>
                {asset.trust.guardrails.map((g) => (
                  <li key={g}>{g}</li>
                ))}
              </ul>
            ) : agentId ? (
              <Link to={`/marketplace/agents/${agentId}/docs#limitations-and-guardrails`}>
                Limitations and guardrails in its documentation
              </Link>
            ) : (
              <span className="is-tbc">{TBC}</span>
            )}
          </dd>
          <dt>Feedback</dt>
          <dd>
            <Value>{asset.trust.feedback}</Value>
          </dd>
        </dl>
      </details>
    </li>
  )
}
