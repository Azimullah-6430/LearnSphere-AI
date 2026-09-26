import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import { Button } from '../components/ui/Primitives.jsx'

export default function NotFound() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center text-center bg-[var(--bg)] px-6">
      <Compass size={34} strokeWidth={1.6} className="text-[var(--text-faint)] mb-5" />
      <h1 className="text-xl font-bold mb-2">We couldn't find that page.</h1>
      <p className="text-[var(--text-soft)] text-sm mb-7 max-w-[360px]">
        The page you're looking for doesn't exist or may have moved.
      </p>
      <Link to="/">
        <Button>Back to sign in</Button>
      </Link>
    </div>
  )
}
