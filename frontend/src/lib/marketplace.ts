import { getJson, postJson } from './api'
export type AgentStatus = 'production' | 'pilot' | 'beta' | 'in_development' | 'deprecated'
export type AccessType = 'open' | 'request' | 'restricted'

/** A link to one of the agent's documents, where the owning team keeps it. */
interface AgentDocument {
  /** What the document is, as the owning team calls it: BRD, HLD, Runbook. */
  label: string
  url: string
  /** What this document covers, in the owning team's words; may be blank. */
  description: string
}

/**
 * Demo setting. Sample agents carry placeholder launch links (agents.mufg.example),
 * which open a page that does not exist. While this is on they count as launchable,
 * so the Launch button can be clicked in a demo. Turn it off once owners have
 * registered real links: only confirmed, non-sample links launch then.
 */
const DEMO_LAUNCH = true

/** The link Launch opens for this agent, or '' when there is none to open. */
export function launchLink(agent: Agent): string {
  if (agent.access.type !== 'open' || !agent.access.launch_url) return ''
  return DEMO_LAUNCH || agent.source_kind !== 'sample' ? agent.access.launch_url : ''
}

export interface Agent {
  source_kind: 'sample' | 'enterprise'
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
  /** Its documents, linked where they live. Nexus keeps no copies. */
  documents: AgentDocument[]
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
}

interface SearchIntent {
  summary: string
  concepts: string[]
  domains: string[]
  capabilities: string[]
  keywords: string[]
}

interface AgentMatch {
  agent: Agent
  score: number
  why: string
  reasons: string[]
  /** Share of the understood request this agent covers, 0-100; null when nothing was extracted. */
  coverage: number | null
}

export interface SearchResponse {
  query: string
  intent: SearchIntent
  results: AgentMatch[]
  no_match: boolean
  next_steps: { label: string; href: string }[]
}

// Footprints and feedback live in the shared hub layer: see lib/context.ts

export function fetchMarketplaceHome(persona: string, signal?: AbortSignal, domain = '') {
  const qs = '?' + new URLSearchParams({ ...(persona ? { persona } : {}), ...(domain && domain !== 'all' ? { domain } : {}) }).toString()
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
  return postJson<SearchResponse>('/api/marketplace/search', { query, persona: persona || null, domain: domain || null, limit: 6 }, signal)
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
