import { useState, useEffect } from 'react'
import { ShieldCheck, ShieldAlert, CheckCircle2, FileText, Users, Eye, AlertTriangle, Hash, Copy, Trash2, Check, HelpCircle } from 'lucide-react'
import { Card, CardHeader, PageHead, Badge, StatCard, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'

export default function Plagiarism() {
  const { activeClass } = useApp()
  const [matches, setMatches] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadPlagiarismData() {
      setLoading(true)
      try {
        const matchRes = await api.getPlagiarismMatches()
        if (matchRes && matchRes.success && Array.isArray(matchRes.matches)) {
          setMatches(matchRes.matches)
        } else {
          setMatches([])
        }
      } catch (err) {
        setMatches([])
      }

      try {
        const sumRes = await api.getPlagiarismSummary()
        if (sumRes && sumRes.success) {
          setSummary(sumRes)
        }
      } catch (err) {}
      setLoading(false)
    }
    loadPlagiarismData()
  }, [])

  const handleDelete = (id) => {
    if (window.confirm("Delete this plagiarism audit record permanently?")) {
      setMatches(prev => prev.filter(m => m.id !== id))
    }
  }

  const handleToggleCompleted = (id) => {
    setMatches(prev => prev.map(m => {
      if (m.id === id) {
        const isDone = m.status === 'Completed / Reviewed'
        return { ...m, status: isDone ? 'Pending Review' : 'Completed / Reviewed' }
      }
      return m
    }))
  }

  const hasMatches = matches.length > 0
  const totalChecked = summary?.total_checked || 0

  return (
    <>
      <PageHead
        title="Plagiarism & Integrity Audit"
        subtitle="Cross-submission similarity analysis and academic integrity monitoring across student cohorts."
      />

      {activeClass && (
        <div className="mb-5 p-3.5 rounded-2xl bg-[var(--accent-soft)] border border-[var(--accent)] text-xs font-bold text-[var(--accent)] flex items-center justify-between shadow-xs">
          <span>🏫 Active Class Filter: <strong className="text-[var(--text)]">{activeClass.name}</strong></span>
          <Badge tone="accent">{activeClass.type}</Badge>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <StatCard label="Total Submissions Audited" value={totalChecked} delta="database audit" />
        <StatCard label="High Similarity Flagged" value={summary?.high_risk_matches || matches.filter(m => m.similarity >= 85).length} delta="review required" deltaTone="down" />
        <StatCard label="Possible Matches" value={summary?.possible_matches || matches.filter(m => m.similarity >= 70 && m.similarity < 85).length} delta="potential overlap" />
      </div>

      {!hasMatches ? (
        <Card className="p-12 text-center my-6 border-dashed border-2">
          {totalChecked === 0 ? (
            <>
              <HelpCircle size={44} className="text-amber-500 mx-auto mb-3" />
              <h3 className="text-lg font-bold mb-1 text-[var(--text)]">No Comparable Submissions Available</h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
                No previous student evaluation scripts exist in the database for cross-comparison. Once multiple student scripts are evaluated, similarity cross-checking will execute automatically.
              </p>
            </>
          ) : (
            <>
              <CheckCircle2 size={44} className="text-emerald-500 mx-auto mb-3" />
              <h3 className="text-lg font-bold mb-1 text-[var(--text)]">No Plagiarism Matches Found</h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
                Compared against stored database submissions. All evaluated scripts appear distinct.
              </p>
            </>
          )}
        </Card>
      ) : (
        <div className="space-y-4">
          {matches.map((match) => (
            <Card key={match.id || match._id} className="p-5">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-3.5 pb-3.5 border-b border-[var(--border)]">
                <div>
                  <div className="flex items-center gap-2 mb-1.5">
                    <Badge tone={match.similarity >= 85 ? 'error' : match.similarity >= 70 ? 'warning' : 'info'}>
                      {match.status || (match.similarity >= 95 ? 'EXACT_DUPLICATE' : match.similarity >= 85 ? 'HIGH_SIMILARITY' : 'POSSIBLE_MATCH')}
                    </Badge>
                    <span className="text-xs font-bold text-[var(--accent)]">{match.subject || 'Subject'}</span>
                    <span className="text-xs text-[var(--text-faint)] font-semibold">· {match.similarity}% Similarity</span>
                  </div>
                  <h4 className="font-extrabold text-base text-[var(--text)]">
                    {match.student_name} <span className="text-xs font-semibold text-[var(--text-soft)]">({match.roll_number || 'N/A'})</span>
                  </h4>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleToggleCompleted(match.id || match._id)}
                    className="px-3.5 py-1.5 rounded-xl text-xs font-bold border border-[var(--border)] hover:bg-[var(--surface-alt)] flex items-center gap-1.5 transition-colors"
                  >
                    <Check size={14} /> {match.status === 'Completed / Reviewed' ? 'Mark Pending' : 'Mark Reviewed'}
                  </button>
                  <button
                    onClick={() => handleDelete(match.id || match._id)}
                    className="p-2 rounded-xl text-red-500 hover:bg-red-500/10 border border-red-500/20 transition-colors"
                    title="Delete Record"
                    aria-label="Delete plagiarism record"
                  >
                    <Trash2 size={15} />
                  </button>
                </div>
              </div>

              <div className="mt-3.5 text-xs text-[var(--text-soft)] leading-relaxed">
                {match.details || match.context || 'Cross-referenced against stored submissions.'}
              </div>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
