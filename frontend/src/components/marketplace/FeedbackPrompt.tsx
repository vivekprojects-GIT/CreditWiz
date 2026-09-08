import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { useEffect, useState } from 'react'
import { sendFeedback, track, type Pillar } from '../../lib/context'
import { usePersona } from '../../lib/persona'

interface Props {
  /** Which pillar is asking. Feedback is stored hub-wide, not per pillar. */
  pillar: Pillar
  /** Where in that pillar: search, agent, video … */
  context: string
  query?: string
  subjectId?: string
  /** Changing this resets the prompt (e.g. a new search). */
  resetKey?: string
  question?: string
}

type Stage = 'ask' | 'missing' | 'done'

export function FeedbackPrompt({ pillar, context, query, subjectId, resetKey, question }: Props) {
  const { persona } = usePersona()
  const [stage, setStage] = useState<Stage>('ask')
  const [missing, setMissing] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    setStage('ask')
    setMissing('')
  }, [resetKey])

  async function submit(helpful: boolean, missingText?: string) {
    setBusy(true)
    try {
      await sendFeedback({ pillar, context, helpful, query, subject_id: subjectId, persona, missing: missingText || undefined })
      track(pillar, helpful ? 'feedback_positive' : 'feedback_negative', { subject_id: subjectId, query, persona, meta: { context } })
    } catch {
      /* feedback is best-effort */
    } finally {
      setBusy(false)
    }
  }

  if (stage === 'done') {
    return (
      <div className="feedback feedback--done" role="status">
        Thanks. Your feedback helps us improve the hub.
      </div>
    )
  }

  if (stage === 'missing') {
    return (
      <form
        className="feedback"
        onSubmit={(e) => {
          e.preventDefault()
          void submit(false, missing.trim()).then(() => setStage('done'))
        }}
      >
        <label className="feedback__label" htmlFor={`fb-missing-${pillar}-${context}`}>
          Tell us what was missing
        </label>
        <div className="feedback__row">
          <input
            id={`fb-missing-${pillar}-${context}`}
            className="feedback__input"
            value={missing}
            onChange={(e) => setMissing(e.target.value)}
            placeholder="e.g. I need an agent for payroll queries"
            maxLength={2000}
            autoFocus
          />
          <button type="submit" className="btn btn--inline" disabled={busy}>
            Send
          </button>
          <button type="button" className="feedback__skip" onClick={() => void submit(false).then(() => setStage('done'))}>
            Skip
          </button>
        </div>
      </form>
    )
  }

  return (
    <div className="feedback">
      <span className="feedback__q">{question ?? 'Did you find what you needed?'}</span>
      <div className="feedback__row">
        <button type="button" className="feedback__btn" disabled={busy} onClick={() => void submit(true).then(() => setStage('done'))}>
          <ThumbsUp size={16} strokeWidth={2.4} /> Yes
        </button>
        <button type="button" className="feedback__btn" disabled={busy} onClick={() => setStage('missing')}>
          <ThumbsDown size={16} strokeWidth={2.4} /> No
        </button>
      </div>
    </div>
  )
}
