import { useState, useRef } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { getDynamicSubjects } from '../data/syllabusData.js'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import {
  UploadCloud, FileText, CheckCircle2, AlertTriangle, Loader2,
  Award, Brain, RotateCcw, ChevronRight, BookOpen, AlertCircle
} from 'lucide-react'

const STAGES = [
  'Extracting Question Paper & Maximum Marks...',
  'Extracting Student Answer Script Content...',
  'Matching Questions & Answer Order...',
  'Evaluating Answers against Academic Rubric...',
  'Running Verification & Fraud Pass...',
  'Finalizing Self-Evaluation Report...'
]

export default function SelfEvaluation() {
  const { user, profile, syllabusData, recordActivity } = useApp()
  const activeProfile = { ...user, ...profile }

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
      const effectiveSubject = selectedSubject || customSubject || ''
      formData.append('subject', effectiveSubject)
      formData.append('student_name', user?.name || 'Student')
      formData.append('roll_number', user?.roll_number || '')
      formData.append('assessment_title', 'Self Evaluation Exam')
      formData.append('role', 'student')
      formData.append('level', activeProfile?.level || '')
      formData.append('board', activeProfile?.board || '')
      formData.append('stream', activeProfile?.stream || '')

      formData.append('question_paper', qpRawFile)
      formData.append('answer_script', ansRawFile)
      if (rubricRawFile) {
        formData.append('rubric', rubricRawFile)
      }

      const response = await api.evaluate(formData)
      clearInterval(timerRef.current)

      if (response && response.success) {
        setEvalResult(response.result)
        setEvalId(response.evaluation_id)
        recordActivity('self-eval', `Self-evaluated paper: Score ${response.result?.total_awarded}/${response.result?.total_max} (${response.result?.percentage}%)`)
      } else {
        setErrorMsg(response?.error || 'Self-evaluation failed. Please verify files and try again.')
      }
    } catch (err) {
      clearInterval(timerRef.current)
      setErrorMsg(err.message || 'Evaluation engine request failed.')
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
        title="Student Self Evaluation"
        subtitle="Upload your question paper & written answer script for central AI rubric grading using Gemini 3.6 Flash."
      />

      {!hasSubjects ? (
        <div className="p-8 max-w-[600px] mx-auto text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto text-2xl">
            <BookOpen size={32} />
          </div>
          <h2 className="text-xl font-extrabold text-[var(--text)]">Syllabus Document Required</h2>
          <p className="text-sm text-[var(--text-soft)]">
            Self Evaluation relies on your syllabus structure to accurately evaluate exam answer scripts. Please upload your syllabus document to unlock Self Evaluation.
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
        <div className="max-w-[840px] space-y-6">
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
                <h3 className="text-base font-extrabold text-[var(--text)]">Self Evaluation Exam Papers</h3>
                <p className="text-xs text-[var(--text-soft)]">
                  Provide your actual exam question paper and handwritten/printed answer script for exact question matching & verified marking.
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
                className="w-full justify-center py-3 text-sm"
              >
                <Brain size={18} /> Run Central Evaluation Engine
              </Button>
            </Card>
          )}

          {/* Processing State */}
          {processing && (
            <Card className="p-8 text-center space-y-4 border-2 border-[var(--accent)]">
              <Loader2 size={36} className="animate-spin text-[var(--accent)] mx-auto" />
              <div>
                <h3 className="text-base font-extrabold text-[var(--text)]">Evaluating Answer Script</h3>
                <p className="text-xs text-[var(--text-soft)] mt-1">{STAGES[currentStage]}</p>
              </div>
              <div className="w-full bg-[var(--surface-alt)] h-2 rounded-full overflow-hidden max-w-[400px] mx-auto border border-[var(--border)]">
                <div
                  className="bg-[var(--accent)] h-full transition-all duration-500"
                  style={{ width: `${((currentStage + 1) / STAGES.length) * 100}%` }}
                />
              </div>
            </Card>
          )}

          {/* Evaluation Results */}
          {evalResult && (
            <div className="space-y-6">
              {/* Overall Summary Card */}
              <Card className="border-2 border-[var(--accent)] bg-gradient-to-br from-[var(--surface)] to-[var(--surface-alt)]">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-[var(--border)]">
                  <div>
                    <Badge tone="accent">{evalResult.subject || selectedSubject || 'Self Evaluation'}</Badge>
                    <h2 className="text-2xl font-black text-[var(--text)] mt-1">
                      {evalResult.total_awarded} / {evalResult.total_max} Marks ({evalResult.percentage}%)
                    </h2>
                    <p className="text-xs text-[var(--text-soft)] mt-0.5">
                      Status: <strong className="text-emerald-500">{evalResult.status || 'COMPLETED'}</strong>
                      {evalResult.grade && ` • Grade: ${evalResult.grade}`}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button onClick={handleReset} variant="secondary">
                      <RotateCcw size={14} /> Evaluate Another Script
                    </Button>
                  </div>
                </div>

                {evalResult.summary && (
                  <div className="mt-4 p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-soft)] leading-relaxed">
                    <strong className="text-[var(--text)] block mb-1">Academic Summary:</strong>
                    {evalResult.summary}
                  </div>
                )}
              </Card>

              {/* Question-by-Question Breakdown */}
              <div className="space-y-4">
                <h3 className="text-sm font-extrabold uppercase tracking-wider text-[var(--text-faint)]">
                  Question-by-Question Marking & Feedback
                </h3>

                {evalResult.evaluations && evalResult.evaluations.length > 0 ? (
                  evalResult.evaluations.map((q, idx) => (
                    <Card key={q.question_id || idx} className="space-y-3">
                      <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
                        <div className="flex items-center gap-2">
                          <span className="font-black text-sm text-[var(--accent)]">
                            Q{q.question_number || idx + 1}
                          </span>
                          <span className="text-xs font-semibold text-[var(--text-soft)]">
                            (Max Marks: {q.max_marks})
                          </span>
                        </div>
                        <Badge tone={q.awarded_marks === q.max_marks ? 'success' : q.awarded_marks > 0 ? 'warning' : 'error'}>
                          {q.awarded_marks} / {q.max_marks} Marks
                        </Badge>
                      </div>

                      {q.question_text && (
                        <div className="text-xs font-bold text-[var(--text)] bg-[var(--surface-alt)] p-2.5 rounded-lg border border-[var(--border)]">
                          {q.question_text}
                        </div>
                      )}

                      {q.student_answer && (
                        <div className="text-xs text-[var(--text-soft)]">
                          <span className="font-semibold text-[var(--text-faint)] block mb-1">Your Answer:</span>
                          <p className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] leading-relaxed italic">
                            {q.student_answer}
                          </p>
                        </div>
                      )}

                      {q.feedback && (
                        <div className="text-xs text-[var(--text-soft)]">
                          <span className="font-semibold text-[var(--text-faint)] block mb-1">Feedback:</span>
                          <p className="p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] leading-relaxed">
                            {q.feedback}
                          </p>
                        </div>
                      )}

                      {q.misconception && (
                        <div className="text-xs text-red-400 bg-red-500/10 p-2.5 rounded-lg border border-red-500/20">
                          <span className="font-bold block mb-0.5">Misconception Identified:</span>
                          {q.misconception}
                        </div>
                      )}

                      {q.expected_points && (
                        <div className="text-xs text-emerald-400 bg-emerald-500/10 p-2.5 rounded-lg border border-emerald-500/20">
                          <span className="font-bold block mb-0.5">Expected Key Points:</span>
                          {Array.isArray(q.expected_points) ? q.expected_points.join(', ') : q.expected_points}
                        </div>
                      )}
                    </Card>
                  ))
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
