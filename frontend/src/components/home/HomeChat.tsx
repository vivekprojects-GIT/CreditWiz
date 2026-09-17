import { RotateCcw } from 'lucide-react'
import { Fragment, useEffect, useRef, useState, type ReactNode } from 'react'
import { useSearchParams } from 'react-router-dom'
import { track } from '../../lib/context'
import { askHubStream, reduceLive, startLive, type Live } from '../../lib/journeys'
import { AssistantAnswer, type Turn } from './AssistantAnswer'
import { Composer } from './Composer'
const MAX_KEPT = 20

// The conversation survives leaving home for an agent page and coming back.
// Per viewer and per tab only, and gone when the tab closes: it is the task
// context of this session, including any client it names, not a record.
function readThread(key: string): Turn[] {
  try {
    const raw = sessionStorage.getItem(key)
    const turns: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(turns) ? (turns as Turn[]).filter((t) => t && t.status === 'done' && t.ask?.kind) : []
  } catch {
    return []
  }
}

function writeThread(key: string, turns: Turn[]) {
  try {
    sessionStorage.setItem(key, JSON.stringify(turns.filter((t) => t.status === 'done').slice(-MAX_KEPT)))
  } catch {
    /* storage may be unavailable */
  }
}

function readValue(key: string): string {
  try {
    return sessionStorage.getItem(key) ?? ''
  } catch {
    return ''
  }
}

function writeValue(key: string, value: string) {
  try {
    if (value) sessionStorage.setItem(key, value)
    else sessionStorage.removeItem(key)
  } catch {
    /* storage may be unavailable */
  }
}

interface Props {
  storeKey: string
  firstName: string
  initials: string
  persona: string
  personaLabel: string
  examples: string[]
  /** What home shows under the composer before a conversation starts. */
  below: ReactNode
}

/**
 * Home as a conversation. Before the first question: a greeting, the
 * composer and suggestions. After it: a transcript filling the screen, with
 * the composer resting at its foot. Each reply comes from /api/ask, the hub's
 * graph: the job, what every pillar found, and how it was chosen.
 */
export function HomeChat({ storeKey, firstName, initials, persona, personaLabel, examples, below }: Props) {
  const [turns, setTurns] = useState<Turn[]>(() => readThread(storeKey))
  const [draft, setDraft] = useState('')
  const [params, setParams] = useSearchParams()
  const log = useRef<HTMLDivElement>(null)
  const started = useRef(false)
  const nextId = useRef(0)
  // Which conversation this is, for telemetry. Ids only; the server starts one when absent.
  const sessionKey = `${storeKey}.session`
  const session = useRef(readValue(sessionKey))
  const busy = turns.some((t) => t.status === 'loading')
  const talking = turns.length > 0

  useEffect(() => writeThread(storeKey, turns), [storeKey, turns])

  // Bring the latest question to the top of the view, so its answer reads
  // from the start rather than from the foot of a long list.
  const count = turns.length
  useEffect(() => {
    const el = log.current
    const asked = el?.querySelectorAll<HTMLElement>('.msg--me')
    const last = asked?.[asked.length - 1]
    if (!el || !last) return
    const top = el.scrollTop + last.getBoundingClientRect().top - el.getBoundingClientRect().top - 8
    el.scrollTo({ top, behavior: 'smooth' })
  }, [count])

  async function send(text: string) {
    const q = text.trim()
    if (!q || busy) return
    const id = Date.now() + ++nextId.current
    // A follow-up that names no job or client stays on the ones the
    // conversation was on. Session context only: it lives in this thread.
    const earlier = [...turns].reverse()
    const journey = earlier.find((t) => t.ask?.task?.activity)?.ask?.task?.activity?.id
    const subject = earlier.find((t) => t.ask?.task?.subject)?.ask?.task?.subject?.name
    setDraft('')
    setTurns((ts) => [...ts, { id, q, status: 'loading', live: startLive() }])
    // The answer builds on the page event by event, as the hub produces it.
    const update = (fn: (live: Live) => Live) =>
      setTurns((ts) => ts.map((t) => (t.id === id && t.live ? { ...t, live: fn(t.live) } : t)))
    try {
      const ask = await askHubStream(q, persona, { journey, subject, session: session.current }, (e) =>
        update((live) => reduceLive(live, e)),
      )
      session.current = ask.session_id
      writeValue(sessionKey, ask.session_id)
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, status: 'done', ask, live: undefined } : t)))
      // Usage analytics get the server's loggable form: a client name never,
      // and for small talk only what kind it was.
      track('hub', 'search', {
        query: ask.task ? ask.task.loggable_query : `[${ask.kind}]`,
        persona,
        meta: ask.task
          ? {
              surface: 'chat',
              intents: ask.task.intents,
              journey: ask.task.activity?.id ?? null,
              pillars: ask.plan?.selected_pillars ?? [],
              sensitivity: ask.task.sensitivity,
              planned_by: ask.plan?.plan_source ?? null,
            }
          : { surface: 'chat', kind: ask.kind },
      })
    } catch (e: unknown) {
      const error = e instanceof Error ? e.message : 'The hub could not answer just now.'
      setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, status: 'error', error, live: undefined } : t)))
    }
  }

  function rated(id: number, helpful: boolean) {
    setTurns((ts) => ts.map((t) => (t.id === id ? { ...t, helpful } : t)))
  }

  // A link to /?q=... still opens a conversation with that question.
  useEffect(() => {
    const q = params.get('q')
    if (started.current || !q) return
    started.current = true
    setParams({}, { replace: true })
    void send(q)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function reset() {
    setTurns([])
    setDraft('')
    session.current = ''
    writeValue(sessionKey, '')
  }

  return (
    <div className={`content home${talking ? ' home--talking' : ''}`}>
      <section className={`chat${talking ? ' is-talking' : ''}`} aria-label="Ask the AI Hub">
        {talking ? (
          <div className="chat__bar">
            <span className="chat__bar-title">
              Ask the AI Hub
            </span>
            <button type="button" className="chat__new" onClick={reset}>
              <RotateCcw size={15} strokeWidth={2.2} aria-hidden="true" /> New conversation
            </button>
          </div>
        ) : (
          <>
            <h1 className="chat__title">Welcome, {firstName}</h1>
            <p className="chat__sub">
              Describe a task and the hub finds the agents, prompts and learning for it.
            </p>
          </>
        )}

        {talking && (
          <div className="chatlog" ref={log} aria-live="polite">
            {turns.map((t, i) => (
              <Fragment key={t.id}>
                <div className="msg msg--me">
                  <span className="msg__who" aria-hidden="true">
                    {initials}
                  </span>
                  <div className="bubble">{t.q}</div>
                </div>
                <div className="msg msg--ai">
                  <span className="msg__who" aria-hidden="true">
                    AI
                  </span>
                  <div className="bubble">
                    <AssistantAnswer turn={t} latest={i === turns.length - 1} onAsk={send} onRated={rated} />
                  </div>
                </div>
              </Fragment>
            ))}
          </div>
        )}

        <div className={talking ? 'dock' : undefined}>
          <Composer
            value={draft}
            onChange={setDraft}
            onSend={send}
            busy={busy}
            personaLabel={personaLabel}
            placeholder="Describe the task you need help with"
            autoFocus={talking}
          />
          {!talking && (
            <div className="suggests" role="group" aria-label="Try asking">
              {examples.map((q) => (
                <button key={q} type="button" className="suggest" onClick={() => send(q)}>
                  {q}
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      {!talking && <div className="home-below">{below}</div>}
    </div>
  )
}
