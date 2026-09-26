import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { Card, PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { Building, School, GraduationCap, Plus, ArrowRight, CheckCircle2, Users, FileSpreadsheet, Upload, Sparkles, BookOpen } from 'lucide-react'

export default function SelectClass() {
  const { user, teacherClasses, addClass, setActiveClassId, uploadStudentRoster } = useApp()
  const navigate = useNavigate()

  // Creation Mode State
  const [classLevel, setClassLevel] = useState('school') // 'school' | 'college'

  // School Form State
  const [schoolClassName, setSchoolClassName] = useState('')
  const [board, setBoard] = useState('CBSE')
  const [gradeLevel, setGradeLevel] = useState('12')
  const [section, setSection] = useState('A')
  const [schoolSubjects, setSchoolSubjects] = useState('Physics, Chemistry, Mathematics, Biology')

  // College Form State
  const [collegeDept, setCollegeDept] = useState('Computer Science & AI')
  const [semester, setSemester] = useState('5')
  const [collegeSection, setCollegeSection] = useState('CSE-5A')
  const [collegeSubjects, setCollegeSubjects] = useState('Artificial Intelligence, Web Technologies, Theory of Computation, Compiler Design')

  // Optional Initial Roster Paste
  const [rosterText, setRosterText] = useState('')
  const [toast, setToast] = useState('')
  const fileInputRef = useRef(null)

  const showToastMsg = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const handleSelectExistingClass = (clsId) => {
    setActiveClassId(clsId)
    navigate('/app/dashboard')
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
          rollNo: `ROLL-${100 + newStudents.length + 1}`,
          name: parts[0],
          order: newStudents.length + 1,
          marksHistory: []
        })
      }
    })

    return newStudents
  }

  const handleCreateNewClass = (e) => {
    e.preventDefault()

    let created = null
    if (classLevel === 'school') {
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
      const name = `${collegeDept} — Semester ${semester}`
      const subs = collegeSubjects.split(',').map((s) => s.trim()).filter(Boolean)
      created = addClass({
        level: 'college',
        name,
        type: 'College Department',
        department: collegeDept,
        semester,
        section: collegeSection,
        subjects: subs.length > 0 ? subs : ['Core Subject 1', 'Core Subject 2'],
        students_count: 0,
        students: []
      })
    }

    if (created) {
      if (rosterText.trim()) {
        const parsedRoster = parseRosterText(rosterText)
        if (parsedRoster.length > 0) {
          uploadStudentRoster(created.id, parsedRoster)
        }
      }

      setActiveClassId(created.id)
      navigate('/app/dashboard')
    }
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
    <div className="max-w-6xl mx-auto space-y-6 pb-12">
      {/* Welcome Banner Header */}
      <div className="p-7 rounded-2xl bg-gradient-to-r from-[var(--accent)] to-[var(--accent-dim)] text-white shadow-xl flex flex-col md:flex-row md:items-center justify-between gap-6">
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 rounded-full bg-white/20 text-white text-[12px] font-bold tracking-wide uppercase">
              Teacher Portal Onboarding
            </span>
            <Sparkles size={18} className="text-yellow-300 animate-pulse" />
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight">
            Welcome, {user?.name || 'Educator'}!
          </h1>
          <p className="text-white/80 text-sm max-w-xl font-medium">
            Create a class or select an existing class below to navigate into the Teacher Portal and access paper evaluation, misconception maps, action center, and student analytics.
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-md p-4 rounded-xl border border-white/20 text-center min-w-[200px]">
          <div className="text-3xl font-extrabold text-white mb-0.5">{teacherClasses.length}</div>
          <div className="text-xs font-bold text-white/80 uppercase tracking-wider">Created Classes</div>
        </div>
      </div>

      {toast && (
        <div className="p-3 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] text-[var(--success)] text-xs font-bold flex items-center gap-2">
          <CheckCircle2 size={16} />
          <span>{toast}</span>
        </div>
      )}

      {/* Grid Section 1: Choose Existing Class */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-extrabold text-[var(--text)] flex items-center gap-2">
            <Building size={20} className="text-[var(--accent)]" />
            <span>Select Existing Class / Department</span>
          </h2>
          <span className="text-xs text-[var(--text-soft)] font-medium">
            Click any class card to navigate into the Teacher Portal for that class
          </span>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          {teacherClasses.map((cls) => {
            const studentCount = cls.students ? cls.students.length : (cls.students_count || 0)
            return (
              <Card
                key={cls.id}
                className="p-5 hover:border-[var(--accent)] transition-all cursor-pointer group flex flex-col justify-between space-y-4 hover:shadow-lg border-2"
                onClick={() => handleSelectExistingClass(cls.id)}
              >
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <Badge tone={cls.level === 'college' ? 'accent' : 'gold'}>
                      {cls.type}
                    </Badge>
                    <span className="text-xs text-[var(--text-soft)] font-bold flex items-center gap-1">
                      <Users size={13} /> {studentCount} Enrolled Students
                    </span>
                  </div>

                  <h3 className="text-lg font-extrabold text-[var(--text)] group-hover:text-[var(--accent)] transition-colors mb-1">
                    {cls.name}
                  </h3>

                  <p className="text-xs text-[var(--text-soft)] font-medium mb-3">
                    {cls.level === 'school'
                      ? `Board: ${cls.board} • Grade ${cls.gradeLevel} • Section ${cls.section}`
                      : `Dept: ${cls.department} • Semester ${cls.semester} • Section ${cls.section}`}
                  </p>

                  <div className="flex flex-wrap gap-1.5 text-[11.5px]">
                    <span className="font-bold text-[var(--text-faint)] mr-1">Subjects:</span>
                    {cls.subjects.map((sub, sIdx) => (
                      <span key={sIdx} className="px-2 py-0.5 rounded-md bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] font-semibold">
                        {sub}
                      </span>
                    ))}
                  </div>
                </div>

                <div className="pt-3 border-t border-[var(--border)] flex items-center justify-between">
                  <span className="text-xs font-bold text-[var(--accent)]">Enter Class Portal</span>
                  <div className="w-8 h-8 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center group-hover:bg-[var(--accent)] group-hover:text-white transition-all">
                    <ArrowRight size={16} />
                  </div>
                </div>
              </Card>
            )
          })}
        </div>
      </div>

      {/* Grid Section 2: Create New Class Form */}
      <Card className="p-6 space-y-5 border-2 border-[var(--accent)] bg-[var(--surface)]">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-4">
          <div>
            <h2 className="text-lg font-extrabold text-[var(--text)] flex items-center gap-2">
              <Plus size={22} className="text-[var(--accent)]" />
              <span>Create New Class / Department</span>
            </h2>
            <p className="text-xs text-[var(--text-soft)] font-medium">
              Set up your school class or college department and navigate directly into the Teacher Portal.
            </p>
          </div>
          <Badge tone="accent">Quick Setup</Badge>
        </div>

        <form onSubmit={handleCreateNewClass} className="space-y-4 text-[13px]">
          {/* Level Switcher */}
          <div>
            <label className="block font-bold text-[var(--text-soft)] mb-2 uppercase text-[11px] tracking-wider">
              1. Select Tier:
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                type="button"
                onClick={() => setClassLevel('school')}
                className={`p-4 rounded-xl border-2 text-left flex items-center gap-3 transition-all ${
                  classLevel === 'school'
                    ? 'bg-[var(--accent-soft)] border-[var(--accent)] text-[var(--accent)] font-bold shadow-sm'
                    : 'bg-[var(--surface-alt)] border-[var(--border)] text-[var(--text-soft)]'
                }`}
              >
                <School size={24} />
                <div>
                  <div className="text-[14px] font-bold">School Educator</div>
                  <div className="text-[11.5px] opacity-80 font-normal">Classes 10, 11, 12, CBSE/ICSE Board</div>
                </div>
              </button>

              <button
                type="button"
                onClick={() => setClassLevel('college')}
                className={`p-4 rounded-xl border-2 text-left flex items-center gap-3 transition-all ${
                  classLevel === 'college'
                    ? 'bg-[var(--accent-soft)] border-[var(--accent)] text-[var(--accent)] font-bold shadow-sm'
                    : 'bg-[var(--surface-alt)] border-[var(--border)] text-[var(--text-soft)]'
                }`}
              >
                <GraduationCap size={24} />
                <div>
                  <div className="text-[14px] font-bold">College Professor</div>
                  <div className="text-[11.5px] opacity-80 font-normal">Department, Semester & Course Modules</div>
                </div>
              </button>
            </div>
          </div>

          {/* Form Fields */}
          {classLevel === 'school' ? (
            <div className="space-y-3 pt-1">
              <div className="grid md:grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">Class Name:</label>
                  <input
                    type="text"
                    required
                    value={schoolClassName}
                    onChange={(e) => setSchoolClassName(e.target.value)}
                    placeholder="e.g. Class 12-B (Physics & Math)"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none focus:border-[var(--accent)]"
                  />
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">Board:</label>
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
                    placeholder="e.g. B"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-[var(--text-soft)] mb-1">Subjects (Comma Separated):</label>
                <input
                  type="text"
                  value={schoolSubjects}
                  onChange={(e) => setSchoolSubjects(e.target.value)}
                  placeholder="Physics, Chemistry, Mathematics, Computer Science"
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
                    placeholder="e.g. Artificial Intelligence & Data Science"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">Semester / Year:</label>
                  <input
                    type="text"
                    value={semester}
                    onChange={(e) => setSemester(e.target.value)}
                    placeholder="e.g. Semester 6"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block font-bold text-[var(--text-soft)] mb-1">Class Section / Batch:</label>
                <input
                  type="text"
                  value={collegeSection}
                  onChange={(e) => setCollegeSection(e.target.value)}
                  placeholder="e.g. AI-6A"
                  className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                />
              </div>

              <div>
                <label className="block font-bold text-[var(--text-soft)] mb-1">Course Subjects (Comma Separated):</label>
                <input
                  type="text"
                  value={collegeSubjects}
                  onChange={(e) => setCollegeSubjects(e.target.value)}
                  placeholder="Deep Learning, Natural Language Processing, Machine Learning"
                  className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                />
              </div>
            </div>
          )}

          {/* Optional Roster Upload / Text Paste */}
          <div className="p-3.5 rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface-alt)] space-y-2">
            <div className="flex items-center justify-between">
              <label className="block font-bold text-[var(--text)] text-[12.5px]">
                Upload Student Roster (Optional - CSV / TXT / Paste):
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
                <span>Upload File</span>
              </button>
            </div>

            <textarea
              rows={2}
              value={rosterText}
              onChange={(e) => setRosterText(e.target.value)}
              placeholder={`12B-01, Aarav R. Sharma\n12B-02, Vignesh B.`}
              className="w-full p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[12px] font-mono text-[var(--text)] outline-none"
            />
          </div>

          <div className="pt-2 flex justify-end">
            <Button type="submit" size="lg" className="w-full md:w-auto font-extrabold flex items-center justify-center gap-2">
              <span>Create Class & Enter Teacher Portal</span>
              <ArrowRight size={18} />
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
