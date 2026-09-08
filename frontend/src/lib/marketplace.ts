export type AgentStatus = 'production' | 'pilot' | 'beta' | 'in_development' | 'deprecated'
export type AccessType = 'open' | 'request' | 'restricted'

export interface Agent {
  id: string
  name: string
  tagline: string
  version: string
  description: string
  problem_solved: string
  business_domains: string[]
  use_cases: string[]
  capabilities: string[]
  services: string[]
  example_tasks: string[]
  personas: string[]
  category: string
  owner: { team: string; name: string; email: string }
  status: AgentStatus
  platform: string
  tools_services: string[]
  models: string[]
  architecture_pattern: string
  access: { type: AccessType; how: string; launch_url: string; request_url: string }
  documentation_url: string
  architecture_url: string
  tags: string[]
  featured: boolean
  popularity: number
  created_at: string
  updated_at: string
}

export interface Persona {
  id: string
  label: string
  description: string
  interests: { domains: string[]; capabilities: string[]; tags: string[] }
}

export interface Carousel {
  id: string
  title: string
  subtitle: string
  agents: Agent[]
}

export interface MarketplaceHome {
  persona: string
  personas: Persona[]
  domains: string[]
  carousels: Carousel[]
  agent_count: number
  example_queries: string[]
}

export interface SearchIntent {
  summary: string
  concepts: string[]
  domains: string[]
  capabilities: string[]
  keywords: string[]
}

export interface AgentMatch {
  agent: Agent
  score: number
  why: string
  reasons: string[]
}

export interface SearchResponse {
  query: string
  intent: SearchIntent
  engine: 'claude' | 'local'
  results: AgentMatch[]
  no_match: boolean
  next_steps: { label: string; href: string }[]
}

// Footprints and feedback live in the shared hub layer: see lib/context.ts

const JSON_HEADERS = { 'Content-Type': 'application/json', Accept: 'application/json' }

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`)
  return (await res.json()) as T
}

async function postJson<T>(url: string, body: unknown, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { method: 'POST', headers: JSON_HEADERS, body: JSON.stringify(body), signal })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`)
  return (await res.json()) as T
}

export function fetchMarketplaceHome(persona: string, signal?: AbortSignal) {
  const qs = persona ? `?persona=${encodeURIComponent(persona)}` : ''
  return getJson<MarketplaceHome>(`/api/marketplace/home${qs}`, signal)
}

export function fetchAgents(params: Record<string, string>, signal?: AbortSignal) {
  const qs = new URLSearchParams(Object.entries(params).filter(([, v]) => v)).toString()
  return getJson<Agent[]>(`/api/marketplace/agents${qs ? `?${qs}` : ''}`, signal)
}

export function fetchAgent(id: string, signal?: AbortSignal) {
  return getJson<Agent>(`/api/marketplace/agents/${encodeURIComponent(id)}`, signal)
}

export function fetchRelated(id: string, signal?: AbortSignal) {
  return getJson<Agent[]>(`/api/marketplace/agents/${encodeURIComponent(id)}/related`, signal)
}

export function searchAgents(query: string, persona: string, domain: string, signal?: AbortSignal) {
  return postJson<SearchResponse>(
    '/api/marketplace/search',
    { query, persona: persona || null, domain: domain || null, limit: 6 },
    signal,
  )
}

export const STATUS_LABEL: Record<AgentStatus, string> = {
  production: 'Production',
  pilot: 'Pilot',
  beta: 'Beta',
  in_development: 'In development',
  deprecated: 'Deprecated',
}

export const ACCESS_LABEL: Record<AccessType, string> = {
  open: 'Open to all employees',
  request: 'Request access',
  restricted: 'Restricted',
}
