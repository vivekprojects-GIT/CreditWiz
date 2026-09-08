import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react'
import type { PersonaInfo } from './types'

const KEY = 'creditwiz.persona.preview'

interface PersonaState {
  /** Persona in effect: the preview override if set, else the derived one. */
  persona: string
  /** Persona the hub derived from the directory profile. */
  derived: PersonaInfo
  /** True when a demo preview override is active. */
  isPreview: boolean
  /** Set a preview persona, or null to return to the derived persona. */
  setPreview: (id: string | null) => void
}

const PersonaContext = createContext<PersonaState | null>(null)

function readStored(): string | null {
  try {
    return localStorage.getItem(KEY)
  } catch {
    return null
  }
}

export function PersonaProvider({ derived, children }: { derived: PersonaInfo; children: ReactNode }) {
  const [preview, setPreviewState] = useState<string | null>(readStored)
  const setPreview = useCallback((id: string | null) => {
    setPreviewState(id)
    try {
      if (id) localStorage.setItem(KEY, id)
      else localStorage.removeItem(KEY)
    } catch {
      /* ignore */
    }
  }, [])
  const value = useMemo<PersonaState>(
    () => ({ persona: preview ?? derived.id, derived, isPreview: preview !== null && preview !== derived.id, setPreview }),
    [preview, derived, setPreview],
  )
  return <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>
}

export function usePersona(): PersonaState {
  const ctx = useContext(PersonaContext)
  if (!ctx) throw new Error('usePersona must be used inside PersonaProvider')
  return ctx
}
