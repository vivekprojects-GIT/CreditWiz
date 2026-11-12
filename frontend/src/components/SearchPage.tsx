import { ArrowRight, ChevronRight } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { isAbort, searchHub } from '../lib/api'
import { fetchItems, type Item } from '../lib/learning'
import type { SearchResult } from '../lib/types'
import { BandSearch } from './BandSearch'
import { PageBand } from './PageBand'
import { ItemCard } from './learning/ItemCard'
import { ProviderSearch } from './learning/ProviderSearch'
import '../search.css'

const SHOWN = 6

/** What one part of the search answered, for the words it was asked. */
type Answer<T> = { q: string; value: T } | { q: string; error: string }

function load<T>(q: string, run: Promise<T>, set: (answer: Answer<T>) => void) {
  run
    .then((value) => set({ q, value }))
    .catch((e: unknown) => {
      if (!isAbort(e)) set({ q, error: e instanceof Error ? e.message : 'This part of the search did not answer.' })
    })
}

/** Each part loads and fails on its own, so a slow provider never holds up the rest. */
function Part<T>({ answer, children }: { answer: Answer<T> | null; children: (value: T) => ReactNode }) {
  if (!answer) return <div className="skeleton" style={{ height: 120 }} />
  if ('error' in answer)
    return (
      <p className="psearch__note" role="alert">
        {answer.error}
      </p>
    )
  return <>{children(answer.value)}</>
}

/**
 * Search across Nexus: one query, every pillar's answer. Agents from Discover,
 * learning from its catalog and live from Pluralsight and Microsoft Learn.
 */
export function SearchPage() {
  const [params, setParams] = useSearchParams()
  const q = (params.get('q') ?? '').trim()
  const [draft, setDraft] = useState(q)
  useEffect(() => setDraft(q), [q])

  const [hub, setHub] = useState<Answer<SearchResult[]> | null>(null)
  const [items, setItems] = useState<Answer<Item[]> | null>(null)

  useEffect(() => {
    if (!q) return
    const ctrl = new AbortController()
    load(q, searchHub(q, ctrl.signal), setHub)
    load(q, fetchItems({ q }, ctrl.signal), setItems)
    return () => ctrl.abort()
  }, [q])

  const current = <T,>(answer: Answer<T> | null) => (answer?.q === q ? answer : null)
  const learning = current(items)
  const encoded = encodeURIComponent(q)

  return (
    <div className="content">
      <nav className="crumbs" aria-label="Breadcrumb">
        <Link to="/">Home</Link>
        <ChevronRight size={16} />
        <span>Search</span>
      </nav>
      <PageBand compact kicker="Search across Nexus" title={q ? `Results for “${q}”` : 'Search across Nexus'}>
        <BandSearch
          value={draft}
          onChange={setDraft}
          onSearch={(value) => value.trim() && setParams({ q: value.trim() })}
          onClear={() => setDraft('')}
          placeholder="Agents and courses"
          label="Search Nexus"
          action="Search"
        />
      </PageBand>

      {!q ? (
        <div className="state">Search for an agent or a course.</div>
      ) : (
        <>
          <div className="hsearch__top">
            <section className="psearch__group" aria-labelledby="hsearch-agents">
              <div className="hsearch__head">
                <h2 className="hsearch__title" id="hsearch-agents">
                  Agents
                </h2>
                <Link to={`/marketplace?q=${encoded}`} className="textlink">
                  Marketplace <ArrowRight size={14} strokeWidth={2.2} />
                </Link>
              </div>
              <Part answer={current(hub)}>
                {(results) => {
                  const found = results.filter((r) => r.kind !== 'learning')
                  return found.length ? (
                    <ul className="psearch__list">
                      {found.map((r) => (
                        <li key={r.href}>
                          <Link to={r.href} className="hsearch__hit">
                            <span className={`search__kind search__kind--${r.kind}`}>{r.kind}</span>
                            <span>{r.title}</span>
                          </Link>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="psearch__note">No agents match “{q}”. The marketplace can take a request for one.</p>
                  )
                }}
              </Part>
            </section>

          </div>

          <section aria-labelledby="hsearch-learning">
            <div className="hsearch__head">
              <h2 className="section-title" id="hsearch-learning">
                Learning in the Nexus catalog
              </h2>
              <Link to={`/learning/catalog?q=${encoded}`} className="textlink">
                {learning && 'value' in learning && learning.value.length > SHOWN ? `See all ${learning.value.length}` : 'Learning'}{' '}
                <ArrowRight size={14} strokeWidth={2.2} />
              </Link>
            </div>
            <Part answer={learning}>
              {(found) =>
                found.length ? (
                  <div className="item-grid">
                    {found.slice(0, SHOWN).map((i) => (
                      <ItemCard key={i.id} item={i} />
                    ))}
                  </div>
                ) : (
                  <div className="state">Nothing in Nexus's catalog matches “{q}”.</div>
                )
              }
            </Part>
            <ProviderSearch q={q} source="" catalog={learning && 'value' in learning ? learning.value : []} />
          </section>
        </>
      )}
    </div>
  )
}
