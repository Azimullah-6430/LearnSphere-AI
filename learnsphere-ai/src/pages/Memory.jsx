import { useState, useEffect } from 'react'
import { Card, CardHeader, PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { BookOpen, Trash2, Plus, CheckCircle2, RotateCcw, Brain, Sparkles, AlertCircle } from 'lucide-react'

export default function Memory() {
  const { user } = useApp()
  const [cards, setCards] = useState([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newSubject, setNewSubject] = useState('')
  const [newTopic, setNewTopic] = useState('')
  const [newMastery, setNewMastery] = useState(70)
  const [filter, setFilter] = useState('ALL')
  const [toastMessage, setToastMessage] = useState('')

  const showToast = (msg) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(''), 3500)
  }

  const loadMemory = async () => {
    setLoading(true)
    try {
      const res = await api.getMemoryCards(user?.name)
      if (res && res.success && Array.isArray(res.cards)) {
        setCards(res.cards)
      } else {
        setCards([])
      }
    } catch {
      setCards([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadMemory()
  }, [user])

  const handleDeleteCard = async (cardId, e) => {
    e.stopPropagation()
    if (!cardId) return
    setActionLoading(true)
    try {
      const res = await api.deleteMemoryCard(cardId)
      if (res && res.success) {
        setCards((prev) => prev.filter((c) => (c.id || c._id) !== cardId))
        showToast('Memory card deleted.')
      } else {
        showToast(res?.error || 'Failed to delete card.')
      }
    } catch (err) {
      showToast('Error deleting card.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleClearAll = async () => {
    if (!window.confirm('Are you sure you want to clear all academic memory cards?')) return
    setActionLoading(true)
    try {
      const res = await api.clearMemoryCards()
      if (res && res.success) {
        setCards([])
        showToast('All academic memories cleared.')
      } else {
        showToast(res?.error || 'Failed to clear cards.')
      }
    } catch {
      showToast('Error clearing cards.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleReviewCard = async (cardId) => {
    if (!cardId) return
    try {
      const res = await api.reviewMemoryCard(cardId)
      if (res && res.success) {
        setCards((prev) =>
          prev.map((c) =>
            (c.id || c._id) === cardId
              ? { ...c, status: 'Mastered', mastery: Math.min(100, (c.mastery || 0) + 15), retention_rate: Math.min(100, (c.retention_rate || 0) + 10) }
              : c
          )
        )
        showToast('Marked as mastered! Retention scheduled for next interval.')
      }
    } catch {
      showToast('Failed to update review status.')
    }
  }

  const handleCreateCard = async (e) => {
    e.preventDefault()
    if (!newSubject.trim() || !newTopic.trim()) return
    setActionLoading(true)
    try {
      const res = await api.createMemoryCard({
        subject: newSubject.trim(),
        topic: newTopic.trim(),
        mastery: Number(newMastery),
        retention_rate: Number(newMastery),
        status: Number(newMastery) >= 80 ? 'Mastered' : 'Learning',
      })
      if (res && res.success) {
        if (res.card) {
          setCards((prev) => [res.card, ...prev])
        } else {
          loadMemory()
        }
        setShowAddModal(false)
        setNewSubject('')
        setNewTopic('')
        setNewMastery(70)
        showToast('New concept memory card added.')
      } else {
        showToast(res?.error || 'Failed to add card.')
      }
    } catch {
      showToast('Error adding card.')
    } finally {
      setActionLoading(false)
    }
  }

  const filteredCards = cards.filter((c) => {
    if (filter === 'MASTERED') return c.status === 'Mastered' || (c.mastery || 0) >= 80
    if (filter === 'LEARNING') return c.status !== 'Mastered' && (c.mastery || 0) < 80
    return true
  })

  const masteredCount = cards.filter((c) => c.status === 'Mastered' || (c.mastery || 0) >= 80).length
  const learningCount = cards.length - masteredCount
  const avgRetention = cards.length ? Math.round(cards.reduce((acc, c) => acc + (c.retention_rate || c.mastery || 0), 0) / cards.length) : 0

  return (
    <>
      <PageHead
        title="Academic Memory"
        action={
          <div className="flex items-center gap-2">
            {cards.length > 0 && (
              <Button variant="secondary" size="sm" onClick={handleClearAll} disabled={actionLoading} className="text-red-500 hover:text-red-600 hover:bg-red-500/10 border-red-500/30">
                <Trash2 size={14} className="mr-1.5" />
                Clear All
              </Button>
            )}
            <Button variant="primary" size="sm" onClick={() => setShowAddModal(true)}>
              <Plus size={14} className="mr-1.5" />
              Add Memory Card
            </Button>
          </div>
        }
      />

      {toastMessage && (
        <div className="mb-4 px-4 py-2.5 rounded-lg bg-[var(--accent)] text-white text-xs font-semibold shadow-md flex items-center justify-between animate-fadeIn">
          <span>{toastMessage}</span>
          <button onClick={() => setToastMessage('')} className="ml-3 opacity-80 hover:opacity-100">✕</button>
        </div>
      )}

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3.5 mb-6">
        <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/10 text-indigo-500 flex items-center justify-center shrink-0">
            <Brain size={20} />
          </div>
          <div>
            <div className="text-xs text-[var(--text-faint)] font-medium">Tracked Concepts</div>
            <div className="text-lg font-bold">{cards.length}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-500 flex items-center justify-center shrink-0">
            <CheckCircle2 size={20} />
          </div>
          <div>
            <div className="text-xs text-[var(--text-faint)] font-medium">Mastered Topics</div>
            <div className="text-lg font-bold text-emerald-600">{masteredCount}</div>
          </div>
        </div>

        <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] flex items-center gap-3.5">
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-500 flex items-center justify-center shrink-0">
            <Sparkles size={20} />
          </div>
          <div>
            <div className="text-xs text-[var(--text-faint)] font-medium">Avg Retention Rate</div>
            <div className="text-lg font-bold text-amber-600">{avgRetention}%</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 mb-4">
        <button
          onClick={() => setFilter('ALL')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            filter === 'ALL' ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
          }`}
        >
          All ({cards.length})
        </button>
        <button
          onClick={() => setFilter('MASTERED')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            filter === 'MASTERED' ? 'bg-emerald-600 text-white' : 'bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
          }`}
        >
          Mastered ({masteredCount})
        </button>
        <button
          onClick={() => setFilter('LEARNING')}
          className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
            filter === 'LEARNING' ? 'bg-amber-600 text-white' : 'bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] hover:bg-[var(--surface-alt)]'
          }`}
        >
          Learning ({learningCount})
        </button>
      </div>

      {loading ? (
        <Card className="p-12 text-center my-6">
          <div className="w-8 h-8 border-3 border-[var(--accent)] border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <div className="text-xs text-[var(--text-faint)]">Loading academic memory...</div>
        </Card>
      ) : filteredCards.length === 0 ? (
        <Card className="p-10 text-center my-6 border-dashed border-2">
          <BookOpen size={44} className="text-[var(--accent)] mx-auto mb-3 opacity-80" />
          <h3 className="text-base font-bold mb-1">
            {cards.length === 0 ? 'Academic Memory Empty' : 'No memory cards match this filter'}
          </h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto mb-5 leading-relaxed">
            {cards.length === 0
              ? "Your long-term retention memory tracks topics you've mastered and flags concepts needing spaced review. Complete an evaluation or click 'Add Memory Card' above to create cards."
              : 'Switch filters or create a new card to expand your memory index.'}
          </p>
          <Button variant="primary" size="sm" onClick={() => setShowAddModal(true)}>
            <Plus size={14} className="mr-1.5" />
            Add First Memory Card
          </Button>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {filteredCards.map((c, i) => {
            const cardId = c.id || c._id
            const isMastered = c.status === 'Mastered' || (c.mastery || 0) >= 80
            return (
              <div
                key={cardId || i}
                className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] hover:border-[var(--accent)]/50 transition-all flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div>
                      <span className="text-[11px] font-extrabold uppercase tracking-wider text-[var(--accent)] bg-[var(--accent-soft)] px-2 py-0.5 rounded">
                        {c.subject || 'General'}
                      </span>
                      <h4 className="text-[14px] font-bold mt-1 text-[var(--text)]">{c.topic}</h4>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Badge tone={isMastered ? 'success' : 'warning'}>
                        {isMastered ? 'Mastered' : 'Learning'}
                      </Badge>
                      <button
                        onClick={(e) => handleDeleteCard(cardId, e)}
                        title="Delete this memory card"
                        className="p-1.5 rounded text-[var(--text-faint)] hover:text-red-500 hover:bg-red-500/10 transition-colors opacity-70 group-hover:opacity-100"
                      >
                        <Trash2 size={15} />
                      </button>
                    </div>
                  </div>

                  {/* Progress Bars */}
                  <div className="mt-3 space-y-2">
                    <div>
                      <div className="flex justify-between text-[11px] text-[var(--text-faint)] mb-1">
                        <span>Concept Mastery</span>
                        <span className="font-bold">{c.mastery ?? 0}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${
                            isMastered ? 'bg-emerald-500' : 'bg-[var(--accent)]'
                          }`}
                          style={{ width: `${Math.min(100, Math.max(5, c.mastery ?? 0))}%` }}
                        />
                      </div>
                    </div>

                    <div>
                      <div className="flex justify-between text-[11px] text-[var(--text-faint)] mb-1">
                        <span>Retention Index</span>
                        <span className="font-bold">{c.retention_rate ?? c.mastery ?? 0}%</span>
                      </div>
                      <div className="w-full h-1.5 bg-[var(--border)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-amber-500 rounded-full transition-all"
                          style={{ width: `${Math.min(100, Math.max(5, c.retention_rate ?? c.mastery ?? 0))}%` }}
                        />
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-4 pt-3 border-t border-[var(--border)] flex items-center justify-between text-xs">
                  <span className="text-[11px] text-[var(--text-faint)]">
                    {c.next_review ? `Next Review: ${String(c.next_review).slice(0, 10)}` : 'Active Spaced Repetition'}
                  </span>
                  {!isMastered && (
                    <button
                      onClick={() => handleReviewCard(cardId)}
                      className="flex items-center gap-1 text-[11.5px] font-bold text-[var(--accent)] hover:underline"
                    >
                      <CheckCircle2 size={13} />
                      Mark Mastered
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Add Memory Card Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h3 className="text-base font-bold mb-1">Add Academic Memory Card</h3>
            <p className="text-xs text-[var(--text-faint)] mb-4">
              Track retention rate and spaced repetition for important concepts, formulas, and topics.
            </p>

            <form onSubmit={handleCreateCard} className="space-y-3.5">
              <div>
                <label className="block text-xs font-bold mb-1">Subject</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Physics, Data Structures, Mathematics"
                  value={newSubject}
                  onChange={(e) => setNewSubject(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg)] focus:outline-none focus:border-[var(--accent)]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold mb-1">Topic / Key Concept</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Newton's 3rd Law, Dynamic Programming, Integration"
                  value={newTopic}
                  onChange={(e) => setNewTopic(e.target.value)}
                  className="w-full px-3.5 py-2 text-xs rounded-lg border border-[var(--border)] bg-[var(--bg)] focus:outline-none focus:border-[var(--accent)]"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold mb-1">
                  <label>Initial Mastery Level</label>
                  <span>{newMastery}%</span>
                </div>
                <input
                  type="range"
                  min="10"
                  max="100"
                  step="5"
                  value={newMastery}
                  onChange={(e) => setNewMastery(e.target.value)}
                  className="w-full accent-[var(--accent)] cursor-pointer"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-[var(--border)] mt-4">
                <Button type="button" variant="secondary" size="sm" onClick={() => setShowAddModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" variant="primary" size="sm" disabled={actionLoading}>
                  {actionLoading ? 'Saving...' : 'Save Concept'}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}
