import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { getDynamicSubjects } from '../data/syllabusData.js'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import {
  UploadCloud, FileText, CheckCircle2, AlertTriangle, Loader2,
  Award, Brain, RotateCcw, ChevronRight, BookOpen, AlertCircle,
  Sparkles, History, Check, X, ShieldAlert, Layers
} from 'lucide-react'

const STAGES = [
  'Extracting Question Paper & Maximum Marks...',
  'Extracting Student Answer Script Content...',
  'Matching Questions & Answer Order...',
  'Evaluating Answers against Academic Rubric...',
  'Running Strict Multi-Level Quality & Fraud Verification...',
  'Finalizing Teacher-Style Self-Evaluation Report...'
]

export default function SelfEvaluation() {
  const { user, syllabusData, recordActivity } = useApp()
  const navigate = useNavigate()
  const activeProfile = user

  const subjects = getDynamicSubjects(activeProfile, syllabusData)
  const hasSubjects = subjects.length > 0
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)

  // Upload state
  const [qpRawFile, setQpRawFile] = useState(null)
  const [qpFileName, setQpFileName] = useState('')
  const [ansRawFile, setAnsRawFile] = useState(null)
  const [ansFileName, setAnsFileName] = useState('')
  const [rubricRawFile, setRubricRawFile] = useState(null)
  const [rubricFileName, setRubricFileName] = useState('')

  const [selectedSubject, setSelectedSubject] = useState(user?.subjects?.[0] || '')
  const [customSubject, setCustomSubject] = useState('')

  // Status & Results
  const [processing, setProcessing] = useState(false)
  const [currentStage, setCurrentStage] = useState(0)
  const [evalResult, setEvalResult] = useState(null)
  const [evalId, setEvalId] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  const timerRef = useRef(null)

  const handleQpUpload = (e) => {
    if (e.target.files[0]) {
      const file = e.target.files[0]
      setQpRawFile(file)
      setQpFileName(file.name)
    }
  }

  const handleAnsUpload = (e) => {
    if (e.target.files[0]) {
      const file = e.target.files[0]
      setAnsRawFile(file)
      setAnsFileName(file.name)
    }
  }

  const handleRubricUpload = (e) => {
    if (e.target.files[0]) {
      const file = e.target.files[0]
      setRubricRawFile(file)
      setRubricFileName(file.name)
    }
  }

  const handleStartSelfEval = async () => {
    if (!qpRawFile) {
      setErrorMsg('Please upload a Question Paper file first.')
      return
    }
    if (!ansRawFile) {
      setErrorMsg('Please upload your Answer Script file.')
      return
    }

    setProcessing(true)
    setErrorMsg('')
    setEvalResult(null)
    setCurrentStage(0)

    timerRef.current = setInterval(() => {
      setCurrentStage((prev) => (prev + 1 < STAGES.length ? prev + 1 : prev))
    }, 900)

    try {
      const formData = new FormData()
      const effectiveSubject = selectedSubject || customSubject || 'General'
      formData.append('subject', effectiveSubject)
      formData.append('student_name', user?.name || 'Student')
      formData.append('roll_number', user?.roll_number || user?.id || 'N/A')
      formData.append('assessment_title', `${effectiveSubject} Self Evaluation`)
      formData.append('role', 'student')
      formData.append('level', activeProfile?.level || 'Standard')
      formData.append('board', activeProfile?.board || '')
      formData.append('stream', activeProfile?.stream || '')

      formData.append('question_paper', qpRawFile)
      formData.append('answer_script', ansRawFile)
      if (rubricRawFile) {
        formData.append('rubrics', rubricRawFile)
      }

      const response = await api.evaluate(formData)
      clearInterval(timerRef.current)

      if (response && response.success) {
        setEvalResult(response.result)
        setEvalId(response.evaluation_id)
        const r = response.result
        recordActivity(
          'self-eval',
          `Self-evaluated ${effectiveSubject}: ${r?.obtained_marks ?? '?'}/${r?.total_marks ?? '?'} (${r?.percentage ?? '?'}%)`
        )
      } else {
        setErrorMsg(response?.error || 'Self-evaluation failed. Please verify files and try again.')
      }
    } catch (err) {
      clearInterval(timerRef.current)
      setErrorMsg(err.message || 'Central evaluation engine request failed.')
    } finally {
      setProcessing(false)
    }
  }

  const handleReset = () => {
    setQpRawFile(null)
    setQpFileName('')
    setAnsRawFile(null)
    setAnsFileName('')
    setRubricRawFile(null)
    setRubricFileName('')
    setEvalResult(null)
    setEvalId(null)
    setErrorMsg('')
  }

  return (
    <>
      <PageHead
        title="Student Self-Evaluation"
        subtitle="Evaluated by the exact same strict, centralized AI teacher engine used across LearnSphere AI. Every question is individually assessed against academic marking standards."
      />

      {/* Engine Parity Notice */}
      <div className="mb-6 p-4 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[13px] text-[var(--text)] flex items-start gap-3 shadow-sm">
        <ShieldAlert size={22} className="text-[var(--accent)] shrink-0 mt-0.5" />
        <div>
          <div className="font-extrabold text-[var(--accent)] text-[14px] mb-0.5">
            Centralized Strict Teacher Standards
          </div>
          <div className="text-[12.5px] text-[var(--text-soft)] leading-relaxed">
            Your self-evaluation is processed by the <strong>same unified evaluator</strong> as official teacher assessments. Question-wise marks, conceptual diagnostic feedback, step-by-step calculations, and expected answers are permanently saved to your academic profile.
          </div>
        </div>
      </div>

      {!hasSubjects ? (
        <div className="p-8 max-w-[600px] mx-auto text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto text-2xl">
            <BookOpen size={32} />
          </div>
          <h2 className="text-xl font-extrabold text-[var(--text)]">Syllabus Document Required</h2>
          <p className="text-sm text-[var(--text-soft)]">
            Self Evaluation uses your curriculum structure to accurately evaluate exam answer scripts. Please upload your syllabus document to unlock Self Evaluation.
          </p>
          <div className="pt-2">
            <button
              onClick={() => setIsSyllabusModalOpen(true)}
              className="px-5 py-2.5 bg-[var(--accent)] text-white text-xs font-bold rounded-xl hover:bg-[var(--accent-dim)] inline-flex items-center gap-2 shadow-md"
            >
              <UploadCloud size={16} /> Upload Syllabus Document
            </button>
          </div>
          <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
        </div>
      ) : (
        <div className="max-w-[880px] space-y-6">
          {errorMsg && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold flex items-center gap-2">
              <AlertTriangle size={18} className="shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Form / Upload Section */}
          {!evalResult && !processing && (
            <Card className="space-y-6">
              <div className="border-b border-[var(--border)] pb-4">
                <h3 className="text-base font-extrabold text-[var(--text)]">Upload Exam Files for Strict Teacher Grading</h3>
                <p className="text-xs text-[var(--text-soft)]">
                  Provide your official question paper and written answer script (PDF or images). The central engine extracts all questions, analyzes your handwritten or typed answers, and allocates verified marks.
                </p>
              </div>

              {/* Upload Grid */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Question Paper Upload */}
                <div className="p-4 rounded-xl border-2 border-dashed border-[var(--border-strong)] hover:border-[var(--accent)] transition-all bg-[var(--surface-alt)] flex flex-col items-center text-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mb-2">
                    <FileText size={20} />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[var(--text)] block mb-1">1. Question Paper *</span>
                    <span className="text-[11px] text-[var(--text-faint)] block mb-3">PDF or Image of Question Paper</span>
                  </div>
                  {qpFileName ? (
                    <div className="text-xs font-semibold text-emerald-500 flex items-center gap-1">
                      <CheckCircle2 size={14} /> {qpFileName}
                    </div>
                  ) : (
                    <label className="cursor-pointer px-3 py-1.5 bg-[var(--surface)] text-[var(--text)] border border-[var(--border-strong)] text-xs font-bold rounded-lg hover:bg-[var(--accent-soft)] transition-colors">
                      Browse File
                      <input type="file" accept=".pdf,image/*" onChange={handleQpUpload} className="hidden" />
                    </label>
                  )}
                </div>

                {/* Answer Script Upload */}
                <div className="p-4 rounded-xl border-2 border-dashed border-[var(--border-strong)] hover:border-[var(--accent)] transition-all bg-[var(--surface-alt)] flex flex-col items-center text-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-500 flex items-center justify-center mb-2">
                    <UploadCloud size={20} />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[var(--text)] block mb-1">2. Answer Script *</span>
                    <span className="text-[11px] text-[var(--text-faint)] block mb-3">PDF, JPG, PNG of your answers</span>
                  </div>
                  {ansFileName ? (
                    <div className="text-xs font-semibold text-emerald-500 flex items-center gap-1">
                      <CheckCircle2 size={14} /> {ansFileName}
                    </div>
                  ) : (
                    <label className="cursor-pointer px-3 py-1.5 bg-[var(--surface)] text-[var(--text)] border border-[var(--border-strong)] text-xs font-bold rounded-lg hover:bg-[var(--accent-soft)] transition-colors">
                      Browse File
                      <input type="file" accept=".pdf,image/*" onChange={handleAnsUpload} className="hidden" />
                    </label>
                  )}
                </div>

                {/* Optional Rubric */}
                <div className="p-4 rounded-xl border-2 border-dashed border-[var(--border)] hover:border-[var(--accent)] transition-all bg-[var(--surface-alt)] flex flex-col items-center text-center justify-between">
                  <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center mb-2">
                    <Award size={20} />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-[var(--text)] block mb-1">3. Rubric (Optional)</span>
                    <span className="text-[11px] text-[var(--text-faint)] block mb-3">Answer key or Marking Scheme</span>
                  </div>
                  {rubricFileName ? (
                    <div className="text-xs font-semibold text-emerald-500 flex items-center gap-1">
                      <CheckCircle2 size={14} /> {rubricFileName}
                    </div>
                  ) : (
                    <label className="cursor-pointer px-3 py-1.5 bg-[var(--surface)] text-[var(--text)] border border-[var(--border-strong)] text-xs font-bold rounded-lg hover:bg-[var(--accent-soft)] transition-colors">
                      Browse File
                      <input type="file" accept=".pdf,image/*" onChange={handleRubricUpload} className="hidden" />
                    </label>
                  )}
                </div>
              </div>

              {/* Subject Confirmation */}
              <div className="space-y-2 pt-2 border-t border-[var(--border)]">
                <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] block">
                  Select or Confirm Subject
                </label>
                <div className="flex gap-2 flex-wrap items-center">
                  {subjects.map((sub) => (
                    <button
                      key={sub}
                      onClick={() => { setSelectedSubject(sub); setCustomSubject(''); }}
                      className={`px-3 py-1.5 rounded-full text-xs font-semibold border transition-all ${
                        selectedSubject === sub
                          ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                          : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent)]'
                      }`}
                    >
                      {sub}
                    </button>
                  ))}
                </div>
                {!subjects.includes(selectedSubject) && (
                  <input
                    type="text"
                    placeholder="Subject title extracted from paper (or type custom subject)..."
                    value={customSubject}
                    onChange={(e) => setCustomSubject(e.target.value)}
                    className="w-full mt-2 px-3 py-2 border border-[var(--border-strong)] rounded-xl text-xs bg-[var(--surface)] text-[var(--text)]"
                  />
                )}
              </div>

              <Button
                onClick={handleStartSelfEval}
                disabled={!qpRawFile || !ansRawFile}
                className="w-full justify-center py-3 text-sm font-extrabold"
              >
                <Brain size={18} /> Launch Central AI Evaluation
              </Button>
            </Card>
          )}

          {/* Processing State */}
          {processing && (
            <Card className="p-8 text-center space-y-4 border-2 border-[var(--accent)] shadow-xl">
              <Loader2 size={38} className="animate-spin text-[var(--accent)] mx-auto" />
              <div>
                <h3 className="text-base font-extrabold text-[var(--text)]">Evaluating Answer Script Against Rubric</h3>
                <p className="text-xs text-[var(--text-soft)] mt-1">{STAGES[currentStage]}</p>
              </div>
              <div className="w-full bg-[var(--surface-alt)] h-2.5 rounded-full overflow-hidden max-w-[420px] mx-auto border border-[var(--border)]">
                <div
                  className="bg-gradient-to-r from-[var(--accent)] to-[var(--accent-dim)] h-full transition-all duration-500"
                  style={{ width: `${((currentStage + 1) / STAGES.length) * 100}%` }}
                />
              </div>
            </Card>
          )}

          {/* Evaluation Results */}
          {evalResult && (
            <div className="space-y-6">
              {/* Overall Summary Card */}
              <Card className="border-2 border-[var(--accent)] bg-gradient-to-br from-[var(--surface)] to-[var(--surface-alt)] shadow-lg">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border)]">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <Badge tone="accent">{evalResult.student?.subject || selectedSubject || 'Self Evaluation'}</Badge>
                      {evalId && (
                        <span className="text-[11px] font-mono text-[var(--text-faint)] bg-[var(--surface)] px-2 py-0.5 rounded border border-[var(--border)]">
                          Evaluation ID: {evalId}
                        </span>
                      )}
                    </div>
                    {evalResult.evaluation_status === 'NEEDS_TEACHER_REVIEW' ? (
                      <div className="mt-2">
                        <h2 className="text-lg font-black text-[var(--warning)]">Needs Review</h2>
                        <p className="text-xs text-[var(--text-soft)] mt-0.5">{evalResult.overall_feedback || evalResult.unreadable_reason}</p>
                      </div>
                    ) : (
                      <h2 className="text-3xl font-black text-[var(--text)] mt-1">
                        {evalResult.obtained_marks} / {evalResult.total_marks} Marks ({evalResult.percentage}%)
                      </h2>
                    )}
                    <p className="text-xs text-[var(--text-soft)] mt-0.5">
                      Student: <strong>{user?.name}</strong> &bull; Status: <strong className={evalResult.evaluation_status === 'COMPLETED' ? 'text-emerald-500' : 'text-amber-500'}>{evalResult.evaluation_status || 'COMPLETED'}</strong>
                      {evalResult.grade && evalResult.grade !== 'NEEDS_REVIEW' && ` • Grade: ${evalResult.grade}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button onClick={() => navigate('/app/history')} variant="secondary" className="flex items-center gap-1.5 text-xs">
                      <History size={14} />
                      <span>Evaluation History</span>
                    </Button>
                    <Button onClick={handleReset} variant="secondary" className="flex items-center gap-1.5 text-xs">
                      <RotateCcw size={14} />
                      <span>Evaluate Another Script</span>
                    </Button>
                  </div>
                </div>

                {(evalResult.overall_teacher_comment || evalResult.overall_feedback) && evalResult.evaluation_status !== 'NEEDS_TEACHER_REVIEW' && (
                  <div className="mt-4 p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text)] leading-relaxed space-y-3">
                    <div>
                      <strong className="text-[var(--accent)] block text-xs uppercase tracking-wider mb-1">
                        Teacher Executive Assessment:
                      </strong>
                      <p className="text-[13px] font-medium leading-relaxed">{evalResult.overall_teacher_comment || evalResult.overall_feedback}</p>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-[var(--border)]">
                      {evalResult.strongest_areas?.length > 0 && (
                        <div className="p-3 bg-emerald-500/10 rounded-xl border border-emerald-500/20">
                          <span className="text-[11px] font-bold uppercase tracking-wide text-emerald-500 block mb-1">
                            Demonstrated Strengths:
                          </span>
                          <ul className="list-disc pl-4 space-y-0.5 text-[var(--text)]">
                            {evalResult.strongest_areas.map((s, i) => <li key={i}>{s}</li>)}
                          </ul>
                        </div>
                      )}

                      {evalResult.weakest_areas?.length > 0 && (
                        <div className="p-3 bg-amber-500/10 rounded-xl border border-amber-500/20">
                          <span className="text-[11px] font-bold uppercase tracking-wide text-amber-500 block mb-1">
                            Areas for Improvement:
                          </span>
                          <ul className="list-disc pl-4 space-y-0.5 text-[var(--text)]">
                            {evalResult.weakest_areas.map((w, i) => <li key={i}>{w}</li>)}
                          </ul>
                        </div>
                      )}
                    </div>

                    {evalResult.priority_topics_to_revise?.length > 0 && (
                      <div className="p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)]">
                        <span className="text-[11px] font-bold uppercase tracking-wide text-[var(--accent)] block mb-1">
                          Priority Topics to Revise:
                        </span>
                        <ul className="list-disc pl-4 space-y-0.5 text-[var(--text)] font-semibold">
                          {evalResult.priority_topics_to_revise.map((p, i) => <li key={i}>{p}</li>)}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </Card>

              {/* Question-by-Question Breakdown */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--text-faint)]">
                    Question-by-Question Detailed Feedback
                  </h3>
                  <span className="text-xs text-[var(--text-soft)] font-semibold">
                    {(evalResult.evaluations || evalResult.questions || []).length} Questions Evaluated
                  </span>
                </div>

                {(evalResult.evaluations || evalResult.questions || []).length > 0 ? (
                  (evalResult.evaluations || evalResult.questions).map((q, idx) => {
                    const maxMarks = q.maximum_marks ?? q.max_marks ?? '?'
                    const awardedMarks = q.awarded_marks ?? 0
                    const isFull = maxMarks > 0 && awardedMarks >= maxMarks
                    const isPartial = awardedMarks > 0 && awardedMarks < maxMarks

                    return (
                      <Card key={q.question_id || idx} className="space-y-3.5 shadow-sm">
                        <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5 flex-wrap gap-2">
                          <div className="flex items-center gap-2">
                            <span className="font-black text-sm text-[var(--accent)]">
                              Question {q.question_number || idx + 1}
                            </span>
                            <span className="text-xs font-semibold text-[var(--text-soft)]">
                              (Max: {maxMarks} marks)
                            </span>
                            {q.percentage_of_question !== undefined && (
                              <span className="text-xs font-bold text-[var(--accent)]">
                                &bull; {q.percentage_of_question}%
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-2 flex-wrap">
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
                            <Badge tone={q.is_skipped_due_to_choice ? 'neutral' : isFull ? 'success' : isPartial ? 'warning' : 'error'}>
                              {awardedMarks} / {maxMarks} Marks {q.is_skipped_due_to_choice || q.is_extra_choice ? '(Not counted in total)' : ''}
                            </Badge>
                          </div>
                        </div>

                        {/* Question Text */}
                        {q.question_text && (
                          <div className="text-xs font-bold text-[var(--text)] bg-[var(--surface-alt)] p-2.5 rounded-lg border border-[var(--border)]">
                            <span className="text-[10.5px] uppercase tracking-wider text-[var(--text-faint)] block mb-0.5">Question Paper Text:</span>
                            {q.question_text}
                          </div>
                        )}

                        {/* Student Answer */}
                        {(q.student_answer || q.answer_summary) && (
                          <div className="text-xs text-[var(--text-soft)] space-y-1">
                            <span className="font-semibold text-[var(--text-faint)] block">Your Extracted Answer:</span>
                            <p className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] leading-relaxed italic font-mono text-[11.5px] text-[var(--text)]">
                              &ldquo;{q.student_answer || q.answer_summary}&rdquo;
                            </p>
                            {q.evidence_reference && (
                              <span className="text-[11px] text-[var(--text-faint)] mt-0.5 block font-mono">
                                Evidence Reference: {q.evidence_reference}
                              </span>
                            )}
                          </div>
                        )}

                        {/* Teacher Allocation Feedback */}
                        {(q.teacher_feedback || q.evaluation_reason) && (
                          <div className="text-xs p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] space-y-1">
                            <span className="font-bold text-[var(--accent)] block text-[11px] uppercase tracking-wider">Teacher Mark Breakdown:</span>
                            <p className="text-[var(--text)] leading-relaxed">{q.teacher_feedback || q.evaluation_reason}</p>
                          </div>
                        )}

                        {/* What was done correctly */}
                        {(q.what_was_done_correctly?.length > 0 || q.strengths?.length > 0) && (
                          <div className="text-xs text-emerald-500 bg-emerald-500/10 p-2.5 rounded-lg border border-emerald-500/20">
                            <span className="font-bold block mb-0.5">What You Did Correctly:</span>
                            <ul className="list-disc pl-4 space-y-0.5 text-[var(--text)]">
                              {(q.what_was_done_correctly || q.strengths || []).map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                          </div>
                        )}

                        {/* What is incorrect */}
                        {(q.what_is_incorrect?.length > 0 || q.errors?.length > 0) && (
                          <div className="text-xs text-red-400 bg-red-500/10 p-2.5 rounded-lg border border-red-500/20">
                            <span className="font-bold block mb-0.5">What Is Incorrect:</span>
                            <ul className="list-disc pl-4 space-y-0.5 text-[var(--text)]">
                              {(q.what_is_incorrect || q.errors || []).map((err, i) => <li key={i}>{err}</li>)}
                            </ul>
                          </div>
                        )}

                        {/* Calculation mistake */}
                        {q.step_or_calculation_mistake && (
                          <div className="text-xs text-amber-400 bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/20">
                            <span className="font-bold block mb-0.5">Calculation / Step Mistake:</span>
                            <p className="text-[var(--text)]">{q.step_or_calculation_mistake}</p>
                          </div>
                        )}

                        {/* Conceptual Misunderstanding */}
                        {(q.conceptual_mistake || (q.misconception_detected && q.misconception)) && (
                          <div className="text-xs text-red-400 bg-red-500/10 p-2.5 rounded-lg border border-red-500/20 space-y-1">
                            <span className="font-bold block flex items-center gap-1 text-[11px] uppercase tracking-wider">
                              <AlertCircle size={14} />
                              <span>Conceptual Misunderstanding Identified:</span>
                            </span>
                            <p className="text-[var(--text)] font-semibold">{q.conceptual_mistake || q.misconception}</p>
                          </div>
                        )}

                        {/* Missing Points */}
                        {(q.what_is_missing?.length > 0 || q.missing_points?.length > 0) && (
                          <div className="text-xs text-amber-400 bg-amber-500/10 p-2.5 rounded-lg border border-amber-500/20">
                            <span className="font-bold block mb-0.5">Missing Key Points / Steps:</span>
                            <ul className="list-disc pl-4 space-y-0.5 text-[var(--text)]">
                              {(q.what_is_missing || q.missing_points || []).map((m, i) => <li key={i}>{m}</li>)}
                            </ul>
                          </div>
                        )}

                        {/* What Should Have Been Written */}
                        {(q.what_student_should_have_written || q.correct_answer_or_expected_points || q.feedback?.expected_answer) && (
                          <div className="text-xs text-[var(--text)] bg-[var(--surface)] p-2.5 rounded-lg border border-[var(--border)]">
                            <span className="font-bold text-[var(--accent)] block mb-0.5 text-[11px] uppercase tracking-wider">What You Should Have Written:</span>
                            <div className="leading-relaxed font-mono whitespace-pre-line text-[11.5px] bg-[var(--surface-alt)] p-2 rounded border border-[var(--border)] mt-1">
                              {q.what_student_should_have_written || q.correct_answer_or_expected_points || q.feedback?.expected_answer}
                            </div>
                          </div>
                        )}

                        {/* How to Improve */}
                        {(q.how_to_improve || q.feedback_text || q.feedback?.improvement) && (
                          <div className="text-xs text-[var(--text-soft)] p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)]">
                            <span className="font-semibold text-[var(--accent-dim)] block mb-0.5 text-[11px] uppercase tracking-wider">How to Improve:</span>
                            <p className="leading-relaxed text-[var(--text)]">
                              {q.how_to_improve || q.feedback_text || q.feedback?.improvement}
                            </p>
                          </div>
                        )}
                      </Card>
                    )
                  })
                ) : (
                  <Card className="text-center p-6 text-xs text-[var(--text-faint)]">
                    No detailed question breakdown available for this paper.
                  </Card>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </>
  )
}
