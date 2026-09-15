import { getJson } from './api'

export type NodeKind = 'person' | 'external' | 'channel' | 'agent' | 'model' | 'tool' | 'store'

export interface ArchNode {
  id: string
  label: string
  detail: string
  kind: NodeKind
  highlight: boolean
}

export interface ArchGroup {
  label: string
  nodes: ArchNode[]
}

export interface ArchColumn {
  id: string
  label: string
  sublabel: string
  groups: ArchGroup[]
}

export interface ArchEdge {
  source: string
  target: string
  step: number | null
  dashed: boolean
}

export interface ArchBandItem {
  label: string
  detail: string
}

export interface ArchitecturePage {
  agent_id: string
  agent_name: string
  title: string
  pattern: string
  status: string
  owner: string
  team: string
  version: string
  updated: string
  summary: string
  confirmed: boolean
  columns: ArchColumn[]
  edges: ArchEdge[]
  band: ArchBandItem[]
  steps: { number: number; title: string; detail: string }[]
  components: { name: string; type: string; responsibility: string }[]
  principles: string[]
  related: { id: string; name: string }[]
  source_kind: string
}

export const fetchArchitecture = (agentId: string, signal?: AbortSignal) =>
  getJson<ArchitecturePage>(`/api/marketplace/agents/${encodeURIComponent(agentId)}/architecture`, signal)
