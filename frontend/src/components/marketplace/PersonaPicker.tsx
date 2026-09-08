import { ChevronDown, Eye, UserRound } from 'lucide-react'
import type { Persona } from '../../lib/marketplace'
import { usePersona } from '../../lib/persona'

/**
 * Persona badge for the "Recommended for you" row: which persona the row is tuned
 * for, and a demo-only "preview as" control. Profile details live in the account menu.
 */
export function PersonaPreview({ personas }: { personas: Persona[] }) {
  const { persona, derived, isPreview, setPreview } = usePersona()
  const current = personas.find((p) => p.id === persona)

  return (
    <div className={`pbadge${isPreview ? ' is-preview' : ''}`}>
      <span className="pbadge__chip">
        {isPreview ? <Eye size={15} strokeWidth={2.4} /> : <UserRound size={15} strokeWidth={2.4} />}
        <span className="pbadge__label">{isPreview ? 'Previewing as' : 'Your persona'}</span>
        <strong>{current?.label ?? persona}</strong>
      </span>
      {isPreview ? (
        <button type="button" className="pbadge__reset" onClick={() => setPreview(null)}>
          Back to {derived.label}
        </button>
      ) : (
        <label className="pbadge__select">
          <span>Preview as</span>
          <select value="" onChange={(e) => e.target.value && setPreview(e.target.value)} aria-label="Preview recommendations as another persona">
            <option value="">…</option>
            {personas
              .filter((p) => p.id !== derived.id)
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.label}
                </option>
              ))}
          </select>
          <ChevronDown size={14} strokeWidth={2.2} />
        </label>
      )}
    </div>
  )
}
