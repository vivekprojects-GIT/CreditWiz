import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRef, type ReactNode } from 'react'
import type { Carousel as CarouselData } from '../../lib/marketplace'
import { AgentCard } from './AgentCard'

export function Carousel({ data, extra }: { data: CarouselData; extra?: ReactNode }) {
  const trackRef = useRef<HTMLDivElement>(null)

  function scrollBy(dir: 1 | -1) {
    const el = trackRef.current
    if (!el) return
    el.scrollBy({ left: dir * Math.max(320, el.clientWidth * 0.8), behavior: 'smooth' })
  }

  return (
    <section className="carousel" aria-labelledby={`carousel-${data.id}`}>
      <div className="carousel__head">
        <div className="carousel__titles">
          <h2 className="carousel__title" id={`carousel-${data.id}`}>
            {data.title}
          </h2>
          {data.subtitle && <p className="carousel__subtitle">{data.subtitle}</p>}
        </div>
        {extra && <div className="carousel__extra">{extra}</div>}
        <div className="carousel__nav">
          <button type="button" className="carousel__btn" aria-label={`Scroll ${data.title} left`} onClick={() => scrollBy(-1)}>
            <ChevronLeft size={20} strokeWidth={2.4} />
          </button>
          <button type="button" className="carousel__btn" aria-label={`Scroll ${data.title} right`} onClick={() => scrollBy(1)}>
            <ChevronRight size={20} strokeWidth={2.4} />
          </button>
        </div>
      </div>
      <div className="carousel__track" ref={trackRef}>
        {data.agents.map((a) => (
          <div className="carousel__item" key={a.id}>
            <AgentCard agent={a} source={`carousel:${data.id}`} compact hideForYou={data.id === 'recommended'} />
          </div>
        ))}
      </div>
    </section>
  )
}
