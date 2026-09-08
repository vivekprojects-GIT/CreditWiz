import { useEffect, useState } from 'react'
import { getJson, isAbort, postJson } from '../../lib/api'
import { track } from '../../lib/context'
export function AccessRequestForm({ agentId }: { agentId: string }) {
  const [reason, setReason] = useState('')
  const [sent, setSent] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    const ctrl = new AbortController()
    getJson<{ agent_id: string }[]>('/api/access-requests', ctrl.signal)
      .then((rows) => setSent(rows.some((r) => r.agent_id === agentId)))
      .catch((e) => {
        if (!isAbort(e)) setError('Could not check existing requests.')
      })
    return () => ctrl.abort()
  }, [agentId])
  async function submit() {
    setBusy(true)
    setError('')
    try {
      await postJson('/api/access-requests', { agent_id: agentId, reason: reason.trim() })
      setSent(true)
      track('marketplace', 'request_access', { subject_id: agentId })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save request')
    } finally {
      setBusy(false)
    }
  }
  return (
    <section className="panel" id="request-access">
      <h2 className="panel__title">Request access</h2>
      <p>
        Record a request for this MVP. This saves a pending request in your profile; enterprise approval and provisioning are not connected.
      </p>
      {error && <p role="alert">{error}</p>}
      {sent ? (
        <p role="status">Your request is saved and pending review. See it in Settings.</p>
      ) : (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            void submit()
          }}
        >
          <label className="field">
            Business reason
            <textarea required minLength={10} maxLength={2000} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <button className="btn btn--inline" disabled={busy || reason.trim().length < 10}>
            {busy ? 'Saving…' : 'Save access request'}
          </button>
        </form>
      )}
    </section>
  )
}
