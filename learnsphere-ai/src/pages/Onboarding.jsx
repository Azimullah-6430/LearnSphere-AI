import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { BOARDS, STREAMS, CLASSES, COLLEGE_SEMESTERS, COLLEGE_STREAMS, COLLEGE_DOMAINS } from '../data/syllabusData.js'
import { api } from '../services/api.js'
import { CheckCircle2, ChevronRight, ChevronLeft, GraduationCap, BookOpen, Upload, X, Sparkles, Building, Layers } from 'lucide-react'

const STEPS_SCHOOL = ['Level', 'School & Board', 'Class & Stream', 'Subjects', 'Done']
const STEPS_COLLEGE = ['Level', 'Program & Branch', 'Year & Semester', 'Syllabus', 'Done']

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
      <span className="text-xs text-[var(--text-faint)] ml-1 font-semibold">{steps[current]}</span>
    </div>
  )
}

export default function Onboarding() {
  const { user, studentProfile, updateProfile, setSyllabusData } = useApp()
  const navigate = useNavigate()

  const [step, setStep] = useState(0)
  const [level, setLevel] = useState(user?.level || 'college') // 'school' | 'college'

  // School profile states
  const [schoolName, setSchoolName] = useState(user?.institution_name || user?.school || '')
  const [board, setBoard] = useState(user?.board || 'CBSE')
  const [classLevel, setClassLevel] = useState(user?.grade_level || user?.classLevel || 12)
  const [schoolStream, setSchoolStream] = useState(user?.stream || 'Science')
  const [schoolSection, setSchoolSection] = useState(user?.section || '')
  const [schoolRoll, setSchoolRoll] = useState(user?.roll_number || '')
  const [subjects, setSubjects] = useState(user?.subjects || STREAMS['Science'] || [])

  // College profile states
  const [institutionName, setInstitutionName] = useState(user?.institution_name || user?.institution || user?.college || '')
  const [degree, setDegree] = useState(user?.degree || user?.program || 'B.Tech')
  const [collegeStream, setCollegeStream] = useState(user?.stream || 'Engineering & Technology')
  const [collegeDomain, setCollegeDomain] = useState(user?.domain || user?.department || 'Computer Science & AI')
  const [collegeBranch, setCollegeBranch] = useState(user?.branch || user?.department || 'Computer Science & Engineering')
  const [currentYear, setCurrentYear] = useState(user?.current_year || user?.currentYear || user?.year || '3rd Year')
  const [semester, setSemester] = useState(Number(user?.semester || user?.current_semester || user?.currentSemester || 5))
  const [regulation, setRegulation] = useState(user?.regulation || user?.batch || '')
  const [academicYear, setAcademicYear] = useState(user?.academic_year || user?.academicYear || '2024-2025')

  // Syllabus file state
  const [syllabusFile, setSyllabusFile] = useState(null)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [analysing, setAnalysing] = useState(false)
  const [analysisError, setAnalysisError] = useState('')

  const steps = level === 'college' ? STEPS_COLLEGE : STEPS_SCHOOL

  const handleLevelSelect = (l) => {
    setLevel(l)
    setStep(1)
  }

  const handleCollegeStreamChange = (val) => {
    setCollegeStream(val)
    const availableDomains = COLLEGE_DOMAINS[val] || []
    if (availableDomains.length > 0) {
      setCollegeDomain(availableDomains[0])
      setCollegeBranch(availableDomains[0])
    }
  }

  const handleSemesterSelect = (s) => {
    const sem = Number(s)
    setSemester(sem)
    if (sem <= 2) setCurrentYear('1st Year')
    else if (sem <= 4) setCurrentYear('2nd Year')
    else if (sem <= 6) setCurrentYear('3rd Year')
    else setCurrentYear('4th Year')
  }

  const toggleSubject = (sub) => {
    setSubjects((prev) =>
      prev.includes(sub) ? prev.filter((s) => s !== sub) : [...prev, sub]
    )
  }

  const handleFileUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setSyllabusFile(file.name)
    setUploadProgress(0)
    setAnalysing(true)
    setAnalysisError('')

    const interval = setInterval(() => {
      setUploadProgress((p) => {
        if (p >= 90) return 90
        return p + 15
      })
    }, 150)

    try {
      const formData = new FormData()
      formData.append('syllabus_file', file)
      formData.append('level', level)
      formData.append('semester', semester)
      formData.append('domain', collegeBranch || collegeDomain)
      formData.append('stream', collegeStream)

      const res = await api.analyzeSyllabus(formData)
      clearInterval(interval)
      setUploadProgress(100)
      if (res && res.success && res.analysis) {
        if (setSyllabusData) setSyllabusData(res.analysis)
      }
    } catch (err) {
      clearInterval(interval)
      setAnalysisError('Uploaded PDF will be parsed during dashboard load.')
    } finally {
      setAnalysing(false)
    }
  }

  const finish = async () => {
    const profileData = level === 'college' ? {
      level: 'college',
      institution_name: institutionName.trim() || 'University College',
      degree: degree.trim() || 'B.Tech',
      program: degree.trim() || 'B.Tech',
      department: (collegeBranch || collegeDomain).trim(),
      branch: (collegeBranch || collegeDomain).trim(),
      domain: collegeDomain.trim(),
      stream: collegeStream.trim(),
      current_year: currentYear,
      currentYear: currentYear,
      semester: Number(semester) || 1,
      current_semester: Number(semester) || 1,
      currentSemester: Number(semester) || 1,
      regulation: regulation.trim() || null,
      batch: regulation.trim() || null,
      academic_year: academicYear.trim() || null,
      academicYear: academicYear.trim() || null,
      // Clear school fields
      board: null,
      grade_level: null,
      classLevel: null,
    } : {
      level: 'school',
      institution_name: schoolName.trim() || 'Secondary School',
      board: board,
      grade_level: classLevel,
      classLevel: classLevel,
      stream: schoolStream,
      section: schoolSection.trim() || null,
      roll_number: schoolRoll.trim() || null,
      subjects: subjects,
      // Clear college fields
      degree: null,
      program: null,
      semester: null,
      current_semester: null,
      currentSemester: null,
    }

    try {
      if (updateProfile) await updateProfile(profileData)
    } catch (err) {
      console.warn('Profile update notice:', err)
    }
    navigate('/app/dashboard')
  }

  const currentSchoolSubjects = STREAMS[schoolStream] || []

  return (
    <div className="min-h-screen bg-[var(--bg)] flex items-center justify-center p-6">
      <div className="w-full max-w-[560px]">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-8">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="10.5" stroke="var(--accent)" strokeWidth="2" />
            <circle cx="24" cy="9" r="4" fill="var(--accent)" />
          </svg>
          <div className="text-base font-extrabold tracking-tight">
            LearnSphere<small className="font-semibold text-[var(--accent)] text-xs ml-0.5">AI</small>
          </div>
        </div>

        {/* Step 0: Level Selection */}
        {step === 0 && (
          <div>
            <h1 className="text-2xl font-extrabold mb-1.5">Let's configure your academic profile</h1>
            <p className="text-[var(--text-soft)] text-sm mb-8">
              We'll use your verified academic context for authoritative curriculum mapping, question generation, and strict AI evaluation.
            </p>
            <div className="grid grid-cols-2 gap-4">
              {[
                { id: 'school', label: 'School Student', sub: 'Class 1 to 12', icon: BookOpen, desc: 'CBSE, State Board, ICSE & state curricula' },
                { id: 'college', label: 'College Student', sub: 'Semester-Aware (Sem 1–8)', icon: GraduationCap, desc: 'Degree, department, branch & semester mapped' },
              ].map(({ id, label, sub, icon: Icon, desc }) => (
                <button
                  key={id}
                  onClick={() => handleLevelSelect(id)}
                  className="text-left border-[1.5px] border-[var(--border-strong)] rounded-2xl p-5 hover:border-[var(--accent)] hover:bg-[var(--accent-soft)] transition-all group shadow-sm"
                >
                  <Icon size={28} strokeWidth={1.5} className="text-[var(--accent)] mb-3 group-hover:scale-110 transition-transform" />
                  <div className="text-[14.5px] font-bold mb-0.5">{label}</div>
                  <div className="text-xs text-[var(--text-soft)] mb-2 font-medium">{sub}</div>
                  <div className="text-[11.5px] text-[var(--text-faint)] leading-relaxed">{desc}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── SCHOOL ONBOARDING STEPS ───────────────────────────────────────── */}
        {level === 'school' && step > 0 && (
          <div>
            <StepDots steps={STEPS_SCHOOL} current={step} />

            {/* Step 1: School & Board */}
            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <h2 className="text-xl font-extrabold mb-1">Your School & Board</h2>
                  <p className="text-sm text-[var(--text-soft)] mb-5">We'll load the official syllabus for your board.</p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">School Name</label>
                  <input
                    type="text"
                    placeholder="e.g. Delhi Public School, St. Xavier's"
                    value={schoolName}
                    onChange={(e) => setSchoolName(e.target.value)}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm outline-none focus:border-[var(--accent)]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-2">Examination Board</label>
                  <div className="grid grid-cols-2 gap-2.5">
                    {BOARDS.map((b) => (
                      <button
                        key={b}
                        type="button"
                        onClick={() => setBoard(b)}
                        className={`border-[1.5px] rounded-xl px-4 py-3 text-left text-[13px] font-semibold transition-all ${
                          board === b
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)] font-bold shadow-sm'
                            : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        {b}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Class & Stream */}
            {step === 2 && (
              <div className="space-y-4">
                <div>
                  <h2 className="text-xl font-extrabold mb-1">Class & Academic Stream</h2>
                  <p className="text-sm text-[var(--text-soft)] mb-5">Helps load standard grade questions and topics.</p>
                </div>

                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2">Class (1 to 12)</div>
                  <div className="grid grid-cols-6 gap-2">
                    {CLASSES.map((c) => (
                      <button
                        key={c}
                        type="button"
                        onClick={() => setClassLevel(c)}
                        className={`border-[1.5px] rounded-xl py-2.5 text-[13px] font-bold transition-all ${
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
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2">Stream</div>
                  <div className="flex gap-2.5">
                    {Object.keys(STREAMS).map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => { setSchoolStream(s); setSubjects(STREAMS[s] || []) }}
                        className={`flex-1 border-[1.5px] rounded-xl py-3 text-[13px] font-bold transition-all ${
                          schoolStream === s
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)]'
                            : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Section (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. A"
                      value={schoolSection}
                      onChange={(e) => setSchoolSection(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Roll No. (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. 101"
                      value={schoolRoll}
                      onChange={(e) => setSchoolRoll(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs"
                    />
                  </div>
                </div>
              </div>
            )}

            {/* Step 3: Subjects */}
            {step === 3 && (
              <div>
                <h2 className="text-xl font-extrabold mb-1">Select your subjects</h2>
                <p className="text-sm text-[var(--text-soft)] mb-5">Customize your active study subjects.</p>
                <div className="grid grid-cols-2 gap-2.5 mb-4">
                  {currentSchoolSubjects.map((sub) => {
                    const selected = subjects.includes(sub)
                    return (
                      <button
                        key={sub}
                        type="button"
                        onClick={() => toggleSubject(sub)}
                        className={`flex items-center gap-2.5 border-[1.5px] rounded-xl px-3.5 py-3 text-left transition-all ${
                          selected
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm'
                            : 'border-[var(--border-strong)] opacity-60 hover:opacity-100 hover:border-[var(--accent-dim)]'
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
              </div>
            )}

            {/* Step 4: Done */}
            {step === 4 && (
              <div className="text-center py-4">
                <div className="text-5xl mb-4">🎉</div>
                <h2 className="text-xl font-extrabold mb-2">School Profile Ready!</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6 max-w-[380px] mx-auto">
                  Your {board} Class {classLevel} ({schoolStream}) profile is saved to your account.
                </p>
                <div className="bg-[var(--accent-soft)] rounded-xl p-4 text-left mb-6 text-xs space-y-1.5 border border-[var(--border)]">
                  <div className="font-bold text-[var(--accent)] uppercase tracking-wider text-[11px] mb-2">Profile Summary</div>
                  <div>🏫 School: <strong>{schoolName || 'Standard School'}</strong></div>
                  <div>📋 Board & Class: <strong>{board} · Class {classLevel}</strong></div>
                  <div>📚 Stream: <strong>{schoolStream}</strong></div>
                  <div>📖 Subjects: <strong>{subjects.join(' · ') || 'General'}</strong></div>
                </div>
                <button
                  onClick={finish}
                  className="w-full py-3.5 bg-[var(--accent)] text-white font-bold rounded-xl hover:bg-[var(--accent-dim)] transition-colors shadow-md text-sm"
                >
                  Start Learning →
                </button>
              </div>
            )}
          </div>
        )}

        {/* ── COLLEGE ONBOARDING STEPS ──────────────────────────────────────── */}
        {level === 'college' && step > 0 && (
          <div>
            <StepDots steps={STEPS_COLLEGE} current={step} />

            {/* Step 1: Program & Branch */}
            {step === 1 && (
              <div className="space-y-4">
                <div>
                  <h2 className="text-xl font-extrabold mb-1">College, Degree & Department</h2>
                  <p className="text-sm text-[var(--text-soft)] mb-5">
                    Your institutional context ensures semester-aligned subject mapping.
                  </p>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Institution / College / University Name</label>
                  <input
                    type="text"
                    placeholder="e.g. IIT Madras, BITS Pilani, Stanford University"
                    value={institutionName}
                    onChange={(e) => setInstitutionName(e.target.value)}
                    required
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm outline-none focus:border-[var(--accent)]"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Degree / Program</label>
                    <select
                      value={degree}
                      onChange={(e) => setDegree(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold outline-none focus:border-[var(--accent)]"
                    >
                      <option value="B.Tech">B.Tech / B.E.</option>
                      <option value="B.Sc">B.Sc</option>
                      <option value="BCA">BCA</option>
                      <option value="B.Com">B.Com</option>
                      <option value="BBA">BBA</option>
                      <option value="M.Tech">M.Tech / M.E.</option>
                      <option value="MCA">MCA</option>
                      <option value="MBA">MBA</option>
                      <option value="MBBS">MBBS / Medical</option>
                      <option value="Other">Other Program</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Discipline Stream</label>
                    <select
                      value={collegeStream}
                      onChange={(e) => handleCollegeStreamChange(e.target.value)}
                      className="w-full px-3 py-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold outline-none focus:border-[var(--accent)]"
                    >
                      {COLLEGE_STREAMS.map(cs => <option key={cs} value={cs}>{cs}</option>)}
                    </select>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Department / Branch Specialization</label>
                  <select
                    value={collegeBranch}
                    onChange={(e) => { setCollegeBranch(e.target.value); setCollegeDomain(e.target.value); }}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold outline-none focus:border-[var(--accent)]"
                  >
                    {(COLLEGE_DOMAINS[collegeStream] || []).map(cd => <option key={cd} value={cd}>{cd}</option>)}
                  </select>
                </div>
              </div>
            )}

            {/* Step 2: Year & Semester */}
            {step === 2 && (
              <div className="space-y-5">
                <div>
                  <h2 className="text-xl font-extrabold mb-1">Academic Year & Current Semester</h2>
                  <p className="text-sm text-[var(--text-soft)] mb-5">
                    The backend uses your stored semester as the authoritative curriculum context.
                  </p>
                </div>

                <div>
                  <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2.5">
                    Select Current Semester
                  </div>
                  <div className="grid grid-cols-4 gap-2.5">
                    {COLLEGE_SEMESTERS.map((s) => (
                      <button
                        key={s}
                        type="button"
                        onClick={() => handleSemesterSelect(s)}
                        className={`border-[1.5px] rounded-xl py-3 text-[14px] font-bold transition-all ${
                          semester === s
                            ? 'border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)] shadow-sm'
                            : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                        }`}
                      >
                        Sem {s}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Current Academic Year</label>
                    <select
                      value={currentYear}
                      onChange={(e) => setCurrentYear(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold outline-none"
                    >
                      <option value="1st Year">1st Year</option>
                      <option value="2nd Year">2nd Year</option>
                      <option value="3rd Year">3rd Year</option>
                      <option value="4th Year">4th Year</option>
                      <option value="5th Year">5th Year</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Academic Batch / Year (Optional)</label>
                    <input
                      type="text"
                      placeholder="e.g. 2024-2025"
                      value={academicYear}
                      onChange={(e) => setAcademicYear(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Academic Regulation / Batch (Optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. R20, R23, or 2022-2026"
                    value={regulation}
                    onChange={(e) => setRegulation(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs outline-none"
                  />
                </div>
              </div>
            )}

            {/* Step 3: Syllabus Upload */}
            {step === 3 && (
              <div className="space-y-4">
                <div>
                  <h2 className="text-xl font-extrabold mb-1">Syllabus Blueprint & Document</h2>
                  <p className="text-sm text-[var(--text-soft)] mb-4">
                    Semester {semester} subjects will be automatically loaded. You can optionally upload your university syllabus PDF for custom blueprint extraction.
                  </p>
                </div>

                <div className="border-[1.5px] border-dashed border-[var(--border-strong)] rounded-2xl p-6 text-center bg-[var(--surface-alt)]">
                  <Upload size={28} className="mx-auto mb-2 text-[var(--accent)]" />
                  <div className="text-sm font-bold mb-1">Upload University Syllabus PDF</div>
                  <div className="text-xs text-[var(--text-faint)] mb-4">Optional — Gemini AI extracts exact unit learning outcomes</div>
                  <label className="cursor-pointer inline-flex items-center gap-2 px-4 py-2 bg-[var(--surface)] border border-[var(--border-strong)] rounded-xl text-xs font-bold text-[var(--text)] hover:border-[var(--accent)] transition-colors shadow-sm">
                    <Upload size={13} /> Choose PDF Document
                    <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
                  </label>
                  {syllabusFile && (
                    <div className="mt-4 p-3 bg-[var(--surface)] rounded-xl border border-[var(--border)] text-left">
                      <div className="flex items-center justify-between text-xs mb-1.5">
                        <span className="text-[var(--accent)] font-bold truncate max-w-[300px]">{syllabusFile}</span>
                        {analysing ? <span className="text-[var(--text-faint)]">Analysing with AI…</span> : <span className="text-emerald-600 font-bold">✓ Analysed</span>}
                      </div>
                      <div className="h-1.5 bg-[var(--surface-alt)] rounded-full overflow-hidden">
                        <div className="h-full bg-[var(--accent)] rounded-full transition-all duration-300" style={{ width: `${uploadProgress}%` }} />
                      </div>
                    </div>
                  )}
                  {analysisError && (
                    <div className="text-xs text-[var(--text-soft)] mt-2">{analysisError}</div>
                  )}
                </div>
              </div>
            )}

            {/* Step 4: Done */}
            {step === 4 && (
              <div className="text-center py-4">
                <div className="text-5xl mb-4">🎓</div>
                <h2 className="text-xl font-extrabold mb-2">College Profile Configured!</h2>
                <p className="text-sm text-[var(--text-soft)] mb-6 max-w-[400px] mx-auto">
                  Your <strong>Semester {semester}</strong> academic context is stored against your MongoDB account. All curriculum tools now reflect your semester.
                </p>
                <div className="bg-[var(--accent-soft)] rounded-xl p-4 text-left mb-6 text-xs space-y-2 border border-[var(--border)]">
                  <div className="font-bold text-[var(--accent)] uppercase tracking-wider text-[11px]">Authoritative College Profile</div>
                  <div>🏛️ <strong>{institutionName || 'University College'}</strong></div>
                  <div>📜 Program: <strong>{degree} · {collegeBranch || collegeDomain}</strong></div>
                  <div>📅 Stage: <strong>Semester {semester} ({currentYear})</strong></div>
                  {regulation && <div>🔖 Regulation/Batch: <strong>{regulation}</strong></div>}
                  {academicYear && <div>🗓️ Academic Year: <strong>{academicYear}</strong></div>}
                  {syllabusFile && <div>📄 Custom Syllabus: <strong>{syllabusFile}</strong></div>}
                </div>
                <button
                  onClick={finish}
                  className="w-full py-3.5 bg-[var(--accent)] text-white font-bold rounded-xl hover:bg-[var(--accent-dim)] transition-colors shadow-md text-sm"
                >
                  Start Learning →
                </button>
              </div>
            )}
          </div>
        )}

        {/* Navigation buttons */}
        {step > 0 && step < steps.length - 1 && (
          <div className="flex items-center justify-between mt-8 pt-4 border-t border-[var(--border)]">
            <button
              onClick={() => setStep((s) => s - 1)}
              className="flex items-center gap-1.5 px-4 py-2 border border-[var(--border-strong)] rounded-xl text-xs font-semibold text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors"
            >
              <ChevronLeft size={14} /> Back
            </button>
            <button
              onClick={() => setStep((s) => s + 1)}
              disabled={level === 'school' && step === 3 && subjects.length === 0}
              className="flex items-center gap-1.5 px-5 py-2.5 bg-[var(--accent)] text-white rounded-xl text-xs font-bold hover:bg-[var(--accent-dim)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors shadow-sm"
            >
              Continue <ChevronRight size={14} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
