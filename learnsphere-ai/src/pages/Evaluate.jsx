import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, FileText, UploadCloud, X, ShieldAlert, Sparkles, ArrowRight, BookOpen, Download, AlertCircle } from 'lucide-react'
import { Card, CardHeader, Badge, Button, RowItem, PageHead, StatCard } from '../components/ui/Primitives.jsx'
import { api } from '../services/api.js'
import { useApp } from '../context/AppContext.jsx'

const STEP_LABELS = ['Question Paper', 'Answer Script', 'Student Details', 'Review', 'Evaluate']
const STAGES = [
  'Upload received & validating files',
  'Gemini OCR & Question Paper extraction',
  'Handwritten script step-by-step analysis',
  'Calculating verified marks & teacher feedback',
  'Persisting records into MongoDB Atlas'
]

function Stepper({ step }) {
  return (
    <div className="flex items-center mb-8 overflow-x-auto pb-2 scrollbar-thin">
      {STEP_LABELS.map((label, i) => {
        const n = i + 1
        const state = n < step ? 'done' : n === step ? 'active' : 'pending'
        return (
          <div className="flex items-center" key={label}>
            <div className="flex items-center gap-3 shrink-0">
              <div
                className={`w-9 h-9 rounded-xl flex items-center justify-center text-xs md:text-sm font-bold shrink-0 transition-all shadow-xs ${
                  state === 'active'
                    ? 'bg-[var(--accent)] text-white shadow-sm ring-4 ring-[var(--accent-soft)]'
                    : state === 'done'
                    ? 'bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/30 font-extrabold'
                    : 'bg-[var(--surface-alt)] border border-[var(--border-strong)] text-[var(--text-faint)]'
                }`}
              >
                {state === 'done' ? '✓' : `0${n}`}
              </div>
              <div className={`text-xs md:text-sm font-bold ${state === 'pending' ? 'text-[var(--text-faint)]' : 'text-[var(--text)]'}`}>
                {label}
              </div>
            </div>
            {n < STEP_LABELS.length && <div className="flex-1 h-0.5 bg-[var(--border)] mx-4 min-w-[28px]" />}
          </div>
        )
      })}
    </div>
  )
}

function UploadZone({ label, hint, icon: Icon = UploadCloud, onUpload }) {
  return (
    <label className="block border-2 border-dashed border-[var(--border-strong)] rounded-2xl py-8 sm:py-10 px-5 sm:px-6 text-center bg-[var(--surface-alt)]/50 hover:bg-[var(--accent-soft)]/30 hover:border-[var(--accent)] transition-all cursor-pointer relative shadow-xs">
      <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto mb-3 shadow-xs">
        <Icon size={24} strokeWidth={1.8} />
      </div>
      <h3 className="text-sm md:text-base font-bold text-[var(--text)] mb-1">{label}</h3>
      <p className="text-xs text-[var(--text-soft)] max-w-sm mx-auto leading-relaxed">{hint}</p>
      <input 
        type="file" 
        aria-label={label || "Upload document"}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" 
        onChange={onUpload} 
      />
    </label>
  )
}

function DocPreview({ name, info, onRemove }) {
  return (
    <div className="flex items-center gap-3 p-3.5 border border-[var(--border)] rounded-xl bg-[var(--surface)] mt-3.5 shadow-xs">
      <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 shadow-xs">
        <FileText size={18} strokeWidth={1.8} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs md:text-sm font-bold text-[var(--text)] truncate">{name}</div>
        <div className="text-[11px] sm:text-xs text-[var(--text-soft)] mt-0.5">{info}</div>
      </div>
      {onRemove && (
        <button
          onClick={onRemove}
          className="w-8 h-8 flex items-center justify-center rounded-lg border border-[var(--border)] text-[var(--text-soft)] hover:text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors cursor-pointer"
          title="Remove attached file"
          aria-label="Remove attached file"
        >
          <X size={15} strokeWidth={1.8} />
        </button>
      )}
    </div>
  )
}

