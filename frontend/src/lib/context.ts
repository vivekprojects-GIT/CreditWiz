/**
 * Shared AI Hub user-context client.
 *
 *   ALL PILLARS -> track()/sendFeedback() -> /api/context/*  -> shared footprint store
 *
 * No pillar owns this. Marketplace, Learning and every future pillar call the
 * same functions so one user context is assembled across the hub.
 */

export type Pillar =
  | 'marketplace'
  | 'prompts'
  | 'learning'
  | 'intake'
  | 'governance'
  | 'knowledge'
  | 'community'
  | 'insights'
  | 'platform'
  | 'hub'

export type EventType =
  | 'search'
  | 'view'
  | 'click'
  | 'launch'
  | 'request_access'
  | 'documentation_click'
  | 'architecture_click'
  | 'collaborate'
  | 'learning_view'
  | 'learning_complete'
  | 'feedback_positive'
  | 'feedback_negative'

export interface InterestSignal {
  topic: string
  weight: number
  events: number
  pillars: string[]
}

export interface UserContext {
  user_id: string
  display_name: string
  job_title: string
  department: string
  business_unit: string
  persona: string
  persona_label: string
  persona_rule: string
  interests: InterestSignal[]
  event_count: number
  pillars_seen: string[]
}

interface TrackPayload {
  subject_id?: string
  subject_type?: string
  query?: string
  persona?: string
  topics?: string[]
  meta?: Record<string, unknown>
}

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' }

/** Fire-and-forget footprint. Never throws, never blocks the UI. */
export function track(pillar: Pillar, type: EventType, data: TrackPayload = {}) {
  try {
    const body = JSON.stringify({ pillar, type, ...data })
    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/context/events', new Blob([body], { type: 'application/json' }))
    } else {
      void fetch('/api/context/events', { method: 'POST', headers: JSON_HEADERS, body, keepalive: true }).catch(() => {})
    }
  } catch {
    /* footprints are best-effort */
  }
}

export async function sendFeedback(body: {
  pillar: Pillar
  context: string
  helpful: boolean
  subject_id?: string
  query?: string
  persona?: string
  missing?: string
}) {
  const res = await fetch('/api/context/feedback', { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body) })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as { ok: boolean; id: string }
}

export async function fetchUserContext(signal?: AbortSignal) {
  const res = await fetch('/api/context/me', { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as UserContext
}
