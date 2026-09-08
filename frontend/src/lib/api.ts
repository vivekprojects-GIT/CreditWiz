import type { HomeData, Notification, Pillar, SearchResult } from './types'

async function getJson<T>(url: string, signal?: AbortSignal): Promise<T> {
  const res = await fetch(url, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} for ${url}`)
  return (await res.json()) as T
}

export function fetchHome(signal?: AbortSignal) {
  return getJson<HomeData>('/api/home', signal)
}

export function fetchPillar(id: string, signal?: AbortSignal) {
  return getJson<Pillar>(`/api/pillars/${encodeURIComponent(id)}`, signal)
}

export function fetchNotifications(signal?: AbortSignal) {
  return getJson<Notification[]>('/api/notifications', signal)
}

export async function searchHub(q: string, signal?: AbortSignal) {
  const data = await getJson<{ query: string; results: SearchResult[] }>(
    `/api/search?q=${encodeURIComponent(q)}`,
    signal,
  )
  return data.results
}

export function isAbort(err: unknown): boolean {
  return (err as { name?: string } | null)?.name === 'AbortError'
}
