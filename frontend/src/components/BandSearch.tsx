import { Loader2, Search, Sparkles, X } from 'lucide-react'
import type { RefObject } from 'react'

interface Props {
  value: string
  onChange: (value: string) => void
  /** Runs on submit and when an example is chosen. */
  onSearch: (query: string) => void
  onClear?: () => void
  placeholder: string
  /** What the input is, for screen readers: "Describe what you need". */
  label: string
  /** The button's label: "Find agents", "Search guidance", ... */
  action: string
  examples?: string[]
  busy?: boolean
  inputRef?: RefObject<HTMLInputElement | null>
}

/**
 * The search bar every pillar opens with. What it says and suggests comes from
 * the pillar; what a search does is the page's business, so the same bar can
 * sit on top of the agent engine, the learning catalog, or a planned pillar.
 */
export function BandSearch({
  value,
  onChange,
  onSearch,
  onClear,
  placeholder,
  label,
  action,
  examples = [],
  busy = false,
  inputRef,
}: Props) {
  return (
    <>
      <form
        className={`gsearch${busy ? ' is-busy' : ''}`}
        onSubmit={(e) => {
          e.preventDefault()
          onSearch(value)
        }}
        role="search"
      >
        <Sparkles className="gsearch__icon" size={22} strokeWidth={2.2} aria-hidden="true" />
        <input
          ref={inputRef}
          className="gsearch__input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          aria-label={label}
          autoComplete="off"
        />
        {value && onClear && (
          <button type="button" className="gsearch__clear" aria-label="Clear search" onClick={onClear}>
            <X size={18} strokeWidth={2.4} />
          </button>
        )}
        <button type="submit" className="gsearch__go" disabled={busy || !value.trim()}>
          {busy ? <Loader2 className="spin" size={20} strokeWidth={2.4} /> : <Search size={20} strokeWidth={2.4} />}
          {action}
        </button>
      </form>

      {examples.length > 0 && (
        <div className="examples">
          <span className="examples__label">Try</span>
          {examples.map((q) => (
            <button key={q} type="button" className="examples__chip" onClick={() => onSearch(q)}>
              {q}
            </button>
          ))}
        </div>
      )}
    </>
  )
}
