import {
  AlertCircle,
  ArrowRight,
  Bot,
  Check,
  Clapperboard,
  LayoutTemplate,
  Loader2,
  MessageSquareText,
  ShieldCheck,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { isAbort } from '../../lib/api'
import { CreateContext, type CreateStart } from '../../lib/create'
import {
  AUDIENCE_LABEL,
  KIND_NAME,
  fetchMyDeskLibrary,
  fetchTemplates,
  submitContribution,
  type Contribution,
  type LibraryPage,
  type Relation,
  type Risk,
  type Safety,
  type Submission,
  type Template,
} from '../../lib/prompts'

type Screen =
  | { name: 'choose' }
  | { name: 'prompt'; step: 1 | 2 | 3 }
  | { name: 'templates'; back: 'prompt' | 'choose' | 'none' }
  | { name: 'video' }
  | { name: 'agent' }
  | { name: 'done'; result: Contribution }

interface PromptForm {
  title: string
  description: string
  category: string
  tags: string
  scope: Relation
  body: string
  inputs: string
  hours: string
  safety: Safety
  guidelines: string
  tested: boolean
  learnedFrom: string[]
}

interface Proposal {
  title: string
  description: string
  recording: string
  chain: string[]
}

const blankPrompt = (): PromptForm => ({
  title: '',
  description: '',
  category: '',
  tags: '',
  scope: 'team',
  body: '',
  inputs: '',
  hours: '',
  safety: { client_data: false, mnpi: false, feeds_control: false },
  guidelines: '',
  tested: false,
  learnedFrom: [],
})
const blankProposal = (): Proposal => ({ title: '', description: '', recording: '', chain: [] })

const SAFETY_QUESTIONS: [keyof Safety, string][] = [
  ['client_data', 'Does this prompt process client-identifying data?'],
  ['mnpi', 'Does it handle material non-public information?'],
  ['feeds_control', 'Does its output feed a control or decision system?'],
]

const PICKS: [CreateStart['kind'], LucideIcon, string, string][] = [
  ['prompt', MessageSquareText, 'Prompt', 'A validated template your desk can reuse'],
  ['video', Clapperboard, 'Skill video', 'A short walkthrough of how you work'],
  ['agent', Bot, 'AI agent', 'Chain validated prompts into one workflow'],
  ['templates', LayoutTemplate, 'Prompt template', 'Start from a scaffold that already passes review'],
]

const MAX_CHAIN = 8

/** The same rule the server applies to a declaration. */
function impliedRisk(s: Safety): Risk {
  if (s.mnpi || s.feeds_control) return 'High'
  return s.client_data ? 'Medium' : 'Low'
}

const listOf = (text: string, sep: RegExp, max: number) =>
  text
    .split(sep)
    .map((s) => s.trim())
    .filter(Boolean)
    .slice(0, max)

function Steps({ labels, at }: { labels: string[]; at: number }) {
  return (
    <ol className="steps" aria-label="Progress">
      {labels.map((label, i) => (
        <li key={label} className={i < at ? 'is-done' : i === at ? 'is-on' : undefined} aria-current={i === at ? 'step' : undefined}>
          <i>{i < at ? <Check size={13} strokeWidth={3} aria-hidden="true" /> : i + 1}</i>
          {label}
        </li>
      ))}
    </ol>
  )
}

function FieldError({ children }: { children: ReactNode }) {
  return (
    <span className="field__err" role="alert">
      <AlertCircle size={14} strokeWidth={2.4} aria-hidden="true" /> {children}
    </span>
  )
}

/**
 * Create, as the design reference has it: choose what to make, then a
 * three-step prompt (basics, the prompt itself, a data safety declaration),
 * a skill video, or an agent proposal. Everything submitted waits for review;
 * nothing goes live from here.
 */
export function CreateProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const dialog = useRef<HTMLDialogElement>(null)
  const [screen, setScreen] = useState<Screen | null>(null)
  const [form, setForm] = useState<PromptForm>(blankPrompt)
  const [proposal, setProposal] = useState<Proposal>(blankProposal)
  const [library, setLibrary] = useState<LibraryPage | null>(null)
  const [templates, setTemplates] = useState<Template[] | null>(null)
  const [loadError, setLoadError] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [checked, setChecked] = useState(false)

  const open = useCallback((start: CreateStart) => {
    setError('')
    setChecked(false)
    if (start.kind === 'prompt') {
      const d = start.draft
      setForm({
        ...blankPrompt(),
        ...(d && {
          title: d.title,
          description: d.description,
          category: d.category,
          tags: d.tags.join(', '),
          body: d.body,
          learnedFrom: d.learned_from.map((s) => s.id),
        }),
        ...(start.body && { body: start.body }),
      })
      setScreen({ name: 'prompt', step: 1 })
    } else if (start.kind === 'video' || start.kind === 'agent') {
      setProposal(blankProposal())
      setScreen(start.kind === 'video' ? { name: 'video' } : { name: 'agent' })
    } else if (start.kind === 'templates') {
      setScreen({ name: 'templates', back: 'none' })
    } else {
      setScreen({ name: 'choose' })
    }
  }, [])
  const close = useCallback(() => setScreen(null), [])
  const api = useMemo(() => ({ open }), [open])

  // The categories, the desk's prompts and the templates, loaded once.
  const opened = screen !== null
  useEffect(() => {
    if (!opened || (library && templates)) return
    const ctrl = new AbortController()
    Promise.all([fetchMyDeskLibrary(ctrl.signal), fetchTemplates(ctrl.signal)])
      .then(([lib, t]) => {
        setLibrary(lib)
        setTemplates(t)
        setLoadError('')
      })
      .catch((e: unknown) => {
        if (!isAbort(e)) setLoadError('The prompt library could not load. Close this and try again.')
      })
    return () => ctrl.abort()
  }, [opened, library, templates])

  useEffect(() => {
    const el = dialog.current
    if (!el) return
    if (opened && !el.open) {
      if (typeof el.showModal === 'function') el.showModal()
      else el.setAttribute('open', '')
    } else if (!opened && el.open) {
      if (typeof el.close === 'function') el.close()
      else el.removeAttribute('open')
    }
  }, [opened])

  async function submit(body: Submission) {
    setBusy(true)
    setError('')
    try {
      const result = await submitContribution(body)
      setScreen({ name: 'done', result })
      // My library, if it is open, lists what was just submitted.
      window.dispatchEvent(new CustomEvent('creditwiz:contributed'))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not submit. Try again.')
    } finally {
      setBusy(false)
    }
  }

  const set = <K extends keyof PromptForm>(key: K, value: PromptForm[K]) => setForm((f) => ({ ...f, [key]: value }))
  const category = form.category || library?.categories[0] || ''
  const ready = library !== null && templates !== null

  function view(): { title: string; body: ReactNode; foot: ReactNode } {
    if (!screen) return { title: '', body: null, foot: null }
    const cancel = (
      <button type="button" className="btn-outline" onClick={close}>
        Cancel
      </button>
    )

    if (screen.name === 'choose')
      return {
        title: 'What would you like to create?',
        body: (
          <>
            <p className="dialog__lead">
              Everything you submit is reviewed by the Data Privacy Office before it goes live.
            </p>
            <div className="picks">
              {PICKS.map(([kind, Icon, title, text]) => (
                <button
                  key={kind}
                  type="button"
                  className="pick"
                  onClick={() => (kind === 'templates' ? setScreen({ name: 'templates', back: 'choose' }) : open({ kind } as CreateStart))}
                >
                  <span className="pick__icon" aria-hidden="true">
                    <Icon size={20} strokeWidth={2} />
                  </span>
                  <span>
                    <b>{title}</b>
                    <span className="pick__text">{text}</span>
                  </span>
                </button>
              ))}
            </div>
          </>
        ),
        foot: cancel,
      }

    if (screen.name === 'templates')
      return {
        title: 'Prompt templates',
        body: (
          <>
            <p className="dialog__lead">
              Four scaffolds cover most banking work. Each already carries the constraints that get prompts through
              validation.
            </p>
            {templates?.map((t) => (
              <div key={t.id} className="tpl">
                <span className="pick__icon" aria-hidden="true">
                  <LayoutTemplate size={18} strokeWidth={2} />
                </span>
                <div className="tpl__body">
                  <b>{t.name}</b>
                  <div className="muted">{t.use}</div>
                  <div className="tpl__when">Used for: {t.when}</div>
                </div>
                <button
                  type="button"
                  className="btn-outline"
                  onClick={() => {
                    if (screen.back === 'prompt') {
                      set('body', t.body)
                      setScreen({ name: 'prompt', step: 2 })
                    } else {
                      setForm({ ...blankPrompt(), body: t.body })
                      setScreen({ name: 'prompt', step: 1 })
                    }
                  }}
                >
                  Use this
                </button>
              </div>
            )) ?? <div className="skeleton" style={{ height: 240 }} />}
          </>
        ),
        foot:
          screen.back === 'none' ? (
            cancel
          ) : (
            <button
              type="button"
              className="btn-outline"
              onClick={() => setScreen(screen.back === 'prompt' ? { name: 'prompt', step: 2 } : { name: 'choose' })}
            >
              Back
            </button>
          ),
      }

    if (screen.name === 'prompt') {
      const bar = <Steps labels={['Basics', 'Prompt', 'Safety']} at={screen.step - 1} />
      if (screen.step === 1) {
        const missing = checked && !form.title.trim()
        return {
          title: 'Create a prompt',
          body: (
            <>
              {bar}
              <div className={`field${missing ? ' field--invalid' : ''}`}>
                <label htmlFor="c-title">Title</label>
                <input
                  id="c-title"
                  type="text"
                  value={form.title}
                  maxLength={120}
                  placeholder="e.g. Deal screening summary"
                  aria-invalid={missing}
                  onChange={(e) => set('title', e.target.value)}
                  autoFocus
                />
                <span className="field__hint">Name it for the job it does, not the model it uses.</span>
                {missing && <FieldError>Give the prompt a title.</FieldError>}
              </div>
              <div className="field">
                <label htmlFor="c-desc">Description</label>
                <textarea
                  id="c-desc"
                  value={form.description}
                  maxLength={600}
                  placeholder="One sentence on what it takes in and what it returns."
                  onChange={(e) => set('description', e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="c-cat">Category</label>
                <select id="c-cat" value={category} onChange={(e) => set('category', e.target.value)}>
                  {library?.categories.map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label htmlFor="c-tags">Tags</label>
                <input
                  id="c-tags"
                  type="text"
                  value={form.tags}
                  placeholder="Comma separated, 2 to 5 tags"
                  onChange={(e) => set('tags', e.target.value)}
                />
                <span className="field__hint">Tags are how colleagues find this in search.</span>
              </div>
              <div className="field">
                <label htmlFor="c-scope">Who made it</label>
                <select id="c-scope" value={form.scope} onChange={(e) => set('scope', e.target.value as Relation)}>
                  <option value="team">My team</option>
                  <option value="dept">My department</option>
                  <option value="other">Another desk</option>
                </select>
              </div>
            </>
          ),
          foot: (
            <>
              {cancel}
              <button
                type="button"
                className="btn btn--inline"
                onClick={() => {
                  setChecked(true)
                  if (form.title.trim()) {
                    setChecked(false)
                    setScreen({ name: 'prompt', step: 2 })
                  }
                }}
              >
                Continue <ArrowRight size={16} strokeWidth={2.4} />
              </button>
            </>
          ),
        }
      }
      if (screen.step === 2)
        return {
          title: 'Create a prompt',
          body: (
            <>
              {bar}
              <div className="dialog__row">
                <h3 className="dialog__subtitle">Write the prompt</h3>
                <button type="button" className="btn-outline" onClick={() => setScreen({ name: 'templates', back: 'prompt' })}>
                  <LayoutTemplate size={15} strokeWidth={2.2} /> Start from a template
                </button>
              </div>
              <div className="field">
                <label htmlFor="c-body">Prompt text</label>
                <textarea
                  id="c-body"
                  className="field__code"
                  value={form.body || templates?.[0]?.body || ''}
                  onChange={(e) => set('body', e.target.value)}
                />
                <span className="field__hint">
                  Wrap anything the user must supply in double braces, like {'{{CLIENT NAME}}'}. Those become fillable fields.
                </span>
              </div>
              <div className="field">
                <label htmlFor="c-inputs">Inputs needed</label>
                <input
                  id="c-inputs"
                  type="text"
                  value={form.inputs}
                  placeholder="e.g. Annual report (attachment), Facility size (text)"
                  onChange={(e) => set('inputs', e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="c-hours">Time saved per use, in hours</label>
                <input
                  id="c-hours"
                  type="text"
                  inputMode="decimal"
                  value={form.hours}
                  placeholder="e.g. 4"
                  onChange={(e) => set('hours', e.target.value)}
                />
              </div>
            </>
          ),
          foot: (
            <>
              <button type="button" className="btn-outline" onClick={() => setScreen({ name: 'prompt', step: 1 })}>
                Back
              </button>
              <button
                type="button"
                className="btn btn--inline"
                onClick={() => {
                  if (!form.body) set('body', templates?.[0]?.body ?? '')
                  setScreen({ name: 'prompt', step: 3 })
                }}
              >
                Continue <ArrowRight size={16} strokeWidth={2.4} />
              </button>
            </>
          ),
        }
      const untested = checked && !form.tested
      const risk = impliedRisk(form.safety)
      const hours = Number(form.hours)
      return {
        title: 'Create a prompt',
        body: (
          <>
            {bar}
            <h3 className="dialog__subtitle">Data safety declaration</h3>
            <p className="dialog__lead">
              The Data Privacy Office reviews every prompt within two working days. Answering accurately speeds that up.
            </p>
            {SAFETY_QUESTIONS.map(([key, question]) => (
              <div key={key} className="yn" role="group" aria-label={question}>
                <span className="yn__q">{question}</span>
                <span className="yn__opts">
                  <button
                    type="button"
                    className="is-yes"
                    aria-pressed={form.safety[key]}
                    onClick={() => set('safety', { ...form.safety, [key]: true })}
                  >
                    Yes
                  </button>
                  <button
                    type="button"
                    aria-pressed={!form.safety[key]}
                    onClick={() => set('safety', { ...form.safety, [key]: false })}
                  >
                    No
                  </button>
                </span>
              </div>
            ))}
            <p className="implied" aria-live="polite">
              <ShieldCheck size={15} strokeWidth={2.2} aria-hidden="true" /> These answers mean a{' '}
              <span className={`risk risk--${risk.toLowerCase()}`}>{risk} risk</span> rating on the library&rsquo;s scale.
            </p>
            <div className="field">
              <label htmlFor="c-guide">Usage guidelines</label>
              <textarea
                id="c-guide"
                value={form.guidelines}
                placeholder="One rule per line. What must a colleague check before trusting the output?"
                onChange={(e) => set('guidelines', e.target.value)}
              />
            </div>
            <label className={`check${untested ? ' check--invalid' : ''}`}>
              <input type="checkbox" checked={form.tested} onChange={(e) => set('tested', e.target.checked)} />
              <span>I have tested this prompt at least three times and the guidelines reflect what I found.</span>
            </label>
            {untested && <FieldError>Confirm you have tested the prompt.</FieldError>}
          </>
        ),
        foot: (
          <>
            <button type="button" className="btn-outline" onClick={() => setScreen({ name: 'prompt', step: 2 })}>
              Back
            </button>
            <button
              type="button"
              className="btn btn--inline"
              disabled={busy || !ready}
              onClick={() => {
                setChecked(true)
                if (!form.tested || !ready) return
                void submit({
                  kind: 'prompt',
                  title: form.title.trim(),
                  description: form.description.trim(),
                  category,
                  tags: listOf(form.tags, /,/, 5),
                  scope: form.scope,
                  body: (form.body || templates[0]?.body || '').trim(),
                  inputs: listOf(form.inputs, /,/, 12),
                  hours_saved: form.hours.trim() && Number.isFinite(hours) ? Math.min(Math.max(hours, 0), 100) : null,
                  safety: form.safety,
                  guidelines: listOf(form.guidelines, /\n/, 12),
                  tested: true,
                  learned_from: form.learnedFrom,
                })
              }}
            >
              {busy && <Loader2 className="spin" size={16} aria-hidden="true" />} Submit for validation
            </button>
          </>
        ),
      }
    }

    if (screen.name === 'video' || screen.name === 'agent') {
      const isVideo = screen.name === 'video'
      const missingTitle = checked && !proposal.title.trim()
      const missingChain = checked && !isVideo && proposal.chain.length === 0
      const prompts = library?.prompts ?? []
      const toggle = (id: string) =>
        setProposal((p) => ({
          ...p,
          chain: p.chain.includes(id) ? p.chain.filter((c) => c !== id) : [...p.chain, id].slice(0, MAX_CHAIN),
        }))
      return {
        title: isVideo ? 'Add a skill video' : 'Propose an AI agent',
        body: (
          <>
            <Steps labels={['Details', 'Review', 'Published']} at={0} />
            <div className={`field${missingTitle ? ' field--invalid' : ''}`}>
              <label htmlFor="p-title">Title</label>
              <input
                id="p-title"
                type="text"
                value={proposal.title}
                maxLength={120}
                placeholder={isVideo ? 'e.g. Structuring an RFP response in 8 minutes' : 'e.g. End-to-end credit application assistant'}
                onChange={(e) => setProposal((p) => ({ ...p, title: e.target.value }))}
                autoFocus
              />
              {missingTitle && <FieldError>Give it a title.</FieldError>}
            </div>
            <div className="field">
              <label htmlFor="p-desc">What will people learn or get?</label>
              <textarea
                id="p-desc"
                value={proposal.description}
                maxLength={600}
                onChange={(e) => setProposal((p) => ({ ...p, description: e.target.value }))}
              />
            </div>
            {isVideo ? (
              <div className="field">
                <label htmlFor="p-file">Recording</label>
                <input
                  id="p-file"
                  type="file"
                  accept="video/mp4,video/*"
                  onChange={(e) => setProposal((p) => ({ ...p, recording: e.target.files?.[0]?.name ?? '' }))}
                />
                <span className="field__hint">MP4, up to 500 MB. This prototype keeps the file name only; nothing is uploaded.</span>
              </div>
            ) : (
              <div className={`field${missingChain ? ' field--invalid' : ''}`}>
                <span className="field__label" id="p-chain">
                  Validated prompts to chain, in the order they run
                </span>
                <ul className="chainlist" aria-labelledby="p-chain">
                  {prompts.map((p) => {
                    const at = proposal.chain.indexOf(p.id)
                    return (
                      <li key={p.id}>
                        <label>
                          <input type="checkbox" checked={at >= 0} onChange={() => toggle(p.id)} />
                          <span>{p.title}</span>
                          {at >= 0 && <span className="chainlist__n">Step {at + 1}</span>}
                        </label>
                      </li>
                    )
                  })}
                </ul>
                {missingChain && <FieldError>Pick at least one prompt to chain.</FieldError>}
              </div>
            )}
            <p className="infonote">
              {isVideo
                ? 'The Data Privacy Office reviews it before it goes live.'
                : 'Agents need Model Risk approval before they run. Expect a two-week review.'}
            </p>
          </>
        ),
        foot: (
          <>
            {cancel}
            <button
              type="button"
              className="btn btn--inline"
              disabled={busy || !ready}
              onClick={() => {
                setChecked(true)
                if (!proposal.title.trim() || (!isVideo && !proposal.chain.length)) return
                void submit(
                  isVideo
                    ? { kind: 'video', title: proposal.title.trim(), description: proposal.description.trim(), recording: proposal.recording }
                    : { kind: 'agent', title: proposal.title.trim(), description: proposal.description.trim(), chain: proposal.chain },
                )
              }}
            >
              {busy && <Loader2 className="spin" size={16} aria-hidden="true" />} Submit for review
            </button>
          </>
        ),
      }
    }

    const r = screen.result
    return {
      title: r.kind === 'prompt' ? 'Submitted for validation' : 'Submitted for review',
      body: (
        <div className="done">
          <span className="done__icon" aria-hidden="true">
            <Check size={30} strokeWidth={2.6} />
          </span>
          <h3>{r.title} is in the queue</h3>
          <p>{r.review}</p>
          <p>
            It is in search now, for you. Once approved, {AUDIENCE_LABEL[r.audience]} can find it too.
          </p>
          {r.risk && (
            <p className="done__risk">
              Your declaration means a <span className={`risk risk--${r.risk.toLowerCase()}`}>{r.risk} risk</span> rating.
            </p>
          )}
        </div>
      ),
      foot: (
        <>
          <button
            type="button"
            className="btn-outline"
            onClick={() => {
              close()
              navigate('/library/mine')
            }}
          >
            See it in My library
          </button>
          <button type="button" className="btn btn--inline" onClick={close}>
            Done
          </button>
        </>
      ),
    }
  }

  const v = view()
  return (
    <CreateContext.Provider value={api}>
      {children}
      <dialog
        ref={dialog}
        className="dialog"
        aria-labelledby="create-title"
        onClose={close}
        onClick={(e) => {
          if (e.target === dialog.current) close()
        }}
      >
        {screen && (
          <>
            <header className="dialog__head">
              <h2 className="dialog__title" id="create-title">
                {v.title}
              </h2>
              {screen.name !== 'done' && screen.name !== 'choose' && (
                <span className="dialog__kind">
                  {screen.name === 'templates' ? 'Template' : KIND_NAME[screen.name === 'prompt' ? 'prompt' : screen.name]}
                </span>
              )}
              <button type="button" className="dialog__close" onClick={close} aria-label="Close">
                <X size={18} strokeWidth={2.4} />
              </button>
            </header>
            <div className="dialog__body">
              {loadError && (
                <p className="state state--error" role="alert">
                  {loadError}
                </p>
              )}
              {v.body}
              {error && (
                <p className="state state--error" role="alert">
                  {error}
                </p>
              )}
            </div>
            <footer className="dialog__foot">{v.foot}</footer>
          </>
        )}
      </dialog>
    </CreateContext.Provider>
  )
}
