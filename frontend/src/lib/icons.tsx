import {
  BarChart3,
  ClipboardCheck,
  Database,
  FileText,
  GraduationCap,
  Search,
  Settings,
  ShieldCheck,
  Users,
  type LucideProps,
} from 'lucide-react'
import type { ComponentType } from 'react'
import type { PillarIcon } from './types'

const ICONS: Record<PillarIcon, ComponentType<LucideProps>> = {
  search: Search,
  library: FileText,
  graduation: GraduationCap,
  clipboard: ClipboardCheck,
  shield: ShieldCheck,
  database: Database,
  users: Users,
  chart: BarChart3,
  settings: Settings,
}

export function PillarGlyph({ icon, ...props }: { icon: PillarIcon } & LucideProps) {
  const Icon = ICONS[icon] ?? Search
  return <Icon {...props} />
}
