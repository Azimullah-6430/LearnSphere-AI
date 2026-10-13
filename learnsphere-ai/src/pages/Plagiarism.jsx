import { useState, useEffect, useCallback } from 'react'
import {
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  FileText,
  Users,
  Eye,
  AlertTriangle,
  Hash,
  Copy,
  Trash2,
  Check,
  HelpCircle,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronUp,
  MessageSquare,
  Sparkles,
  Info
} from 'lucide-react'
import { Card, PageHead, Badge, StatCard, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'

export default function Plagiarism() {
  const { activeClass, teacherClasses } = useApp()
  const [selectedClassId, setSelectedClassId] = useState(activeClass?.id || 'all')
  const [matches, setMatches] = useState([])
  const [summary, setSummary] = useState(null)
  const [loading, setLoading] = useState(true)
  const [auditing, setAuditing] = useState(false)
  const [expandedRecordId, setExpandedRecordId] = useState(null)
  const [filterStatus, setFilterStatus] = useState('all') // 'all' | 'high' | 'possible' | 'pending'
  const [reviewNoteInput, setReviewNoteInput] = useState({})
  const [savingReviewId, setSavingReviewId] = useState(null)

  // Keep selectedClassId synced when activeClass from global header changes
  useEffect(() => {
    if (activeClass?.id) {
      setSelectedClassId(activeClass.id)
    }
  }, [activeClass?.id])

  const loadPlagiarismData = useCallback(async (classId) => {
    setLoading(true)
    const effectiveClass = classId && classId !== 'all' ? classId : null

    try {
      const matchRes = await api.getPlagiarismMatches(effectiveClass)
      if (matchRes && matchRes.success && Array.isArray(matchRes.matches)) {
        setMatches(matchRes.matches)
      } else {
        setMatches([])
      }
    } catch (err) {
      console.error('[Plagiarism] Error fetching matches:', err)
      setMatches([])
    }

    try {
      const sumRes = await api.getPlagiarismSummary(effectiveClass)
      if (sumRes && sumRes.success) {
        setSummary(sumRes)
      }
    } catch (err) {
      console.error('[Plagiarism] Error fetching summary:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadPlagiarismData(selectedClassId)
  }, [selectedClassId, loadPlagiarismData])

  const handleRunAudit = async () => {
    setAuditing(true)
    try {
      const payload = selectedClassId && selectedClassId !== 'all' ? { class_id: selectedClassId } : {}
      const res = await api.runPlagiarismAudit(payload)
      if (res && res.success) {
        await loadPlagiarismData(selectedClassId)
      }
    } catch (err) {
      console.error('[Plagiarism] Audit run failed:', err)
    } finally {
      setAuditing(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this plagiarism audit record permanently?')) return
    try {
      const res = await api.deletePlagiarismRecord(id)
      if (res && res.success) {
        setMatches((prev) => prev.filter((m) => (m.id || m._id) !== id))
        if (summary) {
          setSummary((prev) => ({
            ...prev,
            records: (prev.records || []).filter((m) => (m.id || m._id) !== id),
            flagged_count: Math.max(0, (prev.flagged_count || 1) - 1),
          }))
        }
      } else {
        alert(res?.error || 'Failed to delete record.')
      }
    } catch (err) {
      console.error('[Plagiarism] Delete error:', err)
      alert('Error deleting record.')
    }
  }

  const handleSaveReview = async (id, currentStatus) => {
    setSavingReviewId(id)
    try {
      const isDone = currentStatus === 'Reviewed' || currentStatus === 'Completed / Reviewed'
      const newStatus = isDone ? 'Pending Review' : 'Reviewed'
      const note = reviewNoteInput[id] || ''

      const res = await api.reviewPlagiarismRecord(id, {
        status: newStatus,
        review_notes: note,
      })

      if (res && res.success && res.record) {
        setMatches((prev) =>
          prev.map((m) => ((m.id || m._id) === id ? { ...m, ...res.record } : m))
        )
      } else {
        // Optimistic update fallback
        setMatches((prev) =>
          prev.map((m) =>
            (m.id || m._id) === id ? { ...m, status: newStatus, review_notes: note } : m
          )
        )
      }
    } catch (err) {
      console.error('[Plagiarism] Review update failed:', err)
    } finally {
      setSavingReviewId(null)
    }
  }

  const filteredMatches = matches.filter((m) => {
    const sim = parseFloat(m.similarity || 0)
    const isReviewed =
      m.status === 'Reviewed' || m.status === 'Completed / Reviewed' || m.status === 'Dismissed'

    if (filterStatus === 'high') {
      return sim >= 85 || m.status === 'EXACT_DUPLICATE' || m.status === 'HIGH_SIMILARITY'
    }
    if (filterStatus === 'possible') {
      return (
        (sim >= 70 && sim < 85) ||
        m.status === 'POSSIBLE_MATCH' ||
        m.status === 'POSSIBLE_COLLUSION'
      )
    }
    if (filterStatus === 'pending') {
      return !isReviewed
    }
    return true
  })

  const totalChecked = summary?.total_checked ?? matches.length
  const highRiskCount =
    summary?.high_risk_matches ??
    matches.filter((m) => parseFloat(m.similarity || 0) >= 85 || m.status === 'EXACT_DUPLICATE').length
  const possibleCount =
    summary?.possible_matches ??
    matches.filter((m) => {
      const s = parseFloat(m.similarity || 0)
      return s >= 70 && s < 85
    }).length
  const pendingCount =
    summary?.pending_review_count ??
    matches.filter(
      (m) =>
        m.status !== 'Reviewed' &&
        m.status !== 'Completed / Reviewed' &&
        m.status !== 'Dismissed'
    ).length

  const getStatusTone = (status, sim) => {
    if (status === 'EXACT_DUPLICATE' || sim >= 90) return 'error'
    if (status === 'HIGH_SIMILARITY' || sim >= 85) return 'error'
    if (status === 'POSSIBLE_MATCH' || status === 'POSSIBLE_COLLUSION' || sim >= 70) return 'warning'
    if (status === 'REPEATED_SUBMISSION') return 'accent'
    return 'info'
  }

  return (
    <>
      <PageHead
        title="Plagiarism & Academic Integrity Audit"
        subtitle="Cryptographic n-gram & stylistic peer comparison strictly scoped to your authorized class submissions."
        action={
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => loadPlagiarismData(selectedClassId)}
              disabled={loading}
              className="gap-1.5"
            >
              <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
              Refresh
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={handleRunAudit}
              disabled={auditing}
              className="gap-1.5"
            >
              <Sparkles size={14} className={auditing ? 'animate-spin' : ''} />
              {auditing ? 'Auditing Class...' : 'Run Peer Audit'}
            </Button>
          </div>
        }
      />

      {/* Class Selector Bar */}
      <div className="mb-5 p-3.5 rounded-2xl bg-[var(--surface)] border border-[var(--border)] shadow-xs flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
            Class Scope:
          </span>
          <select
            value={selectedClassId}
            onChange={(e) => setSelectedClassId(e.target.value)}
            className="px-3 py-1.5 rounded-xl text-xs font-semibold bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
          >
            <option value="all">All My Classes</option>
            {(teacherClasses || []).map((cls) => (
              <option key={cls.id} value={cls.id}>
                {cls.name} ({cls.grade || cls.subject || 'Class'})
              </option>
            ))}
          </select>
        </div>

        {/* Filter Tabs */}
        <div className="flex items-center gap-1.5">
          {[
            { id: 'all', label: 'All Findings' },
            { id: 'high', label: `High Risk (${highRiskCount})` },
            { id: 'possible', label: `Possible (${possibleCount})` },
            { id: 'pending', label: `Pending Review (${pendingCount})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setFilterStatus(tab.id)}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold transition-colors ${
                filterStatus === tab.id
                  ? 'bg-[var(--accent)] text-white shadow-xs'
                  : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="Submissions Audited"
          value={totalChecked}
          delta="verified in database"
          deltaTone="neutral"
        />
        <StatCard
          label="High Risk Flags"
          value={highRiskCount}
          delta="similarity >= 85%"
          deltaTone={highRiskCount > 0 ? 'down' : 'up'}
        />
        <StatCard
          label="Possible Overlaps"
          value={possibleCount}
          delta="similarity 70-84%"
          deltaTone="neutral"
        />
        <StatCard
          label="Pending Review"
          value={pendingCount}
          delta="requires teacher decision"
          deltaTone={pendingCount > 0 ? 'warning' : 'up'}
        />
      </div>

      {/* Main Content Area */}
      {loading ? (
        <Card className="p-12 text-center my-6">
          <RefreshCw size={36} className="text-[var(--accent)] mx-auto mb-3 animate-spin" />
          <h4 className="text-sm font-bold text-[var(--text)]">Loading Integrity Audit Data...</h4>
          <p className="text-xs text-[var(--text-soft)] mt-1">
            Validating submissions against your authorized class records.
          </p>
        </Card>
      ) : matches.length === 0 ? (
        <Card className="p-12 text-center my-6 border-dashed border-2">
          {totalChecked === 0 ? (
            <>
              <HelpCircle size={44} className="text-amber-500 mx-auto mb-3" />
              <h3 className="text-lg font-bold mb-1 text-[var(--text)]">
                No Submissions Available for Comparison
              </h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed mb-4">
                No completed student evaluation scripts exist yet in this class scope. Once evaluations
                are performed via the Evaluate portal, automated peer similarity audits will become active.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunAudit}
                disabled={auditing}
                className="mx-auto"
              >
                Check Database Submissions
              </Button>
            </>
          ) : totalChecked === 1 ? (
            <>
              <Info size={44} className="text-blue-500 mx-auto mb-3" />
              <h3 className="text-lg font-bold mb-1 text-[var(--text)]">
                Baseline Established (1 Submission)
              </h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
                Only 1 submission has been evaluated in this class so far. Peer cross-comparison requires
                at least 2 student submissions to detect collusion or duplicate work.
              </p>
            </>
          ) : (
            <>
              <CheckCircle2 size={44} className="text-emerald-500 mx-auto mb-3" />
              <h3 className="text-lg font-bold mb-1 text-[var(--text)]">
                All Clear — Zero Plagiarism Flags Detected
              </h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed mb-4">
                Cross-referenced {totalChecked} student submissions using n-gram similarity and structural hashing.
                All student scripts show independent work.
              </p>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRunAudit}
                disabled={auditing}
                className="mx-auto"
              >
                Re-Run Verification
              </Button>
            </>
          )}
        </Card>
      ) : filteredMatches.length === 0 ? (
        <Card className="p-8 text-center my-6 border-dashed">
          <p className="text-xs text-[var(--text-soft)]">
            No plagiarism records match the filter <strong>{filterStatus}</strong>.
          </p>
        </Card>
      ) : (
        <div className="space-y-4">
          {filteredMatches.map((match) => {
            const mId = match.id || match._id
            const isExpanded = expandedRecordId === mId
            const isReviewed =
              match.status === 'Reviewed' || match.status === 'Completed / Reviewed'
            const sim = parseFloat(match.similarity || 0)

            return (
              <Card key={mId} className="p-5 transition-all">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3.5 pb-3.5 border-b border-[var(--border)]">
                  <div>
                    <div className="flex flex-wrap items-center gap-2 mb-1.5">
                      <Badge tone={getStatusTone(match.status, sim)}>
                        {match.status || (sim >= 85 ? 'HIGH_SIMILARITY' : 'POSSIBLE_MATCH')}
                      </Badge>
                      <span className="text-xs font-bold text-[var(--accent)]">
                        {match.subject || 'General'}
                      </span>
                      <span className="text-xs text-[var(--text-faint)] font-semibold">
                        · {sim.toFixed(1)}% Similarity
                      </span>
                      {isReviewed ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 bg-emerald-500/10 px-2 py-0.5 rounded-md">
                          <Check size={12} /> Teacher Reviewed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600 bg-amber-500/10 px-2 py-0.5 rounded-md">
                          <AlertTriangle size={12} /> Pending Decision
                        </span>
                      )}
                    </div>
                    <h4 className="font-extrabold text-base text-[var(--text)]">
                      {match.student_name}{' '}
                      <span className="text-xs font-semibold text-[var(--text-soft)]">
                        (Roll: {match.roll_number || 'N/A'})
                      </span>
                    </h4>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleSaveReview(mId, match.status)}
                      disabled={savingReviewId === mId}
                      className={`px-3.5 py-1.5 rounded-xl text-xs font-bold border transition-colors flex items-center gap-1.5 ${
                        isReviewed
                          ? 'border-[var(--border)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                          : 'border-emerald-500/30 text-emerald-600 bg-emerald-500/10 hover:bg-emerald-500/20'
                      }`}
                    >
                      <Check size={14} />
                      {savingReviewId === mId
                        ? 'Saving...'
                        : isReviewed
                        ? 'Mark as Pending'
                        : 'Confirm Reviewed'}
                    </button>
                    <button
                      onClick={() => setExpandedRecordId(isExpanded ? null : mId)}
                      className="p-2 rounded-xl text-[var(--text-soft)] hover:bg-[var(--surface-alt)] border border-[var(--border)] transition-colors"
                      title={isExpanded ? 'Collapse Evidence' : 'View Evidence'}
                      aria-label="Toggle evidence view"
                    >
                      {isExpanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
                    </button>
                    <button
                      onClick={() => handleDelete(mId)}
                      className="p-2 rounded-xl text-red-500 hover:bg-red-500/10 border border-red-500/20 transition-colors"
                      title="Delete Record"
                      aria-label="Delete plagiarism record"
                    >
                      <Trash2 size={15} />
                    </button>
                  </div>
                </div>

                {/* Summary Context */}
                <div className="mt-3.5 text-xs text-[var(--text-soft)] leading-relaxed">
                  {match.details || match.context || 'Cross-referenced against stored class submissions.'}
                </div>

                {/* Evidence & Comparison Drawer */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-[var(--border)] space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      {/* Compared Target */}
                      <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs">
                        <div className="font-bold text-[var(--text)] mb-1 flex items-center gap-1.5">
                          <Users size={14} className="text-[var(--accent)]" />
                          Matched Peer Submission
                        </div>
                        <div className="text-[var(--text-soft)] space-y-1">
                          <div>
                            <strong>Peer Student:</strong>{' '}
                            {match.matched_student_name || 'Classmate submission'}
                          </div>
                          <div>
                            <strong>Peer Roll Number:</strong>{' '}
                            {match.matched_roll_number || 'N/A'}
                          </div>
                          {match.matched_evaluation_id && (
                            <div>
                              <strong>Evaluation Ref:</strong>{' '}
                              <code className="text-[10px] bg-[var(--surface)] px-1 py-0.5 rounded">
                                {match.matched_evaluation_id}
                              </code>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Overlap Metrics */}
                      <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs">
                        <div className="font-bold text-[var(--text)] mb-1 flex items-center gap-1.5">
                          <FileText size={14} className="text-amber-500" />
                          Integrity Breakdown
                        </div>
                        <div className="text-[var(--text-soft)] space-y-1">
                          <div>
                            <strong>Similarity Score:</strong> {sim.toFixed(1)}%
                          </div>
                          <div>
                            <strong>Audit Type:</strong> Class-Scoped Shingled N-Gram
                          </div>
                          {match.review_notes && (
                            <div className="mt-1 pt-1 border-t border-[var(--border)]">
                              <strong>Teacher Notes:</strong> {match.review_notes}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* Matched Passage Snippet */}
                    {match.matched_passage && (
                      <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs">
                        <div className="font-bold text-[var(--text)] mb-1">
                          Extracted Overlapping Passage:
                        </div>
                        <blockquote className="italic text-[var(--text-soft)] border-l-2 border-amber-500 pl-3 my-1">
                          &ldquo;{match.matched_passage}&rdquo;
                        </blockquote>
                      </div>
                    )}

                    {/* Review Note Input */}
                    <div className="flex items-center gap-2 pt-2">
                      <input
                        type="text"
                        placeholder="Add review notes or teacher determination..."
                        value={reviewNoteInput[mId] ?? match.review_notes ?? ''}
                        onChange={(e) =>
                          setReviewNoteInput({ ...reviewNoteInput, [mId]: e.target.value })
                        }
                        className="flex-1 px-3 py-1.5 rounded-xl text-xs bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleSaveReview(mId, match.status)}
                        disabled={savingReviewId === mId}
                        className="text-xs"
                      >
                        Save Note
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            )
          })}
        </div>
      )}
    </>
  )
}
