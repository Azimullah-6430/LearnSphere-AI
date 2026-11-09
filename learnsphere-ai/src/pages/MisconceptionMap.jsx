import { useState, useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { PageHead, Card, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { CheckCircle2, Lightbulb, ShieldAlert, Trash2, Check, Sparkles, BookOpen, AlertCircle, FileText, X, Filter } from 'lucide-react'

export default function MisconceptionMap() {
  const { activeClass } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [misconceptions, setMisconceptions] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedEvidence, setSelectedEvidence] = useState(null)
  const [conceptFilter, setConceptFilter] = useState(
    location.state?.concept || new URLSearchParams(location.search).get('concept') || ''
  )

  useEffect(() => {
    const c = location.state?.concept || new URLSearchParams(location.search).get('concept') || ''
    if (c) setConceptFilter(c)
  }, [location.search, location.state])

  useEffect(() => {
    async function loadMisconceptions() {
      setLoading(true)
      try {
        const params = activeClass?.id ? { class_id: activeClass.id } : {}
        const res = await api.getMisconceptions(params)
        if (res && res.success && Array.isArray(res.misconceptions)) {
          setMisconceptions(res.misconceptions)
        } else {
          setMisconceptions([])
        }
      } catch (err) {
        setMisconceptions([])
      } finally {
        setLoading(false)
      }
    }
    loadMisconceptions()
  }, [activeClass?.id])

  useEffect(() => {
    if (!selectedEvidence) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setSelectedEvidence(null)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [selectedEvidence])

  // Delete Misconception
  const handleDelete = async (id) => {
    if (window.confirm("Delete this misconception record permanently?")) {
      setMisconceptions(prev => prev.filter(m => m.id !== id))
      try {
        await api.deleteMisconception(id)
      } catch (err) {
        console.warn("Delete misconception notice:", err)
      }
    }
  }

  // Toggle Completed / Resolved Status
  const handleToggleResolved = async (id) => {
    let nextStatus = 'Completed / Resolved'
    setMisconceptions(prev => prev.map(m => {
      if (m.id === id) {
        const isDone = m.status === 'Completed / Resolved'
        nextStatus = isDone ? 'Active' : 'Completed / Resolved'
        return { ...m, status: nextStatus }
      }
      return m
    }))
    try {
      await api.updateMisconception(id, { status: nextStatus })
    } catch (err) {
      console.warn("Update misconception status notice:", err)
    }
  }

  const handleMasterInTrainer = (m) => {
    navigate('/app/trainer', {
      state: {
        subject: m.subject,
        concept: m.concept || m.identified_concept || m.actual_misconception
      }
    })
  }

  const filteredMisconceptions = misconceptions.filter(m => {
    if (!conceptFilter.trim()) return true
    const target = conceptFilter.trim().toLowerCase()
    const match = (
      (m.concept || '') + ' ' +
      (m.identified_concept || '') + ' ' +
      (m.actual_misconception || '') + ' ' +
      (m.topic || '') + ' ' +
      (m.student_name || '')
    ).toLowerCase()
    return match.includes(target)
  })

  const hasData = filteredMisconceptions.length > 0

  return (
    <>
      <PageHead
        title="Misconception Map"
        subtitle="Catalog of diagnosed conceptual misunderstandings extracted from evaluated student answer scripts."
      />

      {activeClass && (
        <div className="mb-5 p-3.5 rounded-2xl bg-[var(--accent-soft)] border border-[var(--accent)] text-xs font-bold text-[var(--accent)] flex items-center justify-between shadow-xs">
          <span>🏫 Active Class Filter: <strong className="text-[var(--text)]">{activeClass.name}</strong></span>
          <Badge tone="accent">{activeClass.type}</Badge>
        </div>
      )}

      {conceptFilter && (
        <div className="mb-5 p-3.5 rounded-2xl bg-[var(--gold-soft)] border border-[var(--gold)] text-xs font-bold text-[var(--gold)] flex items-center justify-between shadow-xs">
          <div className="flex items-center gap-2">
            <Filter size={15} />
            <span>Filtered by concept evidence: <strong className="text-[var(--text)]">&ldquo;{conceptFilter}&rdquo;</strong></span>
          </div>
          <button
            onClick={() => setConceptFilter('')}
            className="px-2.5 py-1 rounded-lg bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] hover:bg-[var(--surface-alt)] font-bold text-[11px] cursor-pointer"
          >
            Clear Filter
          </button>
        </div>
      )}

      {!hasData ? (
        <Card className="p-12 text-center my-6 border-dashed border-2">
          <CheckCircle2 size={44} className="text-emerald-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1 text-[var(--text)]">
            {conceptFilter ? "No Misconceptions Match This Concept" : "No Conceptual Misconceptions Flagged"}
          </h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
            {conceptFilter
              ? `No evaluated records match "${conceptFilter}". Try resetting your filter to view all diagnosed items.`
              : "When evaluation evidence proves a student has misunderstood an underlying concept, detailed evidence cards will automatically appear here."}
          </p>
          {conceptFilter && (
            <div className="mt-4">
              <Button onClick={() => setConceptFilter('')}>View All Misconceptions</Button>
            </div>
          )}
        </Card>
      ) : (
        <div className="space-y-5">
          {filteredMisconceptions.map((m, i) => {
            const studentName = m.student_name || (m.student_names && m.student_names[0]) || "Student"
            const isHigh = (m.confidence || m.severity) === 'High'
            const isResolved = m.status === 'Completed / Resolved'
            const occurrences = m.occurrences || 1
            const qNum = m.question_number || m.question_num || `Q${i + 1}`

            return (
              <Card key={m.id || i} className={`relative transition-all shadow-sm border-l-4 ${isResolved ? 'opacity-75 bg-[var(--surface-alt)] border-l-gray-400' : isHigh ? 'border-l-[var(--error)] hover:border-[var(--accent-dim)]' : 'border-l-[var(--gold)] hover:border-[var(--accent-dim)]'}`}>
                <div className="space-y-4">
                  
                  {/* Top Header: Student, Subject, Question, Marks, Confidence */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3 border-b border-[var(--border)] pb-3.5">
                    <div className="flex items-center gap-3 flex-wrap">
                      <span className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold text-xs flex items-center justify-center shrink-0">
                        {studentName.split(' ').map(n => n[0]).join('')}
                      </span>
                      <div>
                        <div className="text-base font-extrabold text-[var(--text)] flex items-center gap-2 flex-wrap">
                          <span>{studentName}</span>
                          <span className="text-xs font-bold text-[var(--accent)]">— {m.subject}</span>
                          {m.awarded_marks !== undefined && m.maximum_marks !== undefined && (
                            <span className="text-xs font-semibold text-[var(--text-faint)]">
                              ({m.awarded_marks}/{m.maximum_marks} marks)
                            </span>
                          )}
                        </div>
                        <div className="text-xs text-[var(--text-soft)] font-semibold mt-0.5">
                          Concept: <strong>{m.identified_concept || m.concept || m.topic}</strong> &bull; {qNum}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <Badge tone={isHigh ? 'error' : 'warning'}>
                        Confidence: {m.confidence || 'High'}
                      </Badge>
                      <Badge tone="accent">
                        Occurrences: {occurrences} {occurrences === 1 ? 'assessment' : 'assessments'}
                      </Badge>
                      {isResolved && <Badge tone="success">✅ Resolved</Badge>}
                    </div>
                  </div>

                  {/* Performance Summary Banner */}
                  {m.performance_summary && (
                    <div className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs space-y-2">
                      <div className="flex items-center justify-between gap-2 border-b border-[var(--border)] pb-1.5 flex-wrap">
                        <span className="font-extrabold text-[11.5px] text-[var(--accent)] flex items-center gap-1.5">
                          <Sparkles size={13} />
                          <span>Performance & Diagnostic Profile</span>
                        </span>
                        {m.performance_summary.percentage !== undefined && (
                          <span className="text-[11px] font-bold text-[var(--text-soft)]">
                            Score: <strong className="text-[var(--text)]">{m.performance_summary.percentage}%</strong>
                          </span>
                        )}
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                        {Array.isArray(m.performance_summary.strengths) && m.performance_summary.strengths.length > 0 && (
                          <div className="text-[11px]">
                            <strong className="text-[var(--success)]">Strengths: </strong>
                            <span>{m.performance_summary.strengths.join(', ')}</span>
                          </div>
                        )}
                        {m.performance_summary.recommended_next_practice && (
                          <div className="text-[11px]">
                            <strong className="text-[var(--accent)]">Practice Focus: </strong>
                            <span>{m.performance_summary.recommended_next_practice}</span>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Diagnosed Concept Groups (1 consolidated student record) */}
                  {Array.isArray(m.concept_groups) && m.concept_groups.length > 0 ? (
                    <div className="space-y-4">
                      {m.concept_groups.map((cg, cgIdx) => (
                        <div key={cgIdx} className="p-4 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-3">
                          {/* Concept Group Header */}
                          <div className="flex items-center justify-between flex-wrap gap-2 border-b border-[var(--border)] pb-2.5">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="w-6 h-6 rounded-lg bg-[var(--accent)] text-white font-extrabold text-xs flex items-center justify-center">
                                {cgIdx + 1}
                              </span>
                              <strong className="text-sm font-extrabold text-[var(--text)]">
                                {cg.concept}
                              </strong>
                              {cg.error_label && (
                                <span className="text-[10.5px] px-2 py-0.5 rounded bg-[var(--surface)] text-[var(--accent)] border border-[var(--accent-dim)] font-bold">
                                  {cg.error_label}
                                </span>
                              )}
                              {cg.evidence_status && (
                                <span className={`text-[10px] px-2 py-0.5 rounded font-bold ${
                                  cg.evidence_status === 'VERIFIED'
                                    ? 'bg-[var(--success-soft)] text-[var(--success)] border border-[var(--success)]/40'
                                    : 'bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning)]/40'
                                }`}>
                                  {cg.evidence_status === 'VERIFIED' ? '✓ Evidence Supported' : '⚠ Needs Review'}
                                </span>
                              )}
                              {cg.related_questions && cg.related_questions.length > 0 && (
                                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-[var(--surface)] text-[var(--accent)] border border-[var(--accent-dim)] font-bold">
                                  Affecting: Q{cg.related_questions.join(', Q')}
                                </span>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5">
                              <button
                                onClick={() => navigate('/app/trainer', { state: { subject: m.subject, concept: cg.concept } })}
                                className="px-2.5 py-1 rounded-lg text-[11px] font-extrabold bg-[var(--accent-soft)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white transition-colors flex items-center gap-1"
                              >
                                <Sparkles size={12} />
                                <span>Master This Concept</span>
                              </button>
                            </div>
                          </div>

                          {/* Flawed Reasoning vs Correct Model */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            <div className="p-3.5 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] space-y-1.5 text-xs">
                              <div className="font-extrabold text-[var(--error)] uppercase tracking-wider flex items-center gap-1">
                                <span>❌ Diagnosed Conceptual Flaw:</span>
                              </div>
                              <p className="font-semibold text-[var(--text)] leading-relaxed">
                                {cg.actual_misconception || cg.misconception}
                              </p>
                            </div>

                            <div className="p-3.5 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] space-y-1.5 text-xs">
                              <div className="font-extrabold text-[var(--success)] uppercase tracking-wider flex items-center gap-1">
                                <span>✅ Correct Academic Model:</span>
                              </div>
                              <p className="font-semibold text-[var(--text)] leading-relaxed">
                                {cg.correct_understanding || `Standard curriculum scientific principles of ${cg.concept}.`}
                              </p>
                            </div>
                          </div>

                          {/* Nested Question Evidence */}
                          {Array.isArray(cg.questions) && cg.questions.length > 0 && (
                            <div className="space-y-2 pt-1">
                              <span className="text-[10.5px] font-extrabold uppercase tracking-wider text-[var(--text-faint)] block">
                                Supporting Question Evidence ({cg.questions.length}):
                              </span>
                              <div className="space-y-2">
                                {cg.questions.map((q, qIdx) => (
                                  <div key={qIdx} className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs space-y-1.5">
                                    <div className="flex items-center justify-between flex-wrap gap-2">
                                      <span className="font-extrabold text-[var(--accent)] text-[11.5px]">
                                        Question {q.question_number}
                                      </span>
                                      {q.awarded_marks !== undefined && q.maximum_marks !== undefined && (
                                        <span className="text-[11px] font-semibold text-[var(--text-faint)]">
                                          Score: <strong>{q.awarded_marks} / {q.maximum_marks} marks</strong>
                                        </span>
                                      )}
                                    </div>
                                    {q.exact_question && (
                                      <p className="text-[var(--text)] font-semibold text-[11.5px] leading-snug">
                                        &ldquo;{q.exact_question}&rdquo;
                                      </p>
                                    )}
                                    {q.student_answer && (
                                      <div className="font-mono text-[11px] text-[var(--text-soft)] italic bg-[var(--surface-alt)] p-2 rounded-lg border border-[var(--border)]">
                                        <strong>Student Wrote:</strong> &ldquo;{q.student_answer}&rdquo;
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Remediation for this concept */}
                          {cg.remedy && (
                            <div className="p-3 rounded-xl bg-[var(--gold-soft)] border border-[var(--gold)] text-[12px] font-medium text-[var(--text)] flex items-start gap-2">
                              <Lightbulb size={15} className="text-[var(--gold)] shrink-0 mt-0.5" />
                              <div>
                                <strong className="text-[var(--gold)]">Recommended Remediation:</strong> {cg.remedy}
                              </div>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    /* Fallback Single Question View */
                    <>
                      {/* Exact Question Text */}
                      {m.exact_question && (
                        <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs">
                          <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block mb-1">Evaluated Question ({qNum}):</span>
                          <p className="text-[var(--text)] font-semibold leading-relaxed">{m.exact_question}</p>
                        </div>
                      )}

                      {/* Highlighted Evidence Quote Banner */}
                      <div className="p-4 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] text-xs leading-relaxed">
                        <div className="font-extrabold text-[var(--error)] mb-1 flex items-center gap-1.5 uppercase tracking-wider">
                          <AlertCircle size={15} />
                          <span>Script Evidence Diagnostic:</span>
                        </div>
                        <div className="italic text-sm font-semibold text-[var(--text)]">
                          &ldquo;{m.evidence || `${studentName}'s written response in ${qNum} demonstrates a conceptual misunderstanding of ${m.identified_concept || m.concept}.`}&rdquo;
                        </div>
                      </div>

                      {/* Actual Misconception vs Correct Concept Comparison Table */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                        <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-1.5 text-xs">
                          <div className="font-extrabold text-[var(--error)] uppercase tracking-wider flex items-center gap-1">
                            <span>❌ Actual Flawed Reasoning:</span>
                          </div>
                          <div className="font-semibold text-[var(--text)] leading-relaxed">
                            {m.actual_misconception || m.misconception || m.description}
                          </div>
                          {(m.student_answer || m.student_reasoning) && (
                            <div className="pt-2 text-xs text-[var(--text-soft)] font-mono bg-[var(--surface)] p-2.5 rounded-xl border border-[var(--border)] mt-1.5">
                              <strong>Student Wrote:</strong> &ldquo;{m.student_answer || m.student_reasoning}&rdquo;
                            </div>
                          )}
                        </div>

                        <div className="p-4 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] space-y-1.5 text-xs">
                          <div className="font-extrabold text-[var(--success)] uppercase tracking-wider flex items-center gap-1">
                            <span>✅ Correct Academic Model:</span>
                          </div>
                          <div className="font-semibold text-[var(--text)] leading-relaxed">
                            {m.correct_understanding || m.correct_concept || `Standard scientific principles of ${m.identified_concept || m.concept || m.subject}.`}
                          </div>
                          {m.assessments && m.assessments.length > 0 && (
                            <div className="pt-2 text-xs text-[var(--text-soft)] font-semibold mt-1.5">
                              <strong>Detected in:</strong> {m.assessments.join(', ')}
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Teacher Remedy & Class Context */}
                      {(m.recommended_remediation || m.remedy) && (
                        <div className="p-3 rounded-xl bg-[var(--gold-soft)] border border-[var(--gold)] text-[12.5px] font-medium text-[var(--text)] flex items-start gap-2">
                          <Lightbulb size={16} className="text-[var(--gold)] shrink-0 mt-0.5" />
                          <div>
                            <strong className="text-[var(--gold)]">Recommended Remediation:</strong> {m.recommended_remediation || m.remedy}
                          </div>
                        </div>
                      )}
                    </>
                  )}

                  {/* Footer Controls */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[var(--border)]">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleMasterInTrainer(m)}
                        className="px-4 py-2 rounded-xl text-[12.5px] font-extrabold bg-gradient-to-r from-[var(--accent)] to-[var(--accent-dim)] text-white hover:shadow-md transition-all flex items-center gap-2"
                      >
                        <Sparkles size={15} />
                        <span>Master in Personal Trainer</span>
                      </button>

                      <button
                        onClick={() => setSelectedEvidence(m)}
                        className="px-3.5 py-2 rounded-xl text-[12px] font-bold border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] flex items-center gap-1.5"
                      >
                        <FileText size={14} />
                        <span>View Evaluation Evidence</span>
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleToggleResolved(m.id)}
                        className={`px-3.5 py-1.5 rounded-lg text-[12px] font-bold border transition-colors flex items-center gap-1.5 ${
                          isResolved
                            ? 'bg-[var(--success-soft)] text-[var(--success)] border-[var(--success)]'
                            : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)]'
                        }`}
                      >
                        <Check size={14} />
                        <span>{isResolved ? 'Completed / Resolved' : 'Mark Completed'}</span>
                      </button>

                      <button
                        onClick={() => handleDelete(m.id)}
                        className="px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)] hover:bg-[var(--error)] hover:text-white transition-all flex items-center gap-1.5"
                        title="Delete Misconception"
                      >
                        <Trash2 size={14} />
                        <span>Delete</span>
                      </button>
                    </div>
                  </div>

                </div>
              </Card>
            )
          })}
        </div>
      )}

      {/* Evidence Modal */}
      {selectedEvidence && (
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setSelectedEvidence(null); }}
        >
          <div 
            role="dialog"
            aria-modal="true"
            aria-labelledby="evidence-modal-title"
            className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <div>
                <h3 id="evidence-modal-title" className="text-base font-extrabold text-[var(--text)]">
                  Evaluation Evidence: {selectedEvidence.student_name}
                </h3>
                <p className="text-xs text-[var(--text-soft)]">
                  {selectedEvidence.subject} &bull; {selectedEvidence.question_number || selectedEvidence.question_num}
                </p>
              </div>
              <button 
                onClick={() => setSelectedEvidence(null)} 
                aria-label="Close evaluation evidence"
                className="p-1 rounded-lg text-[var(--text-faint)] hover:text-[var(--text)]"
              >
                <X size={18} />
              </button>
            </div>

            {Array.isArray(selectedEvidence.concept_groups) && selectedEvidence.concept_groups.length > 0 ? (
              <div className="space-y-4">
                {selectedEvidence.concept_groups.map((cg, i) => (
                  <div key={i} className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-3 text-xs">
                    <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
                      <strong className="text-sm font-extrabold text-[var(--accent)]">
                        {cg.concept}
                      </strong>
                      {cg.related_questions && (
                        <span className="font-mono text-[11px] px-2 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)] text-[var(--text-soft)]">
                          Questions: Q{cg.related_questions.join(', Q')}
                        </span>
                      )}
                    </div>

                    <div className="p-3 bg-[var(--error-soft)] rounded-lg border border-[var(--error)] space-y-1">
                      <span className="font-bold text-[var(--error)] block uppercase tracking-wider text-[10.5px]">Identified Conceptual Misunderstanding:</span>
                      <p className="font-semibold text-[var(--text)] leading-relaxed">{cg.actual_misconception || cg.misconception}</p>
                    </div>

                    <div className="p-3 bg-[var(--success-soft)] rounded-lg border border-[var(--success)] space-y-1">
                      <span className="font-bold text-[var(--success)] block uppercase tracking-wider text-[10.5px]">What the Student Should Have Understood:</span>
                      <p className="font-medium text-[var(--text)] leading-relaxed">{cg.correct_understanding}</p>
                    </div>

                    {Array.isArray(cg.questions) && cg.questions.length > 0 && (
                      <div className="space-y-2 pt-1">
                        <span className="font-bold uppercase tracking-wider text-[10.5px] text-[var(--text-faint)] block">Question Scripts & Student Answers:</span>
                        {cg.questions.map((q, qi) => (
                          <div key={qi} className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)] space-y-1">
                            <div className="flex items-center justify-between text-[11px]">
                              <span className="font-extrabold text-[var(--accent)]">Question {q.question_number}</span>
                              {q.awarded_marks !== undefined && q.maximum_marks !== undefined && (
                                <span className="font-semibold text-[var(--text-faint)]">Score: {q.awarded_marks}/{q.maximum_marks} marks</span>
                              )}
                            </div>
                            {q.exact_question && (
                              <p className="font-medium text-[var(--text)] text-[11.5px]">&ldquo;{q.exact_question}&rdquo;</p>
                            )}
                            {q.student_answer && (
                              <p className="font-mono text-[11px] italic text-[var(--text-soft)] bg-[var(--surface-alt)] p-2 rounded border border-[var(--border)]">
                                <strong>Written:</strong> &ldquo;{q.student_answer}&rdquo;
                              </p>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <>
                {selectedEvidence.exact_question && (
                  <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs space-y-1">
                    <span className="font-bold text-[var(--accent)] block">Official Question Text:</span>
                    <p className="text-[var(--text)] leading-relaxed">{selectedEvidence.exact_question}</p>
                  </div>
                )}

                <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs space-y-1">
                  <span className="font-bold text-[var(--text-faint)] block">Student Script Response:</span>
                  <p className="text-[var(--text)] leading-relaxed italic font-mono bg-[var(--surface)] p-2.5 rounded-lg border border-[var(--border)]">
                    {selectedEvidence.student_answer || selectedEvidence.student_reasoning || selectedEvidence.evidence}
                  </p>
                </div>

                <div className="p-3 bg-[var(--error-soft)] rounded-xl border border-[var(--error)] text-xs space-y-1">
                  <span className="font-bold text-[var(--error)] block">Identified Conceptual Misunderstanding:</span>
                  <p className="text-[var(--text)] leading-relaxed font-semibold">
                    {selectedEvidence.actual_misconception || selectedEvidence.misconception || selectedEvidence.description}
                  </p>
                </div>

                <div className="p-3 bg-[var(--success-soft)] rounded-xl border border-[var(--success)] text-xs space-y-1">
                  <span className="font-bold text-[var(--success)] block">What the Student Should Have Understood:</span>
                  <p className="text-[var(--text)] leading-relaxed">
                    {selectedEvidence.correct_understanding || selectedEvidence.correct_concept}
                  </p>
                </div>
              </>
            )}

            <div className="flex justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setSelectedEvidence(null)}>Close</Button>
              {selectedEvidence.evaluation_id && (
                <Button onClick={() => navigate('/app/history')}>
                  View Full Evaluation History
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}

