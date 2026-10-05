import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHead, Card, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { CheckCircle2, Users, Lightbulb, ShieldAlert, Trash2, Check, Sparkles, BookOpen, AlertCircle } from 'lucide-react'

export default function MisconceptionMap() {
  const { activeClass } = useApp()
  const navigate = useNavigate()
  const [misconceptions, setMisconceptions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadMisconceptions() {
      setLoading(true)
      try {
        const res = await api.getMisconceptions()
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
  }, [])

  // Delete Misconception
  const handleDelete = (id) => {
    if (window.confirm("Delete this misconception record permanently?")) {
      setMisconceptions(prev => prev.filter(m => m.id !== id))
    }
  }

  // Toggle Completed / Resolved Status
  const handleToggleResolved = (id) => {
    setMisconceptions(prev => prev.map(m => {
      if (m.id === id) {
        const isDone = m.status === 'Completed / Resolved'
        return { ...m, status: isDone ? 'Active' : 'Completed / Resolved' }
      }
      return m
    }))
  }

  const handleMasterInTrainer = (m) => {
    // Navigate to Trainer with pre-selected subject and concept
    navigate('/app/trainer', {
      state: {
        subject: m.subject,
        concept: m.concept || m.actual_misconception
      }
    })
  }

  const hasData = misconceptions.length > 0

  return (
    <>
      <PageHead
        title="Evidence-Based Misconception Map"
        subtitle="Identifies genuine conceptual misunderstandings grounded in evaluation evidence. Calculation & arithmetic mistakes are strictly excluded."
      />

      {activeClass && (
        <div className="mb-4 p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[12.5px] font-bold text-[var(--accent)] flex items-center justify-between">
          <span>🏫 Active Class Filter: <strong>{activeClass.name}</strong></span>
          <Badge tone="accent">{activeClass.type}</Badge>
        </div>
      )}

      {/* Strict Mistake != Misconception Rule Banner */}
      <div className="mb-6 p-4 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[13px] text-[var(--text)] flex items-start gap-3 shadow-sm">
        <ShieldAlert size={22} className="text-[var(--accent)] shrink-0 mt-0.5" />
        <div>
          <div className="font-extrabold text-[var(--accent)] text-[14px] mb-1">
            Strict Standard: Mistake &ne; Misconception
          </div>
          <div className="text-[12.5px] text-[var(--text-soft)] leading-relaxed">
            Arithmetic slips, spelling mistakes, or misread questions are <strong>never</strong> classified as misconceptions.
            Only persistent evidence demonstrating a flawed underlying model, principle, or method is recorded here.
          </div>
        </div>
      </div>

      {!hasData ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <CheckCircle2 size={42} className="text-emerald-600 mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">No Conceptual Misconceptions Flagged</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto">
            When evaluation evidence proves a student has misunderstood an underlying concept, detailed evidence cards will automatically appear here.
          </p>
        </Card>
      ) : (
        <div className="space-y-5">
          {misconceptions.map((m, i) => {
            const studentName = m.student_name || (m.student_names && m.student_names[0]) || "Student"
            const affectedList = m.student_names || [studentName]
            const isHigh = (m.confidence || m.severity) === 'High'
            const isResolved = m.status === 'Completed / Resolved'
            const occurrences = m.occurrences || 1
            const assessmentsList = m.assessments || []

            return (
              <Card key={m.id || i} className={`relative transition-all shadow-md border-l-4 ${isResolved ? 'opacity-75 bg-[var(--surface-alt)] border-l-gray-400' : isHigh ? 'border-l-[var(--error)] hover:border-[var(--accent-dim)]' : 'border-l-[var(--gold)] hover:border-[var(--accent-dim)]'}`}>
                <div className="space-y-4">
                  
                  {/* Top Header: Student, Subject, Topic, Confidence */}
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-2 border-b border-[var(--border)] pb-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="w-8 h-8 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold text-[12px] flex items-center justify-center shrink-0">
                        {studentName.split(' ').map(n => n[0]).join('')}
                      </span>
                      <div>
                        <div className="text-[16px] font-extrabold text-[var(--text)] flex items-center gap-2">
                          <span>{studentName}</span>
                          <span className="text-[13px] font-bold text-[var(--accent)]">— {m.subject}</span>
                        </div>
                        <div className="text-[12px] text-[var(--text-soft)] font-semibold">
                          Topic: <strong>{m.concept || m.topic}</strong> &bull; {m.question_num || `Question ${i + 1}`}
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

                  {/* Highlighted Evidence Quote Banner */}
                  <div className="p-3.5 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] text-[13px] leading-relaxed">
                    <div className="font-extrabold text-[var(--error)] mb-1 flex items-center gap-1.5 text-[12.5px] uppercase tracking-wider">
                      <AlertCircle size={15} />
                      <span>Evidence Diagnostic:</span>
                    </div>
                    <div className="italic text-[13.5px] font-semibold text-[var(--text)]">
                      &ldquo;{m.evidence || `${studentName}'s reasoning in ${m.question_num || 'evaluations'} indicates a persistent misunderstanding of ${m.concept}.`}&rdquo;
                    </div>
                  </div>

                  {/* Actual Misconception vs Correct Concept Comparison Table */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-1 text-[12.5px]">
                      <div className="font-extrabold text-[var(--error)] text-[11px] uppercase tracking-wider flex items-center gap-1">
                        <span>❌ Actual Misconception Believed:</span>
                      </div>
                      <div className="font-semibold text-[var(--text)] leading-snug">
                        {m.actual_misconception || m.description}
                      </div>
                      {m.student_reasoning && (
                        <div className="pt-2 text-[11.5px] text-[var(--text-soft)] font-mono bg-[var(--surface)] p-2 rounded-lg border border-[var(--border)] mt-1">
                          <strong>Student Reasoning:</strong> &ldquo;{m.student_reasoning}&rdquo;
                        </div>
                      )}
                    </div>

                    <div className="p-3.5 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] space-y-1 text-[12.5px]">
                      <div className="font-extrabold text-[var(--success)] text-[11px] uppercase tracking-wider flex items-center gap-1">
                        <span>✅ Correct Academic Concept:</span>
                      </div>
                      <div className="font-semibold text-[var(--text)] leading-snug">
                        {m.correct_concept || `Standard governing principles of ${m.concept || m.subject}.`}
                      </div>
                      {m.assessments && m.assessments.length > 0 && (
                        <div className="pt-2 text-[11.5px] text-[var(--text-soft)] font-semibold mt-1">
                          <strong>Detected in:</strong> {m.assessments.join(', ')}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Teacher Remedy & Class Context */}
                  {m.remedy && (
                    <div className="p-3 rounded-xl bg-[var(--gold-soft)] border border-[var(--gold)] text-[12.5px] font-medium text-[var(--text)] flex items-start gap-2">
                      <Lightbulb size={16} className="text-[var(--gold)] shrink-0 mt-0.5" />
                      <div>
                        <strong className="text-[var(--gold)]">Recommended Action Plan:</strong> {m.remedy}
                      </div>
                    </div>
                  )}

                  {/* Footer Controls: Personal Trainer CTA + Status Controls */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-3 border-t border-[var(--border)]">
                    <button
                      onClick={() => handleMasterInTrainer(m)}
                      className="px-4 py-2 rounded-xl text-[12.5px] font-extrabold bg-gradient-to-r from-[var(--accent)] to-[var(--accent-dim)] text-white hover:shadow-md transition-all flex items-center gap-2"
                    >
                      <Sparkles size={15} />
                      <span>Master in Personal Trainer</span>
                    </button>

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
    </>
  )
}

