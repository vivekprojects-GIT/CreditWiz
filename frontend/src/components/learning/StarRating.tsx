import { Star } from 'lucide-react'
import { useState } from 'react'

const STARS = [1, 2, 3, 4, 5]

/**
 * Read-only summary of what learners think of an item.
 *
 * Deliberately shows the count rather than only an average: on a catalogue this
 * size "4.7" means something very different from 4 votes than from 400. Below
 * the display threshold the backend sends a null average and we say so.
 */
export function RatingSummary({ average, count }: { average: number | null; count: number }) {
  // == null catches an absent field as well as an explicit null: an older API
  // response must render as "no ratings", never crash the card it sits in.
  if (!count) return null
  if (average == null) {
    return (
      <span className="rating rating--thin" title={`${count} rating${count === 1 ? '' : 's'} so far`}>
        <Star size={13} strokeWidth={2} />
        {count} rating{count === 1 ? '' : 's'}
      </span>
    )
  }
  return (
    <span className="rating" title={`Average of ${count} ratings`}>
      <Star size={13} strokeWidth={2} fill="currentColor" />
      <strong>{average.toFixed(1)}</strong>
      <span className="rating__n">({count})</span>
    </span>
  )
}

/** The learner's own rating. Clicking the star you already chose withdraws it. */
export function RatingInput({
  value,
  disabled,
  onRate,
}: {
  value: number | null
  disabled?: boolean
  onRate: (stars: number | null) => void
}) {
  const [hover, setHover] = useState<number | null>(null)
  const shown = hover ?? value ?? 0

  return (
    <div className="starinput" onMouseLeave={() => setHover(null)}>
      {STARS.map((n) => (
        <button
          key={n}
          type="button"
          disabled={disabled}
          className={`starinput__btn${n <= shown ? ' is-on' : ''}`}
          onMouseEnter={() => setHover(n)}
          onFocus={() => setHover(n)}
          onBlur={() => setHover(null)}
          onClick={() => onRate(value === n ? null : n)}
          aria-label={`${n} star${n === 1 ? '' : 's'}`}
          aria-pressed={value === n}
        >
          <Star size={22} strokeWidth={1.8} fill={n <= shown ? 'currentColor' : 'none'} />
        </button>
      ))}
    </div>
  )
}
