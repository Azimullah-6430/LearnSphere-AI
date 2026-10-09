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
      const name = `${collegeDept.trim()} — Semester ${semester}`
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

      // Seamlessly transition directly into the educator portal dashboard
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
      {/* Top Standalone Header */}
      <header className="h-16 border-b border-[var(--border)] px-8 flex items-center justify-between bg-[var(--surface)] shadow-sm sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="10.5" stroke="#28503F" strokeWidth="2" />
            <circle cx="24" cy="9" r="4" fill="#28503F" />
          </svg>
          <div>
            <span className="font-extrabold text-[16px] tracking-tight">LearnSphere AI</span>
            <span className="text-xs text-[var(--accent)] font-semibold ml-2">
              {isSchool ? 'School Educator Gateway' : 'College Professor Gateway'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-semibold">
          <div className="hidden sm:block text-right">
            <div className="font-bold text-[var(--text)]">{user?.name || 'Educator'}</div>
            <div className="text-[var(--text-soft)]">
              {isSchool ? '🏫 School Educator' : '🎓 College Professor'} • {user?.institution_name || user?.email}
            </div>
          </div>

          <button
            onClick={() => {
              logout()
              navigate('/')
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface-alt)] hover:bg-[var(--border)] transition-colors text-[var(--error)] font-bold"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="flex-1 max-w-6xl w-full mx-auto p-6 md:p-10 space-y-8">
        {/* Welcome Banner */}
        <div className="p-7 rounded-2xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-dim)] text-white shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="px-3 py-1 rounded-full bg-white/20 text-white text-[12px] font-bold tracking-wide uppercase flex items-center gap-1.5">
                {isSchool ? <School size={15} /> : <GraduationCap size={15} />}
                {isSchool ? 'School Educator Account' : 'College Professor Account'}
              </span>
              <Sparkles size={18} className="text-yellow-300 animate-pulse" />
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
              {isSchool ? 'School Class Setup' : 'College Department Setup'}
            </h1>
          </div>

          <div className="bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/20 text-center min-w-[200px] flex flex-col items-center justify-center gap-2">
            <div>
              <div className="text-3xl font-extrabold text-white mb-0.5">{teacherClasses.length}</div>
              <div className="text-xs font-bold text-white/80 uppercase tracking-wider">
                {isSchool ? 'Stored Classes' : 'Stored Departments'}
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
                className="mt-1 px-3 py-1.5 rounded-lg bg-white text-[var(--accent)] font-extrabold text-xs hover:bg-white/90 transition-all shadow-sm flex items-center gap-1.5 cursor-pointer"
              >
                <span>Enter Portal</span>
                <ArrowRight size={14} />
              </button>
            )}
          </div>
        </div>

        {toast && (
          <div className="p-3.5 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] text-[var(--success)] text-xs font-bold flex items-center gap-2">
            <CheckCircle2 size={16} />
            <span>{toast}</span>
          </div>
        )}

        {/* SECTION 1: CREATE FORM (NO TOGGLE, STRICTLY BASED ON ACCOUNT ROLE) */}
        <Card className="p-6 space-y-5 border-2 border-[var(--accent)] bg-[var(--surface)] shadow-md">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <div>
              <h2 className="text-lg font-extrabold text-[var(--text)] flex items-center gap-2">
                <Plus size={22} className="text-[var(--accent)]" />
                <span>
                  {isSchool ? 'Create New School Class' : 'Create New College Department'}
                </span>
              </h2>
              <p className="text-xs text-[var(--text-soft)] font-medium">
                {isSchool
                  ? 'Fill out class name, education board, grade level, section, subjects, and student roster.'
                  : 'Fill out department name, semester, batch section, course subjects, and student roster.'}
              </p>
            </div>
            <Badge tone="accent">
              {isSchool ? 'School Educator Setup' : 'College Professor Setup'}
            </Badge>
          </div>

          <form onSubmit={handleCreateClass} className="space-y-4 text-[13px]">
            {/* Form Fields: School vs College */}
            {isSchool ? (
              <div className="space-y-3 pt-1">
                <div className="grid md:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Class Name:</label>
                    <input
                      type="text"
                      required
                      value={schoolClassName}
                      onChange={(e) => setSchoolClassName(e.target.value)}
                      placeholder="e.g. Grade 10 - Mathematics"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none focus:border-[var(--accent)]"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Education Board:</label>
                    <select
                      value={board}
                      onChange={(e) => setBoard(e.target.value)}
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none focus:border-[var(--accent)]"
                    >
                      <option value="CBSE">CBSE</option>
                      <option value="ICSE">ICSE</option>
                      <option value="State Board">State Board</option>
                      <option value="IB / International">IB / International</option>
                    </select>
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Grade Level:</label>
                    <input
                      type="text"
                      value={gradeLevel}
                      onChange={(e) => setGradeLevel(e.target.value)}
                      placeholder="e.g. 12"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Section:</label>
                    <input
                      type="text"
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                      placeholder="e.g. A"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">School Subjects (Comma Separated):</label>
                  <input
                    type="text"
                    value={schoolSubjects}
                    onChange={(e) => setSchoolSubjects(e.target.value)}
                    placeholder="Physics, Chemistry, Mathematics, Biology"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-3 pt-1">
                <div className="grid md:grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Department Name:</label>
                    <input
                      type="text"
                      required
                      value={collegeDept}
                      onChange={(e) => setCollegeDept(e.target.value)}
                      placeholder="e.g. Computer Science & Engineering"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Semester / Year:</label>
                    <input
                      type="text"
                      value={semester}
                      onChange={(e) => setSemester(e.target.value)}
                      placeholder="e.g. 5"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">Batch / Class Section:</label>
                  <input
                    type="text"
                    value={collegeSection}
                    onChange={(e) => setCollegeSection(e.target.value)}
                    placeholder="e.g. CSE-5A"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">Course Modules (Comma Separated):</label>
                  <input
                    type="text"
                    value={collegeSubjects}
                    onChange={(e) => setCollegeSubjects(e.target.value)}
                    placeholder="Artificial Intelligence, Web Tech, Compiler Design"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>
              </div>
            )}

            {/* Student Roster Upload / Text Paste */}
            <div className="p-3.5 rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface-alt)] space-y-2">
              <div className="flex items-center justify-between">
                <label className="block font-bold text-[var(--text)] text-[12.5px]">
                  Upload Student Roster ({isSchool ? 'Name & Roll No' : 'Name & RRN / Register No'}) (CSV / TXT / Paste):
                </label>

                <input
                  type="file"
                  accept=".csv,.txt,.tsv"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  type="button"
                  onClick={() => fileInputRef.current?.click()}
                  className="px-2.5 py-1 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--accent)] text-[11.5px] font-bold hover:bg-[var(--accent-soft)] transition-colors flex items-center gap-1"
                >
                  <Upload size={13} />
                  <span>Choose Roster File</span>
                </button>
              </div>

              <textarea
                rows={3}
                value={rosterText}
                onChange={(e) => setRosterText(e.target.value)}
                placeholder={
                  isSchool
                    ? "ROLL-01, Student Name\nROLL-02, Student Name"
                    : "REG-101, Student Name\nREG-102, Student Name"
                }
                className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[12px] font-mono text-[var(--text)] outline-none"
              />
            </div>

            <div className="pt-2 flex justify-end">
              <Button type="submit" size="lg" className="w-full md:w-auto font-extrabold flex items-center justify-center gap-2">
                <Plus size={18} />
                <span>
                  {isSchool ? 'Store & Add School Class' : 'Store & Add Department'}
                </span>
              </Button>
            </div>
          </form>
        </Card>

        {/* SECTION 2: STORED LIST (STRICTLY ACCORDING TO ACCOUNT ROLE) */}
        <div className="space-y-4 pt-2">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-extrabold text-[var(--text)] flex items-center gap-2">
              <Building size={20} className="text-[var(--accent)]" />
              <span>
                {isSchool
                  ? `Stored School Classes (${teacherClasses.length})`
                  : `Stored College Departments (${teacherClasses.length})`}
              </span>
            </h2>
            <span className="text-xs text-[var(--text-soft)] font-medium">
              Click to open the Teacher Portal for that respective {isSchool ? 'class' : 'department'}
            </span>
          </div>

          {teacherClasses.length === 0 ? (
            <Card className="p-8 text-center border-dashed border-2 bg-[var(--surface)]">
              <Building size={40} className="mx-auto text-[var(--text-faint)] mb-2" />
              <h3 className="text-base font-bold text-[var(--text)] mb-1">
                No {isSchool ? 'School Classes' : 'College Departments'} Stored Yet
              </h3>
              <p className="text-xs text-[var(--text-soft)] max-w-sm mx-auto">
                Fill out the form above to create your first {isSchool ? 'school class' : 'college department'} and start evaluating students!
              </p>
            </Card>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {teacherClasses.map((cls) => {
                const studentCount = cls.students ? cls.students.length : (cls.students_count || 0)
                return (
                  <Card
                    key={cls.id}
                    className="p-5 border-2 hover:border-[var(--accent)] transition-all flex flex-col justify-between space-y-4 hover:shadow-lg bg-[var(--surface)]"
                  >
                    <div>
                      <div className="flex items-center justify-between mb-2">
                        <Badge tone={cls.level === 'college' ? 'accent' : 'gold'}>
                          {cls.type}
                        </Badge>

                        <div className="flex items-center gap-2">
                          <span className="text-xs text-[var(--text-soft)] font-bold flex items-center gap-1">
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
                            className="p-1 rounded text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                            title="Delete"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </div>

                      <h3 className="text-lg font-extrabold text-[var(--text)] mb-1">
                        {cls.name}
                      </h3>

                      <p className="text-xs text-[var(--text-soft)] font-medium mb-3">
                        {cls.level === 'school'
                          ? [cls.board ? `Board: ${cls.board}` : null, cls.gradeLevel ? `Grade ${cls.gradeLevel}` : null, cls.section ? `Section ${cls.section}` : null].filter(Boolean).join(' • ') || 'Configured Class'
                          : [cls.department ? `Dept: ${cls.department}` : null, cls.semester ? `Semester ${cls.semester}` : null, cls.section ? `Batch ${cls.section}` : null].filter(Boolean).join(' • ') || 'Configured Department'}
                      </p>

                      <div className="flex flex-wrap gap-1.5 text-[11.5px]">
                        <span className="font-bold text-[var(--text-faint)] mr-1">Subjects:</span>
                        {(cls.subjects || []).map((sub, sIdx) => (
                          <span key={sIdx} className="px-2 py-0.5 rounded-md bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] font-semibold">
                            {sub}
                          </span>
                        ))}
                      </div>
                    </div>

                    <div className="pt-3 border-t border-[var(--border)] flex items-center justify-between">
                      <span className="text-xs font-bold text-[var(--accent)]">Isolated Roster & Analytics</span>
                      <Button
                        onClick={() => handleEnterPortal(cls.id)}
                        size="sm"
                        className="font-extrabold flex items-center gap-1.5"
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
