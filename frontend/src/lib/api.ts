import type { HomeData, Notification, Pillar, SearchResult } from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}
export async function requestJson<T>(url: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(url, {
    ...init,
    credentials: 'same-origin',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CreditWiz-Request': '1', ...init.headers },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    if (res.status === 401 && !url.startsWith('/api/auth/')) window.dispatchEvent(new Event('creditwiz:signed-out'))
    throw new ApiError(res.status, typeof body?.detail === 'string' ? body.detail : `Request failed (${res.status}). Please try again.`)
  }
  return res.json() as Promise<T>
}
export const getJson = <T>(url: string, signal?: AbortSignal) => requestJson<T>(url, { signal })
export const postJson = <T>(url: string, body: unknown, signal?: AbortSignal) =>
  requestJson<T>(url, { method: 'POST', body: JSON.stringify(body), signal })
export const fetchHome = (signal?: AbortSignal) => getJson<HomeData>('/api/home', signal)
export const fetchPillar = (id: string, signal?: AbortSignal) => getJson<Pillar>(`/api/pillars/${encodeURIComponent(id)}`, signal)
export const fetchNotifications = (signal?: AbortSignal) => getJson<Notification[]>('/api/notifications', signal)
export async function searchHub(q: string, signal?: AbortSignal) {
  return (await getJson<{ results: SearchResult[] }>(`/api/search?q=${encodeURIComponent(q)}`, signal)).results
}
export function isAbort(err: unknown) {
  return (err as { name?: string } | null)?.name === 'AbortError'
}
export interface Preferences {
  default_domain: string
  show_learning_reminders: boolean
}
export const fetchPreferences = (signal?: AbortSignal) => getJson<Preferences>('/api/preferences', signal)

/** Notify other tabs that the shared cookie has changed accounts. */
export function announceSessionChange() {
  try {
    localStorage.setItem('creditwiz.session-change', crypto.randomUUID())
  } catch {
    /* storage may be unavailable */
  }
}
