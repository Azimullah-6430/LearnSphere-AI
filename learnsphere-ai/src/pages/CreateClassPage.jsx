import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { Card, Badge, Button } from '../components/ui/Primitives.jsx'
import { Building, School, GraduationCap, Plus, ArrowRight, CheckCircle2, Users, Upload, Sparkles, Trash2, LogOut } from 'lucide-react'

export default function CreateClassPage() {
  const {
    user,
    teacherClasses,
    addClass,
    deleteClass,
    activeClassId,
    setActiveClassId,
    uploadStudentRoster,
    logout,
    institutionMode
  } = useApp()

  const navigate = useNavigate()

  // Mode derived strictly from teacher's logged-in account
  const activeMode = user?.teacherLevel || user?.level || institutionMode || 'school'
  const isSchool = activeMode === 'school'

  // School Form Fields
  const [schoolClassName, setSchoolClassName] = useState('')
  const [board, setBoard] = useState(user?.board || 'CBSE')
  const [gradeLevel, setGradeLevel] = useState(user?.grade_level || '')
  const [section, setSection] = useState(user?.section || '')
  const [schoolSubjects, setSchoolSubjects] = useState('')

  // College Form Fields
  const [collegeDept, setCollegeDept] = useState(user?.department || user?.domain || '')
  const [semester, setSemester] = useState(user?.semester || '')
  const [collegeSection, setCollegeSection] = useState(user?.section || '')
  const [collegeSubjects, setCollegeSubjects] = useState('')

  // Roster Text / File State
  const [rosterText, setRosterText] = useState('')
  const [toast, setToast] = useState('')
  const fileInputRef = useRef(null)

  const showToastMsg = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3500)
  }

  const parseRosterText = (text) => {
    const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
    const newStudents = []

    lines.forEach((line, idx) => {
      const lower = line.toLowerCase()
      if (idx === 0 && (lower.includes('name') || lower.includes('roll') || lower.includes('rrn') || lower.includes('s.no'))) {
        return
      }

      const parts = line.split(/[,;\t]+/).map((p) => p.trim()).filter(Boolean)
      if (parts.length >= 2) {
        newStudents.push({
          id: `std_${Date.now()}_${idx}`,
          rollNo: parts[0],
          name: parts.slice(1).join(' '),
          order: newStudents.length + 1,
          marksHistory: []
        })
      } else if (parts.length === 1) {
        newStudents.push({
          id: `std_${Date.now()}_${idx}`,
          rollNo: isSchool ? `ROLL-${100 + newStudents.length + 1}` : `RRN-${2000 + newStudents.length + 1}`,
          name: parts[0],
          order: newStudents.length + 1,
          marksHistory: []
        })
      }
    })

    return newStudents
  }

  const handleCreateClass = (e) => {
    e.preventDefault()

    let created = null
    if (isSchool) {
      if (!schoolClassName.trim()) return
      const subs = schoolSubjects.split(',').map((s) => s.trim()).filter(Boolean)
      created = addClass({
        level: 'school',
        name: schoolClassName.trim(),
        type: 'School Class',
        board,
        gradeLevel,
        section,
        subjects: subs.length > 0 ? subs : ['Mathematics', 'Science'],
        students_count: 0,
        students: []
      })
    } else {
      if (!collegeDept.trim()) return
      const name = `${collegeDept.trim()} — Semester ${semester || '1'}`
      const subs = collegeSubjects.split(',').map((s) => s.trim()).filter(Boolean)
      created = addClass({
        level: 'college',
        name,
        type: 'College Department',
        department: collegeDept.trim(),
        semester,
        section: collegeSection,
        subjects: subs.length > 0 ? subs : ['Core Subject 1', 'Core Subject 2'],
        students_count: 0,
        students: []
      })
    }

    if (created) {
      if (rosterText.trim()) {
        const parsed = parseRosterText(rosterText)
        if (parsed.length > 0) {
          uploadStudentRoster(created.id, parsed)
        }
      }

      setActiveClassId(created.id)
      showToastMsg(`${isSchool ? 'Class' : 'Department'} "${created.name}" created! Entering portal...`)
      setSchoolClassName('')
      setCollegeDept('')
      setRosterText('')

      setTimeout(() => {
        navigate('/app/dashboard')
      }, 500)
    }
  }

  const handleEnterPortal = (clsId) => {
    setActiveClassId(clsId)
    navigate('/app/dashboard')
  }

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result
      if (typeof content === 'string') {
        setRosterText(content)
        showToastMsg(`Roster file "${file.name}" loaded for parsing!`)
      }
    }
    reader.readAsText(file)
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text)] flex flex-col">
      {/* Top Header */}
      <header className="h-16 border-b border-[var(--border)] px-6 sm:px-8 flex items-center justify-between bg-[var(--surface)] shadow-xs sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center shadow-xs">
            <svg width="22" height="22" viewBox="0 0 32 32" fill="none">
              <circle cx="16" cy="16" r="10.5" stroke="currentColor" strokeWidth="2.5" />
              <circle cx="23" cy="10" r="4.5" fill="currentColor" />
            </svg>
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight text-[var(--text)]">LearnSphere AI</span>
            <span className="text-xs text-[var(--accent)] font-bold ml-2">
              {isSchool ? 'School Class Setup' : 'Faculty Course Setup'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-semibold">
          <div className="hidden sm:block text-right">
            <div className="font-bold text-[var(--text)] text-sm">{user?.name || 'Educator'}</div>
            <div className="text-[var(--text-soft)] text-xs">
              {isSchool ? '🏫 School Educator' : '🎓 College Professor'} • {user?.institution_name || user?.email}
            </div>
          </div>

          <button
            onClick={() => {
              logout()
              navigate('/')
            }}
            className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--surface-hover)] transition-colors text-[var(--error)] font-bold cursor-pointer"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 md:p-10 space-y-8">
        {/* Welcome Banner */}
        <div className="p-8 rounded-3xl bg-gradient-to-r from-[var(--accent)] via-[#153c30] to-[var(--accent-dim)] text-white shadow-md flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2.5">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-white/15 backdrop-blur-md text-white text-xs font-bold tracking-wide uppercase flex items-center gap-1.5 border border-white/20">
                {isSchool ? <School size={14} /> : <GraduationCap size={14} />}
                {isSchool ? 'School Educator Gateway' : 'College Faculty Gateway'}
              </span>
              <Sparkles size={16} className="text-emerald-300" />
            </div>
            <h1 className="text-2xl sm:text-3xl md:text-4xl font-extrabold tracking-tight">
              {isSchool ? 'School Class Setup' : 'College Department Setup'}
            </h1>
            <p className="text-sm md:text-base text-emerald-100/85 max-w-xl leading-relaxed">
              Organize isolated class sections, define subject syllabi, and import your student roster for automated grading and analytics.
            </p>
          </div>

          <div className="bg-white/10 backdrop-blur-md p-5 rounded-2xl border border-white/20 text-center w-full md:w-auto md:min-w-[200px] flex flex-col items-center justify-center gap-2 shadow-xs">
            <div>
              <div className="text-4xl font-extrabold text-white mb-0.5">{teacherClasses.length}</div>
              <div className="text-xs font-bold text-white/80 uppercase tracking-wider">
                {isSchool ? 'Active Classes' : 'Active Departments'}
              </div>
            </div>
            {teacherClasses.length > 0 && (
              <button
                onClick={() => {
                  if (!activeClassId && teacherClasses[0]) {
                    setActiveClassId(teacherClasses[0].id)
                  }
                  navigate('/app/dashboard')
                }}
                className="mt-2 px-4 py-2 rounded-xl bg-white text-[var(--accent)] font-extrabold text-xs md:text-sm hover:bg-emerald-50 transition-all shadow-sm flex items-center gap-2 cursor-pointer"
              >
                <span>Enter Portal</span>
                <ArrowRight size={15} />
              </button>
            )}
          </div>
        </div>

        {toast && (
          <div className="p-4 rounded-2xl bg-[var(--success-soft)] border border-[var(--success)]/30 text-[var(--success)] text-sm font-bold flex items-center gap-2 shadow-xs">
            <CheckCircle2 size={18} />
            <span>{toast}</span>
          </div>
        )}

        {/* SECTION 1: CREATE FORM */}
        <Card className="p-7 md:p-8 space-y-6 border border-[var(--border)] bg-[var(--surface)] shadow-sm">
          <div className="flex items-start md:items-center justify-between border-b border-[var(--border)] pb-4 gap-4 flex-wrap">
            <div>
              <h2 className="text-xl font-extrabold text-[var(--text)] flex items-center gap-2.5">
                <Plus size={22} className="text-[var(--accent)]" />
                <span>
                  {isSchool ? 'Create New School Class' : 'Create New College Department'}
                </span>
              </h2>
              <p className="text-sm text-[var(--text-soft)] mt-1 font-normal">
                {isSchool
                  ? 'Define class name, education board, grade level, section, and enrolled subjects.'
                  : 'Define department name, semester, section batch, and course modules.'}
              </p>
            </div>
            <Badge tone="accent">
              {isSchool ? 'School Educator Setup' : 'College Professor Setup'}
            </Badge>
          </div>

          <form onSubmit={handleCreateClass} className="space-y-5">
            {/* Form Fields: School vs College */}
            {isSchool ? (
              <div className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Class Name</label>
                    <input
                      type="text"
                      required
                      value={schoolClassName}
                      onChange={(e) => setSchoolClassName(e.target.value)}
                      placeholder="e.g. Grade 10 - Mathematics"
                      className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Education Board</label>
                    <select
                      value={board}
                      onChange={(e) => setBoard(e.target.value)}
                      className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                    >
                      <option value="CBSE">CBSE</option>
                      <option value="ICSE">ICSE</option>
                      <option value="State Board">State Board</option>
                      <option value="IB / International">IB / International</option>
                    </select>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Grade Level</label>
                    <input
                      type="text"
                      value={gradeLevel}
                      onChange={(e) => setGradeLevel(e.target.value)}
                      placeholder="e.g. 10 or 12"
                      className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Section</label>
                    <input
                      type="text"
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                      placeholder="e.g. A"
                      className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">School Subjects (Comma Separated)</label>
                  <input
                    type="text"
                    value={schoolSubjects}
                    onChange={(e) => setSchoolSubjects(e.target.value)}
                    placeholder="Mathematics, Physics, Chemistry, Biology"
                    className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Department Name</label>
                    <input
                      type="text"
                      required
                      value={collegeDept}
                      onChange={(e) => setCollegeDept(e.target.value)}
                      placeholder="e.g. Computer Science & Engineering"
                      className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Semester</label>
                    <input
                      type="text"
                      value={semester}
                      onChange={(e) => setSemester(e.target.value)}
                      placeholder="e.g. 5"
                      className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Batch / Section Identifier</label>
                  <input
                    type="text"
                    value={collegeSection}
                    onChange={(e) => setCollegeSection(e.target.value)}
                    placeholder="e.g. CSE-5A"
                    className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Course Modules (Comma Separated)</label>
                  <input
                    type="text"
                    value={collegeSubjects}
                    onChange={(e) => setCollegeSubjects(e.target.value)}
                    placeholder="Artificial Intelligence, Web Technologies, Database Systems"
                    className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] font-medium text-sm md:text-base text-[var(--text)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all"
                  />
                </div>
              </div>
            )}

            {/* Student Roster Upload */}
            <div className="p-5 rounded-2xl border border-dashed border-[var(--border-strong)] bg-[var(--surface-alt)]/60 space-y-3">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <label className="block font-bold text-[var(--text)] text-sm">
                  Upload Student Roster ({isSchool ? 'Roll No & Name' : 'Register No & Name'}):
                </label>

                <input
                  type="file"
                  id="roster-file-upload"
                  aria-label="Upload student roster CSV or TXT file"
                  accept=".csv,.txt,.tsv"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3.5 py-1.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-[var(--accent)] text-xs font-bold hover:bg-[var(--accent-soft)] transition-colors flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Upload size={14} />
                  <span>Choose Roster File (CSV / TXT)</span>
                </button>
              </div>

              <textarea
                id="roster-textarea-input"
                aria-label="Paste student roster text"
                rows={3}
                value={rosterText}
                onChange={(e) => setRosterText(e.target.value)}
                placeholder={
                  isSchool
                    ? "ROLL-01, Student Name\nROLL-02, Student Name"
                    : "REG-101, Student Name\nREG-102, Student Name"
                }
                className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm font-mono text-[var(--text)] outline-none focus:border-[var(--accent)] transition-all"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <Button type="submit" size="lg" className="w-full md:w-auto font-bold flex items-center justify-center gap-2 shadow-sm">
                <Plus size={18} />
                <span>
                  {isSchool ? 'Create School Class' : 'Create College Department'}
                </span>
              </Button>
            </div>
          </form>
        </Card>

        {/* SECTION 2: STORED LIST */}
        <div className="space-y-5 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-extrabold text-[var(--text)] flex items-center gap-2.5">
              <Building size={22} className="text-[var(--accent)]" />
              <span>
                {isSchool
                  ? `Configured School Classes (${teacherClasses.length})`
                  : `Configured College Departments (${teacherClasses.length})`}
              </span>
            </h2>
            <span className="text-xs md:text-sm text-[var(--text-soft)] font-medium">
              Click Enter Portal to open dashboard
            </span>
          </div>

          {teacherClasses.length === 0 ? (
            <Card className="p-10 text-center border-dashed border-2 bg-[var(--surface)]">
              <Building size={48} className="mx-auto text-[var(--text-faint)] mb-3" />
              <h3 className="text-lg font-bold text-[var(--text)] mb-1">
                No {isSchool ? 'School Classes' : 'College Departments'} Stored Yet
              </h3>
              <p className="text-sm text-[var(--text-soft)] max-w-sm mx-auto leading-relaxed">
                Fill out the configuration form above to set up your first {isSchool ? 'school class' : 'college department'} and begin grading student scripts!
              </p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 gap-5">
              {teacherClasses.map((cls) => {
                const studentCount = cls.students ? cls.students.length : (cls.students_count || 0)
                return (
                  <Card
                    key={cls.id}
                    className="p-6 border border-[var(--border)] hover:border-[var(--accent)] transition-all flex flex-col justify-between space-y-4 hover:shadow-md bg-[var(--surface)]"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-3">
                        <Badge tone={cls.level === 'college' ? 'accent' : 'gold'}>
                          {cls.type}
                        </Badge>

                        <div className="flex items-center gap-2.5">
                          <span className="text-xs text-[var(--text-soft)] font-bold flex items-center gap-1 bg-[var(--surface-alt)] px-2.5 py-1 rounded-full border border-[var(--border)]">
                            <Users size={13} /> {studentCount} Students
                          </span>
                          <button
                            onClick={(e) => {
                              e.stopPropagation()
                              if (window.confirm(`Delete "${cls.name}" permanently?`)) {
                                deleteClass(cls.id)
                                showToastMsg(`"${cls.name}" removed.`)
                              }
                            }}
                            className="p-1.5 rounded-lg text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors cursor-pointer"
                            title="Delete"
                            aria-label={`Delete class ${cls.name}`}
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>

                      <h3 className="text-base sm:text-lg font-bold text-[var(--text)] mb-1 leading-snug">
                        {cls.name}
                      </h3>

                      <p className="text-xs md:text-sm text-[var(--text-soft)] font-medium mb-3">
                        {cls.level === 'school'
                          ? [cls.board ? `Board: ${cls.board}` : null, cls.gradeLevel ? `Grade ${cls.gradeLevel}` : null, cls.section ? `Section ${cls.section}` : null].filter(Boolean).join(' • ') || 'Configured Class'
                          : [cls.department ? `Dept: ${cls.department}` : null, cls.semester ? `Semester ${cls.semester}` : null, cls.section ? `Batch ${cls.section}` : null].filter(Boolean).join(' • ') || 'Configured Department'}
                      </p>

                      <div className="flex flex-wrap gap-2 text-xs">
                        <span className="font-bold text-[var(--text-faint)] py-1">Subjects:</span>
                        {(cls.subjects || []).map((sub, sIdx) => (
                          <span key={sIdx} className="px-2.5 py-1 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] font-semibold">
                            {sub}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--accent)]">Isolated Data Roster</span>
                      <Button
                        onClick={() => handleEnterPortal(cls.id)}
                        size="sm"
                        className="font-bold flex items-center gap-1.5"
                      >
                        <span>Enter Portal</span>
                        <ArrowRight size={15} />
                      </Button>
                    </div>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
