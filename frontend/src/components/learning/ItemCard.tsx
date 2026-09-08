import { BookOpen, Check, Clock, FileText, GraduationCap, Layers, ListChecks, PlayCircle, Sparkles } from 'lucide-react'
import type { ComponentType } from 'react'
import { Link } from 'react-router-dom'
import { TYPE_LABEL, duration, itemHref, type Item, type ItemType } from '../../lib/learning'

const ICON: Record<ItemType, ComponentType<{ size?: number; strokeWidth?: number }>> = {
  video: PlayCircle,
  course: GraduationCap,
  confluence: FileText,
  guide: BookOpen,
  documentation: Layers,
  'quick-reference': ListChecks,
  'best-practice': Sparkles,
}

export function ItemCard({ item, fromAgentId, compact }: { item: Item; fromAgentId?: string; compact?: boolean }) {
  const Icon = ICON[item.type] ?? BookOpen
  const isVideo = item.type === 'video'
  const time = duration(item.duration_seconds)

  return (
    <Link to={itemHref(item.id, fromAgentId)} className={`icard icard--${item.type}${compact ? ' icard--compact' : ''}`}>
      {isVideo && item.poster_url ? (
        <div className="icard__thumb">
          <img src={item.poster_url} alt="" loading="lazy" />
          <span className="icard__play">
            <PlayCircle size={compact ? 26 : 32} strokeWidth={1.8} />
          </span>
          {time && <span className="icard__duration">{time}</span>}
          {item.status === 'in_progress' && (
            <span className="icard__bar" aria-label={`${item.progress}% complete`}>
              <span style={{ width: `${item.progress}%` }} />
            </span>
          )}
        </div>
      ) : (
        <div className="icard__cover" aria-hidden="true">
          <Icon size={compact ? 30 : 44} strokeWidth={1.4} />
        </div>
      )}

      <div className="icard__body">
        <span className="icard__meta">
          <span className="icard__type">{TYPE_LABEL[item.type]}</span>
          {item.required && <span className="icard__required">Required</span>}
          {item.status === 'completed' && (
            <span className="icard__done">
              <Check size={12} strokeWidth={3} /> Completed
            </span>
          )}
          {item.status === 'in_progress' && <span className="icard__pct">{item.progress ? `${item.progress}%` : 'Started'}</span>}
        </span>
        <span className="icard__title">
          {item.sequence ? `${item.sequence}. ` : ''}
          {item.title}
        </span>
        {(item.blocked_by?.length > 0 || item.prerequisite_unavailable) && <span className="icard__required">Prerequisite needed</span>}
        {item.recommendation_reason && <span className="icard__desc">{item.recommendation_reason}</span>}
        {!compact && <span className="icard__desc">{item.description}</span>}
        {!isVideo && time && (
          <span className="icard__time">
            <Clock size={12} strokeWidth={2.4} /> {time}
          </span>
        )}
      </div>
    </Link>
  )
}
