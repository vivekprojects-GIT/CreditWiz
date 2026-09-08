import { ArrowLeft } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

interface Props {
  /** Where to go when there is no in-app history (deep link, new tab). */
  fallback: string
  label?: string
}

/**
 * Behaves like a real Back: returns to the previous in-app page (search results keep
 * their query because it lives in the URL), or to `fallback` when the user landed here directly.
 */
export function BackButton({ fallback, label = 'Back' }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const hasHistory = typeof window !== 'undefined' && window.history.state?.idx > 0

  return (
    <button
      type="button"
      className="backbtn"
      onClick={() => (hasHistory ? navigate(-1) : navigate(fallback, { replace: true, state: location.state }))}
    >
      <ArrowLeft size={16} strokeWidth={2.4} />
      {label}
    </button>
  )
}
