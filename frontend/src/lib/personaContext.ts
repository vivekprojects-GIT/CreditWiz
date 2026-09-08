import { createContext, useContext } from 'react'
import type { PersonaInfo } from './types'
interface PersonaState {
  persona: string
  derived: PersonaInfo
  isPreview: boolean
  setPreview: (id: string | null) => void
}
export const PersonaContext = createContext<PersonaState | null>(null)
export function usePersona(): PersonaState {
  const ctx = useContext(PersonaContext)
  if (!ctx) throw new Error('usePersona must be used inside PersonaProvider')
  return ctx
}
