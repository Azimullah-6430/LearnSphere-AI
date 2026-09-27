import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { CheckCircle2, FileText, UploadCloud, X, ShieldAlert, Sparkles, ArrowRight, BookOpen, Download } from 'lucide-react'
import { Card, CardHeader, Badge, Button, RowItem, PageHead } from '../components/ui/Primitives.jsx'
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
    <div className="flex items-center mb-7 overflow-x-auto">
      {STEP_LABELS.map((label, i) => {
        const n = i + 1
        const state = n < step ? 'done' : n === step ? 'active' : 'pending'
        return (
          <div className="flex items-center" key={label}>
            <div className="flex items-center gap-2.5 shrink-0">
              <div
                className={`w-7 h-7 rounded-full border-[1.5px] flex items-center justify-center text-xs font-bold shrink-0 transition-all ${
                  state === 'active'
                    ? 'border-[var(--accent)] bg-[var(--accent)] text-white'
                    : state === 'done'
                    ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                    : 'border-[var(--border-strong)] text-[var(--text-faint)]'
                }`}
              >
                {state === 'done' ? '✓' : `0${n}`}
              </div>
              <div className={`text-xs font-semibold ${state === 'pending' ? 'text-[var(--text-faint)]' : 'text-[var(--text)]'}`}>{label}</div>
            </div>
            {n < STEP_LABELS.length && <div className="flex-1 h-px bg-[var(--border-strong)] mx-3.5 min-w-[24px]" />}
          </div>
        )
      })}
    </div>
  )
}

function UploadZone({ label, hint, icon: Icon = UploadCloud, onUpload }) {
  return (
    <label className="block border-[1.5px] border-dashed border-[var(--border-strong)] rounded-md py-[48px] px-6 text-center bg-[var(--surface-alt)] hover:border-[var(--accent-dim)] transition-colors cursor-pointer relative">
      <Icon size={34} strokeWidth={1.6} className="text-[var(--accent)] mx-auto mb-3" />
      <h3 className="text-[15px] font-semibold mb-1">{label}</h3>
      <p className="text-xs text-[var(--text-faint)]">{hint}</p>
      <input type="file" className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" onChange={onUpload} />
    </label>
  )
}

