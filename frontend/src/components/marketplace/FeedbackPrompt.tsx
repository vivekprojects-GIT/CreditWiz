import { ThumbsDown, ThumbsUp } from 'lucide-react'
import { useState } from 'react'
import { sendFeedback, track, type Pillar } from '../../lib/context'
import { usePersona } from '../../lib/personaContext'
interface Props {
  pillar: Pillar
  context: string
  query?: string
  subjectId?: string
  resetKey?: string
  question?: string
}
export function FeedbackPrompt(props: Props) {
  return <FeedbackForm key={props.resetKey} {...props} />
}
function FeedbackForm({ pillar, context, query, subjectId, question }: Props) {
  const { derived } = usePersona()
  const [stage, setStage] = useState<'ask' | 'missing' | 'done'>('ask')
  const [missing, setMissing] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function submit(helpful: boolean, text?: string) {
    if (busy) return
    setBusy(true)
    setError('')
    try {
      await sendFeedback({ pillar, context, helpful, query, subject_id: subjectId, persona: derived.id, missing: text })
      track(pillar, helpful ? 'feedback_positive' : 'feedback_negative', { subject_id: subjectId, query, meta: { context } })
      setStage('done')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Feedback was not saved. Please retry.')
    } finally {
      setBusy(false)
    }
  }
  if (stage === 'done')
    return (
      <div className="feedback feedback--done" role="status">
        Thanks. Your feedback has been saved.
      </div>
    )
  return (
    <div className="feedback">
      {error && <p role="alert">{error}</p>}
      {stage === 'missing' ? (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void submit(false, missing.trim())
          }}
        >
          <label className="feedback__label" htmlFor={`feedback-${pillar}-${context}`}>
            Tell us what was missing
          </label>
          <div className="feedback__row">
            <input
              id={`feedback-${pillar}-${context}`}
              className="feedback__input"
              value={missing}
              onChange={(e) => setMissing(e.target.value)}
              maxLength={2000}
              placeholder="What would help you?"
            />
            <button className="btn btn--inline" disabled={busy}>
              Send
            </button>
            <button type="button" className="feedback__skip" disabled={busy} onClick={() => void submit(false)}>
              Skip detail
            </button>
          </div>
        </form>
      ) : (
        <>
          <span className="feedback__q">{question ?? 'Did you find what you needed?'}</span>
          <div className="feedback__row">
            <button className="feedback__btn" disabled={busy} onClick={() => void submit(true)}>
              <ThumbsUp size={16} /> Yes
            </button>
            <button className="feedback__btn" disabled={busy} onClick={() => setStage('missing')}>
              <ThumbsDown size={16} /> No
            </button>
          </div>
        </>
      )}
    </div>
  )
}
