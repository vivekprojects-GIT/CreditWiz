import { getJson, postJson } from './api'
export type ItemType = 'video' | 'course' | 'confluence' | 'guide' | 'documentation' | 'quick-reference' | 'best-practice'
export type LearningStatus = 'not_started' | 'in_progress' | 'completed'

export interface LearningPath {
  id: string
  title: string
  blurb: string
  steps: string[]
  owner: string
  completed_steps: number
  total_steps: number
  next_item_id: string | null
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
  source_kind: 'sample' | 'enterprise'
  owner: string
  prerequisites: string[]
  recommendation_reason: string
  blocked_by: string[]
  prerequisite_unavailable: boolean
  sequence: number | null
  status: LearningStatus
  progress: number
  required: boolean
  rating_count: number
  /** null until the item clears the minimum rating count; an average of one vote is noise. */
  rating_average: number | null
  /** Shrunk toward the catalogue mean. Not displayed; this is what a future ranker would sort on. */
  rating_weighted: number | null
  my_rating: number | null
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
  role_paths: LearningPath[]
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
  source_kind: 'sample' | 'enterprise'
  agent_id: string
  agent_name: string
  title: string
  markdown: string
  source_url: string
}

export const fetchLearningHome = (persona: string, signal?: AbortSignal) =>
  getJson<LearningHome>(`/api/learning${persona ? `?persona=${encodeURIComponent(persona)}` : ''}`, signal)

export const fetchItems = (params: Record<string, string>, signal?: AbortSignal) => {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
  return getJson<Item[]>(`/api/learning/items${qs ? `?${qs}` : ''}`, signal)
}

export const fetchItem = (id: string, signal?: AbortSignal) => getJson<ItemDetail>(`/api/learning/items/${encodeURIComponent(id)}`, signal)

export const fetchMyLearning = (signal?: AbortSignal) => getJson<MyLearning>('/api/learning/my-learning', signal)

/** Learning owns this capability; the marketplace agent page only consumes it. */
export const fetchAgentLearning = (agentId: string, persona: string, signal?: AbortSignal) =>
  getJson<Item[]>(
    `/api/learning/for-agent/${encodeURIComponent(agentId)}${persona ? `?persona=${encodeURIComponent(persona)}` : ''}`,
    signal,
  )

/** Learning state, owned by the Learning pillar. Separate from hub footprints. */
export async function recordProgress(item_id: string, status: LearningStatus, progress?: number) {
  return postJson<Item>('/api/learning/progress', { item_id, status, progress })
}

/** Rate an item you have opened. Pass null to withdraw your rating. */
export async function rateItem(item_id: string, stars: number | null) {
  return postJson<Item>('/api/learning/ratings', { item_id, stars })
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
