import { ArrowRight } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { fetchItems, PROVIDERS, type Item } from '../../lib/learning'
import { CourseDrawer } from '../learning/CourseDrawer'
import { CourseCard } from '../learning/ProviderShelves'

/** What to pick up next: one course from Pluralsight or Microsoft Learn. */
export function ForYou({ persona }: { persona: string }) {
  const [courses, setCourses] = useState<{ continuing: boolean; items: Item[] } | null>(null)
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    const ctrl = new AbortController()
    // The best course from each provider for this role: what was started first,
    // then what is mapped to the role and not yet done.
    Promise.all(PROVIDERS.map((source) => fetchItems({ source, persona }, ctrl.signal)))
      .then((lists) => {
        const ranked = lists.map((items) =>
          items
            .filter((i) => i.status === 'in_progress' || (i.status === 'not_started' && i.personas.includes(persona)))
            .sort((a, b) => Number(b.status === 'in_progress') - Number(a.status === 'in_progress')),
        )
        // One from each provider where the role has one, then the next best from either.
        const picks = ranked.map((r) => r[0]).filter((i): i is Item => !!i)
        for (const extra of ranked.flatMap((r) => r.slice(1))) {
          if (picks.length >= 2) break
          picks.push(extra)
        }
        setCourses({ continuing: picks.some((i) => i.status === 'in_progress'), items: picks })
      })
      .catch((e: unknown) => {
        if (!isAbort(e)) setCourses({ continuing: false, items: [] })
      })
    return () => ctrl.abort()
  }, [persona, open])

  return (
    <section className="foryou" aria-labelledby="foryou-title">
      <h2 className="home-work__title" id="foryou-title">
        For you
      </h2>
      <div className="foryou__grid">
        <div className="panel foryou__card">
          <div className="home-card__head">
            <h3 className="home-card__title">{courses?.continuing ? 'Continue learning' : 'Recommended for your role'}</h3>
            <Link to="/learning" className="textlink">
              Learning <ArrowRight size={14} strokeWidth={2.2} />
            </Link>
          </div>
          {!courses ? (
            <div className="skeleton" style={{ height: 120 }} />
          ) : courses.items.length ? (
            <div className="foryou__courses">
              {courses.items.map((i) => (
                <CourseCard key={i.id} item={i} onOpen={setOpen} />
              ))}
            </div>
          ) : (
            <p className="muted">You're up to date.</p>
          )}
        </div>

      </div>
      <CourseDrawer itemId={open} onClose={() => setOpen(null)} />
    </section>
  )
}
