import { render, screen, within } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { HubContext } from '../../lib/hub'
import { PersonaProvider } from '../../lib/persona'
import type { HomeData, PersonaInfo } from '../../lib/types'
import { AgentDetailPage } from './AgentDetailPage'

const persona = { id: 'business_user', label: 'Business user', rule: 'role', derived_from: 'role' } as PersonaInfo
const hub = { user: { is_admin: false }, pillars: [] } as unknown as HomeData
const response = (body: unknown) =>
  new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })

const agent = {
  id: 'contract-analyzer',
  name: 'Contract Analyzer',
  tagline: 'Summarises contracts.',
  version: '3.0',
  description: 'Reads contracts.',
  problem_solved: '',
  business_domains: ['Legal'],
  use_cases: [],
  capabilities: [],
  services: [],
  example_tasks: [],
  personas: [],
  category: 'Document Intelligence',
  owner: { team: 'Legal Technology', name: '', email: '' },
  status: 'production',
  platform: '',
  tools_services: [],
  models: [],
  architecture_pattern: '',
  access: { type: 'open', how: 'Open to all.', launch_url: '', request_url: '' },
  documentation_url: '',
  architecture_url: '',
  documents: [
    {
      type: 'hld',
      system: 'confluence',
      url: 'https://confluence.example/contract-analyzer/hld',
      description: 'Components, integrations and data flows of the Contract Analyzer.',
    },
  ],
  tags: [],
  featured: false,
  popularity: 0,
  created_at: '2026-01-01',
  updated_at: '2026-07-14',
  source_kind: 'sample',
}

const sources = {
  systems: [
    { id: 'confluence', name: 'Confluence', kind: 'wiki', feeds: '', owner: '', location: '', connection: 'not_connected' },
  ],
  document_types: [
    { id: 'brd', abbreviation: 'BRD', name: 'Business Requirements Document', about: 'The business need and scope.', feeds: '', lives_in: [], owner: '' },
    { id: 'hld', abbreviation: 'HLD', name: 'High-level design', about: 'The architecture.', feeds: '', lives_in: [], owner: '' },
  ],
  link_groups: [],
}

describe('agent documentation', () => {
  it('lists each document with what it covers, where it lives and a link to open it there', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = String(input)
      if (url.includes('/api/knowledge/sources')) return response(sources)
      if (url.includes('/related') || url.includes('/for-agent/')) return response([])
      if (url.includes('/api/marketplace/agents/contract-analyzer')) return response(agent)
      return response({ ok: true, id: 'event' })
    })
    render(
      <MemoryRouter initialEntries={['/marketplace/agents/contract-analyzer']}>
        <HubContext.Provider value={hub}>
          <PersonaProvider derived={persona}>
            <Routes>
              <Route path="/marketplace/agents/:id" element={<AgentDetailPage />} />
            </Routes>
          </PersonaProvider>
        </HubContext.Provider>
      </MemoryRouter>,
    )

    const table = await screen.findByRole('table')
    const [, brd, hld] = within(table).getAllByRole('row')

    // A given link opens where the document lives, in a new tab, described in the owner's words.
    const open = within(hld).getByRole('link', { name: /Open in Confluence/ })
    expect(open.getAttribute('href')).toBe('https://confluence.example/contract-analyzer/hld')
    expect(open.getAttribute('target')).toBe('_blank')
    expect(within(hld).getByText('Components, integrations and data flows of the Contract Analyzer.')).toBeTruthy()

    // A document with no link yet is still described, and says its link is to be confirmed.
    expect(within(brd).getByText('The business need and scope.')).toBeTruthy()
    expect(within(brd).getByText('Link to be confirmed')).toBeTruthy()
    expect(within(brd).queryByRole('link')).toBeNull()
  })
})
