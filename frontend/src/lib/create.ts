import { createContext, useContext } from 'react'
import type { Draft } from './prompts'

/** Where the Create dialog opens. */
export type CreateStart =
  | { kind: 'choose' }
  | { kind: 'prompt'; draft?: Draft; body?: string }
  | { kind: 'video' }
  | { kind: 'agent' }
  | { kind: 'templates' }

export interface CreateApi {
  open: (start: CreateStart) => void
}

export const CreateContext = createContext<CreateApi>({ open: () => undefined })

export const useCreate = () => useContext(CreateContext)
