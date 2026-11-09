import { useState, useEffect } from 'react'
import { Card, PageHead, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { BOARDS, CLASSES, STREAMS, COLLEGE_SEMESTERS, COLLEGE_STREAMS, COLLEGE_DOMAINS } from '../data/syllabusData.js'
import { api } from '../services/api.js'
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Sparkles, GraduationCap, BookOpen, Building, Headphones, Volume2, Mic, Sliders, ShieldCheck, Keyboard } from 'lucide-react'

export default function Settings() {
  const { user, studentProfile, updateProfile, setSyllabusData } = useApp()

  const isStudent = user?.role === 'student'
  const isCollege = user?.level === 'college'
  const isSchool = user?.level === 'school'

  // Profile Form States
  const [name, setName] = useState(user?.name || '')
  const [email, setEmail] = useState(user?.email || '')
  const [level, setLevel] = useState(user?.level || 'college')

  // College States
  const [institutionName, setInstitutionName] = useState(user?.institution_name || user?.institution || user?.college || '')
  const [degree, setDegree] = useState(user?.degree || user?.program || 'B.Tech')
  const [collegeStream, setCollegeStream] = useState(user?.stream || 'Engineering & Technology')
  const [collegeBranch, setCollegeBranch] = useState(user?.branch || user?.department || 'Computer Science & AI')
  const [currentYear, setCurrentYear] = useState(user?.current_year || user?.currentYear || user?.year || '3rd Year')
  const [semester, setSemester] = useState(Number(user?.semester || user?.current_semester || user?.currentSemester || 5))
  const [regulation, setRegulation] = useState(user?.regulation || user?.batch || '')
  const [academicYear, setAcademicYear] = useState(user?.academic_year || user?.academicYear || '2024-2025')

  // School States
  const [schoolName, setSchoolName] = useState(user?.institution_name || user?.school || '')
  const [board, setBoard] = useState(user?.board || 'CBSE')
  const [classLevel, setClassLevel] = useState(user?.grade_level || user?.classLevel || 12)
  const [schoolStream, setSchoolStream] = useState(user?.stream || 'Science')
  const [section, setSection] = useState(user?.section || '')
  const [rollNumber, setRollNumber] = useState(user?.roll_number || '')

  // Syllabus state
  const [syllabusFile, setSyllabusFile] = useState(null)
  const [uploadingSyllabus, setUploadingSyllabus] = useState(false)
  const [syllabusSuccess, setSyllabusSuccess] = useState('')
  const [syllabusError, setSyllabusError] = useState('')

  // Save State
  const [saving, setSaving] = useState(false)
  const [savedMsg, setSavedMsg] = useState('')
  const [errorMsg, setErrorMsg] = useState('')

  // Blind Learning Companion States
  const [isDisabledStudent, setIsDisabledStudent] = useState(Boolean(user?.is_disabled_student))
  const [blindCompanionEnabled, setBlindCompanionEnabled] = useState(Boolean(user?.blind_companion_enabled || user?.is_disabled_student))
  const [blindSettings, setBlindSettings] = useState({
    audio_first: true,
    text_to_speech: true,
    voice_questions: true,
    voice_navigation: true,
    audio_speed: 1.0,
    explanation_mode: 'detailed',
    spoken_diagrams: true,
    keyboard_nav: true,
    ...(user?.blind_companion_settings || {})
  })

  useEffect(() => {
    if (user) {
      setName(user.name || '')
      setEmail(user.email || '')
      setLevel(user.level || 'college')
      setInstitutionName(user.institution_name || user.institution || user.college || user.school || '')
      setDegree(user.degree || user.program || 'B.Tech')
      setCollegeBranch(user.branch || user.department || 'Computer Science & AI')
      setCurrentYear(user.current_year || user.currentYear || user.year || '3rd Year')
      setSemester(Number(user.semester || user.current_semester || user.currentSemester || 5))
      setRegulation(user.regulation || user.batch || '')
      setAcademicYear(user.academic_year || user.academicYear || '2024-2025')

      setSchoolName(user.institution_name || user.school || '')
      setBoard(user.board || 'CBSE')
      setClassLevel(user.grade_level || user.classLevel || 12)
      setSchoolStream(user.stream || 'Science')
      setSection(user.section || '')
      setRollNumber(user.roll_number || '')

      setIsDisabledStudent(Boolean(user.is_disabled_student))
      setBlindCompanionEnabled(Boolean(user.blind_companion_enabled || user.is_disabled_student))
      if (user.blind_companion_settings && typeof user.blind_companion_settings === 'object') {
        setBlindSettings(prev => ({ ...prev, ...user.blind_companion_settings }))
      }
    }
  }, [user])

  const handleCollegeStreamChange = (val) => {
    setCollegeStream(val)
    const availableDomains = COLLEGE_DOMAINS[val] || []
    if (availableDomains.length > 0) {
      setCollegeBranch(availableDomains[0])
    }
  }

  const handleSemesterChange = (s) => {
    const sem = Number(s)
    setSemester(sem)
    if (sem <= 2) setCurrentYear('1st Year')
    else if (sem <= 4) setCurrentYear('2nd Year')
    else if (sem <= 6) setCurrentYear('3rd Year')
    else setCurrentYear('4th Year')
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setSaving(true)
    setErrorMsg('')
    setSavedMsg('')

    try {
      const payload = isStudent ? (
        level === 'college' ? {
          name,
          level: 'college',
          institution_name: institutionName,
          degree,
          program: degree,
          department: collegeBranch,
          branch: collegeBranch,
          stream: collegeStream,
          domain: collegeBranch,
          current_year: currentYear,
          currentYear: currentYear,
          semester: Number(semester) || 1,
          current_semester: Number(semester) || 1,
          currentSemester: Number(semester) || 1,
          regulation: regulation.trim() || null,
          batch: regulation.trim() || null,
          academic_year: academicYear.trim() || null,
          academicYear: academicYear.trim() || null,
          // clear school fields
          board: null,
          grade_level: null,
          is_disabled_student: Boolean(isDisabledStudent),
          disability_type: isDisabledStudent ? 'blind_or_low_vision' : null,
          blind_companion_enabled: Boolean(blindCompanionEnabled),
          blind_companion_settings: blindSettings,
        } : {
          name,
          level: 'school',
          institution_name: schoolName,
          board,
          grade_level: classLevel,
          classLevel,
          stream: schoolStream,
          section: section.trim() || null,
          roll_number: rollNumber.trim() || null,
          // clear college fields
          semester: null,
          current_semester: null,
          currentSemester: null,
          degree: null,
          program: null,
          is_disabled_student: Boolean(isDisabledStudent),
          disability_type: isDisabledStudent ? 'blind_or_low_vision' : null,
          blind_companion_enabled: Boolean(blindCompanionEnabled),
          blind_companion_settings: blindSettings,
        }
      ) : {
        name,
        institution_name: institutionName,
      }

      await updateProfile(payload)
      setSavedMsg('Profile and academic configuration successfully saved.')
      setTimeout(() => setSavedMsg(''), 4000)
    } catch (err) {
      setErrorMsg(err?.message || 'Failed to save profile.')
    } finally {
      setSaving(false)
    }
  }

  const handleUploadSyllabus = async () => {
    if (!syllabusFile) return
    setUploadingSyllabus(true)
    setSyllabusError('')
    setSyllabusSuccess('')

    try {
      const formData = new FormData()
      formData.append('syllabus_file', syllabusFile)
      formData.append('level', level)
      formData.append('semester', semester)
      formData.append('classLevel', classLevel)
      formData.append('degree', degree)
      formData.append('department', collegeBranch)
      formData.append('domain', collegeBranch)
      formData.append('stream', isCollege ? collegeStream : schoolStream)
      formData.append('regulation', regulation)
      formData.append('academic_year', academicYear)

      const res = await api.analyzeSyllabus(formData)
      if (res && res.success && res.analysis) {
        const vStatus = (res.validation_status || res.validationStatus || 'VALID').toUpperCase()
        if (vStatus === 'MISMATCH') {
          setSyllabusError(res.mismatch_reason || `The uploaded syllabus does not match your current Semester ${semester} profile.`)
        } else if (vStatus === 'NEEDS_REVIEW') {
          setSyllabusError(res.mismatch_reason || 'Syllabus semester information is ambiguous (Status: NEEDS_REVIEW). Please verify and confirm.')
        } else {
          if (setSyllabusData) setSyllabusData(res.analysis)
          setSyllabusSuccess(`Syllabus validated and mapped to Semester ${semester} successfully!`)
          setSyllabusFile(null)
        }
      } else {
        setSyllabusError(res?.error || 'Syllabus upload failed.')
      }
    } catch (err) {
      setSyllabusError(err?.message || 'Failed to upload syllabus.')
    } finally {
      setUploadingSyllabus(false)
    }
  }

  return (
    <>
      <PageHead
        title="Settings & Profile"
        subtitle="Manage your institutional affiliation, academic level, and curriculum preferences."
      />

      <div className="grid md:grid-cols-[1.3fr_1fr] gap-6">
        {/* Left Card: Academic Profile Details */}
        <Card className="p-7">
          <div className="flex items-center justify-between mb-5 pb-3.5 border-b border-[var(--border)]">
            <h3 className="font-extrabold text-lg text-[var(--text)]">Academic Profile & Credentials</h3>
            <Badge tone="accent">
              {user?.role === 'teacher' ? 'Teacher Account' : isCollege ? `College (Sem ${semester})` : `School (Class ${classLevel})`}
            </Badge>
          </div>

          {savedMsg && (
            <div className="mb-4 p-3.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 text-xs font-semibold rounded-xl flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
              <span>{savedMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="mb-4 p-3.5 bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-semibold rounded-xl flex items-center gap-2">
              <AlertCircle size={16} className="text-red-500 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-2 gap-3.5">
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1.5">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm text-[var(--text)] focus:bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)]"
                />
              </div>

              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1.5">Email Address</label>
                <input
                  type="email"
                  value={email}
                  disabled
                  className="w-full px-3.5 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm text-[var(--text-faint)] cursor-not-allowed opacity-80"
                />
              </div>
            </div>

            {isStudent && (
              <>
                <div>
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Academic Level</label>
                  <select
                    value={level}
                    onChange={(e) => setLevel(e.target.value)}
                    className="w-full px-3.5 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                  >
                    <option value="school">School Student (Class 1 to 12)</option>
                    <option value="college">College / University Student (Semester-aware)</option>
                  </select>
                </div>

                {level === 'college' ? (
                  /* College Settings */
                  <div className="p-4 bg-[var(--accent-soft)] rounded-xl border border-[var(--border)] space-y-3.5">
                    <div className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
                      Authoritative College & Semester Context
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">
                        College / University Name
                      </label>
                      <input
                        type="text"
                        value={institutionName}
                        onChange={(e) => setInstitutionName(e.target.value)}
                        placeholder="e.g. IIT Madras, BITS Pilani"
                        required
                        className="w-full px-3.5 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Degree / Program</label>
                        <select
                          value={degree}
                          onChange={(e) => setDegree(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
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
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Discipline Stream</label>
                        <select
                          value={collegeStream}
                          onChange={(e) => handleCollegeStreamChange(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                        >
                          {COLLEGE_STREAMS.map(cs => <option key={cs} value={cs}>{cs}</option>)}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Department / Branch</label>
                      <select
                        value={collegeBranch}
                        onChange={(e) => setCollegeBranch(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                      >
                        {(COLLEGE_DOMAINS[collegeStream] || []).map(cd => <option key={cd} value={cd}>{cd}</option>)}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Current Year</label>
                        <select
                          value={currentYear}
                          onChange={(e) => setCurrentYear(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                        >
                          <option value="1st Year">1st Year</option>
                          <option value="2nd Year">2nd Year</option>
                          <option value="3rd Year">3rd Year</option>
                          <option value="4th Year">4th Year</option>
                          <option value="5th Year">5th Year</option>
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">
                          Current Semester <span className="text-[var(--accent)] font-bold">*</span>
                        </label>
                        <select
                          value={semester}
                          onChange={(e) => handleSemesterChange(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--accent)] bg-[var(--surface)] text-xs font-bold text-[var(--accent)]"
                        >
                          {COLLEGE_SEMESTERS.map(s => <option key={s} value={s}>Semester {s}</option>)}
                        </select>
                      </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Regulation / Batch (Optional)</label>
                        <input
                          type="text"
                          placeholder="e.g. R20 or 2022-2026"
                          value={regulation}
                          onChange={(e) => setRegulation(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Academic Year (Optional)</label>
                        <input
                          type="text"
                          placeholder="e.g. 2024-2025"
                          value={academicYear}
                          onChange={(e) => setAcademicYear(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs"
                        />
                      </div>
                    </div>
                  </div>
                ) : (
                  /* School Settings */
                  <div className="p-4 bg-[var(--accent-soft)] rounded-xl border border-[var(--border)] space-y-3.5">
                    <div className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
                      School Profile & Grade
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">School Name</label>
                      <input
                        type="text"
                        value={schoolName}
                        onChange={(e) => setSchoolName(e.target.value)}
                        placeholder="e.g. Delhi Public School"
                        className="w-full px-3.5 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                      />
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Board</label>
                        <select
                          value={board}
                          onChange={(e) => setBoard(e.target.value)}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                        >
                          {BOARDS.map(b => <option key={b} value={b}>{b}</option>)}
                        </select>
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Class (1 to 12)</label>
                        <select
                          value={classLevel}
                          onChange={(e) => setClassLevel(Number(e.target.value))}
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                        >
                          {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
                        </select>
                      </div>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Stream</label>
                      <select
                        value={schoolStream}
                        onChange={(e) => setSchoolStream(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs font-semibold"
                      >
                        {Object.keys(STREAMS).map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Section</label>
                        <input
                          type="text"
                          value={section}
                          onChange={(e) => setSection(e.target.value)}
                          placeholder="e.g. A"
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs"
                        />
                      </div>

                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Roll Number</label>
                        <input
                          type="text"
                          value={rollNumber}
                          onChange={(e) => setRollNumber(e.target.value)}
                          placeholder="e.g. 104"
                          className="w-full px-3 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}

            <Button type="submit" disabled={saving} className="w-full mt-2">
              {saving ? 'Persisting to MongoDB...' : 'Save Academic Profile'}
            </Button>
          </form>
        </Card>

        {/* Right Card: Syllabus Management */}
        <Card className="p-6 space-y-4">
          <div className="border-b border-[var(--border)] pb-3">
            <h3 className="font-extrabold text-base text-[var(--text)] mb-1">Course Syllabus Document</h3>
            <p className="text-xs text-[var(--text-soft)]">
              Upload your official syllabus PDF to auto-extract chapters, units, and learning outcomes for your exact semester.
            </p>
          </div>

          {syllabusSuccess && (
            <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-semibold rounded-xl flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
              <span>{syllabusSuccess}</span>
            </div>
          )}

          {syllabusError && (
            <div className="p-3 bg-red-50 border border-red-300 text-red-800 text-xs font-semibold rounded-xl flex items-center gap-2">
              <AlertCircle size={16} className="text-red-600 shrink-0" />
              <span>{syllabusError}</span>
            </div>
          )}

          <div className="border-2 border-dashed border-[var(--border-strong)] rounded-xl p-6 text-center bg-[var(--surface-alt)] hover:border-[var(--accent)] transition-colors relative">
            <input 
              type="file" 
              accept=".pdf,.png,.jpg,.jpeg" 
              className="absolute inset-0 opacity-0 cursor-pointer"
              onChange={(e) => e.target.files[0] && setSyllabusFile(e.target.files[0])}
            />
            <div className="w-12 h-12 mx-auto mb-2.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
              <UploadCloud size={24} />
            </div>
            <div className="font-semibold text-xs text-[var(--text)] mb-0.5">
              {syllabusFile ? syllabusFile.name : 'Click to select PDF or image syllabus'}
            </div>
            <div className="text-[11px] text-[var(--text-faint)]">Supports PDF, PNG, JPG (Max 50MB)</div>
          </div>

          {syllabusFile && (
            <div className="p-3 bg-[var(--accent-soft)] rounded-lg flex items-center justify-between text-xs">
              <div className="flex items-center gap-2 font-semibold text-[var(--accent)] truncate max-w-[200px]">
                <FileText size={15} />
                <span>{syllabusFile.name}</span>
              </div>
              <button
                type="button"
                onClick={() => setSyllabusFile(null)}
                className="text-xs text-red-600 font-semibold hover:underline"
              >
                Remove
              </button>
            </div>
          )}

          <Button
            variant="secondary"
            disabled={!syllabusFile || uploadingSyllabus}
            onClick={handleUploadSyllabus}
            className="w-full flex items-center justify-center gap-2"
          >
            <Sparkles size={14} />
            {uploadingSyllabus ? 'Analyzing Syllabus via Gemini...' : 'Analyze & Save Syllabus'}
          </Button>
        </Card>
      </div>

      {/* Dedicated Blind Learning Companion Settings Section for Students */}
      {isStudent && (
        <Card className="mt-6 p-6 border-2 border-indigo-200 dark:border-indigo-900/60 bg-gradient-to-br from-indigo-50/40 via-white to-sky-50/30 dark:from-slate-900 dark:via-slate-900 dark:to-indigo-950/20 shadow-xs">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[var(--border)] pb-4 mb-5">
            <div className="flex items-center gap-3">
              <div className="w-11 h-11 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
                <Headphones size={22} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-slate-900 dark:text-white">
                    Blind Learning Companion Settings
                  </h3>
                  <Badge variant={blindCompanionEnabled ? 'default' : 'secondary'} className={blindCompanionEnabled ? 'bg-indigo-600 text-white' : ''}>
                    {blindCompanionEnabled ? 'Active' : 'Off by Default'}
                  </Badge>
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                  Exclusively designed for blind and low-vision learners. Master toggle remains OFF by default.
                </p>
              </div>
            </div>

            {/* Master Toggle */}
            <div className="flex items-center gap-3 self-start sm:self-center bg-white dark:bg-slate-800 px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700">
              <label htmlFor="master-blind-toggle" className="text-xs font-bold text-slate-800 dark:text-slate-200 cursor-pointer">
                Enable Companion
              </label>
              <input
                id="master-blind-toggle"
                type="checkbox"
                checked={blindCompanionEnabled}
                onChange={(e) => {
                  const val = e.target.checked
                  setBlindCompanionEnabled(val)
                  if (val && !isDisabledStudent) setIsDisabledStudent(true)
                }}
                className="w-5 h-5 accent-indigo-600 cursor-pointer"
                aria-label="Master Enable Blind Learning Companion Toggle"
              />
            </div>
          </div>

          {/* Student Disability Confirmation */}
          <div className="mb-5 p-3.5 bg-white dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/80">
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                type="checkbox"
                checked={isDisabledStudent}
                onChange={(e) => {
                  const checked = e.target.checked
                  setIsDisabledStudent(checked)
                  if (checked && !blindCompanionEnabled) setBlindCompanionEnabled(true)
                }}
                className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
              />
              <div>
                <span className="text-xs font-bold text-slate-800 dark:text-slate-200 block">
                  I am a blind or low-vision student
                </span>
                <span className="text-[11px] text-slate-500 dark:text-slate-400 block mt-0.5">
                  Your preferences are stored securely against your authenticated student account. Non-disabled student accounts do not display this interface.
                </span>
              </div>
            </label>
          </div>

          {/* Detailed Preferences Grid */}
          <div className={`space-y-5 transition-opacity ${blindCompanionEnabled ? 'opacity-100' : 'opacity-60 pointer-events-none'}`}>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3.5">
              {/* Audio-First Learning */}
              <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/90 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Volume2 size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Audio-First Learning</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Prioritizes spoken explanations and audio summaries across your syllabus.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={blindSettings.audio_first}
                  onChange={(e) => setBlindSettings(prev => ({ ...prev, audio_first: e.target.checked }))}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
                  aria-label="Toggle Audio-First Learning"
                />
              </div>

              {/* Text-to-Speech (TTS) */}
              <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/90 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Sparkles size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Text-to-Speech</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Browser speech synthesis reads all curriculum concepts and notes aloud.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={blindSettings.text_to_speech}
                  onChange={(e) => setBlindSettings(prev => ({ ...prev, text_to_speech: e.target.checked }))}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
                  aria-label="Toggle Text-to-Speech"
                />
              </div>

              {/* Voice Questions */}
              <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/90 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Mic size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Voice Questions</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Practice questions and checkpoints are announced verbally with audio replay.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={blindSettings.voice_questions}
                  onChange={(e) => setBlindSettings(prev => ({ ...prev, voice_questions: e.target.checked }))}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
                  aria-label="Toggle Voice Questions"
                />
              </div>

              {/* Voice Navigation */}
              <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/90 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Sliders size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Voice Navigation</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Spoken notifications and announcements when switching units or topics.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={blindSettings.voice_navigation}
                  onChange={(e) => setBlindSettings(prev => ({ ...prev, voice_navigation: e.target.checked }))}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
                  aria-label="Toggle Voice Navigation"
                />
              </div>

              {/* Spoken Diagram Descriptions */}
              <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/90 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <FileText size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Spoken Diagrams</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Provides detailed verbal descriptions for visual charts, schemas, and figures.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={blindSettings.spoken_diagrams}
                  onChange={(e) => setBlindSettings(prev => ({ ...prev, spoken_diagrams: e.target.checked }))}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
                  aria-label="Toggle Spoken Diagram Descriptions"
                />
              </div>

              {/* Keyboard Navigation */}
              <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/90 flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Keyboard size={16} className="text-indigo-600 shrink-0" />
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200">Keyboard Shortcuts</span>
                  </div>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
                    Hotkeys: <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">P</kbd> Play/Pause, <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">N</kbd> Next, <kbd className="px-1 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-[10px]">R</kbd> Repeat.
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={blindSettings.keyboard_nav}
                  onChange={(e) => setBlindSettings(prev => ({ ...prev, keyboard_nav: e.target.checked }))}
                  className="mt-0.5 w-4 h-4 accent-indigo-600 cursor-pointer"
                  aria-label="Toggle Keyboard Navigation"
                />
              </div>
            </div>

            {/* Audio Speed & Explanation Mode Controls */}
            <div className="grid sm:grid-cols-2 gap-4 pt-2">
              <div className="p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                <label className="block text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">
                  Adjustable Audio Speed ({blindSettings.audio_speed || 1.0}x)
                </label>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-3">
                  Adjust audio synthesis pacing according to your listening preference.
                </p>
                <div className="grid grid-cols-5 gap-1.5">
                  {[0.75, 1.0, 1.25, 1.5, 2.0].map((rate) => (
                    <button
                      key={rate}
                      type="button"
                      onClick={() => setBlindSettings(prev => ({ ...prev, audio_speed: rate }))}
                      className={`py-2 px-1 text-xs font-bold rounded-lg border transition-all ${
                        (blindSettings.audio_speed || 1.0) === rate
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                          : 'bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-indigo-400'
                      }`}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              </div>

              <div className="p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700">
                <label className="block text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">
                  Explanation Depth Mode
                </label>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mb-3">
                  Choose between quick high-yield essence or detailed syllabus explanations.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => setBlindSettings(prev => ({ ...prev, explanation_mode: 'simple' }))}
                    className={`py-2.5 px-3 rounded-lg border text-left text-xs transition-all ${
                      blindSettings.explanation_mode === 'simple'
                        ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 font-bold text-indigo-700 dark:text-indigo-300'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="font-bold">Simple Mode</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Concise, everyday words</div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setBlindSettings(prev => ({ ...prev, explanation_mode: 'detailed' }))}
                    className={`py-2.5 px-3 rounded-lg border text-left text-xs transition-all ${
                      blindSettings.explanation_mode === 'detailed'
                        ? 'border-indigo-600 bg-indigo-50/50 dark:bg-indigo-950/40 font-bold text-indigo-700 dark:text-indigo-300'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div className="font-bold">Detailed Mode</div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5">Comprehensive depth</div>
                  </button>
                </div>
              </div>
            </div>

            {/* Quick Save Preferences Action */}
            <div className="pt-2 flex justify-end">
              <Button
                type="button"
                disabled={saving}
                onClick={handleSaveProfile}
                className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs px-5 py-2.5 rounded-xl shadow-xs"
              >
                {saving ? 'Saving...' : 'Save Accessibility Preferences'}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </>
  )
}
