import { useState, useEffect } from 'react'
import { Card, CardHeader, PageHead, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { BookOpen } from 'lucide-react'

export default function Memory() {
  const { user } = useApp()
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadMemory() {
      setLoading(true)
      const res = await api.getMemoryCards(user?.name)
      if (res && res.success && Array.isArray(res.cards)) {
        setCards(res.cards)
      } else {
        setCards([])
      }
      setLoading(false)
    }
    loadMemory()
  }, [user])

  const hasData = cards.length > 0

  return (
    <>
      <PageHead title="Academic Memory" subtitle="Spaced-repetition retention memory generated from your evaluation performance." />

      {!hasData ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <BookOpen size={42} className="text-[var(--accent)] mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">Academic Memory Empty</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto">
            Your long-term retention memory tracks topics you've mastered and flags concepts needing review. Complete an evaluation to populate your memory index.
          </p>
        </Card>
      ) : (
        <Card>
          <CardHeader title="Tracked Concept Mastery" />
          {cards.map((c, i) => (
            <div key={i} className="flex items-center justify-between py-3.5 border-b border-[var(--border)] last:border-0">
              <div>
                <div className="text-[13.5px] font-bold">{c.subject} — {c.topic}</div>
                <div className="text-xs text-[var(--text-faint)] mt-0.5">Retention Rate: {c.retention_rate ?? 0}%</div>
              </div>
              <Badge tone={c.status === 'Mastered' ? 'success' : 'warning'}>
                {c.status || 'Learning'} ({c.mastery ?? 0}% Mastery)
              </Badge>
            </div>
          ))}
        </Card>
      )}
    </>
  )
}
