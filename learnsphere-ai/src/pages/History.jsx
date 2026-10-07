import { useState, useEffect } from 'react'
import { Card, PageHead, SearchBox, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  X, CheckCircle2, AlertTriangle, Download, Trash2, Eye, Check,
  Sparkles, BookOpen, AlertCircle, Zap, ShieldAlert, ArrowRight,
  TrendingDown, CheckSquare, Edit3
} from 'lucide-react'

export default function History() {
  const { role, user, activeClass } = useApp()
  const [evaluations, setEvaluations] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedEval, setSelectedEval] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    async function loadData() {
      setLoading(true)
      const params = {}
      if (role === 'student' && user?.name) {
        params.student_name = user.name
      }
      const res = await api.getEvaluations(params)
      if (res && res.success && Array.isArray(res.evaluations)) {
        setEvaluations(res.evaluations)
      } else {
        setEvaluations([])
      }
      setLoading(false)
    }
    loadData()
  }, [role, user])

  const handleViewDetail = async (id) => {
    if (!id) return
    setDetailLoading(true)
    try {
      const res = await api.getEvaluationDetail(id)
      if (res && res.success && res.evaluation) {
        setSelectedEval(res.evaluation)
      } else {
        const match = evaluations.find(e => String(e.id || e._id) === String(id))
        setSelectedEval(match || null)
      }
    } catch {
      const match = evaluations.find(e => String(e.id || e._id) === String(id))
      setSelectedEval(match || null)
    } finally {
      setDetailLoading(false)
    }
  }

  // Delete evaluation record
  const handleDelete = async (id, e) => {
    if (e) e.stopPropagation()
    if (!id) return
    if (!window.confirm("Are you sure you want to delete this evaluation permanently?")) {
      return
    }
    const targetId = String(id)
    try {
      await api.deleteEvaluation(targetId)
    } catch {}
    setEvaluations(prev => prev.filter(item => String(item.id || item._id) !== targetId))
    if (selectedEval && String(selectedEval.id || selectedEval._id) === targetId) {
      setSelectedEval(null)
    }
  }

  // Toggle Mark Completed / Reviewed
  const handleToggleCompleted = (id, e) => {
    if (e) e.stopPropagation()
    setEvaluations(prev => prev.map(item => {
      if (String(item.id || item._id) === String(id)) {
        const isDone = item.review_status === 'Completed'
        return { ...item, review_status: isDone ? 'Pending' : 'Completed' }
      }
      return item
    }))
  }

  // Filter by search
  const filtered = evaluations.filter(e => {
    const term = search.toLowerCase()
    return (
      (e.student_name && e.student_name.toLowerCase().includes(term)) ||
      (e.subject && e.subject.toLowerCase().includes(term)) ||
      (e.assessment_title && e.assessment_title.toLowerCase().includes(term)) ||
      (String(e.id || e._id || '').toLowerCase().includes(term))
    )
  })

  const [isEditingMarks, setIsEditingMarks] = useState(false)
  const [customObtainedMarks, setCustomObtainedMarks] = useState('')
  const [savingOverride, setSavingOverride] = useState(false)

  const handleSaveModalOverride = async () => {
    if (!selectedEval) return
    const id = selectedEval.id || selectedEval._id
    const newObtained = parseFloat(customObtainedMarks)
    if (isNaN(newObtained) || newObtained < 0) {
      alert('Please enter a valid marks value.')
      setSavingOverride(false)
      return
    }
    const newTotal = parseFloat(selectedEval.total_marks)
    if (!newTotal || newTotal <= 0) {
      alert('Cannot override: total marks for this evaluation are not available.')
      setSavingOverride(false)
      return
    }
    if (newObtained > newTotal) {
      alert(`Obtained marks (${newObtained}) cannot exceed total marks (${newTotal}).`)
      setSavingOverride(false)
      return
    }
    const newPct = Math.round((newObtained / newTotal) * 10000) / 100

    function calcGrade(p) {
      if (p >= 90) return 'A+'
      if (p >= 80) return 'A'
      if (p >= 70) return 'B+'
      if (p >= 60) return 'B'
      if (p >= 50) return 'C'
      if (p >= 40) return 'D'
      return 'F'
    }

    setSavingOverride(true)
    try {
      await api.overrideEvaluationMarks(id, {
        obtained_marks: newObtained,
        total_marks: newTotal
      })
    } catch {}

    const updated = {
      ...selectedEval,
      obtained_marks: newObtained,
      total_marks: newTotal,
      percentage: newPct,
      grade: calcGrade(newPct),
      is_unreadable: false,
      assigned_to_teacher: false,
      is_teacher_overridden: true
    }

    setSelectedEval(updated)
    setEvaluations(prev => prev.map(e => (String(e.id || e._id) === String(id) ? updated : e)))
    setIsEditingMarks(false)
    setSavingOverride(false)
  }

  return (
    <>
      <PageHead
        title={role === 'teacher' ? 'Teacher Evaluation History & Traceability' : 'My Evaluation History'}
        subtitle="Searchable repository of stored evaluation records. Opening any record displays question-level mark reasoning, script evidence, feedback, misconceptions, and Action Center relevance without recalculating."
      />

      {activeClass && role === 'teacher' && (
        <div className="mb-4 p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[12.5px] font-bold text-[var(--accent)] flex items-center justify-between shadow-sm">
          <span>🏫 Active Class Filter: <strong>{activeClass.name}</strong></span>
          <Badge tone="accent">{activeClass.type}</Badge>
        </div>
      )}

      <Card className="shadow-sm">
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <SearchBox placeholder="Search by student, subject, assessment title, ID..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="flex gap-2 text-xs text-[var(--text-faint)] font-bold">
            <span>Total Evaluated Records: <strong>{filtered.length}</strong></span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                {['Student', 'Subject', 'Exam / Assessment', 'Marks (Obtained / Max)', 'Percentage', 'Status', 'Date', 'Actions'].map((h) => (
                  <th key={h} className="text-left text-[11px] text-[var(--text-faint)] font-bold uppercase tracking-wider pb-2.5 px-3 border-b border-[var(--border)] bg-[var(--surface-alt)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-[var(--text-soft)]">
                    <div className="animate-spin text-xl text-[var(--accent)] mb-2">⏳</div>
                    <span>Loading evaluation history...</span>
                  </td>
                </tr>
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={8} className="text-center py-10 text-[var(--text-soft)]">
                    No evaluation records found matching your query.
                  </td>
                </tr>
              ) : (
                filtered.map((r, i) => {
                  const evalId = r.id || r._id || `eval_${i}`
                  const isCompleted = r.review_status === 'Completed'
                  const isUnreadable = r.is_unreadable || r.assigned_to_teacher
                  const marksLost = (r.total_marks || 0) - (r.obtained_marks || 0)

                  return (
                    <tr key={evalId} className="hover:bg-[var(--surface-alt)] transition-colors border-b border-[var(--border)] last:border-0">
                      <td className="py-3 px-3 font-semibold text-[var(--text)]">
                        <div className="flex flex-col">
                          <span className="font-extrabold text-[13.5px]">{r.student_name || 'Student'}</span>
                          <span className="text-[11px] text-[var(--text-faint)] font-mono">
                            ID: {r.student_id || r.roll_number || 'N/A'}
                          </span>
                        </div>
                      </td>

                      <td className="py-3 px-3 font-bold text-[var(--accent)]">
                        {r.subject || 'General'}
                      </td>

                      <td className="py-3 px-3 text-[var(--text-soft)] font-medium">
                        <div className="flex flex-col">
                          <span>{r.assessment_title || `${r.subject || 'Exam'} Evaluation`}</span>
                          {marksLost > 20 && (
                            <span className="text-[10.5px] text-[var(--error)] font-bold">
                              &minus;{marksLost} marks lost (&gt;20 Alert)
                            </span>
                          )}
                        </div>
                      </td>

                      <td className="py-3 px-3 font-extrabold text-[var(--text)]">
                        {r.obtained_marks !== undefined ? `${r.obtained_marks} / ${r.total_marks} marks` : '—'}
                      </td>

                      <td className="py-3 px-3 font-black">
                        {(r.percentage !== null && r.percentage !== undefined) ? (
                          <span className={r.percentage >= 75 ? 'text-emerald-500' : r.percentage >= 50 ? 'text-amber-500' : 'text-[var(--error)]'}>
                            {r.percentage}% {r.grade ? `(${r.grade})` : ''}
                          </span>
                        ) : (
                          <span className="text-[var(--text-faint)] text-xs">Unrated</span>
                        )}
                      </td>

                      <td className="py-3 px-3">
                        {isUnreadable ? (
                          <Badge tone="warning">⚠️ Needs Review</Badge>
                        ) : (
                          <Badge tone={r.percentage >= 75 ? 'success' : r.percentage >= 50 ? 'warning' : 'error'}>
                            {r.status || r.evaluation_status || 'Evaluated'}
                          </Badge>
                        )}
                      </td>

                      <td className="py-3 px-3 text-xs text-[var(--text-faint)] whitespace-nowrap">
                        {r.created_at ? String(r.created_at).split('T')[0].split(' ')[0] : 'Recent'}
                      </td>

                      <td className="py-3 px-3 whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleViewDetail(evalId)}
                            className="flex items-center gap-1 text-[11.5px] px-2.5 py-1"
                          >
                            <Eye size={13} />
                            <span>View</span>
                          </Button>

                          <button
                            onClick={(e) => handleDelete(evalId, e)}
                            className="p-1.5 rounded-lg border border-[var(--error-soft)] text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                            title="Delete Evaluation Record"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* EVALUATION DETAIL & TRACEABILITY MODAL */}
      {selectedEval && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <Card className="max-w-3xl w-full bg-[var(--surface)] border-2 border-[var(--accent)] shadow-2xl space-y-4 my-8 max-h-[92vh] overflow-y-auto p-6">
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <div>
                <div className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2 flex-wrap">
                  <span>{selectedEval.student_name || 'Student Evaluation'}</span>
                  <Badge tone="accent">{selectedEval.subject}</Badge>
                  <span className="text-xs text-[var(--text-faint)] font-mono">
                    ID: {selectedEval.student_id || selectedEval.roll_number || 'N/A'}
                  </span>
                  {(selectedEval.is_unreadable || selectedEval.assigned_to_teacher) && (
                    <Badge tone="warning">⚠️ Assigned to Teacher</Badge>
                  )}
                </div>
                <div className="text-[12.5px] text-[var(--text-soft)] font-medium mt-0.5">
                  Exam: <strong>{selectedEval.assessment_title || `${selectedEval.subject} Assessment`}</strong> &bull; Evaluation ID: <span className="font-mono">{selectedEval.id || selectedEval._id || 'Stored'}</span>
                </div>
              </div>
              <button
                onClick={() => setSelectedEval(null)}
                className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Score & Metadata Strip */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs bg-[var(--surface-alt)] p-3 rounded-xl border border-[var(--border)] text-center">
              <div>
                <span className="text-[var(--text-faint)] block text-[10.5px] uppercase font-bold">Marks Scored</span>
                <strong className="text-[15px] font-black text-[var(--accent)]">
                  {selectedEval.obtained_marks} / {selectedEval.total_marks}
                </strong>
              </div>
              <div>
                <span className="text-[var(--text-faint)] block text-[10.5px] uppercase font-bold">Percentage</span>
                <strong className="text-[15px] font-black text-emerald-500">
                  {selectedEval.percentage}%
                </strong>
              </div>
              <div>
                <span className="text-[var(--text-faint)] block text-[10.5px] uppercase font-bold">Assigned Grade</span>
                <strong className="text-[15px] font-black text-[var(--text)]">
                  {selectedEval.grade || 'N/A'}
                </strong>
              </div>
              <div>
                <span className="text-[var(--text-faint)] block text-[10.5px] uppercase font-bold">Evaluated Date</span>
                <strong className="text-xs font-semibold text-[var(--text-soft)]">
                  {selectedEval.created_at ? String(selectedEval.created_at).split('T')[0] : 'Recent'}
                </strong>
              </div>
            </div>

            {/* Action Center Relevance Alert */}
            {((selectedEval.total_marks || 0) - (selectedEval.obtained_marks || 0)) > 20 && (
              <div className="p-3 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] text-xs flex items-start gap-2">
                <AlertTriangle size={16} className="text-[var(--error)] shrink-0 mt-0.5" />
                <div>
                  <strong className="text-[var(--error)] block text-[11.5px] uppercase tracking-wider">Action Center Relevance: High Risk (&gt;20 Marks Lost)</strong>
                  <span className="text-[var(--text-soft)]">
                    This student lost {round2((selectedEval.total_marks || 0) - (selectedEval.obtained_marks || 0))} marks in this assessment, triggering an automatic Action Center remedial item.
                  </span>
                </div>
              </div>
            )}

            {/* Teacher Executive Summary */}
            {(selectedEval.overall_teacher_comment || selectedEval.overall_feedback) && (
              <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs space-y-1">
                <strong className="text-[var(--accent)] block text-[11px] uppercase tracking-wider">Teacher Executive Assessment:</strong>
                <p className="text-[var(--text)] leading-relaxed">{selectedEval.overall_teacher_comment || selectedEval.overall_feedback}</p>
              </div>
            )}

            {/* Teacher Mark Override Controls */}
            {role === 'teacher' && (
              <div className="p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-xs">
                <div className="flex items-center justify-between">
                  <span className="font-extrabold text-[var(--accent)]">Teacher Mark Allotment / Override:</span>
                  {!isEditingMarks ? (
                    <Button size="sm" variant="outline" onClick={() => { setIsEditingMarks(true); setCustomObtainedMarks(selectedEval.obtained_marks || ''); }}>
                      <Edit3 size={12} /> Edit Marks
                    </Button>
                  ) : (
                    <Button size="sm" variant="secondary" onClick={() => setIsEditingMarks(false)}>Cancel</Button>
                  )}
                </div>

                {isEditingMarks && (
                  <div className="flex items-center gap-2 pt-2 mt-2 border-t border-[var(--accent)]">
                    <label className="font-bold text-[var(--text)]">New Obtained Marks:</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0"
                      max={selectedEval.total_marks || 100}
                      value={customObtainedMarks}
                      onChange={(e) => setCustomObtainedMarks(e.target.value)}
                      className="w-20 px-2 py-1 border border-[var(--border-strong)] rounded text-xs font-bold bg-[var(--surface)] text-[var(--text)] text-center"
                    />
                    <span className="text-[var(--text-faint)]">/ {selectedEval.total_marks} max</span>
                    <Button size="sm" onClick={handleSaveModalOverride} disabled={savingOverride} className="ml-auto">
                      {savingOverride ? 'Saving...' : 'Save Override'}
                    </Button>
                  </div>
                )}
              </div>
            )}

            {/* Question-By-Question Detailed Traceability */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-extrabold uppercase tracking-wider text-[var(--text-faint)]">
                Question-by-Question Evaluation Audit Trail
              </h4>

              {(selectedEval.evaluations || selectedEval.questions || []).length > 0 ? (
                (selectedEval.evaluations || selectedEval.questions).map((q, idx) => {
                  const maxM = q.maximum_marks ?? q.max_marks ?? '?'
                  const awdM = q.awarded_marks ?? 0
                  const isFull = maxM > 0 && awdM >= maxM
                  const isPartial = awdM > 0 && awdM < maxM

                  return (
                    <div key={idx} className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2.5 text-xs">
                      {/* Question Header */}
                      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2 flex-wrap gap-2">
                        <div className="flex items-center gap-2">
                          <span className="font-extrabold text-[var(--text)] text-[13px]">
                            Question {q.question_number || idx + 1}
                          </span>
                          {q.is_skipped_due_to_choice ? (
                            <Badge tone="neutral">SKIPPED (ELECTIVE OR OPTION)</Badge>
                          ) : q.is_extra_choice ? (
                            <Badge tone="neutral">EXTRA ATTEMPT (HIGHER COUNTED)</Badge>
                          ) : q.answer_classification ? (
                            <Badge tone={
                              q.answer_classification === 'correct_answer' ? 'success' :
                              q.answer_classification.includes('calculation_error') ? 'warning' :
                              q.answer_classification.includes('concept') ? 'error' : 'neutral'
                            }>
                              {q.answer_classification.replace(/_/g, ' ').toUpperCase()}
                            </Badge>
                          ) : null}
                        </div>
                        <Badge tone={q.is_skipped_due_to_choice ? 'neutral' : isFull ? 'success' : isPartial ? 'warning' : 'error'}>
                          {awdM} / {maxM} marks {q.is_skipped_due_to_choice || q.is_extra_choice ? '(Not counted in total)' : ''}
                        </Badge>
                      </div>

                      {/* Official Question Text */}
                      {q.question_text && (
                        <div className="p-2 bg-[var(--surface)] rounded-lg border border-[var(--border)] font-semibold text-[var(--text)]">
                          <span className="text-[10px] uppercase font-bold text-[var(--text-faint)] block mb-0.5">Question Paper Prompt:</span>
                          {q.question_text}
                        </div>
                      )}

                      {/* Student's Actual Answer */}
                      {(q.student_answer || q.answer_summary) && (
                        <div className="space-y-0.5">
                          <span className="text-[11px] font-bold text-[var(--text-faint)] block">Student's Written Answer on Script:</span>
                          <p className="font-mono italic text-[11.5px] bg-[var(--surface)] p-2.5 rounded-lg border border-[var(--border)] text-[var(--text)]">
                            &ldquo;{q.student_answer || q.answer_summary}&rdquo;
                          </p>
                        </div>
                      )}

                      {/* Reason & Feedback: Why marks were awarded */}
                      {(q.teacher_feedback || q.evaluation_reason) && (
                        <div className="p-2.5 rounded-lg bg-[var(--accent-soft)] border border-[var(--accent)] space-y-0.5">
                          <strong className="text-[var(--accent)] text-[11px] uppercase block">Reason & Mark Allocation Feedback:</strong>
                          <p className="text-[var(--text)] leading-relaxed">{q.teacher_feedback || q.evaluation_reason}</p>
                        </div>
                      )}

                      {/* Mistakes / Missing points */}
                      {(q.what_is_incorrect?.length > 0 || q.step_or_calculation_mistake) && (
                        <div className="p-2 rounded-lg bg-[var(--error-soft)] border border-[var(--error)] space-y-0.5">
                          <strong className="text-[var(--error)] text-[10.5px] uppercase block">Identified Mistakes:</strong>
                          <p className="text-[var(--text)]">{q.step_or_calculation_mistake || (Array.isArray(q.what_is_incorrect) ? q.what_is_incorrect.join(', ') : q.what_is_incorrect)}</p>
                        </div>
                      )}

                      {/* Conceptual Misconception */}
                      {(q.conceptual_mistake || (q.misconception_detected && q.misconception)) && (
                        <div className="p-2.5 rounded-lg bg-[var(--gold-soft)] border border-[var(--gold)] space-y-0.5">
                          <strong className="text-[var(--gold)] text-[10.5px] uppercase block flex items-center gap-1">
                            <AlertTriangle size={12} />
                            <span>Diagnosed Conceptual Misconception:</span>
                          </strong>
                          <p className="text-[var(--text)] font-semibold">{q.conceptual_mistake || q.misconception}</p>
                        </div>
                      )}

                      {/* What Student Should Have Written */}
                      {(q.what_student_should_have_written || q.correct_answer_or_expected_points || q.feedback?.expected_answer) && (
                        <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-0.5">
                          <strong className="text-emerald-500 text-[10.5px] uppercase block">Expected Academic Solution:</strong>
                          <p className="text-[var(--text)] font-mono whitespace-pre-line text-[11px]">
                            {q.what_student_should_have_written || q.correct_answer_or_expected_points || q.feedback?.expected_answer}
                          </p>
                        </div>
                      )}
                    </div>
                  )
                })
              ) : (
                <div className="text-center p-6 text-xs text-[var(--text-soft)] bg-[var(--surface-alt)] rounded-xl">
                  No question-by-question breakdown attached to this record.
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
              <button
                onClick={(e) => handleDelete(selectedEval.id || selectedEval._id, e)}
                className="px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)] hover:bg-[var(--error)] hover:text-white transition-all flex items-center gap-1.5"
              >
                <Trash2 size={14} />
                <span>Delete Evaluation Record</span>
              </button>
              <Button variant="secondary" onClick={() => setSelectedEval(null)} className="ml-auto">
                Close
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}

function round2(num) {
  return Math.round(Number(num) * 100) / 100
}
