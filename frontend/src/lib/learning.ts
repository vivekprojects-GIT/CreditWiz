export type ItemType = 'video' | 'course' | 'confluence' | 'guide' | 'documentation' | 'quick-reference' | 'best-practice'
export type LearningStatus = 'not_started' | 'in_progress' | 'completed'

export interface LearningPath {
  id: string
  title: string
  blurb: string
}

export interface Item {
  id: string
  title: string
  type: ItemType
  description: string
  topics: string[]
  capabilities: string[]
  personas: string[]
  required_for: string[]
  path: string
  level: string
  duration_seconds: number
  tags: string[]
  related_agents: string[]
  url: string
  youtube_id: string
  poster_url: string
  source: string
  body: string
  status: LearningStatus
  progress: number
  required: boolean
}

export interface ItemDetail extends Item {
  path_title: string
  related_items: Item[]
  related_agent_names: Record<string, string>
}

export interface Section {
  id: string
  title: string
  subtitle: string
  items: Item[]
}

export interface LearningHome {
  persona: string
  persona_label: string
  paths: LearningPath[]
  sections: Section[]
  item_count: number
}

export interface TopicCoverage {
  topic: string
  completed: number
  total: number
}

export interface MyLearning {
  persona: string
  persona_label: string
  completed: number
  in_progress: number
  not_started: number
  required_total: number
  required_completed: number
  items: Item[]
  coverage: TopicCoverage[]
  proficiency_note: string
}

export interface DocPage {
  agent_id: string
  agent_name: string
  title: string
  markdown: string
  source_url: string
}

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' }

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`)
  return (await res.json()) as T
}

export const fetchLearningHome = (persona: string, signal?: AbortSignal) =>
  getJson<LearningHome>(`/api/learning${persona ? `?persona=${encodeURIComponent(persona)}` : ''}`, signal)

export const fetchItems = (params: Record<string, string>, signal?: AbortSignal) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
  return getJson<Item[]>(`/api/learning/items${qs ? `?${qs}` : ''}`, signal)
}

export const fetchItem = (id: string, signal?: AbortSignal) =>
  getJson<ItemDetail>(`/api/learning/items/${encodeURIComponent(id)}`, signal)

export const fetchMyLearning = (signal?: AbortSignal) => getJson<MyLearning>('/api/learning/my-learning', signal)

/** Learning owns this capability; the marketplace agent page only consumes it. */
export const fetchAgentLearning = (agentId: string, persona: string, signal?: AbortSignal) =>
  getJson<Item[]>(
    `/api/learning/for-agent/${encodeURIComponent(agentId)}${persona ? `?persona=${encodeURIComponent(persona)}` : ''}`,
    signal,
  )

/** Learning state, owned by the Learning pillar. Separate from hub footprints. */
export async function recordProgress(item_id: string, status: LearningStatus, progress?: number) {
  const res = await fetch('/api/learning/progress', {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ item_id, status, progress }),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return (await res.json()) as Item
}

export const fetchAgentDocs = (agentId: string, signal?: AbortSignal) =>
  getJson<DocPage>(`/api/marketplace/agents/${encodeURIComponent(agentId)}/docs`, signal)

export const fetchAgentArchitecture = (agentId: string, signal?: AbortSignal) =>
  getJson<DocPage>(`/api/marketplace/agents/${encodeURIComponent(agentId)}/architecture`, signal)

/** Deep link to an item, remembering where the user came from so Back works. */
export function itemHref(itemId: string, fromAgentId?: string) {
  return `/learning/items/${encodeURIComponent(itemId)}${fromAgentId ? `?from=${encodeURIComponent(fromAgentId)}` : ''}`
}

export const TYPE_LABEL: Record<ItemType, string> = {
  video: 'Video',
  course: 'Course',
  confluence: 'Confluence',
  guide: 'Guide',
  documentation: 'Documentation',
  'quick-reference': 'Quick reference',
  'best-practice': 'Best practice',
}

export function duration(seconds: number): string {
  if (!seconds) return ''
  const m = Math.round(seconds / 60)
  if (m < 60) return `${m} min`
  const h = Math.floor(m / 60)
  return `${h}h ${m % 60}m`
}
