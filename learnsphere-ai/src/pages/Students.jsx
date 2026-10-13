import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, PageHead, SearchBox, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  Users,
  Plus,
  Upload,
  Building,
  School,
  GraduationCap,
  UserPlus,
  X,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Loader2
} from 'lucide-react'

export default function Students() {
  const { teacherClasses, activeClassId, setActiveClassId, addStudentToClass } = useApp()
  const navigate = useNavigate()

  const [selectedClassId, setSelectedClassId] = useState(activeClassId || (teacherClasses[0]?.id || ''))
  const [students, setStudents] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  // Add Student modal and form state
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [modalClassId, setModalClassId] = useState('')
  const [studentName, setStudentName] = useState('')
  const [rollNo, setRollNo] = useState('')
  const [email, setEmail] = useState('')
  const [section, setSection] = useState('')
  const [confirmDuplicateName, setConfirmDuplicateName] = useState(false)
  const [savingStudent, setSavingStudent] = useState(false)
  const [formError, setFormError] = useState(null)
  const [nameWarning, setNameWarning] = useState(null)
  const [successToast, setSuccessToast] = useState(null)

  // Sync selectedClassId with activeClassId when classes change
  useEffect(() => {
    if (activeClassId && teacherClasses.some(c => c.id === activeClassId)) {
      setSelectedClassId(activeClassId)
    } else if (teacherClasses.length > 0 && !selectedClassId) {
      setSelectedClassId(teacherClasses[0].id)
    }
  }, [activeClassId, teacherClasses, selectedClassId])

  // Auto-dismiss success toast after 5 seconds
  useEffect(() => {
    if (successToast) {
      const timer = setTimeout(() => setSuccessToast(null), 5000)
      return () => clearTimeout(timer)
    }
  }, [successToast])

  useEffect(() => {
    async function loadStudents() {
      if (teacherClasses.length === 0) {
        setStudents([])
        setLoading(false)
        return
      }

      setLoading(true)
      try {
        const res = await api.getStudents(selectedClassId || undefined)
        if (res && res.success && Array.isArray(res.students)) {
          setStudents(res.students)
        } else {
          setStudents([])
        }
      } catch (err) {
        console.error('[Students] Error loading roster:', err)
        setStudents([])
      } finally {
        setLoading(false)
      }
    }
    loadStudents()
  }, [selectedClassId, teacherClasses.length])

  const handleClassChange = (newId) => {
    setSelectedClassId(newId)
    if (newId && newId !== 'all') {
      setActiveClassId(newId)
    }
  }

  const currentClass = teacherClasses.find(c => c.id === selectedClassId)

  const openAddModal = () => {
    const defaultClassId = selectedClassId && selectedClassId !== 'all'
      ? selectedClassId
      : (teacherClasses[0]?.id || '')
    const activeTarget = teacherClasses.find(c => c.id === defaultClassId)

    setModalClassId(defaultClassId)
    setStudentName('')
    setRollNo('')
    setEmail('')
    setSection(activeTarget?.section || '')
    setConfirmDuplicateName(false)
    setFormError(null)
    setNameWarning(null)
    setIsAddModalOpen(true)
  }

  const handleModalClassChange = (newClassId) => {
    setModalClassId(newClassId)
    const target = teacherClasses.find(c => c.id === newClassId)
    if (target?.section && !section) {
      setSection(target.section)
    }
    setFormError(null)
    setNameWarning(null)
    setConfirmDuplicateName(false)
  }

  const handleAddStudentSubmit = async (e) => {
    e.preventDefault()
    setFormError(null)

    const trimmedName = studentName.trim()
    const trimmedRoll = rollNo.trim()
    const trimmedEmail = email.trim()
    const trimmedSection = section.trim()

    // 1. Validate required name
    if (!trimmedName) {
      setFormError('Student name is required.')
      return
    }
    if (trimmedName.length < 2 || !/[a-zA-Z]/.test(trimmedName)) {
      setFormError('Student name must contain letters and be at least 2 characters long.')
      return
    }

    // 2. Validate class membership
    if (!modalClassId) {
      setFormError('Please select a target class for this student.')
      return
    }
    const targetClassObj = teacherClasses.find(c => c.id === modalClassId)
    if (!targetClassObj) {
      setFormError('Selected class was not found in your classes.')
      return
    }

    // 3. Validate optional email format
    if (trimmedEmail && !/^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(trimmedEmail)) {
      setFormError('Please enter a valid email address.')
      return
    }

    // 4. Duplicate checks within selected class
    const targetStudents = (modalClassId === selectedClassId ? students : targetClassObj.students) || []

    // Stable ID duplicate check
    if (trimmedRoll) {
      const normRoll = trimmedRoll.toLowerCase()
      const existingRollMatch = targetStudents.find(
        s => (s.rollNo || s.roll_number || '').trim().toLowerCase() === normRoll
      )
      if (existingRollMatch) {
        setFormError(`A student with Roll Number / ID "${trimmedRoll}" already exists in this class (${existingRollMatch.name}).`)
        return
      }
    }

    // Email duplicate check
    if (trimmedEmail) {
      const normEmail = trimmedEmail.toLowerCase()
      const existingEmailMatch = targetStudents.find(
        s => (s.email || '').trim().toLowerCase() === normEmail
      )
      if (existingEmailMatch) {
        setFormError(`A student with Email "${trimmedEmail}" already exists in this class (${existingEmailMatch.name}).`)
        return
      }
    }

    // Name-only duplicate check
    const normName = trimmedName.toLowerCase()
    const existingNameMatch = targetStudents.find(
      s => (s.name || '').trim().toLowerCase() === normName
    )
    if (existingNameMatch && !confirmDuplicateName) {
      const rollInfo = existingNameMatch.rollNo || existingNameMatch.roll_number ? ` (Roll: ${existingNameMatch.rollNo || existingNameMatch.roll_number})` : ''
      setNameWarning(`A student named "${trimmedName}"${rollInfo} is already enrolled in this class. If this is a different student, check the confirmation box below to proceed.`)
      return
    }

    // 5. Submit to backend
    setSavingStudent(true)
    try {
      const res = await api.addStudentToClass(modalClassId, {
        name: trimmedName,
        rollNo: trimmedRoll,
        email: trimmedEmail,
        section: trimmedSection,
        confirm_duplicate_name: confirmDuplicateName
      })

      if (res && res.success && res.student) {
        // Immediately update roster if currently viewing this class or all classes
        if (selectedClassId === modalClassId || selectedClassId === 'all') {
          setStudents(prev => [
            ...prev,
            {
              ...res.student,
              average: null,
              evaluations: 0,
              status: 'Not evaluated yet'
            }
          ])
        }

        // Update AppContext teacherClasses state
        if (typeof addStudentToClass === 'function') {
          addStudentToClass(modalClassId, res.student)
        }

        setSuccessToast(`Student "${res.student.name}" was successfully added to ${targetClassObj.name}.`)
        setIsAddModalOpen(false)
        setStudentName('')
        setRollNo('')
        setEmail('')
        setSection('')
        setConfirmDuplicateName(false)
        setFormError(null)
        setNameWarning(null)
      } else if (res && res.needs_confirmation) {
        setNameWarning(res.warning || `A student named "${trimmedName}" is already enrolled in this class. Confirm to proceed.`)
      } else {
        setFormError(res?.error || 'Failed to add student to class.')
      }
    } catch (err) {
      console.error('[Students] Error adding student:', err)
      const msg = err?.message || 'Server error occurred while adding student.'
      setFormError(msg)
    } finally {
      setSavingStudent(false)
    }
  }

  const filtered = students.filter(s => {
    const term = search.toLowerCase()
    return (
      (s.name && s.name.toLowerCase().includes(term)) ||
      (s.roll_number && s.roll_number.toLowerCase().includes(term)) ||
      (s.rollNo && s.rollNo.toLowerCase().includes(term)) ||
      (s.section && s.section.toLowerCase().includes(term)) ||
      (s.email && s.email.toLowerCase().includes(term))
    )
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <PageHead
          title="Students Directory"
          subtitle="Class roster performance tracking, evaluation counts, and academic standing."
        />

        {teacherClasses.length > 0 && (
          <div className="flex items-center gap-2">
            <Button
              id="header-add-student-btn"
              onClick={openAddModal}
              size="sm"
              className="font-bold flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <UserPlus size={15} />
              <span>Add Student</span>
            </Button>
            <Button
              onClick={() => navigate('/create-class')}
              size="sm"
              variant="secondary"
              className="font-bold flex items-center gap-1.5 cursor-pointer shadow-xs"
            >
              <Plus size={15} />
              <span>New Class / Roster</span>
            </Button>
          </div>
        )}
      </div>

      {/* Success Notification Banner */}
      {successToast && (
        <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-300 text-xs sm:text-sm font-semibold flex items-center justify-between gap-3 animate-in fade-in duration-200">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={17} className="text-emerald-400 shrink-0" />
            <span>{successToast}</span>
          </div>
          <button
            onClick={() => setSuccessToast(null)}
            className="text-emerald-400 hover:text-emerald-200 p-1 cursor-pointer transition-colors"
            title="Dismiss notification"
          >
            <X size={15} />
          </button>
        </div>
      )}

      {/* Class Selector Bar */}
      {teacherClasses.length > 0 && (
        <Card className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-[var(--surface)] border border-[var(--border)]">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center font-bold">
              {currentClass?.level === 'college' ? <GraduationCap size={20} /> : <School size={20} />}
            </div>
            <div>
              <div className="text-xs text-[var(--text-soft)] font-bold uppercase tracking-wider">Active Class Roster</div>
              <div className="text-sm font-extrabold text-[var(--text)]">
                {currentClass ? currentClass.name : 'All Classes Combined'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <label htmlFor="class-select-dropdown" className="text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
              Select Class:
            </label>
            <select
              id="class-select-dropdown"
              aria-label="Select class to view student roster"
              value={selectedClassId}
              onChange={(e) => handleClassChange(e.target.value)}
              className="p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-alt)] font-semibold text-xs sm:text-sm text-[var(--text)] outline-none focus:border-[var(--accent)] cursor-pointer"
            >
              {teacherClasses.map((cls) => (
                <option key={cls.id} value={cls.id}>
                  {cls.name} {cls.section ? `(Sec ${cls.section})` : ''} — {cls.students_count || cls.students?.length || 0} students
                </option>
              ))}
              {teacherClasses.length > 1 && (
                <option value="all">All Classes Combined</option>
              )}
            </select>
          </div>
        </Card>
      )}

      {/* Main Table or Empty States */}
      {teacherClasses.length === 0 ? (
        <Card className="p-12 text-center border-dashed border-2 bg-[var(--surface)] space-y-4">
          <Building size={48} className="mx-auto text-[var(--text-faint)]" />
          <div className="space-y-1.5">
            <h3 className="text-lg font-bold text-[var(--text)]">
              No Classes Created Yet
            </h3>
            <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto">
              Create your first class in the Teacher Portal and add students or import your roster to track evaluations and performance.
            </p>
          </div>
          <Button
            onClick={() => navigate('/create-class')}
            className="font-bold inline-flex items-center gap-2 mt-2"
          >
            <Plus size={16} />
            <span>Create Class & Roster</span>
          </Button>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden border border-[var(--border)] bg-[var(--surface)] shadow-xs">
          {/* Controls Bar: Search, Add Student Action, and Active Count */}
          <div className="flex items-center justify-between p-4 sm:p-5 border-b border-[var(--border)] flex-wrap gap-3">
            <div className="flex-1 min-w-[240px] max-w-md">
              <SearchBox
                placeholder="Search by student name, roll number, or section..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-3">
              <Button
                id="roster-add-student-btn"
                onClick={openAddModal}
                size="sm"
                className="font-bold flex items-center gap-1.5 cursor-pointer shadow-xs"
              >
                <UserPlus size={14} />
                <span>Add Student</span>
              </Button>
              <div className="text-xs text-[var(--text-faint)] font-bold whitespace-nowrap">
                Active Enrolled: <strong className="text-[var(--text)]">{filtered.length}</strong>
              </div>
            </div>
          </div>

          {loading ? (
            <div className="p-12 text-center text-sm font-semibold text-[var(--text-soft)]">
              Loading class roster...
            </div>
          ) : students.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <Users size={40} className="mx-auto text-[var(--text-faint)]" />
              <h4 className="text-base font-bold text-[var(--text)]">No Students Enrolled in this Class</h4>
              <p className="text-xs sm:text-sm text-[var(--text-soft)] max-w-md mx-auto">
                This class currently has no enrolled students. You can add individual students manually or import a roster file (.xlsx, .csv, .docx, .pdf).
              </p>
              <div className="flex items-center justify-center gap-2.5 pt-2 flex-wrap">
                <Button
                  id="empty-state-add-student-btn"
                  onClick={openAddModal}
                  size="sm"
                  className="font-bold inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <UserPlus size={14} />
                  <span>Add Student</span>
                </Button>
                <Button
                  onClick={() => navigate('/create-class')}
                  size="sm"
                  variant="secondary"
                  className="font-bold inline-flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  <Upload size={14} />
                  <span>Import Student Roster</span>
                </Button>
              </div>
            </div>
          ) : (
            <div className="overflow-x-auto scrollbar-thin">
              <table className="w-full min-w-[640px] border-collapse text-xs">
                <thead>
                  <tr className="bg-[var(--surface-alt)]">
                    {['Student Name', 'Roll / ID', 'Section', 'Average Score', 'Evaluations Count', 'Status'].map((h) => (
                      <th
                        key={h}
                        className="text-left text-xs text-[var(--text-faint)] font-bold uppercase tracking-wider py-3.5 px-4 border-b border-[var(--border)]"
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  {filtered.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="py-8 text-center text-[var(--text-soft)] font-medium">
                        No students matching &ldquo;{search}&rdquo;
                      </td>
                    </tr>
                  ) : (
                    filtered.map((s, i) => (
                      <tr key={s.id || i} className="hover:bg-[var(--surface-alt)] transition-colors">
                        <td className="py-4 px-4 font-bold text-sm text-[var(--text)]">
                          {s.name}
                        </td>
                        <td className="py-4 px-4 text-xs font-mono font-medium text-[var(--text-soft)]">
                          {s.rollNo || s.roll_number || '—'}
                        </td>
                        <td className="py-4 px-4 text-xs font-semibold text-[var(--text-soft)]">
                          {s.section || '—'}
                        </td>
                        <td className="py-4 px-4 font-extrabold text-sm text-[var(--accent)]">
                          {s.average !== null && s.average !== undefined ? `${s.average}%` : '—'}
                        </td>
                        <td className="py-4 px-4 text-xs text-[var(--text-soft)]">
                          {s.evaluations ?? 0} completed
                        </td>
                        <td className="py-4 px-4">
                          <Badge
                            tone={
                              s.status === 'On track'
                                ? 'success'
                                : s.status === 'Needs support'
                                ? 'warning'
                                : s.status === 'At risk'
                                ? 'error'
                                : 'neutral'
                            }
                          >
                            {s.status || 'Not evaluated yet'}
                          </Badge>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      {/* ── Compact "Add Student" Modal ────────────────────────────────────── */}
      {isAddModalOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="add-student-modal-title"
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 animate-in fade-in duration-150"
        >
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-2xl max-w-md w-full overflow-hidden flex flex-col max-h-[90vh]">
            {/* Modal Header */}
            <div className="p-4 sm:p-5 border-b border-[var(--border)] flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center font-bold">
                  <UserPlus size={18} />
                </div>
                <div>
                  <h3 id="add-student-modal-title" className="text-base font-extrabold text-[var(--text)]">
                    Add Student to Class
                  </h3>
                  <p className="text-xs text-[var(--text-soft)] font-medium">
                    Add an individual student directly into the class roster.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setIsAddModalOpen(false)}
                className="text-[var(--text-soft)] hover:text-[var(--text)] p-1.5 rounded-lg hover:bg-[var(--surface-alt)] cursor-pointer transition-colors"
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleAddStudentSubmit} className="p-4 sm:p-5 space-y-4 overflow-y-auto">
              {/* Target Class Selection */}
              <div className="space-y-1.5">
                <label htmlFor="modal-class-select" className="block text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
                  Target Class <span className="text-rose-500">*</span>
                </label>
                <select
                  id="modal-class-select"
                  value={modalClassId}
                  onChange={(e) => handleModalClassChange(e.target.value)}
                  className="w-full p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-alt)] text-sm font-semibold text-[var(--text)] outline-none focus:border-[var(--accent)]"
                >
                  {teacherClasses.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name} {c.section ? `(Sec ${c.section})` : ''}
                    </option>
                  ))}
                </select>
              </div>

              {/* Student Name (Required) */}
              <div className="space-y-1.5">
                <label htmlFor="modal-student-name" className="block text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
                  Student Full Name <span className="text-rose-500">*</span>
                </label>
                <input
                  id="modal-student-name"
                  type="text"
                  required
                  placeholder="e.g. Maya Lin, Aarav Patel"
                  value={studentName}
                  onChange={(e) => {
                    setStudentName(e.target.value)
                    setFormError(null)
                    setNameWarning(null)
                    setConfirmDuplicateName(false)
                  }}
                  className="w-full p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-alt)] text-sm font-semibold text-[var(--text)] outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)]"
                />
              </div>

              {/* Roll Number / Student ID / Register Number (Optional) */}
              <div className="space-y-1.5">
                <label htmlFor="modal-student-roll" className="block text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
                  Roll / Register / ID Number <span className="text-xs font-normal text-[var(--text-faint)] lowercase">(optional)</span>
                </label>
                <input
                  id="modal-student-roll"
                  type="text"
                  placeholder="e.g. 101, CS-2024-42, REG-908"
                  value={rollNo}
                  onChange={(e) => {
                    setRollNo(e.target.value)
                    setFormError(null)
                  }}
                  className="w-full p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-alt)] text-sm font-semibold text-[var(--text)] outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)] font-mono"
                />
              </div>

              {/* Section & Email Row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label htmlFor="modal-student-section" className="block text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
                    Section <span className="text-xs font-normal text-[var(--text-faint)] lowercase">(optional)</span>
                  </label>
                  <input
                    id="modal-student-section"
                    type="text"
                    placeholder="e.g. A, B, CS-1"
                    value={section}
                    onChange={(e) => setSection(e.target.value)}
                    className="w-full p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-alt)] text-sm font-semibold text-[var(--text)] outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label htmlFor="modal-student-email" className="block text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
                    Email Address <span className="text-xs font-normal text-[var(--text-faint)] lowercase">(optional)</span>
                  </label>
                  <input
                    id="modal-student-email"
                    type="email"
                    placeholder="e.g. student@school.edu"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value)
                      setFormError(null)
                    }}
                    className="w-full p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-alt)] text-sm font-semibold text-[var(--text)] outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)]"
                  />
                </div>
              </div>

              {/* Name Duplicate Warning Banner with confirmation checkbox */}
              {nameWarning && (
                <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl space-y-2 text-xs">
                  <div className="flex items-start gap-2 text-amber-300 font-semibold leading-relaxed">
                    <AlertTriangle size={16} className="text-amber-400 shrink-0 mt-0.5" />
                    <span>{nameWarning}</span>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer pt-1 text-amber-200 font-medium">
                    <input
                      id="confirm-duplicate-name-chk"
                      type="checkbox"
                      checked={confirmDuplicateName}
                      onChange={(e) => setConfirmDuplicateName(e.target.checked)}
                      className="rounded border-[var(--border)] text-[var(--accent)] focus:ring-[var(--accent)] cursor-pointer"
                    />
                    <span>Confirm this is a different student with the same name</span>
                  </label>
                </div>
              )}

              {/* Error Message Banner */}
              {formError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-300 text-xs font-semibold flex items-start gap-2">
                  <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Modal Actions */}
              <div className="pt-2 flex items-center justify-end gap-2.5 border-t border-[var(--border)]">
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsAddModalOpen(false)}
                  disabled={savingStudent}
                  className="font-bold cursor-pointer"
                >
                  Cancel
                </Button>
                <Button
                  id="modal-submit-add-student-btn"
                  type="submit"
                  size="sm"
                  disabled={savingStudent}
                  className="font-bold flex items-center gap-1.5 cursor-pointer shadow-xs"
                >
                  {savingStudent ? (
                    <>
                      <Loader2 size={14} className="animate-spin" />
                      <span>Saving Student...</span>
                    </>
                  ) : (
                    <>
                      <Plus size={14} />
                      <span>Add Student</span>
                    </>
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
