export type Tone = 'blue' | 'teal' | 'purple'

export type PillarIcon = 'search' | 'library' | 'graduation' | 'clipboard' | 'shield' | 'database' | 'users' | 'chart' | 'settings'

export interface Link {
  label: string
  href: string
}

export interface Section {
  title: string
  href: string
  blurb: string
}

export interface Pillar {
  id: string
  number: number
  title: string
  short_title: string
  card_title: string
  description: string
  icon: PillarIcon
  tone: Tone
  priority: boolean
  primary_links: Link[]
  secondary_links: Link[]
  cta_label: string
  cta_href: string
  admin_only: boolean
  sections: Section[]
}

export interface PersonaInfo {
  id: string
  label: string
  derived_from: 'role' | 'department' | 'business_unit' | 'default'
  matched_value: string
  rule: string
}

export interface CurrentUser {
  demo_mode: boolean
  id: string
  first_name: string
  display_name: string
  initials: string
  email: string
  job_title: string
  department: string
  business_unit: string
  location: string
  manager: string
  is_admin: boolean
  unread_notifications: number
  persona: PersonaInfo
}

export interface Domain {
  id: string
  name: string
}

export interface HomeData {
  user: CurrentUser
  domains: Domain[]
  pillars: Pillar[]
}

export interface SearchResult {
  kind: 'solution' | 'agent' | 'prompt' | 'learning'
  title: string
  href: string
}

export interface Notification {
  id: string
  title: string
  body: string
  href: string
  created_at: string
  read: boolean
}

/** First path segment a pillar owns, e.g. "/learning" or "/library". */
export function pillarBasePath(p: Pillar): string {
  return '/' + (p.cta_href.split('/')[1] ?? p.id)
}
