import { useState, useEffect } from 'react'
import { Card, PageHead, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { BOARDS, CLASSES, STREAMS, COLLEGE_SEMESTERS, COLLEGE_STREAMS, COLLEGE_DOMAINS } from '../data/syllabusData.js'
import { api } from '../services/api.js'
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Sparkles, GraduationCap, BookOpen, Building } from 'lucide-react'

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
        }
      ) : {
        name,
        institution_name: institutionName,
      }

      await updateProfile(payload)
      setSavedMsg('Profile and semester configuration successfully persisted to MongoDB Atlas!')
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
      formData.append('degree', collegeDegree)
      formData.append('department', collegeBranch)
      formData.append('domain', collegeBranch)
      formData.append('stream', isCollege ? collegeStream : schoolStream)
      formData.append('regulation', collegeRegulation)
      formData.append('academic_year', collegeAcademicYear)

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
        title="Account & Academic Settings"
        subtitle="Manage your authoritative institutional profile, semester mapping, and syllabus documents."
      />

      <div className="grid md:grid-cols-[1.3fr_1fr] gap-6 max-w-[1020px]">
        {/* Left Card: Academic Profile Details */}
        <Card className="p-6">
          <div className="flex items-center justify-between mb-4 pb-3 border-b border-[var(--border)]">
            <h3 className="font-extrabold text-base text-[var(--text)]">Academic Profile & Credentials</h3>
            <Badge tone="accent">
              {user?.role === 'teacher' ? 'Teacher Account' : isCollege ? `College (Sem ${semester})` : `School (Class ${classLevel})`}
            </Badge>
          </div>

          {savedMsg && (
            <div className="mb-4 p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-semibold rounded-xl flex items-center gap-2">
              <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
              <span>{savedMsg}</span>
            </div>
          )}

          {errorMsg && (
            <div className="mb-4 p-3 bg-red-50 border border-red-300 text-red-800 text-xs font-semibold rounded-xl flex items-center gap-2">
              <AlertCircle size={16} className="text-red-600 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}

          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Full Name</label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3.5 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Email Address</label>
                <input
                  type="email"
                  value={email}
                  disabled
                  className="w-full px-3.5 py-2 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-alt)] text-sm text-[var(--text-soft)] cursor-not-allowed"
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
    </>
  )
}
