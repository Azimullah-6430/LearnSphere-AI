import { useState, useRef } from 'react'
import { useApp } from '../context/AppContext.jsx'
import { Button, Card, Badge } from './ui/Primitives.jsx'
import { School, GraduationCap, Plus, Trash2, CheckCircle2, Layers, BookOpen, Building, Upload, Users, UserCheck, FileSpreadsheet, Award, Edit3 } from 'lucide-react'

export default function ClassManagerModal({ isOpen, onClose }) {
  const {
    teacherClasses,
    addClass,
    deleteClass,
    activeClassId,
    setActiveClassId,
    uploadStudentRoster,
    addOrUpdateStudentMarks,
    deleteStudentFromClass
  } = useApp()

  // Form Mode: 'school' | 'college'
  const [classLevel, setClassLevel] = useState('school')
  
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

  const [activeTab, setActiveTab] = useState('list') // 'list' | 'roster' | 'create'
  const [selectedClassForRoster, setSelectedClassForRoster] = useState(null)

  // Roster Upload State
  const [pastedText, setPastedText] = useState('')
  const [rosterFile, setRosterFile] = useState(null)
  const [editingStudentMarks, setEditingStudentMarks] = useState(null) // student object
  const [marksSubject, setMarksSubject] = useState('')
  const [marksValue, setMarksValue] = useState('')
  const [marksAssessment, setMarksAssessment] = useState('Mid-Term Exam')

  const [toast, setToast] = useState('')
  const fileInputRef = useRef(null)

  if (!isOpen) return null

  const showToastMsg = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 3000)
  }

  const currentRosterClass = selectedClassForRoster
    ? teacherClasses.find((c) => c.id === selectedClassForRoster.id) || selectedClassForRoster
    : teacherClasses.find((c) => c.id === activeClassId) || teacherClasses[0]

  const handleCreate = (e) => {
    e.preventDefault()
    if (classLevel === 'school') {
      if (!schoolClassName.trim()) return
      const subs = schoolSubjects.split(',').map((s) => s.trim()).filter(Boolean)
      const created = addClass({
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
      showToastMsg(`Class "${created.name}" created! Upload student roster next.`)
      setSelectedClassForRoster(created)
      setActiveTab('roster')
    } else {
      const name = `${collegeDept} — Semester ${semester}`
      const subs = collegeSubjects.split(',').map((s) => s.trim()).filter(Boolean)
      const created = addClass({
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
      showToastMsg(`Department "${created.name}" created! Upload student roster next.`)
      setSelectedClassForRoster(created)
      setActiveTab('roster')
    }

    setSchoolClassName('')
  }

  // Parse CSV/TXT/TSV text preserving exact order, initials, and Roll No/RRN
  const parseRosterText = (text) => {
    const lines = text.split(/\r?\n/).map((l) => l.trim()).filter(Boolean)
    const newStudents = []

    lines.forEach((line, idx) => {
      // Ignore header row if contains 'roll', 'rrn', 'name', 'student'
      const lower = line.toLowerCase()
      if (idx === 0 && (lower.includes('name') || lower.includes('roll') || lower.includes('rrn') || lower.includes('s.no'))) {
        return
      }

      const parts = line.split(/[,;\t]+/).map((p) => p.trim()).filter(Boolean)
      if (parts.length >= 2) {
        const rollNo = parts[0]
        const name = parts.slice(1).join(' ')
        newStudents.push({
          id: `std_${Date.now()}_${idx}`,
          rollNo,
          name,
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

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setRosterFile(file)
    const reader = new FileReader()
    reader.onload = (event) => {
      const content = event.target?.result
      if (typeof content === 'string') {
        const parsed = parseRosterText(content)
        if (parsed.length > 0 && currentRosterClass) {
          uploadStudentRoster(currentRosterClass.id, parsed)
          showToastMsg(`Extracted & stored ${parsed.length} students in exact file order!`)
        } else {
          showToastMsg('Could not parse student names. Please check file format.')
        }
      }
    }
    reader.readAsText(file)
  }

  const handleProcessPastedText = () => {
    if (!pastedText.trim() || !currentRosterClass) return
    const parsed = parseRosterText(pastedText)
    if (parsed.length > 0) {
      uploadStudentRoster(currentRosterClass.id, parsed)
      showToastMsg(`Extracted & stored ${parsed.length} students in exact order!`)
      setPastedText('')
    } else {
      showToastMsg('No valid student entries found.')
    }
  }

  const handleSaveMarks = (e) => {
    e.preventDefault()
    if (!editingStudentMarks || !marksSubject || !marksValue || !currentRosterClass) return
    const mVal = parseFloat(marksValue)
    if (isNaN(mVal) || mVal < 0 || mVal > 100) {
      alert('Please enter a valid marks percentage (0 - 100).')
      return
    }

    let grade = 'F'
    if (mVal >= 90) grade = 'A+'
    else if (mVal >= 80) grade = 'A'
    else if (mVal >= 70) grade = 'B+'
    else if (mVal >= 60) grade = 'B'
    else if (mVal >= 50) grade = 'C'
    else if (mVal >= 40) grade = 'P'

    addOrUpdateStudentMarks(currentRosterClass.id, editingStudentMarks.id, {
      subject: marksSubject,
      assessment: marksAssessment || 'Term Assessment',
      marks: mVal,
      maxMarks: 100,
      percentage: mVal,
      grade,
      date: new Date().toISOString().split('T')[0]
    })

    showToastMsg(`Saved marks for ${editingStudentMarks.name} (${marksSubject}: ${mVal}%)`)
    setEditingStudentMarks(null)
    setMarksValue('')
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
      <Card className="max-w-[760px] w-full bg-[var(--surface)] border-2 border-[var(--accent)] shadow-2xl space-y-4 my-8">
        {/* Header */}
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <div>
            <div className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2">
              <Building size={20} className="text-[var(--accent)]" />
              <span>Class & Student Roster Manager</span>
            </div>
            <div className="text-[12.5px] text-[var(--text-soft)]">
              Manage classes, upload class student rosters, extract names/RRNs, and track student marks.
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Toast */}
        {toast && (
          <div className="p-2.5 rounded-lg bg-[var(--success-soft)] border border-[var(--success)] text-[var(--success)] text-[12.5px] font-bold flex items-center gap-2">
            <CheckCircle2 size={16} />
            <span>{toast}</span>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 p-1 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
          <button
            onClick={() => setActiveTab('list')}
            className={`flex-1 py-1.5 rounded-lg text-[13px] font-bold transition-all ${
              activeTab === 'list'
                ? 'bg-[var(--surface)] text-[var(--accent)] shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            Classes ({teacherClasses.length})
          </button>
          <button
            onClick={() => setActiveTab('roster')}
            className={`flex-1 py-1.5 rounded-lg text-[13px] font-bold transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'roster'
                ? 'bg-[var(--surface)] text-[var(--accent)] shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            <Users size={15} />
            <span>Student Roster & Marks</span>
          </button>
          <button
            onClick={() => setActiveTab('create')}
            className={`flex-1 py-1.5 rounded-lg text-[13px] font-bold transition-all flex items-center justify-center gap-1.5 ${
              activeTab === 'create'
                ? 'bg-[var(--accent)] text-white shadow-sm'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            <Plus size={15} />
            <span>+ Create Class / Dept</span>
          </button>
        </div>

        {/* TAB 1: LIST OF CLASSES */}
        {activeTab === 'list' && (
          <div className="space-y-3 max-h-[400px] overflow-y-auto pr-1">
            {teacherClasses.map((cls) => {
              const isSelected = activeClassId === cls.id
              const studentCount = cls.students ? cls.students.length : (cls.students_count || 0)
              return (
                <div
                  key={cls.id}
                  className={`p-3.5 rounded-xl border transition-all flex items-start justify-between gap-3 ${
                    isSelected
                      ? 'bg-[var(--accent-soft)] border-[var(--accent)]'
                      : 'bg-[var(--surface)] border-[var(--border)] hover:border-[var(--accent-dim)]'
                  }`}
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-extrabold text-[15px] text-[var(--text)]">
                        {cls.name}
                      </span>
                      <Badge tone={cls.level === 'college' ? 'accent' : 'gold'}>
                        {cls.type}
                      </Badge>
                      {isSelected && <Badge tone="success">Active Filter</Badge>}
                    </div>

                    <div className="text-[12px] text-[var(--text-soft)] font-medium mb-2">
                      {cls.level === 'school' ? `Board: ${cls.board} • Section ${cls.section}` : `Dept: ${cls.department} • Section ${cls.section}`} • {studentCount} Enrolled Students
                    </div>

                    <div className="flex flex-wrap gap-1 text-[11.5px]">
                      <span className="font-bold text-[var(--text-faint)] mr-1">Subjects:</span>
                      {cls.subjects.map((s, idx) => (
                        <span key={idx} className="px-2 py-0.5 rounded bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] font-semibold">
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setSelectedClassForRoster(cls)
                        setActiveTab('roster')
                      }}
                      className="px-2.5 py-1.5 rounded-lg text-[12px] font-bold border border-[var(--accent)] text-[var(--accent)] bg-[var(--accent-soft)] hover:bg-[var(--accent)] hover:text-white transition-all flex items-center gap-1"
                    >
                      <Users size={14} />
                      <span>Roster ({studentCount})</span>
                    </button>

                    <button
                      onClick={() => {
                        setActiveClassId(cls.id)
                        showToastMsg(`Switched active view to "${cls.name}"`)
                      }}
                      className={`px-3 py-1.5 rounded-lg text-[12px] font-bold transition-all ${
                        isSelected
                          ? 'bg-[var(--accent)] text-white'
                          : 'border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                      }`}
                    >
                      {isSelected ? 'Active' : 'Select'}
                    </button>

                    <button
                      onClick={() => {
                        if (window.confirm(`Delete class "${cls.name}" permanently?`)) {
                          deleteClass(cls.id)
                          showToastMsg(`Class "${cls.name}" deleted.`)
                        }
                      }}
                      className="p-1.5 rounded-lg text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors border border-transparent hover:border-[var(--error)]"
                      title="Delete Class"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {/* TAB 2: STUDENT ROSTER & MARKS */}
        {activeTab === 'roster' && (
          <div className="space-y-4 max-h-[420px] overflow-y-auto pr-1">
            {/* Class Switcher for Roster */}
            <div className="flex items-center justify-between bg-[var(--surface-alt)] p-3 rounded-xl border border-[var(--border)]">
              <div>
                <span className="text-[11px] font-bold text-[var(--text-faint)] uppercase tracking-wider block">Managing Student Roster for:</span>
                <span className="text-[15px] font-extrabold text-[var(--accent)]">
                  {currentRosterClass?.name} ({currentRosterClass?.level === 'college' ? currentRosterClass?.department : currentRosterClass?.board})
                </span>
              </div>

              <select
                value={currentRosterClass?.id || ''}
                onChange={(e) => {
                  const target = teacherClasses.find((c) => c.id === e.target.value)
                  if (target) setSelectedClassForRoster(target)
                }}
                className="px-3 py-1.5 text-[12.5px] font-bold rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] outline-none"
              >
                {teacherClasses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.students ? c.students.length : 0} students)
                  </option>
                ))}
              </select>
            </div>

            {/* Upload File / Paste Section */}
            <div className="p-3.5 rounded-xl border border-dashed border-[var(--accent)] bg-[var(--accent-soft)]/20 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-[13px] font-extrabold text-[var(--text)]">
                  <FileSpreadsheet size={18} className="text-[var(--accent)]" />
                  <span>Upload Student List File (CSV / TXT / TSV)</span>
                </div>
                <span className="text-[11px] text-[var(--text-soft)] font-medium">Extracts exact Roll No/RRN, Names & Initials in file order</span>
              </div>

              <div className="flex items-center gap-3">
                <input
                  type="file"
                  accept=".csv,.txt,.tsv"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="px-3.5 py-2 rounded-lg bg-[var(--accent)] text-white text-[12.5px] font-bold hover:opacity-90 transition-all flex items-center gap-1.5"
                >
                  <Upload size={15} />
                  <span>Choose Roster File (.csv, .txt)</span>
                </button>
                {rosterFile && <span className="text-[12px] font-bold text-[var(--accent)]">{rosterFile.name}</span>}
              </div>

              <div className="pt-2 border-t border-[var(--border)]">
                <label className="block text-[11.5px] font-bold text-[var(--text-soft)] mb-1">
                  Or Paste Roster Text (Format: <code className="bg-[var(--surface-alt)] px-1 rounded">RollNo, Student Name Initial</code>):
                </label>
                <div className="flex gap-2">
                  <textarea
                    rows={2}
                    value={pastedText}
                    onChange={(e) => setPastedText(e.target.value)}
                    placeholder={`ROLL-01, Student Name\nROLL-02, Student Name\nROLL-03, Student Name`}
                    className="flex-1 p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[12px] font-mono text-[var(--text)] outline-none"
                  />
                  <button
                    onClick={handleProcessPastedText}
                    className="px-3.5 py-2 rounded-lg bg-[var(--surface-alt)] border border-[var(--accent)] text-[var(--accent)] text-[12px] font-bold hover:bg-[var(--accent-soft)] transition-all self-end"
                  >
                    Extract & Save
                  </button>
                </div>
              </div>
            </div>

            {/* Modal for Editing Marks */}
            {editingStudentMarks && (
              <form onSubmit={handleSaveMarks} className="p-3.5 rounded-xl border border-[var(--accent)] bg-[var(--surface-alt)] space-y-3">
                <div className="flex items-center justify-between text-[13px] font-bold">
                  <span>Record Evaluated Marks for: <strong className="text-[var(--accent)]">{editingStudentMarks.name}</strong> ({editingStudentMarks.rollNo})</span>
                  <button type="button" onClick={() => setEditingStudentMarks(null)} className="text-[var(--text-soft)] hover:text-[var(--text)] font-bold">✕</button>
                </div>

                <div className="grid grid-cols-3 gap-3 text-[12px]">
                  <div>
                    <label className="block font-bold mb-1">Subject:</label>
                    <select
                      value={marksSubject}
                      onChange={(e) => setMarksSubject(e.target.value)}
                      className="w-full p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-bold text-[var(--text)]"
                    >
                      {currentRosterClass?.subjects.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block font-bold mb-1">Assessment Title:</label>
                    <input
                      type="text"
                      value={marksAssessment}
                      onChange={(e) => setMarksAssessment(e.target.value)}
                      placeholder="Mid-Term / CAT 1 / Unit Test"
                      className="w-full p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-bold text-[var(--text)]"
                    />
                  </div>

                  <div>
                    <label className="block font-bold mb-1">Marks Score (%):</label>
                    <input
                      type="number"
                      required
                      min="0"
                      max="100"
                      value={marksValue}
                      onChange={(e) => setMarksValue(e.target.value)}
                      placeholder="e.g. 85"
                      className="w-full p-2 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-bold text-[var(--text)]"
                    />
                  </div>
                </div>

                <div className="flex justify-end gap-2">
                  <button
                    type="button"
                    onClick={() => setEditingStudentMarks(null)}
                    className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-[12px] font-bold text-[var(--text-soft)]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded-lg bg-[var(--accent)] text-white text-[12px] font-bold"
                  >
                    Save Evaluated Marks
                  </button>
                </div>
              </form>
            )}

            {/* Roster Table */}
            <div className="border border-[var(--border)] rounded-xl overflow-hidden bg-[var(--surface)]">
              <table className="w-full border-collapse text-[12.5px]">
                <thead>
                  <tr className="bg-[var(--surface-alt)] border-b border-[var(--border)]">
                    <th className="py-2.5 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">#</th>
                    <th className="py-2.5 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Roll No / RRN</th>
                    <th className="py-2.5 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Student Name & Initial</th>
                    <th className="py-2.5 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Evaluated Marks</th>
                    <th className="py-2.5 px-3 text-center font-bold text-[var(--text-faint)] uppercase text-[11px]">Avg %</th>
                    <th className="py-2.5 px-3 text-right font-bold text-[var(--text-faint)] uppercase text-[11px]">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(!currentRosterClass?.students || currentRosterClass.students.length === 0) ? (
                    <tr>
                      <td colSpan={6} className="py-6 text-center text-[var(--text-soft)] font-medium">
                        No students uploaded for this class yet. Use the upload bar above to add roster.
                      </td>
                    </tr>
                  ) : (
                    currentRosterClass.students.map((std, idx) => {
                      const marksList = std.marksHistory || []
                      const totalPerc = marksList.length > 0
                        ? Math.round(marksList.reduce((acc, m) => acc + m.percentage, 0) / marksList.length)
                        : null

                      return (
                        <tr key={std.id || idx} className="border-b border-[var(--border)] hover:bg-[var(--surface-alt)]">
                          <td className="py-2.5 px-3 font-bold text-[var(--text-faint)] text-[11.5px]">{std.order || idx + 1}</td>
                          <td className="py-2.5 px-3 font-mono font-bold text-[var(--text)]">{std.rollNo}</td>
                          <td className="py-2.5 px-3 font-extrabold text-[var(--text)]">{std.name}</td>
                          <td className="py-2.5 px-3">
                            {marksList.length === 0 ? (
                              <span className="text-[11px] text-[var(--text-soft)] italic">No marks recorded</span>
                            ) : (
                              <div className="flex flex-wrap gap-1">
                                {marksList.map((m, mIdx) => (
                                  <span
                                    key={mIdx}
                                    className={`px-1.5 py-0.5 rounded text-[10.5px] font-bold border ${
                                      m.percentage >= 85
                                        ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
                                        : m.percentage >= 60
                                        ? 'bg-blue-500/10 text-blue-600 border-blue-500/30'
                                        : m.percentage >= 40
                                        ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                                        : 'bg-red-500/10 text-red-600 border-red-500/30'
                                    }`}
                                  >
                                    {m.subject}: {m.percentage}%
                                  </span>
                                ))}
                              </div>
                            )}
                          </td>
                          <td className="py-2.5 px-3 text-center font-extrabold text-[var(--accent)]">
                            {totalPerc !== null ? `${totalPerc}%` : 'N/A'}
                          </td>
                          <td className="py-2.5 px-3 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() => {
                                  setEditingStudentMarks(std)
                                  setMarksSubject(currentRosterClass?.subjects[0] || '')
                                }}
                                className="px-2 py-1 rounded text-[11px] font-bold bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--accent)] hover:bg-[var(--accent-soft)]"
                                title="Add/Edit Evaluated Marks"
                              >
                                + Marks
                              </button>
                              <button
                                onClick={() => {
                                  if (window.confirm(`Delete student ${std.name} (${std.rollNo})?`)) {
                                    deleteStudentFromClass(currentRosterClass.id, std.id)
                                    showToastMsg(`Deleted ${std.name} from roster.`)
                                  }
                                }}
                                className="p-1 text-[var(--error)] hover:bg-[var(--error-soft)] rounded"
                                title="Delete Student"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* TAB 3: CREATE CLASS / DEPARTMENT FORM */}
        {activeTab === 'create' && (
          <form onSubmit={handleCreate} className="space-y-4 text-[13px]">
            {/* Level Switcher */}
            <div>
              <label className="block font-bold text-[var(--text-soft)] mb-1.5 uppercase text-[11px] tracking-wider">
                Select Institution Tier:
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setClassLevel('school')}
                  className={`p-3 rounded-xl border text-left flex items-center gap-2 transition-all ${
                    classLevel === 'school'
                      ? 'bg-[var(--accent-soft)] border-[var(--accent)] text-[var(--accent)] font-bold'
                      : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text-soft)]'
                  }`}
                >
                  <School size={20} />
                  <div>
                    <div className="text-[13.5px]">School Teacher</div>
                    <div className="text-[11px] opacity-75 font-normal">Class 10, 11, 12 & Subjects</div>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setClassLevel('college')}
                  className={`p-3 rounded-xl border text-left flex items-center gap-2 transition-all ${
                    classLevel === 'college'
                      ? 'bg-[var(--accent-soft)] border-[var(--accent)] text-[var(--accent)] font-bold'
                      : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text-soft)]'
                  }`}
                >
                  <GraduationCap size={20} />
                  <div>
                    <div className="text-[13.5px]">College Professor</div>
                    <div className="text-[11px] opacity-75 font-normal">Department & Semester Courses</div>
                  </div>
                </button>
              </div>
            </div>

            {/* School Fields */}
            {classLevel === 'school' ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Class Name:</label>
                    <input
                      type="text"
                      required
                      value={schoolClassName}
                      onChange={(e) => setSchoolClassName(e.target.value)}
                      placeholder="e.g. Grade 10 - Mathematics"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Education Board:</label>
                    <select
                      value={board}
                      onChange={(e) => setBoard(e.target.value)}
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    >
                      <option value="CBSE">CBSE</option>
                      <option value="ICSE">ICSE</option>
                      <option value="State Board">State Board</option>
                      <option value="IB / International">IB / International</option>
                    </select>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Grade Level:</label>
                    <input
                      type="text"
                      value={gradeLevel}
                      onChange={(e) => setGradeLevel(e.target.value)}
                      placeholder="e.g. 10, 11, 12"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Section:</label>
                    <input
                      type="text"
                      value={section}
                      onChange={(e) => setSection(e.target.value)}
                      placeholder="e.g. A, B, C"
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
                    placeholder="Physics, Chemistry, Mathematics, Biology"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>
              </div>
            ) : (
              /* College Fields */
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Department Name:</label>
                    <input
                      type="text"
                      required
                      value={collegeDept}
                      onChange={(e) => setCollegeDept(e.target.value)}
                      placeholder="e.g. Computer Science & AI"
                      className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                    />
                  </div>

                  <div>
                    <label className="block font-bold text-[var(--text-soft)] mb-1">Semester / Year:</label>
                    <input
                      type="text"
                      value={semester}
                      onChange={(e) => setSemester(e.target.value)}
                      placeholder="e.g. Semester 5"
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
                    placeholder="e.g. CSE-5A"
                    className="w-full p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-medium text-[var(--text)] outline-none"
                  />
                </div>

                <div>
                  <label className="block font-bold text-[var(--text-soft)] mb-1">Course Subjects (Comma Separated):</label>
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

            <div className="pt-2 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setActiveTab('list')}
                className="px-4 py-2 rounded-lg border border-[var(--border)] text-[var(--text-soft)] font-bold hover:bg-[var(--surface-alt)]"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="px-5 py-2 rounded-lg bg-[var(--accent)] text-white font-bold hover:opacity-90 transition-opacity"
              >
                Create Class & Set Up Roster
              </button>
            </div>
          </form>
        )}
      </Card>
    </div>
  )
}
