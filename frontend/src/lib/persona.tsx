import { useMemo, useState, type ReactNode } from 'react'
import type { PersonaInfo } from './types'
import { PersonaContext } from './personaContext'
export function PersonaProvider({ derived, children }: { derived: PersonaInfo; children: ReactNode }) {
  const [preview, setPreview] = useState<string | null>(null)
  const value = useMemo(
    () => ({ persona: preview ?? derived.id, derived, isPreview: preview !== null && preview !== derived.id, setPreview }),
    [preview, derived],
  )
  return <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>
}
