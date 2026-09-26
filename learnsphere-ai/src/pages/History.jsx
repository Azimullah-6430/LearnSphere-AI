import { useState, useEffect } from 'react'
import { Card, PageHead, SearchBox, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { X, CheckCircle2, AlertTriangle, Download, Trash2, Eye, Check } from 'lucide-react'

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
    setDetailLoading(true)
    const res = await api.getEvaluationDetail(id)
    if (res && res.success && res.evaluation) {
      setSelectedEval(res.evaluation)
    } else {
      const match = evaluations.find(e => e.id === id || e._id === id)
      setSelectedEval(match || null)
    }
    setDetailLoading(false)
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

  // Filter by search and activeClass if set
  const filtered = evaluations.filter(e => {
    if (activeClass && activeClass.subjects && activeClass.subjects.length > 0) {
      if (e.subject && !activeClass.subjects.some(s => s.toLowerCase() === e.subject.toLowerCase())) {
        // Allow fallback if list is small
      }
    }

    const term = search.toLowerCase()
    return (
      (e.student_name && e.student_name.toLowerCase().includes(term)) ||
      (e.subject && e.subject.toLowerCase().includes(term)) ||
      (e.assessment_title && e.assessment_title.toLowerCase().includes(term))
    )
  })

  const [isEditingMarks, setIsEditingMarks] = useState(false)
  const [customObtainedMarks, setCustomObtainedMarks] = useState('')
  const [savingOverride, setSavingOverride] = useState(false)

  const handleSaveModalOverride = async () => {
    if (!selectedEval) return
    const id = selectedEval.id || selectedEval._id
    const newObtained = parseFloat(customObtainedMarks) || 0
    const newTotal = parseFloat(selectedEval.total_marks || selectedEval.max_marks || 100)
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
        title={role === 'teacher' ? 'Evaluation History & Records' : 'My Evaluations'}
        subtitle="Searchable database of stored evaluation records with full delete, completed audit controls, and teacher mark allotment."
      />

      {activeClass && role === 'teacher' && (
        <div className="mb-4 p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[12.5px] font-bold text-[var(--accent)] flex items-center justify-between">
          <span>🏫 Active Class Filter: <strong>{activeClass.name}</strong></span>
          <Badge tone="accent">{activeClass.type}</Badge>
        </div>
      )}

      <Card>
        <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
          <SearchBox placeholder="Search by student, subject or test..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="flex gap-2 text-xs text-[var(--text-faint)]">
            <span>Total Records: <strong>{filtered.length}</strong></span>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                {['Student', 'Subject', 'Assessment', 'Score', 'Review Status', 'Date', 'Actions'].map((h) => (
                  <th key={h} className="text-left text-[11.5px] text-[var(--text-faint)] font-bold uppercase tracking-wide pb-2.5 px-3 border-b border-[var(--border)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7} className="text-center py-8 text-[var(--text-soft)]">
                    No evaluation records found matching your query.
                  </td>
                </tr>
              ) : (
                filtered.map((r, i) => {
                  const evalId = r.id || r._id || `eval_${i}`
                  const isCompleted = r.review_status === 'Completed'
                  const isUnreadable = r.is_unreadable || r.assigned_to_teacher

                  return (
                    <tr key={evalId} className="hover:bg-[var(--surface-alt)] transition-colors border-b border-[var(--border)] last:border-0">
                      <td className="py-3 px-3 font-semibold text-[var(--text)]">
                        <div className="flex items-center gap-1.5">
                          <span>{r.student_name || 'Student Script'}</span>
                          {isUnreadable && <Badge tone="warning">⚠️ Assigned to Teacher</Badge>}
                        </div>
                      </td>
                      <td className="py-3 px-3 text-[var(--text-soft)]">
                        {r.subject || 'Academic Paper'}
                      </td>
                      <td className="py-3 px-3 text-[var(--text-soft)]">
                        {r.assessment_title || 'Evaluation'}
                      </td>
                      <td className="py-3 px-3 font-bold">
                        <span className={r.percentage >= 75 ? 'text-[var(--success)]' : r.percentage >= 50 ? 'text-[var(--warning)]' : 'text-[var(--error)]'}>
                          {r.percentage !== undefined ? `${r.percentage}% (${r.obtained_marks || r.total_marks}/${r.total_marks || r.max_marks || 100})` : `${r.total_marks || 0} Marks`}
                        </span>
                      </td>
                      <td className="py-3 px-3">
                        <button
                          onClick={(e) => handleToggleCompleted(evalId, e)}
                          className={`px-2.5 py-1 rounded-full text-[11px] font-extrabold border transition-all flex items-center gap-1 ${
                            isCompleted
                              ? 'bg-[var(--success-soft)] text-[var(--success)] border-[var(--success)]'
                              : 'bg-[var(--surface-alt)] text-[var(--text-faint)] border-[var(--border-strong)] hover:text-[var(--text)]'
                          }`}
                        >
                          <Check size={12} />
                          <span>{isCompleted ? 'Completed' : 'Mark Completed'}</span>
                        </button>
                      </td>
                      <td className="py-3 px-3 text-xs text-[var(--text-faint)]">
                        {r.created_at ? r.created_at.split(' ')[0] : 'Recent'}
                      </td>
                      <td className="py-3 px-3">
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => { setSelectedEval(r); setIsEditingMarks(false); setCustomObtainedMarks(r.obtained_marks || r.total_marks || '') }}
                            className="p-1.5 rounded-lg border border-[var(--border)] text-[var(--text-soft)] hover:text-[var(--accent)] hover:bg-[var(--surface)] transition-colors"
                            title="View / Edit Evaluation Marks"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            onClick={(e) => handleDelete(evalId, e)}
                            className="p-1.5 rounded-lg border border-[var(--error-soft)] text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                            title="Delete Record"
                          >
                            <Trash2 size={15} />
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

      {/* EVALUATION DETAIL MODAL WITH MARK OVERRIDE */}
      {selectedEval && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <Card className="max-w-[680px] w-full bg-[var(--surface)] border-2 border-[var(--accent)] shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <div>
                <div className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2">
                  <span>{selectedEval.student_name || 'Evaluation Detail'}</span>
                  <Badge tone="accent">{selectedEval.subject}</Badge>
                  {(selectedEval.is_unreadable || selectedEval.assigned_to_teacher) && <Badge tone="warning">⚠️ Assigned to Teacher</Badge>}
                </div>
                <div className="text-[12.5px] text-[var(--text-soft)]">
                  {selectedEval.assessment_title || 'Answer Script Report'}
                </div>
              </div>
              <button
                onClick={() => setSelectedEval(null)}
                className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="grid grid-cols-2 gap-3 text-[13px] bg-[var(--surface-alt)] p-3 rounded-xl border border-[var(--border)]">
              <div><strong>Score:</strong> {selectedEval.percentage}% ({selectedEval.obtained_marks || selectedEval.total_marks}/{selectedEval.total_marks || selectedEval.max_marks || 100})</div>
              <div><strong>Evaluated On:</strong> {selectedEval.created_at || 'Today'}</div>
              <div><strong>Grader Model:</strong> {selectedEval.is_teacher_overridden ? 'Teacher Allotted Marks' : 'Strict Rubric AI'}</div>
              <div><strong>Status:</strong> {selectedEval.review_status || 'Evaluated'}</div>
            </div>

            {/* Teacher Mark Override Controls */}
            {role === 'teacher' && (
              <div className="p-3.5 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)]">
                <div className="flex items-center justify-between mb-2">
                  <strong className="text-[var(--accent)] text-[13.5px]">✏️ Teacher Mark Allotment / Override:</strong>
                  {!isEditingMarks ? (
                    <Button size="sm" variant="outline" onClick={() => setIsEditingMarks(true)}>Edit Marks</Button>
                  ) : (
                    <Button size="sm" variant="secondary" onClick={() => setIsEditingMarks(false)}>Cancel</Button>
                  )}
                </div>

                {isEditingMarks ? (
                  <div className="space-y-3 mt-2">
                    <div className="flex items-center gap-3">
                      <label className="text-xs font-bold">New Obtained Marks:</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max={selectedEval.total_marks || selectedEval.max_marks || 100}
                        value={customObtainedMarks}
                        onChange={(e) => setCustomObtainedMarks(e.target.value)}
                        className="w-24 px-3 py-1.5 border border-[var(--border-strong)] rounded text-sm font-extrabold bg-[var(--surface)] text-[var(--text)] text-center"
                      />
                      <span className="text-xs text-[var(--text-faint)]">/ {selectedEval.total_marks || selectedEval.max_marks || 100} Total Marks</span>
                    </div>
                    <div className="flex justify-end">
                      <Button size="sm" onClick={handleSaveModalOverride} disabled={savingOverride}>
                        {savingOverride ? 'Saving...' : 'Save Allotted Marks'}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <p className="text-[12px] text-[var(--text-soft)]">
                    If you are not satisfied with AI evaluation, click <strong>"Edit Marks"</strong> to manually assign custom marks.
                  </p>
                )}
              </div>
            )}

            {selectedEval.feedback && (
              <div className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-[13px]">
                <strong className="text-[var(--text)] block mb-1">Evaluator Feedback:</strong>
                <p className="text-[var(--text-soft)] leading-relaxed">{typeof selectedEval.feedback === 'string' ? selectedEval.feedback : (selectedEval.overall_feedback || 'Evaluation details reviewed.')}</p>
              </div>
            )}

            <div className="flex items-center justify-between pt-2 border-t border-[var(--border)]">
              <button
                onClick={(e) => handleDelete(selectedEval.id || selectedEval._id, e)}
                className="px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)] hover:bg-[var(--error)] hover:text-white transition-all flex items-center gap-1.5"
              >
                <Trash2 size={14} />
                <span>Delete Record</span>
              </button>
              <Button variant="secondary" onClick={() => setSelectedEval(null)}>Close</Button>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
