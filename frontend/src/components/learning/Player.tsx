import { ExternalLink, Play } from 'lucide-react'
import { useState } from 'react'
import type { Item } from '../../lib/learning'

/**
 * Click-to-play facade.
 *
 * The YouTube iframe is only mounted after the user clicks, so the page loads
 * without third-party scripts. It also degrades honestly: if the embed is blocked
 * (corporate network, extension, third-party cookie policy) the viewer still sees
 * the poster and a working link out, instead of a black box.
 */
export function Player({ item, onProgress }: { item: Item; onProgress?: (pct: number) => void }) {
  const [playing, setPlaying] = useState(false)
  const [failed, setFailed] = useState(false)
  const watchUrl = item.youtube_id ? `https://www.youtube.com/watch?v=${item.youtube_id}` : item.url

  if (!item.youtube_id) {
    return (
      <div className="player">
        <video
          controls
          preload="metadata"
          poster={item.poster_url || undefined}
          src={item.url}
          onTimeUpdate={(e) => {
            const el = e.currentTarget
            if (el.duration) onProgress?.(Math.min(99, Math.round((el.currentTime / el.duration) * 100)))
          }}
        >
          Your browser does not support video playback.
        </video>
      </div>
    )
  }

  if (playing && !failed) {
    return (
      <div className="player">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${item.youtube_id}?rel=0&autoplay=1`}
          title={item.title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; fullscreen"
          allowFullScreen
          onError={() => setFailed(true)}
        />
      </div>
    )
  }

  return (
    <div className="player player--facade">
      {item.poster_url && <img className="player__poster" src={item.poster_url} alt="" />}
      <button
        type="button"
        className="player__play"
        onClick={() => {
          setPlaying(true)
          // opening the player counts as meaningful engagement
          onProgress?.(15)
        }}
        aria-label={`Play ${item.title}`}
      >
        <span className="player__play-icon">
          <Play size={30} strokeWidth={2} fill="currentColor" />
        </span>
        <span className="player__play-label">Play video</span>
      </button>
      {failed && (
        <div className="player__blocked" role="alert">
          <p>This embed could not load. It may be blocked on this network.</p>
          <a className="btn btn--inline" href={watchUrl} target="_blank" rel="noreferrer">
            Open on YouTube <ExternalLink size={15} strokeWidth={2.4} />
          </a>
        </div>
      )}
    </div>
  )
}
