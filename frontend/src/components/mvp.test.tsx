import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { MarketplacePage } from './marketplace/MarketplacePage'
import { FeedbackPrompt } from './marketplace/FeedbackPrompt'
import { LearningPage } from './learning/LearningPage'
import { ItemPage } from './learning/ItemPage'
import { Routes, Route } from 'react-router-dom'
import { PersonaProvider } from '../lib/persona'
import { HubContext } from '../lib/hub'
import type { HomeData, PersonaInfo } from '../lib/types'

const persona = { id: 'business_user', label: 'Business user', rule: 'role', derived_from: 'role' } as PersonaInfo
const hub = { user: { is_admin: false } } as HomeData
function shell(ui: React.ReactNode, path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <HubContext.Provider value={hub}>
        <PersonaProvider derived={persona}>{ui}</PersonaProvider>
      </HubContext.Provider>
    </MemoryRouter>,
  )
}
const response = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
const mkt = { persona: 'business_user', personas: [], domains: [], carousels: [], agent_count: 10, example_queries: [] }
function item(id = 'guide') {
  return {
    id,
    title: 'A useful guide',
    type: 'guide',
    description: 'Read this',
    topics: [],
    tags: [],
    related_agents: [],
    related_agent_names: {},
    related_items: [],
    path: 'business',
    path_title: 'Business',
    status: 'not_started',
    progress: 0,
    required: false,
    prerequisites: [],
    blocked_by: [],
    prerequisite_unavailable: false,
    source_kind: 'sample',
    owner: 'Sample team',
    url: '',
    duration_seconds: 0,
    body: '',
  }
}

describe('MVP user flows', () => {
  it('clearing an in-flight marketplace search aborts it and enables the next query', async () => {
    let searchSignal: AbortSignal | undefined
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (String(input).includes('/search')) {
        searchSignal = init?.signal as AbortSignal
        return new Promise((_resolve, reject) =>
          searchSignal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))),
        )
      }
      return response(mkt)
    })
    shell(<MarketplacePage />, '/marketplace?q=kyc')
    await waitFor(() => expect(searchSignal).toBeDefined())
    fireEvent.click(screen.getByRole('button', { name: 'Clear search' }))
    expect(searchSignal?.aborted).toBe(true)
    fireEvent.change(screen.getByLabelText('Describe what you need'), { target: { value: 'contracts' } })
    expect((screen.getByRole('button', { name: 'Find agents' }) as HTMLButtonElement).disabled).toBe(false)
  })

  it('failed feedback does not show success and can be retried', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValueOnce(response({ detail: 'Save unavailable' }, 503))
      .mockResolvedValue(response({ ok: true, id: 'saved' }))
    shell(<FeedbackPrompt pillar="learning" context="item" />)
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    expect(await screen.findByRole('alert')).toBeTruthy()
    expect(screen.queryByText(/feedback has been saved/)).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Yes' }))
    expect(await screen.findByRole('status')).toBeTruthy()
    expect(fetch.mock.calls[0][1]?.headers).toMatchObject({ 'X-CreditWiz-Request': '1' })
  })

  it('catalog filters fetch the requested type and keep the landing recommendations separate', async () => {
    const calls: string[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      calls.push(String(input))
      return response(
        String(input).includes('/items')
          ? [item()]
          : { persona_label: 'Business user', paths: [], role_paths: [], sections: [], item_count: 1 },
      )
    })
    shell(<LearningPage />, '/learning/catalog')
    await screen.findByText('A useful guide')
    fireEvent.change(screen.getByLabelText('Content type'), { target: { value: 'quick-reference' } })
    await waitFor(() => expect(calls.some((c) => c.includes('type=quick-reference'))).toBe(true))
    expect(screen.queryByText('Paths for Business user')).toBeNull()
  })

  it('prerequisites prevent starting or completing a blocked item', async () => {
    const fetch = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation(async (input) =>
        response(String(input).includes('/items/') ? { ...item(), blocked_by: ['first-guide'] } : { ok: true }),
      )
    shell(
      <Routes>
        <Route path="/learning/items/:id" element={<ItemPage />} />
      </Routes>,
      '/learning/items/guide',
    )
    await screen.findByText('Complete prerequisites first')
    expect((screen.getByRole('button', { name: 'Mark as complete' }) as HTMLButtonElement).disabled).toBe(true)
    expect(fetch.mock.calls.some(([url]) => String(url).includes('/progress'))).toBe(false)
  })

  it('opening a guide records started with zero progress rather than invented completion', async () => {
    const calls: RequestInit[] = []
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      if (String(input).includes('/progress')) {
        calls.push(init!)
        return response({ ...item(), status: 'in_progress' })
      }
      return response(String(input).includes('/items/') ? item() : { ok: true })
    })
    shell(
      <Routes>
        <Route path="/learning/items/:id" element={<ItemPage />} />
      </Routes>,
      '/learning/items/guide',
    )
    await waitFor(() => expect(calls.length).toBe(1))
    expect(JSON.parse(calls[0].body as string)).toMatchObject({ status: 'in_progress', progress: 0 })
  })

  it('an expired session raises the shared sign-out event', async () => {
    const { getJson, ApiError } = await import('../lib/api')
    const expired = vi.fn()
    window.addEventListener('creditwiz:signed-out', expired)
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(response({ detail: 'Sign in' }, 401))
    await act(async () => {
      await expect(getJson('/api/home')).rejects.toBeInstanceOf(ApiError)
    })
    expect(expired).toHaveBeenCalledOnce()
    window.removeEventListener('creditwiz:signed-out', expired)
  })
})
