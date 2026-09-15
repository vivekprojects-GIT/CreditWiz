import { Pause, Play } from 'lucide-react'
import { useEffect, useState, type ReactNode } from 'react'

export interface HeroLine {
  /** Headline; an <em> inside is set in brand red. */
  h: ReactNode
  s: string
}

const ROTATE_MS = 8000

function reducedMotion() {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function'
    ? window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false
}

/**
 * The home headline, rotating through a few lines. Every line is rendered in
 * the same grid cell, so the block is as tall as the tallest and nothing below
 * it moves as the copy changes. Rotation stops on hover or focus, when the
 * reader pauses it, and entirely for anyone who asks for reduced motion.
 */
export function HeroRotator({ lines }: { lines: HeroLine[] }) {
  const [index, setIndex] = useState(0)
  const [paused, setPaused] = useState(false)
  const [held, setHeld] = useState(false)
  const [still] = useState(reducedMotion)

  useEffect(() => {
    if (paused || held || still || lines.length < 2) return
    const timer = setInterval(() => setIndex((i) => (i + 1) % lines.length), ROTATE_MS)
    return () => clearInterval(timer)
  }, [paused, held, still, lines.length])

  return (
    <div
      className="home-hero"
      onMouseEnter={() => setHeld(true)}
      onMouseLeave={() => setHeld(false)}
      onFocus={() => setHeld(true)}
      onBlur={() => setHeld(false)}
    >
      <div className="home-hero__slides">
        {lines.map((line, i) => (
          <div key={i} className="home-hero__slide" aria-hidden={i !== index}>
            <h1 className="home-hero__title">{line.h}</h1>
            <p className="home-hero__sub">{line.s}</p>
          </div>
        ))}
      </div>
      {lines.length > 1 && (
        <div className="home-hero__dots" role="group" aria-label="Headline rotation">
          {lines.map((_, i) => (
            <button
              key={i}
              type="button"
              className="home-hero__dot"
              aria-current={i === index}
              aria-label={`Show message ${i + 1} of ${lines.length}`}
              onClick={() => setIndex(i)}
            />
          ))}
          {!still && (
            <button
              type="button"
              className="home-hero__pause"
              aria-pressed={paused}
              aria-label={paused ? 'Resume rotating messages' : 'Pause rotating messages'}
              title={paused ? 'Resume' : 'Pause'}
              onClick={() => setPaused((p) => !p)}
            >
              {paused ? <Play size={14} strokeWidth={2.4} /> : <Pause size={14} strokeWidth={2.4} />}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
