import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { BOARDS, STREAMS, CLASSES, COLLEGE_SEMESTERS } from '../data/syllabusData.js'
import { CheckCircle2, ChevronRight, ChevronLeft, GraduationCap, BookOpen, Upload, X } from 'lucide-react'

const STEPS_SCHOOL = ['Level', 'Board', 'Class & Stream', 'Subjects', 'Done']
const STEPS_COLLEGE = ['Level', 'Semester', 'Done']

function StepDots({ steps, current }) {
  return (
    <div className="flex items-center gap-2 mb-8">
      {steps.map((s, i) => (
        <div key={s} className="flex items-center gap-2">
          <div className={`h-2 rounded-full transition-all duration-300 ${
            i < current ? 'w-6 bg-[var(--accent)]' :
            i === current ? 'w-8 bg-[var(--accent)]' :
            'w-2 bg-[var(--border-strong)]'
          }`} />
          {i < steps.length - 1 && <div className="w-3 h-px bg-[var(--border)]" />}
        </div>
      ))}
      <span className="text-xs text-[var(--text-faint)] ml-1">{steps[current]}</span>
    </div>
  )
}

export default function Onboarding() {
  const { setProfile } = useApp()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [level, setLevel] = useState(null) // 'school' | 'college'
  const [board, setBoard] = useState('CBSE')
  const [classLevel, setClassLevel] = useState(12)
  const [stream, setStream] = useState('Science')
  const [subjects, setSubjects] = useState(['Physics', 'Chemistry', 'Mathematics', 'Biology'])
  const [semester, setSemester] = useState(3)
  const [syllabusFile, setSyllabusFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [analysing, setAnalysing] = useState(false)

  const steps = level === 'college' ? STEPS_COLLEGE : STEPS_SCHOOL

  const handleLevelSelect = (l) => {
    setLevel(l)
    setStep(1)
  }

  const toggleSubject = (sub) => {
    setSubjects((prev) =>
      prev.includes(sub) ? prev.filter((s) => s !== sub) : [...prev, sub]
    )
  }

  const handleFileUpload = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setSyllabusFile(file.name)
    setUploadProgress(0)
    setAnalysing(true)
    const interval = setInterval(() => {
      setUploadProgress((p) => {
        if (p >= 100) { clearInterval(interval); setAnalysing(false); return 100 }
        return p + 8
      })
    }, 120)
  }

  const finish = () => {
    const profileData = {
      level,
      board: level === 'school' ? board : null,
      classLevel: level === 'school' ? classLevel : null,
      stream: level === 'school' ? stream : null,
      subjects: level === 'school' ? subjects : ['Engineering Mathematics', 'Physics', 'Data Structures', 'Electronics'],
      semester: level === 'college' ? semester : null,
      syllabusFile: level === 'college' ? syllabusFile : null,
    }
    setProfile(profileData)
    navigate('/app/dashboard')
  }

  const currentSubjects = STREAMS[stream] || []

  return (
    <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center p-6">
      <div className="w-full max-w-[520px]">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="10.5" stroke="var(--accent)" strokeWidth="2" />
            <circle cx="24" cy="9" r="4" fill="var(--accent)" />
          </svg>
          <div className="text-base font-extrabold tracking-tight">
            LearnSphere<small className="font-semibold text-[var(--accent)] text-xs ml-0.5">AI</small>
          </div>
        </div>

        {/* Step 0: Level */}
        {step === 0 && (
          <div>
            <h1 className="text-2xl font-extrabold mb-1.5">Let's personalise your experience</h1>
            <p className="text-[var(--text-soft)] text-sm mb-8">We'll use this to tailor your syllabus, questions, and study plan.</p>
            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'school', label: 'School Student', sub: 'Class 10 · 11 · 12', icon: BookOpen, desc: 'CBSE, State Board, ICSE & more' },
                { id: 'college', label: 'College Student', sub: 'Any semester', icon: GraduationCap, desc: 'Upload your syllabus for personalised content' },
              ].map(({ id, label, sub, icon: Icon, desc }) => (
                <button
                  key={id}
                  onClick={() => handleLevelSelect(id)}
                  className="text-left border-[1.5px] border-[var(--border-strong)] rounded-2xl p-5 hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all group"
                >
                  <Icon size={28} strokeWidth={1.5} className="text-[var(--accent)] mb-3 group-hover:scale-110 transition-transform" />
                  <div className="text-[14.5px] font-bold mb-0.5">{label}</div>
                  <div className="text-xs text-[var(--text-soft)] mb-2">{sub}</div>
                  <div className="text-[11.5px] text-[var(--text-faint)]">{desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* School steps */}
        {level === 'school' && step > 0 && (
          <div>
            <StepDots steps={STEPS_SCHOOL} current={step} />

            {/* Step 1: Board */}
            {step === 1 && (
              <div>
                <h2 className="text-xl font-extrabold mb-1">Which board are you studying under?</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6">We'll load the official syllabus for your board.</p>
                <div className="grid grid-cols-2 gap-3 mb-8">
                  {BOARDS.map((b) => (
                    <button
                      key={b}
                      onClick={() => setBoard(b)}
                      className={`border-[1.5px] rounded-xl px-4 py-3.5 text-left text-[13px] font-semibold transition-all ${
                        board === b
                          ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                          : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                      }`}
                    >
                      {b}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Step 2: Class + Stream */}
            {step === 2 && (
              <div>
                <h2 className="text-xl font-extrabold mb-1">Your class and stream</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6">This helps us load the right chapters and questions.</p>
                <div className="mb-5">
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2.5">Class</div>
                  <div className="flex gap-3">
                    {CLASSES.map((c) => (
                      <button
                        key={c}
                        onClick={() => setClassLevel(c)}
                        className={`flex-1 border-[1.5px] rounded-xl py-3 text-[14px] font-bold transition-all ${
                          classLevel === c
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                            : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        {c}
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2.5">Stream</div>
                  <div className="flex gap-3">
                    {Object.keys(STREAMS).map((s) => (
                      <button
                        key={s}
                        onClick={() => { setStream(s); setSubjects(STREAMS[s]) }}
                        className={`flex-1 border-[1.5px] rounded-xl py-3 text-[13px] font-bold transition-all ${
                          stream === s
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                            : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Subjects */}
            {step === 3 && (
              <div>
                <h2 className="text-xl font-extrabold mb-1">Select your subjects</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6">All are selected by default. Deselect any you don't study.</p>
                <div className="grid grid-cols-2 gap-3 mb-4">
                  {currentSubjects.map((sub) => {
                    const selected = subjects.includes(sub)
                    return (
                      <button
                        key={sub}
                        onClick={() => toggleSubject(sub)}
                        className={`flex items-center gap-2.5 border-[1.5px] rounded-xl px-4 py-3.5 text-left transition-all ${
                          selected
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)]'
                            : 'border-[var(--border-strong)] opacity-50 hover:opacity-80 hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        {selected
                          ? <CheckCircle2 size={16} className="text-[var(--accent)] shrink-0" />
                          : <div className="w-4 h-4 rounded-full border border-[var(--border-strong)] shrink-0" />
                        }
                        <span className="text-[13px] font-semibold">{sub}</span>
                      </button>
                    )
                  })}
                </div>
                {subjects.length === 0 && (
                  <p className="text-xs text-[var(--error)] font-semibold">Select at least one subject to continue.</p>
                )}
              </div>
            )}

            {/* Step 4: Done */}
            {step === 4 && (
              <div className="text-center py-4">
                <div className="text-5xl mb-5">🎉</div>
                <h2 className="text-xl font-extrabold mb-2">You're all set!</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6 max-w-[340px] mx-auto">
                  Your {board} Class {classLevel} {stream} profile is ready. Reality Lab, Knowledge Challenge, and your Personal Trainer are now personalised to your syllabus.
                </p>
                <div className="bg-[var(--accent-soft)] rounded-xl p-4 text-left mb-6 text-sm">
                  <div className="font-bold text-[var(--accent)] mb-2">Your profile</div>
                  <div className="text-[var(--text-soft)] space-y-1">
                    <div>🏫 <strong>{board}</strong> — Class <strong>{classLevel}</strong></div>
                    <div>📚 Stream: <strong>{stream}</strong></div>
                    <div>📖 Subjects: <strong>{subjects.join(' · ')}</strong></div>
                  </div>
                </div>
                <button
                  onClick={finish}
                  className="w-full py-3.5 bg-[var(--accent)] text-white font-bold rounded-xl hover:bg-[var(--accent-dim)] transition-colors"
                >
                  Start Learning →
                </button>
              </div>
            )}
          </div>
        )}

        {/* College steps */}
        {level === 'college' && step > 0 && (
          <div>
            <StepDots steps={STEPS_COLLEGE} current={step} />

            {step === 1 && (
              <div>
                <h2 className="text-xl font-extrabold mb-1">Your semester & syllabus</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6">
                  Select your current semester. Optionally upload your syllabus PDF for fully personalised questions.
                </p>
                <div className="mb-6">
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2.5">Current Semester</div>
                  <div className="grid grid-cols-4 gap-2">
                    {COLLEGE_SEMESTERS.map((s) => (
                      <button
                        key={s}
                        onClick={() => setSemester(s)}
                        className={`border-[1.5px] rounded-xl py-3 text-[14px] font-bold transition-all ${
                          semester === s
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                            : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        Sem {s}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="border-[1.5px] border-dashed border-[var(--border-strong)] rounded-xl p-6 text-center">
                  <Upload size={24} className="mx-auto mb-2 text-[var(--text-faint)]" />
                  <div className="text-[13.5px] font-semibold mb-1">Upload Syllabus PDF</div>
                  <div className="text-xs text-[var(--text-faint)] mb-4">Optional — AI will analyse and generate personalised questions</div>
                  <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 border border-[var(--border-strong)] rounded-lg text-xs font-semibold text-[var(--text-soft)] hover:border-[var(--accent)] transition-colors">
                    <Upload size={12} /> Choose PDF
                    <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                  </label>
                  {syllabusFile && (
                    <div className="mt-3">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-[var(--accent)] font-semibold">{syllabusFile}</span>
                        {analysing ? <span className="text-[var(--text-faint)]">Analysing…</span> : <span className="text-[var(--success)]">✓ Analysed</span>}
                      </div>
                      <div className="h-1.5 bg-[var(--surface-alt)] rounded-full overflow-hidden">
                        <div className="h-full bg-[var(--accent)] rounded-full transition-all duration-200" style={{ width: `${uploadProgress}%` }} />
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="text-center py-4">
                <div className="text-5xl mb-5">🎓</div>
                <h2 className="text-xl font-extrabold mb-2">You're all set!</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6 max-w-[340px] mx-auto">
                  Your Semester {semester} profile is ready. {syllabusFile ? 'Your uploaded syllabus is analysed and' : 'Default college-level content is'} ready for Reality Lab and Knowledge Challenge.
                </p>
                <div className="bg-[var(--accent-soft)] rounded-xl p-4 text-left mb-6 text-sm">
                  <div className="font-bold text-[var(--accent)] mb-2">Your profile</div>
                  <div className="text-[var(--text-soft)] space-y-1">
                    <div>🎓 College Student — <strong>Semester {semester}</strong></div>
                    {syllabusFile && <div>📄 Syllabus: <strong>{syllabusFile}</strong></div>}
                  </div>
                </div>
                <button
                  onClick={finish}
                  className="w-full py-3.5 bg-[var(--accent)] text-white font-bold rounded-xl hover:bg-[var(--accent-dim)] transition-colors"
                >
                  Start Learning →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Navigation buttons */}
        {step > 0 && step < steps.length - 1 && (
          <div className="flex items-center justify-between mt-8">
            <button
              onClick={() => setStep((s) => s - 1)}
              className="flex items-center gap-1.5 px-4 py-2.5 border border-[var(--border-strong)] rounded-xl text-[13px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors"
            >
              <ChevronLeft size={15} /> Back
            </button>
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={level === 'school' && step === 3 && subjects.length === 0}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-[var(--accent)] text-white rounded-xl text-[13px] font-bold hover:bg-[var(--accent-dim)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              Continue <ChevronRight size={15} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
