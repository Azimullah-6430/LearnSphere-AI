import { Card, PageHead } from '../components/ui/Primitives.jsx'

const NOTES = [
  { text: 'Your Physics evaluation is ready', when: '2 hours ago' },
  { text: 'New study technique recommended: Spaced Repetition', when: 'Yesterday' },
  { text: 'Weekly progress summary sent to parent', when: '3 days ago' },
]

export default function Notifications() {
  return (
    <>
      <PageHead title="Notifications" subtitle="Updates from your evaluations and classes." />
      <Card>
        {NOTES.map((n, i) => (
          <div key={i} className="flex gap-3 py-[11px] border-b border-[var(--border)] last:border-0 last:pb-0 first:pt-0">
            <div className="w-[7px] h-[7px] rounded-full bg-[var(--accent)] mt-1.5 shrink-0" />
            <div>
              <div className="text-[13.5px] font-semibold">{n.text}</div>
              <div className="text-xs text-[var(--text-faint)] mt-0.5">{n.when}</div>
            </div>
          </div>
        ))}
      </Card>
    </>
  )
}