export default function Evaluate() {
  const { user, role, activeClass, addOrUpdateStudentMarks } = useApp()
  const [step, setStep] = useState(1)
  const [processing, setProcessing] = useState(false)
  const [doneStages, setDoneStages] = useState(-1)
  const [result, setResult] = useState(false)
  const [activeQ, setActiveQ] = useState(0)

  // File states
  const [qpFile, setQpFile] = useState(null)
  const [qpRawFile, setQpRawFile] = useState(null)

  const [ansFile, setAnsFile] = useState(null)
  const [ansRawFile, setAnsRawFile] = useState(null)

  const [syllabusFile, setSyllabusFile] = useState(null)
  const [syllabusRawFile, setSyllabusRawFile] = useState(null)

  // Details
  const [studentName, setStudentName] = useState(user?.name || '')
  const [subject, setSubject] = useState(user?.subjects?.[0] || '')
  const [rollNumber, setRollNumber] = useState(user?.roll_number || '')
  const [assessmentTitle, setAssessmentTitle] = useState('')

  const [level, setLevel] = useState(user?.level || '')
  const [board, setBoard] = useState(user?.board || '')
  const [stream, setStream] = useState(user?.stream || '')
  const [semester, setSemester] = useState(user?.semester || '')

  // Evaluation response
  const [evalData, setEvalData] = useState(null)
  const [plagiarismData, setPlagiarismData] = useState(null)
  const [evalId, setEvalId] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  // Teacher Mark Override & Allotment State
  const [isOverriding, setIsOverriding] = useState(false)
  const [overrideMarksMap, setOverrideMarksMap] = useState({})
  const [overrideSaving, setOverrideSaving] = useState(false)
  const [overrideSuccess, setOverrideSuccess] = useState('')

  const timerRef = useRef(null)
  const navigate = useNavigate()

  useEffect(() => () => clearInterval(timerRef.current), [])

  const handleStartOverride = () => {
    if (!evalData?.evaluations) return
    const initialMap = {}
    evalData.evaluations.forEach((q, idx) => {
      initialMap[idx] = q.awarded_marks
    })
    setOverrideMarksMap(initialMap)
    setIsOverriding(true)
    setOverrideSuccess('')
  }

  const handleMarkChange = (idx, val, maxMarks) => {
    const num = Math.max(0, Math.min(maxMarks, parseFloat(val) || 0))
    setOverrideMarksMap((prev) => ({ ...prev, [idx]: num }))
  }

  const handleSaveOverride = async () => {
    if (!evalData) return
    setOverrideSaving(true)
    const updatedEvaluations = evalData.evaluations.map((q, idx) => ({
      ...q,
      awarded_marks: overrideMarksMap[idx] !== undefined ? overrideMarksMap[idx] : q.awarded_marks
    }))

    const newObtained = updatedEvaluations.reduce((acc, q) => acc + (q.is_extra_choice ? 0 : (q.awarded_marks || 0)), 0)
    const newTotal = evalData.total_marks || 100
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

    const updatedData = {
      ...evalData,
      obtained_marks: newObtained,
      total_marks: newTotal,
      percentage: newPct,
      grade: calcGrade(newPct),
      is_unreadable: false,
      assigned_to_teacher: false,
      is_teacher_overridden: true,
      evaluations: updatedEvaluations
    }

    if (evalId) {
      try {
        await api.overrideEvaluationMarks(evalId, {
          questions: updatedEvaluations,
          obtained_marks: newObtained,
          total_marks: newTotal
        })
      } catch {}
    }

    if (activeClass?.id && addOrUpdateStudentMarks) {
      addOrUpdateStudentMarks(activeClass.id, studentName, {
        subject,
        assessment: assessmentTitle,
        totalMarks: newTotal,
        obtainedMarks: newObtained,
        percentage: newPct,
        grade: calcGrade(newPct),
        date: new Date().toISOString().split('T')[0]
      })
    }

    setEvalData(updatedData)
    setIsOverriding(false)
    setOverrideSaving(false)
    setOverrideSuccess('Teacher allotted custom marks saved successfully!')
  }

  const handleQpUpload = (e) => {
    if (e.target.files[0]) {
      const file = e.target.files[0]
      setQpRawFile(file)
      setQpFile(file.name)
    }
  }

  const handleAnsUpload = (e) => {
    if (e.target.files[0]) {
      setAnsRawFile(e.target.files[0])
      setAnsFile(e.target.files[0].name)
    }
  }

  const handleSyllabusUpload = (e) => {
    if (e.target.files[0]) {
      setSyllabusRawFile(e.target.files[0])
      setSyllabusFile(e.target.files[0].name)
    }
  }

  const startEvaluation = async () => {
    if (!qpRawFile) {
      setErrorMsg('Please upload a Question Paper file first.')
      setStep(1)
      return
    }
    if (!ansRawFile) {
      setErrorMsg('Please upload an Answer Script file first.')
      setStep(2)
      return
    }

    setStep(5)
    setProcessing(true)
    setResult(false)
    setDoneStages(-1)
    setErrorMsg('')

    timerRef.current = setInterval(() => {
      setDoneStages((prev) => {
        const next = prev + 1
        return next < STAGES.length ? next : prev
      })
    }, 800)

    try {
      const formData = new FormData()
      formData.append('subject', subject)
      formData.append('student_name', studentName)
      formData.append('roll_number', rollNumber)
      formData.append('assessment_title', assessmentTitle)
      formData.append('role', role || 'teacher')
      formData.append('evaluation_source', 'TEACHER_EVALUATION')
      if (activeClass?.id) {
        formData.append('class_id', activeClass.id)
      }
      formData.append('level', level)
      formData.append('board', board)
      formData.append('stream', stream)
      formData.append('semester', semester)

      formData.append('question_paper', qpRawFile)
      formData.append('answer_script', ansRawFile)

      if (syllabusRawFile) {
        formData.append('syllabus', syllabusRawFile)
      }

      const response = await api.evaluate(formData)

      clearInterval(timerRef.current)
      setDoneStages(STAGES.length - 1)

      setTimeout(() => {
        setProcessing(false)
        if (response && response.success) {
          setEvalData(response.result)
          setPlagiarismData(response.plagiarism)
          setEvalId(response.evaluation_id)
          setResult(true)
        } else {
          setErrorMsg(response.error || 'Paper evaluation failed.')
        }
      }, 500)
    } catch (err) {
      clearInterval(timerRef.current)
      setProcessing(false)
      setErrorMsg(err?.message || 'Network error connecting to evaluation server.')
    }
  }

  const rawQs =
    (Array.isArray(evalData?.questions) && evalData.questions.length > 0 && evalData.questions) ||
    (Array.isArray(evalData?.evaluations) && evalData.evaluations.length > 0 && evalData.evaluations) ||
    []

  const questionsList = rawQs

  const totalMarks = evalData?.obtained_marks !== undefined && evalData?.obtained_marks !== null ? evalData.obtained_marks : null
  const totalMax = evalData?.total_marks !== undefined && evalData?.total_marks !== null ? evalData.total_marks : null
  const percentage = evalData?.percentage !== undefined && evalData?.percentage !== null ? evalData.percentage : null
  const grade = evalData?.grade ?? null

  const eq = questionsList[activeQ] || questionsList[0]
  const eqMaxMarks = eq ? (eq.maximum_marks ?? eq.max_marks ?? 0) : 0
  const eqAwardedMarks = eq ? (eq.awarded_marks ?? 0) : 0
  const statusTone = eq ? (eqAwardedMarks === eqMaxMarks && eqMaxMarks > 0 ? 'success' : eqAwardedMarks > 0 ? 'warning' : 'error') : 'neutral'

  return (
    <>
      <PageHead
        title="Evaluate Answer Script"
        subtitle="Multimodal handwritten script grading, rubric alignment, and question-level mark verification."
      />
      <Stepper step={Math.min(step, 5)} />

      {errorMsg && (
        <div className="p-4 bg-[var(--error-soft)] border border-[var(--error)]/30 text-sm font-semibold rounded-2xl mb-6 text-[var(--error)] leading-relaxed shadow-xs flex items-center gap-3">
          <AlertCircle size={20} className="shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {step === 1 && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="1. Question Paper (Source of Truth)"
              subtitle="Upload the official question paper with maximum marks and instructions"
            />
            <UploadZone
              label="Upload Question Paper Document"
              hint="PDF, JPG or PNG · Exam questions, section weights, and maximum marks will be extracted"
              onUpload={handleQpUpload}
            />
            {qpFile && (
              <DocPreview
                name={qpFile}
                info={<>Question Paper attached · <span className="text-[var(--success)] font-semibold">Ready to extract</span></>}
                onRemove={() => { setQpFile(null); setQpRawFile(null) }}
              />
            )}
          </Card>
          <div className="flex justify-end">
            <Button size="lg" onClick={() => setStep(2)}>
              Continue to Answer Script <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="2. Student Answer Script"
              subtitle="Upload the scanned handwritten or typed student answer script"
            />
            <UploadZone
              label="Upload Student Answer Script"
              hint="PDF, JPG or PNG · Handwritten steps, diagrams, and equations will be analyzed"
              onUpload={handleAnsUpload}
            />
            {ansFile && (
              <DocPreview
                name={ansFile}
                info={<>Answer Script attached · <span className="text-[var(--success)] font-semibold">Ready to grade</span></>}
                onRemove={() => { setAnsFile(null); setAnsRawFile(null) }}
              />
            )}
          </Card>
          <div className="flex justify-between items-center">
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button size="lg" onClick={() => setStep(3)}>
              Continue to Student Details <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="3. Student Context & Optional Syllabus"
              subtitle="Link the script to student identifiers and academic curriculum guidelines"
            />
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Student Full Name</label>
                <input
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  className="w-full px-4 py-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm md:text-base outline-none focus:border-[var(--accent)]"
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Subject Name</label>
                  <input
                    value={subject}
                    onChange={(e) => setSubject(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm md:text-base outline-none focus:border-[var(--accent)]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Roll / Registration Number</label>
                  <input
                    value={rollNumber}
                    onChange={(e) => setRollNumber(e.target.value)}
                    className="w-full px-4 py-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm md:text-base outline-none focus:border-[var(--accent)]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Assessment Title</label>
                <input
                  value={assessmentTitle}
                  onChange={(e) => setAssessmentTitle(e.target.value)}
                  placeholder="e.g. Mid-Term Examination 2026"
                  className="w-full px-4 py-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm md:text-base outline-none focus:border-[var(--accent)]"
                />
              </div>

              <div className="p-5 bg-[var(--surface-alt)]/60 border border-[var(--border)] rounded-2xl mt-4 space-y-3">
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--accent)]">
                  Attach Official Syllabus (Optional Grounding)
                </label>
                <p className="text-xs md:text-sm text-[var(--text-soft)] leading-relaxed">
                  Uploading an official syllabus ensures the evaluator grades against your exact institutional guidelines and learning objectives.
                </p>
                <UploadZone label="Upload Syllabus Document" hint="Optional syllabus PDF or image" icon={BookOpen} onUpload={handleSyllabusUpload} />
                {syllabusFile && (
                  <DocPreview
                    name={syllabusFile}
                    info="Syllabus reference attached"
                    onRemove={() => { setSyllabusFile(null); setSyllabusRawFile(null) }}
                  />
                )}
              </div>
            </div>
          </Card>
          <div className="flex justify-between items-center">
            <Button variant="secondary" onClick={() => setStep(2)}>Back</Button>
            <Button size="lg" onClick={() => setStep(4)}>
              Review & Confirmation <ArrowRight size={16} />
            </Button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="4. Confirm & Run Multimodal Evaluation"
              subtitle="Verify that all evaluation artifacts are ready for AI extraction"
            />
            <div className="divide-y divide-[var(--border)]">
              <RowItem
                title="Question Paper"
                subtitle={qpFile || "Not uploaded"}
                right={<Badge tone={qpFile ? "success" : "error"}>{qpFile ? "Attached" : "Missing"}</Badge>}
              />
              <RowItem
                title="Student Answer Script"
                subtitle={ansFile || "Not uploaded"}
                right={<Badge tone={ansFile ? "success" : "error"}>{ansFile ? "Attached" : "Missing"}</Badge>}
              />
              <RowItem
                title="Student Context"
                subtitle={`${studentName} (${rollNumber}) · ${subject} · ${(level || 'school').toUpperCase()}`}
                right={<Badge tone="success">Confirmed</Badge>}
              />
              {syllabusFile && (
                <RowItem
                  title="Syllabus Reference"
                  subtitle={syllabusFile}
                  right={<Badge tone="accent">Attached</Badge>}
                />
              )}
            </div>
          </Card>
          <div className="flex justify-between items-center">
            <Button variant="secondary" onClick={() => setStep(3)}>Back</Button>
            <Button size="lg" onClick={startEvaluation} className="flex items-center gap-2">
              <Sparkles size={18} /> Run Multimodal Evaluation
            </Button>
          </div>
        </div>
      )}

      {step === 5 && processing && (
        <Card className="max-w-xl mx-auto py-10 px-8 text-center shadow-md">
          <div className="w-14 h-14 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto mb-5 shadow-xs">
            <Sparkles size={28} className="animate-spin" />
          </div>
          <h2 className="text-xl md:text-2xl font-extrabold text-[var(--text)] mb-2">Multimodal Evaluation in Progress</h2>
          <p className="text-sm text-[var(--text-soft)] mb-8">
            Extracting handwritten response steps, verifying marks, and cross-referencing criteria…
          </p>
          <div className="flex flex-col gap-3.5 text-left max-w-md mx-auto">
            {STAGES.map((s, i) => {
              const state = i < doneStages ? 'done' : i === doneStages ? 'active' : 'pending'
              return (
                <div className="flex items-center gap-3.5 text-sm" key={s}>
                  <div
                    className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all ${
                      state === 'done'
                        ? 'bg-[var(--success)] text-white'
                        : state === 'active'
                        ? 'bg-[var(--accent)] text-white animate-pulse'
                        : 'bg-[var(--surface-alt)] border border-[var(--border-strong)]'
                    }`}
                  >
                    {state === 'done' && <CheckCircle2 size={16} strokeWidth={3} />}
                  </div>
                  <span className={state === 'pending' ? 'text-[var(--text-faint)]' : state === 'active' ? 'font-bold text-[var(--accent)]' : 'font-semibold text-[var(--text)]'}>
                    {s}
                  </span>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {result && evalData && (
        <div className="space-y-6">
          {(evalData.is_unreadable || evalData.assigned_to_teacher) && (
            <div className="p-5 rounded-2xl bg-[var(--warning-soft)] border border-[var(--warning)]/30 text-sm font-semibold text-[var(--warning)] flex items-start gap-3.5 shadow-xs">
              <ShieldAlert size={24} className="shrink-0 mt-0.5" />
              <div>
                <div className="font-extrabold text-base mb-1">Handwriting Verification Notice</div>
                <p className="text-xs md:text-sm opacity-90 leading-relaxed">
                  {evalData.unreadable_reason || 'The student handwriting could not be parsed with complete certainty. The script has been routed to you for manual mark verification below.'}
                </p>
              </div>
            </div>
          )}

          {overrideSuccess && (
            <div className="p-4 rounded-2xl bg-[var(--success-soft)] border border-[var(--success)]/30 text-sm font-bold text-[var(--success)] flex items-center justify-between shadow-xs">
              <span>✅ {overrideSuccess}</span>
              <button onClick={() => setOverrideSuccess('')} className="text-sm font-bold cursor-pointer">✕</button>
            </div>
          )}

          {/* Grand Evaluation Header Card */}
          <Card className="border-l-4 border-l-[var(--accent)]">
            <div className="flex items-center justify-between flex-wrap gap-5">
              <div>
                <div className="flex items-center gap-2.5 mb-2">
                  <Badge tone={evalData.is_unreadable ? "warning" : "success"}>
                    {evalData.is_unreadable ? "Needs Teacher Review" : "Evaluation Complete & Persistent"}
                  </Badge>
                  {evalId && <span className="text-xs font-mono text-[var(--text-faint)]">ID: {evalId.slice(0, 12)}…</span>}
                </div>
                <h2 className="text-2xl md:text-3xl font-extrabold text-[var(--text)] tracking-tight">
                  {studentName} — {subject}
                </h2>
                <p className="text-xs md:text-sm text-[var(--text-soft)] mt-1 font-medium">
                  {assessmentTitle} · Roll: {rollNumber} ({level ? level.toUpperCase() : 'ACC'})
                </p>
              </div>

              <div className="flex flex-col items-end gap-3">
                <div className="text-right">
                  {totalMarks !== null && totalMax !== null ? (
                    <>
                      <div className="text-4xl md:text-5xl font-extrabold text-[var(--accent)] tracking-tight">
                        {totalMarks} <span className="text-lg font-normal text-[var(--text-faint)]">/ {totalMax}</span>
                      </div>
                      <div className="text-xs md:text-sm font-bold text-[var(--text-soft)] mt-1">{percentage}% · Grade {grade}</div>
                    </>
                  ) : (
                    <div className="text-base font-bold text-[var(--warning)] py-2">
                      {evalData?.evaluation_status === 'NEEDS_TEACHER_REVIEW' ? 'Awaiting teacher review' : 'Evaluation in progress'}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-2.5 flex-wrap">
                  {role === 'teacher' && (
                    <Button
                      size="sm"
                      variant={isOverriding ? "secondary" : "ghost"}
                      onClick={isOverriding ? () => setIsOverriding(false) : handleStartOverride}
                    >
                      {isOverriding ? "Cancel Override" : "✏️ Allot Custom Marks"}
                    </Button>
                  )}
                  <Button size="sm" className="flex items-center gap-1.5" onClick={() => evalId ? api.downloadEvaluationPdf(evalId) : api.generatePdfReport(evalData)}>
                    <Download size={15} /> Download PDF
                  </Button>
                </div>
              </div>
            </div>

            {role === 'teacher' && plagiarismData && plagiarismData.similarity > 0 && (
              <div className="mt-5 pt-4 border-t border-[var(--border)] flex items-center justify-between flex-wrap gap-2 text-xs md:text-sm">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={17} className={plagiarismData.suspected ? "text-[var(--warning)]" : "text-[var(--success)]"} />
                  <span className="font-bold text-[var(--text)]">Academic Integrity:</span>
                  <span className="text-[var(--text-soft)]">{plagiarismData.details}</span>
                </div>
                <Badge tone={plagiarismData.level}>{plagiarismData.similarity}% Similarity</Badge>
              </div>
            )}
          </Card>

          {isOverriding && (
            <Card className="border-2 border-[var(--accent)] bg-[var(--surface-alt)]/50">
              <div className="font-extrabold text-base text-[var(--accent)] mb-3 flex items-center justify-between">
                <span>✏️ Teacher Manual Mark Allotment Panel</span>
                <span className="text-xs font-normal text-[var(--text-soft)]">Adjust awarded marks per question</span>
              </div>
              <div className="space-y-3 my-4">
                {questionsList.map((q, idx) => (
                  <div key={idx} className="flex items-center justify-between p-4 bg-[var(--surface)] border border-[var(--border)] rounded-xl text-xs md:text-sm flex-wrap gap-3">
                    <div>
                      <strong className="text-[var(--text)] text-sm md:text-base">Question {q.question_number}</strong>
                      <span className="text-[var(--text-soft)] ml-2">({q.question_type || 'short_answer'}) · Max: {q.maximum_marks} Marks</span>
                      <p className="text-xs text-[var(--text-soft)] mt-1 italic">{q.answer_summary ? q.answer_summary.slice(0, 100) + '…' : 'No response detected'}</p>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <label className="font-bold text-[var(--text-soft)]">Awarded Marks:</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max={q.maximum_marks}
                        value={overrideMarksMap[idx] !== undefined ? overrideMarksMap[idx] : q.awarded_marks}
                        onChange={(e) => handleMarkChange(idx, e.target.value, q.maximum_marks)}
                        className="w-24 px-3 py-2 border border-[var(--border-strong)] rounded-xl text-base font-extrabold bg-[var(--surface-alt)] text-[var(--text)] text-center focus:border-[var(--accent)] outline-none"
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-3 pt-3 border-t border-[var(--border)]">
                <Button variant="secondary" size="sm" onClick={() => setIsOverriding(false)}>Cancel</Button>
                <Button size="sm" onClick={handleSaveOverride} disabled={overrideSaving}>
                  {overrideSaving ? 'Saving…' : 'Save Allotted Marks'}
                </Button>
              </div>
            </Card>
          )}

          <div className="grid lg:grid-cols-[1fr_380px] gap-6">
            <Card>
              <CardHeader title="Question-Level Breakdown" subtitle="Detailed step analysis and examiner feedback" />
              <div className="flex flex-wrap gap-2.5 mb-6">
                {questionsList.map((q, i) => (
                  <button
                    key={q.question_number || i}
                    onClick={() => setActiveQ(i)}
                    className={`w-11 h-11 rounded-xl border flex items-center justify-center text-sm font-bold transition-all cursor-pointer ${
                      i === activeQ
                        ? 'bg-[var(--accent)] border-[var(--accent)] text-white shadow-sm ring-2 ring-[var(--accent-soft)]'
                        : q.awarded_marks < (q.maximum_marks ?? q.max_marks ?? 0)
                        ? 'border-[var(--warning)] text-[var(--warning)] bg-[var(--warning-soft)]/20'
                        : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                    }`}
                  >
                    {q.question_number || `Q${i+1}`}
                  </button>
                ))}
              </div>

              {eq ? (
                <div className="space-y-4">
                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-1.5">Question {eq.question_number} ({eq.question_type || 'short_answer'})</div>
                    {eq.question_text && (
                      <div className="text-sm md:text-base font-semibold text-[var(--text)] bg-[var(--surface-alt)] p-4 rounded-xl border border-[var(--border)] leading-relaxed">
                        {eq.question_text}
                      </div>
                    )}
                  </div>

                  <div>
                    <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-1.5">Student Answer Script Extract</div>
                    <div className="text-sm leading-relaxed text-[var(--text)] bg-[var(--surface)] p-4 rounded-xl border border-[var(--border)] italic">
                      {eq.student_answer || eq.answer_summary || 'No answer detected in script.'}
                    </div>
                  </div>

                  {eq.answer_classification && (
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)]">Diagnosis:</span>
                      <Badge tone={
                        eq.answer_classification === 'correct_answer' ? 'success' :
                        eq.answer_classification.includes('calculation_error') ? 'warning' :
                        eq.answer_classification.includes('concept') ? 'error' : 'neutral'
                      }>
                        {eq.answer_classification.replace(/_/g, ' ').toUpperCase()}
                      </Badge>
                    </div>
                  )}

                  <div className="flex items-center justify-between p-4 bg-[var(--accent-soft)] rounded-2xl">
                    <div className="flex items-center gap-3">
                      <div className="text-3xl font-extrabold text-[var(--accent)]">{eq.awarded_marks}</div>
                      <div className="text-sm text-[var(--text-soft)] font-medium">
                        out of {eq.maximum_marks ?? eq.max_marks ?? 0} marks
                        {eq.percentage_of_question !== undefined && (
                          <span className="font-bold text-[var(--accent)] ml-2">({eq.percentage_of_question}%)</span>
                        )}
                      </div>
                    </div>
                    <Badge tone={statusTone}>
                      {eq.awarded_marks === (eq.maximum_marks ?? eq.max_marks) && (eq.maximum_marks ?? eq.max_marks) > 0 ? 'Full Marks' : eq.awarded_marks > 0 ? 'Partial Credit' : 'Zero Marks'}
                    </Badge>
                  </div>

                  {(eq.teacher_feedback || eq.evaluation_reason) && (
                    <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)]">
                      <div className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-1.5">Teacher Evaluation & Mark Breakdown</div>
                      <div className="text-sm font-medium text-[var(--text)] leading-relaxed">
                        {eq.teacher_feedback || eq.evaluation_reason}
                      </div>
                    </div>
                  )}

                  {(eq.what_was_done_correctly?.length > 0 || eq.strengths?.length > 0) && (
                    <div className="p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/20">
                      <div className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300 mb-1.5">Correct Steps Identified</div>
                      <ul className="list-disc pl-5 text-sm space-y-1 text-[var(--text)]">
                        {(eq.what_was_done_correctly || eq.strengths || []).map((pt, idx) => <li key={idx}>{pt}</li>)}
                      </ul>
                    </div>
                  )}

                  {(eq.what_is_incorrect?.length > 0 || eq.errors?.length > 0) && (
                    <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20">
                      <div className="text-xs font-bold uppercase tracking-wider text-red-700 dark:text-red-300 mb-1.5">Errors & Deviations</div>
                      <ul className="list-disc pl-5 text-sm space-y-1 text-red-700 dark:text-red-300">
                        {(eq.what_is_incorrect || eq.errors || []).map((pt, idx) => <li key={idx}>{pt}</li>)}
                      </ul>
                    </div>
                  )}

                  {eq.step_or_calculation_mistake && (
                    <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/20">
                      <div className="text-xs font-bold uppercase tracking-wider text-amber-700 dark:text-amber-300 mb-1.5">Calculation Mistake</div>
                      <div className="text-sm text-[var(--text)] leading-relaxed">{eq.step_or_calculation_mistake}</div>
                    </div>
                  )}

                  {(eq.what_student_should_have_written || eq.feedback?.expected_answer) && (
                    <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                      <div className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-1.5">Model Solution & Expected Steps</div>
                      <div className="text-xs md:text-sm text-[var(--text)] whitespace-pre-line leading-relaxed font-mono bg-[var(--surface-alt)] p-3 rounded-lg">
                        {eq.what_student_should_have_written || eq.feedback?.expected_answer}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-sm text-[var(--text-soft)]">No question data available.</div>
              )}
            </Card>

            <div className="space-y-5">
              <Card>
                <CardHeader title="Overall Academic Summary" subtitle="Performance synthesis" />
                <div className="text-sm leading-relaxed mb-4 text-[var(--text)]">
                  {evalData.overall_teacher_comment || evalData.overall_feedback}
                </div>
                <hr className="hairline my-4" />
                <div className="divide-y divide-[var(--border)]">
                  <RowItem title="Overall Grade" right={<Badge tone="success">Grade {grade}</Badge>} />
                  <RowItem title="Percentage" right={<Badge tone="accent">{percentage}%</Badge>} />
                </div>

                {evalData.priority_topics_to_revise?.length > 0 && (
                  <div className="mt-4 pt-4 border-t border-[var(--border)]">
                    <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] block mb-2">Priority Revision Topics</span>
                    <ul className="list-disc pl-5 text-xs md:text-sm text-[var(--text-soft)] space-y-1">
                      {evalData.priority_topics_to_revise.map((p, i) => <li key={i}>{p}</li>)}
                    </ul>
                  </div>
                )}
              </Card>

              <Card>
                <CardHeader title="Actions & Reports" />
                <div className="flex flex-col gap-3">
                  <Button className="w-full flex items-center justify-center gap-2" onClick={() => evalId ? api.downloadEvaluationPdf(evalId) : api.generatePdfReport(evalData)}>
                    <Download size={16} /> Download PDF Evaluation Report
                  </Button>
                  <Button variant="secondary" className="w-full flex items-center justify-center gap-2" onClick={() => navigate('/app/history')}>
                    View All Stored Evaluations <ArrowRight size={16} />
                  </Button>
                  <Button variant="ghost" className="w-full" onClick={() => { setStep(1); setResult(false); setQpFile(null); setAnsFile(null) }}>
                    Evaluate Another Script
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