function DocPreview({ name, info, onRemove }) {
  return (
    <div className="flex items-center gap-3.5 p-4 border border-[var(--border)] rounded-lg bg-[var(--surface)] mt-4">
      <div className="w-10 h-12 rounded-[5px] bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0">
        <FileText size={20} strokeWidth={1.6} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[13.5px] font-bold truncate">{name}</div>
        <div className="text-xs text-[var(--text-faint)] mt-0.5">{info}</div>
      </div>
      {onRemove && (
        <button onClick={onRemove} className="w-9 h-9 flex items-center justify-center rounded-lg border border-[var(--border)] text-[var(--text-soft)] hover:text-[var(--text)]">
          <X size={15} strokeWidth={1.7} />
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
  const [studentName, setStudentName] = useState(user?.name || 'Student')
  const [subject, setSubject] = useState(user?.subjects?.[0] || (user?.level === 'college' ? 'Software Engineering' : 'Science'))
  const [rollNumber, setRollNumber] = useState(user?.roll_number || '12A-01')
  const [assessmentTitle, setAssessmentTitle] = useState('Unit Assessment')
  
  const [level, setLevel] = useState(user?.level || 'school')
  const [board, setBoard] = useState(user?.board || 'CBSE')
  const [stream, setStream] = useState(user?.stream || 'Science')
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
    setOverrideMarksMap(prev => ({ ...prev, [idx]: num }))
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

      // Auto-detect subject from filename if present
      const fname = file.name.toLowerCase()
      if (fname.includes('software') || fname.includes('se_') || fname.includes('cse') || fname.includes('computer') || fname.includes('coding')) {
        setSubject('Software Engineering')
      } else if (fname.includes('math') || fname.includes('calc') || fname.includes('algebra')) {
        setSubject('Mathematics')
      } else if (fname.includes('chem')) {
        setSubject('Chemistry')
      } else if (fname.includes('phy')) {
        setSubject('Physics')
      } else if (fname.includes('tamil')) {
        setSubject('Tamil')
      } else if (fname.includes('hindi')) {
        setSubject('Hindi')
      } else if (fname.includes('eng')) {
        setSubject('English')
      }
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
      formData.append('role', role)
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

  const questionsList = evalData?.evaluations || []
  const totalMarks = evalData ? evalData.obtained_marks : 0
  const totalMax = evalData ? evalData.total_marks : 0
  const percentage = evalData ? evalData.percentage : 0
  const grade = evalData ? evalData.grade : 'B'

  const eq = questionsList[activeQ] || questionsList[0]
  const statusTone = eq ? (eq.awarded_marks === eq.maximum_marks && eq.maximum_marks > 0 ? 'success' : eq.awarded_marks > 0 ? 'warning' : 'error') : 'info'

  return (
    <>
      <PageHead title="Strict Paper Evaluation" subtitle="Upload Question Paper and Answer Script to evaluate strictly based on your materials." />
      <Stepper step={Math.min(step, 5)} />

      {errorMsg && (
        <div className="p-4 bg-[var(--warning-soft)] border border-[var(--warning)] text-xs font-semibold rounded-lg mb-4 text-[var(--warning)]">
          {errorMsg}
        </div>
      )}

      {step === 1 && (
        <>
          <Card>
            <CardHeader title="1. Question Paper (Source of Truth)" />
            <UploadZone label="Upload printed Question Paper" hint="PDF, JPG or PNG · exact questions and marks extracted by AI" onUpload={handleQpUpload} />
            {qpFile && (
              <DocPreview name={qpFile} info={<>Question Paper attached · <span className="text-[var(--success)]">Ready to extract</span></>} onRemove={() => { setQpFile(null); setQpRawFile(null) }} />
            )}
          </Card>
          <div className="flex justify-end mt-[18px]">
            <Button onClick={() => setStep(2)}>Continue</Button>
          </div>
        </>
      )}

      {step === 2 && (
        <>
          <Card>
            <CardHeader title="2. Student Answer Script" />
            <UploadZone label="Upload student handwritten Answer Script" hint="PDF, JPG or PNG · handwritten steps visually graded" onUpload={handleAnsUpload} />
            {ansFile && (
              <DocPreview name={ansFile} info={<>Answer Script attached · <span className="text-[var(--success)]">Ready to grade</span></>} onRemove={() => { setAnsFile(null); setAnsRawFile(null) }} />
            )}
          </Card>
          <div className="flex justify-between mt-[18px]">
            <Button variant="secondary" onClick={() => setStep(1)}>Back</Button>
            <Button onClick={() => setStep(3)}>Continue</Button>
          </div>
        </>
      )}

      {step === 3 && (
        <>
          <Card className="mb-4">
            <CardHeader title="3. Context & Optional Syllabus" />
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Student Name</label>
              <input value={studentName} onChange={(e) => setStudentName(e.target.value)} className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
            </div>
            <div className="grid grid-cols-2 gap-3 mb-4">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Subject</label>
                <input value={subject} onChange={(e) => setSubject(e.target.value)} className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
              </div>
              <div>
                <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Roll / Registration Number</label>
                <input value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
              </div>
            </div>
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Assessment Title</label>
              <input value={assessmentTitle} onChange={(e) => setAssessmentTitle(e.target.value)} className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
            </div>

            <div className="p-4 bg-[var(--surface-alt)] border border-[var(--border)] rounded-lg mt-2">
              <label className="block text-xs font-bold text-[var(--accent)] mb-1.5">Attach Syllabus Document (Optional Context)</label>
              <p className="text-xs text-[var(--text-faint)] mb-3">Uploading your syllabus helps Gemini evaluate concepts against your exact curriculum guidelines.</p>
              <UploadZone label="Upload Syllabus PDF/Image" hint="Optional syllabus criteria" icon={BookOpen} onUpload={handleSyllabusUpload} />
              {syllabusFile && (
                <DocPreview name={syllabusFile} info={<>Syllabus attached</>} onRemove={() => { setSyllabusFile(null); setSyllabusRawFile(null) }} />
              )}
            </div>
          </Card>
          <div className="flex justify-between mt-[18px]">
            <Button variant="secondary" onClick={() => setStep(2)}>Back</Button>
            <Button onClick={() => setStep(4)}>Review</Button>
          </div>
        </>
      )}

      {step === 4 && (
        <>
          <Card>
            <CardHeader title="4. Confirm & Run Evaluation" />
            <RowItem title="Question paper" subtitle={qpFile || "Not uploaded"} right={<Badge tone={qpFile ? "success" : "error"}>{qpFile ? "Ready" : "Missing"}</Badge>} />
            <RowItem title="Answer script" subtitle={ansFile || "Not uploaded"} right={<Badge tone={ansFile ? "success" : "error"}>{ansFile ? "Ready" : "Missing"}</Badge>} />
            <RowItem title="Student & Level" subtitle={`${studentName} (${rollNumber}) · ${subject} · ${(level || 'school').toUpperCase()}`} right={<Badge tone="success">Confirmed</Badge>} />
            {syllabusFile && <RowItem title="Syllabus reference" subtitle={syllabusFile} right={<Badge tone="info">Attached</Badge>} />}
          </Card>
          <div className="flex justify-between mt-[18px]">
            <Button variant="secondary" onClick={() => setStep(3)}>Back</Button>
            <Button onClick={startEvaluation} className="flex items-center gap-2">
              <Sparkles size={16} /> Evaluate Uploaded Materials
            </Button>
          </div>
        </>
      )}

      {step === 5 && processing && (
        <Card className="max-w-[540px] mx-auto py-8">
          <CardHeader title="Gemini Multimodal Evaluation in Progress" />
          <div className="flex flex-col gap-4 mt-2">
            {STAGES.map((s, i) => {
              const state = i < doneStages ? 'done' : i === doneStages ? 'active' : 'pending'
              return (
                <div className="flex items-center gap-3 text-[13.5px]" key={s}>
                  <div
                    className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 transition-all ${
                      state === 'done' ? 'bg-[var(--success)] text-white' : state === 'active' ? 'bg-[var(--accent)] text-white animate-pulse' : 'bg-[var(--surface-alt)] border-[1.5px] border-[var(--border-strong)]'
                    }`}
                  >
                    {state === 'done' && <CheckCircle2 size={14} strokeWidth={3} />}
                  </div>
                  <span className={state === 'pending' ? 'text-[var(--text-faint)]' : state === 'active' ? 'font-bold text-[var(--accent)]' : 'font-semibold'}>{s}</span>
                </div>
              )
            })}
          </div>
        </Card>
      )}

      {result && evalData && (
        <>
          {(evalData.is_unreadable || evalData.assigned_to_teacher) && (
            <div className="mb-4 p-4 rounded-xl bg-[var(--warning-soft)] border border-[var(--warning)] text-xs font-semibold text-[var(--warning)] flex items-start gap-3">
              <ShieldAlert size={20} className="shrink-0 mt-0.5" />
              <div>
                <div className="font-extrabold text-[13.5px] mb-0.5">⚠️ Handwriting Unreadable / Low AI Confidence — Assigned to Teacher</div>
                <p className="text-[12px] opacity-90">
                  {evalData.unreadable_reason || 'The student handwriting could not be parsed with >90% precision safety. The script has been assigned to you for manual mark allotment below.'}
                </p>
              </div>
            </div>
          )}

          {overrideSuccess && (
            <div className="mb-4 p-3 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] text-xs font-bold text-[var(--success)] flex items-center justify-between">
              <span>✅ {overrideSuccess}</span>
              <button onClick={() => setOverrideSuccess('')} className="text-xs font-bold">✕</button>
            </div>
          )}

          <Card className="mb-4 border-l-4 border-l-[var(--accent)]">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <Badge tone={evalData.is_unreadable ? "warning" : "success"}>
                    {evalData.is_unreadable ? "Assigned to Teacher for Manual Grading" : "Evaluation Complete & Stored in MongoDB"}
                  </Badge>
                  {evalId && <span className="text-xs text-[var(--text-faint)]">Doc ID: {evalId}</span>}
                </div>
                <h2 className="text-[20px] font-bold mt-2">{studentName} — {subject}</h2>
                <p className="text-[var(--text-faint)] text-xs mt-0.5">{assessmentTitle} · Roll: {rollNumber} ({(level || 'school').toUpperCase()})</p>
              </div>
              <div className="flex flex-col items-end gap-2">
                <div className="text-right">
                  <div className="text-[34px] font-extrabold text-[var(--accent)] leading-tight">
                    {totalMarks} <span className="text-base font-normal text-[var(--text-faint)]">/ {totalMax}</span>
                  </div>
                  <div className="text-[var(--text-faint)] text-xs font-semibold">{percentage}% · Grade {grade}</div>
                </div>
                <div className="flex items-center gap-2">
                  {role === 'teacher' && (
                    <Button
                      size="sm"
                      variant={isOverriding ? "secondary" : "outline"}
                      onClick={isOverriding ? () => setIsOverriding(false) : handleStartOverride}
                    >
                      {isOverriding ? "Cancel Override" : "✏️ Allot / Override Marks"}
                    </Button>
                  )}
                  <Button size="sm" className="flex items-center gap-1.5" onClick={() => evalId ? api.downloadEvaluationPdf(evalId) : api.generatePdfReport(evalData)}>
                    <Download size={14} /> Download PDF Report
                  </Button>
                </div>
              </div>
            </div>

            {role === 'teacher' && plagiarismData && plagiarismData.similarity > 0 && (
              <div className="mt-4 pt-3.5 border-t border-[var(--border)] flex items-center justify-between flex-wrap gap-2 text-xs">
                <div className="flex items-center gap-2">
                  <ShieldAlert size={16} className={plagiarismData.suspected ? "text-[var(--warning)]" : "text-[var(--success)]"} />
                  <span className="font-semibold">Plagiarism Audit:</span>
                  <span>{plagiarismData.details}</span>
                </div>
                <Badge tone={plagiarismData.level}>{plagiarismData.similarity}% Similarity</Badge>
              </div>
            )}
          </Card>

          {isOverriding && (
            <Card className="mb-4 border-2 border-[var(--accent)] bg-[var(--surface-alt)]">
              <div className="font-extrabold text-[14px] text-[var(--accent)] mb-2 flex items-center justify-between">
                <span>✏️ Teacher Manual Mark Allotment Panel</span>
                <span className="text-xs font-normal text-[var(--text-faint)]">Edit awarded marks per question</span>
              </div>
              <div className="space-y-3 my-3">
                {questionsList.map((q, idx) => (
                  <div key={idx} className="flex items-center justify-between p-3 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-xs flex-wrap gap-2">
                    <div>
                      <strong className="text-[var(--text)] text-[13px]">Question {q.question_number}</strong>
                      <span className="text-[var(--text-faint)] ml-2">({q.question_type || 'short_answer'}) · Max: {q.maximum_marks} Marks</span>
                      <p className="text-[11.5px] text-[var(--text-faint)] mt-0.5 italic">{q.answer_summary ? q.answer_summary.slice(0, 80) + '...' : 'No response summary'}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <label className="font-bold text-[var(--text-soft)]">Awarded Marks:</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        max={q.maximum_marks}
                        value={overrideMarksMap[idx] !== undefined ? overrideMarksMap[idx] : q.awarded_marks}
                        onChange={(e) => handleMarkChange(idx, e.target.value, q.maximum_marks)}
                        className="w-20 px-2.5 py-1.5 border border-[var(--border-strong)] rounded text-sm font-extrabold bg-[var(--surface-alt)] text-[var(--text)] text-center focus:border-[var(--accent)]"
                      />
                    </div>
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2 pt-2 border-t border-[var(--border)]">
                <Button variant="secondary" size="sm" onClick={() => setIsOverriding(false)}>Cancel</Button>
                <Button size="sm" onClick={handleSaveOverride} disabled={overrideSaving}>
                  {overrideSaving ? 'Saving Marks...' : 'Save Custom Marks'}
                </Button>
              </div>
            </Card>
          )}

          <div className="grid lg:grid-cols-[1fr_360px] gap-4">
            <Card>
              <CardHeader title="Extracted Question Breakdown" />
              <div className="flex flex-wrap gap-2 mb-[18px]">
                {questionsList.map((q, i) => (
                  <button
                    key={q.question_number || i}
                    onClick={() => setActiveQ(i)}
                    className={`w-[36px] h-[36px] rounded-lg border-[1.5px] flex items-center justify-center text-xs font-bold transition-all ${
                      i === activeQ
                        ? 'bg-[var(--accent)] border-[var(--accent)] text-white shadow-sm'
                        : q.awarded_marks < q.maximum_marks
                        ? 'border-[var(--warning)] text-[var(--warning)]'
                        : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                    }`}
                  >
                    {q.question_number || `Q${i+1}`}
                  </button>
                ))}
              </div>

              {eq ? (
                <>
                  <div className="mb-4">
                    <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-faint)] mb-1">Question Number & Type</div>
                    <div className="text-[14px] font-semibold">{eq.question_number} ({eq.question_type || 'short_answer'})</div>
                  </div>
                  
                  <div className="mb-4">
                    <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-faint)] mb-1">Handwritten Script Extraction</div>
                    <div className="text-[13.5px] leading-relaxed text-[var(--text-soft)] bg-[var(--surface-alt)] p-3 rounded-md">{eq.answer_summary || 'No response detected for this question.'}</div>
                  </div>

                  <div className="flex items-center gap-4 p-3.5 px-4 bg-[var(--accent-soft)] rounded-lg mb-4">
                    <div className="text-2xl font-extrabold text-[var(--accent)]">{eq.awarded_marks}</div>
                    <div className="text-[13px] text-[var(--text-soft)]">
                      out of {eq.maximum_marks} marks · <Badge tone={statusTone}>{eq.awarded_marks === eq.maximum_marks ? 'Full Marks' : eq.awarded_marks > 0 ? 'Partial Credit' : 'Incorrect'}</Badge>
                    </div>
                  </div>

                  {eq.feedback?.what_was_done_well?.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--success)] mb-1">Correct Working Points</div>
                      <ul className="list-disc pl-5 text-[13px] space-y-1">
                        {eq.feedback.what_was_done_well.map((pt, idx) => <li key={idx}>{pt}</li>)}
                      </ul>
                    </div>
                  )}

                  {eq.feedback?.missing_points?.length > 0 && (
                    <div className="mb-3">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--warning)] mb-1">Missing / Incorrect Points</div>
                      <ul className="list-disc pl-5 text-[13px] space-y-1 text-[var(--warning)]">
                        {eq.feedback.missing_points.map((pt, idx) => <li key={idx}>{pt}</li>)}
                      </ul>
                    </div>
                  )}

                  {eq.feedback?.expected_answer && (
                    <div className="mb-3">
                      <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--text-faint)] mb-1">Expected Standard Solution</div>
                      <div className="text-[13px] p-2.5 bg-[var(--surface)] border border-[var(--border)] rounded">{eq.feedback.expected_answer}</div>
                    </div>
                  )}

                  {eq.feedback?.improvement && (
                    <div>
                      <div className="text-[11px] font-bold uppercase tracking-wide text-[var(--accent-dim)] mb-1">How to Improve</div>
                      <div className="text-[13.5px] leading-relaxed text-[var(--accent-dim)]">{eq.feedback.improvement}</div>
                    </div>
                  )}
                </>
              ) : (
                <div>No question data available.</div>
              )}
            </Card>

            <div className="flex flex-col gap-4">
              <Card>
                <CardHeader title="Overall Summary" />
                <div className="text-[13.5px] leading-relaxed mb-4">{evalData.overall_feedback}</div>
                <hr className="hairline my-3" />
                <RowItem title="Overall Grade" right={<Badge tone="success">Grade {grade}</Badge>} />
                <RowItem title="Percentage" right={<Badge tone="info">{percentage}%</Badge>} />
              </Card>

              <Card>
                <CardHeader title="Next Actions" />
                <div className="flex flex-col gap-2">
                  <Button className="w-full flex items-center justify-center gap-2" onClick={() => evalId ? api.downloadEvaluationPdf(evalId) : api.generatePdfReport(evalData)}>
                    <Download size={14} /> Download PDF Evaluation Report
                  </Button>
                  <Button variant="secondary" className="w-full flex items-center justify-center gap-2" onClick={() => navigate('/app/history')}>
                    View Stored Evaluations <ArrowRight size={14} />
                  </Button>
                  <Button variant="ghost" className="w-full" onClick={() => { setStep(1); setResult(false); setQpFile(null); setAnsFile(null) }}>
                    Evaluate Another Script
                  </Button>
                </div>
              </Card>
            </div>
          </div>
        </>
      )}
    </>
  )
}
