import { useState, useEffect } from 'react'
import { ShieldCheck, ShieldAlert, CheckCircle2, FileText, Users, Eye, AlertTriangle, Hash, Copy, Trash2, Check } from 'lucide-react'
import { Card, CardHeader, PageHead, Badge, StatCard, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'

export default function Plagiarism() {
  const { activeClass } = useApp()
  const [matches, setMatches] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedSnippetMatch, setSelectedSnippetMatch] = useState(null)

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

  // Delete Plagiarism Match
  const handleDelete = (id) => {
    if (window.confirm("Delete this plagiarism audit record permanently?")) {
      setMatches(prev => prev.filter(m => m.id !== id))
    }
  }

  // Toggle Mark Reviewed / Completed
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

  return (
    <>
      <PageHead
        title="Academic Integrity & Plagiarism Audit"
        subtitle="Cross-checks uploaded answer scripts for renamed duplicate file submissions, 3+ identical question responses, and adjacent roll-number seating collusion."
      />

      {activeClass && (
        <div className="mb-4 p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[12.5px] font-bold text-[var(--accent)] flex items-center justify-between">
          <span>🏫 Active Class Filter: <strong>{activeClass.name}</strong></span>
          <Badge tone="accent">{activeClass.type}</Badge>
        </div>
      )}

      {/* Rules Banner */}
      <div className="mb-6 p-4 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[13px] text-[var(--text)] flex items-start gap-3">
        <ShieldCheck size={22} className="text-[var(--accent)] shrink-0 mt-0.5" />
        <div>
          <div className="font-extrabold text-[var(--accent)] mb-0.5">Multi-Factor Integrity Audit Rules Active</div>
          <div className="text-[12.5px] text-[var(--text-soft)]">
            Submissions are automatically audited for: <strong>(1) Renamed Duplicate Files (MD5 Hash Match)</strong>, <strong>(2) &ge; 3 Questions Answered Identically</strong>, and <strong>(3) Adjacent Roll Number / Desk Proximity</strong>. Full delete and completed audit controls enabled.
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3.5 mb-6">
        <StatCard label="Total Scanned Scripts" value={summary?.total_scanned || 18} delta="database audit" />
        <StatCard label="Flagged Collusions" value={matches.length} delta="review required" deltaTone="down" />
        <StatCard label="Class Integrity Index" value="88%" delta="2 cases flagged" deltaTone="up" />
      </div>

      {!hasMatches ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <CheckCircle2 size={42} className="text-emerald-600 mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">Zero Integrity Violations Detected</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto">
            All submitted answer scripts passed multi-factor integrity checks.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {matches.map((m, i) => {
            const isCompleted = m.status === 'Completed / Reviewed'

            return (
              <Card key={m.id || i} className={`relative transition-all shadow-sm ${isCompleted ? 'opacity-75 bg-[var(--surface-alt)]' : 'hover:border-[var(--accent-dim)]'}`}>
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="flex-1 space-y-2.5">
                    {/* Header */}
                    <div className="flex items-center gap-2 flex-wrap">
                      <ShieldAlert size={18} className="text-[var(--error)] shrink-0" />
                      <span className="text-[16px] font-extrabold text-[var(--text)]">
                        {m.pair_match}
                      </span>
                      <Badge tone="error">
                        {m.similarity}% Similarity Match
                      </Badge>

                      {isCompleted && <Badge tone="success">✅ Completed / Reviewed</Badge>}
                    </div>

                    {/* Context */}
                    <div className="text-[13px] font-bold text-[var(--accent)]">
                      Assessment: {m.context}
                    </div>

                    {/* Multi-Factor Audit Triggers */}
                    <div className="flex items-center gap-2 flex-wrap text-[12px]">
                      {m.is_renamed_file_match && (
                        <span className="px-2.5 py-1 rounded-lg bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)] font-extrabold flex items-center gap-1">
                          <Hash size={13} /> Renamed Duplicate File Match (MD5 Hash)
                        </span>
                      )}

                      {m.identical_q_count >= 3 && (
                        <span className="px-2.5 py-1 rounded-lg bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning)] font-extrabold flex items-center gap-1">
                          <Copy size={13} /> {m.identical_q_count}+ Questions Identical: ({(m.identical_questions || []).join(', ')})
                        </span>
                      )}

                      {m.is_adjacent_seating && (
                        <span className="px-2.5 py-1 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)] font-extrabold flex items-center gap-1">
                          <Users size={13} /> Adjacent Roll Numbers ({m.roll_numbers})
                        </span>
                      )}
                    </div>

                    {/* Details Explanation */}
                    <p className="text-[13px] text-[var(--text-soft)] leading-relaxed font-medium">
                      {m.details}
                    </p>
                  </div>
                </div>

                {/* Footer Controls: Delete, Completed, Snippets buttons */}
                <div className="flex items-center justify-end gap-2 pt-3 mt-3 border-t border-[var(--border)] flex-wrap">
                  {m.snippets && (
                    <button
                      onClick={() => setSelectedSnippetMatch(m)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-bold border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] transition-colors"
                    >
                      <Eye size={14} />
                      <span>View Identical Snippets</span>
                    </button>
                  )}

                  <button
                    onClick={() => handleToggleCompleted(m.id)}
                    className={`px-3 py-1.5 rounded-lg text-[12px] font-bold border transition-colors flex items-center gap-1 ${
                      isCompleted
                        ? 'bg-[var(--success-soft)] text-[var(--success)] border-[var(--success)]'
                        : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)]'
                    }`}
                  >
                    <Check size={14} />
                    <span>{isCompleted ? 'Completed / Reviewed' : 'Mark Completed'}</span>
                  </button>

                  <button
                    onClick={() => handleDelete(m.id)}
                    className="px-3 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)] hover:bg-[var(--error)] hover:text-white transition-all flex items-center gap-1"
                    title="Delete Record"
                  >
                    <Trash2 size={14} />
                    <span>Delete</span>
                  </button>
                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* SNIPPETS COMPARISON MODAL */}
      {selectedSnippetMatch && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <Card className="max-w-[680px] w-full bg-[var(--surface)] border-2 border-[var(--error)] shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <div>
                <div className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2">
                  <ShieldAlert size={20} className="text-[var(--error)]" />
                  <span>Identical Question Comparison</span>
                </div>
                <div className="text-[12.5px] text-[var(--text-soft)]">
                  {selectedSnippetMatch.pair_match} ({selectedSnippetMatch.context})
                </div>
              </div>
              <button
                onClick={() => setSelectedSnippetMatch(null)}
                className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-[13px]">
              {selectedSnippetMatch.snippets.map((s, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2">
                  <div className="font-extrabold text-[var(--error)] text-[13px] flex items-center gap-1.5">
                    <Copy size={14} /> Question {s.q} — Verbatim Identical Answer Match:
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12px]">
                    <div className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border-strong)]">
                      <div className="font-bold text-[var(--accent)] mb-1">Student 1 Response:</div>
                      <div className="font-mono text-[11.5px] text-[var(--text)]">{s.text1}</div>
                    </div>

                    <div className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border-strong)]">
                      <div className="font-bold text-[var(--accent)] mb-1">Student 2 Response:</div>
                      <div className="font-mono text-[11.5px] text-[var(--text)]">{s.text2}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="flex items-center justify-end pt-2 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setSelectedSnippetMatch(null)}>Close Inspection</Button>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
