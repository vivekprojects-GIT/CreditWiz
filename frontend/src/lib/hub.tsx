import { createContext, useContext } from 'react'
import type { HomeData } from './types'

export const HubContext = createContext<HomeData | null>(null)

export function useHub(): HomeData {
  const ctx = useContext(HubContext)
  if (!ctx) throw new Error('useHub must be used inside HubContext')
  return ctx
}
