import { useHub } from '../../lib/hub'
import { ChevronDown, Eye } from 'lucide-react'
import type { Persona } from '../../lib/marketplace'
import { usePersona } from '../../lib/personaContext'

/**
 * The demo-only "preview as" control on the "Recommended for you" row, for admins.
 * Nobody is shown their own persona: it is how Nexus tunes the row, not something to read.
 */
export function PersonaPreview({ personas }: { personas: Persona[] }) {
  const { user } = useHub()
  const { persona, derived, isPreview, setPreview } = usePersona()
  const current = personas.find((p) => p.id === persona)
  if (!user.is_admin) return null

  return (
    <div className={`pbadge${isPreview ? ' is-preview' : ''}`}>
      {isPreview && (
        <span className="pbadge__chip">
          <Eye size={15} strokeWidth={2.2} />
          <span className="pbadge__label">Previewing as</span>
          <strong>{current?.label ?? persona}</strong>
        </span>
      )}
      {(isPreview ? (
          <button type="button" className="pbadge__reset" onClick={() => setPreview(null)}>
            Back to {derived.label}
          </button>
        ) : (
          <label className="pbadge__select">
            <span>Preview as</span>
            <select
              value=""
              onChange={(e) => e.target.value && setPreview(e.target.value)}
              aria-label="Preview recommendations as another persona"
            >
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
        ))}
      {isPreview && (
        <span className="muted">Preview affects recommendations only; your permissions and learning account stay the same.</span>
      )}
    </div>
  )
}
