import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'
import { Card, Badge, Button } from '../components/ui/Primitives.jsx'
import { api } from '../services/api.js'
import {
  Building,
  School,
  GraduationCap,
  Plus,
  ArrowRight,
  CheckCircle2,
  Users,
  Upload,
  Sparkles,
  Trash2,
  LogOut,
  FileSpreadsheet,
  FileText,
  AlertTriangle,
  FileUp,
  X,
  Edit2,
  Check,
  RefreshCw,
  Info
} from 'lucide-react'

export default function CreateClassPage() {
  const {
    user,
    teacherClasses,
    addClass,
    deleteClass,
    activeClassId,
    setActiveClassId,
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

  // Student Roster Section State
  const [rosterTab, setRosterTab] = useState('file') // 'file' | 'manual'
  const [selectedFile, setSelectedFile] = useState(null)
  const [manualText, setManualText] = useState('')
  const [isParsing, setIsParsing] = useState(false)
  const [parseError, setParseError] = useState('')
  
  // Extracted Roster Review State
  const [extractedRoster, setExtractedRoster] = useState(null) // Array of students
  const [detectedFields, setDetectedFields] = useState([])
  const [duplicateWarnings, setDuplicateWarnings] = useState([])
  const [isLowConfidence, setIsLowConfidence] = useState(false)
  const [lowConfidenceReason, setLowConfidenceReason] = useState('')
  const [reviewConfirmed, setReviewConfirmed] = useState(false)

  const [toast, setToast] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const fileInputRef = useRef(null)

  const showToastMsg = (msg) => {
    setToast(msg)
    setTimeout(() => setToast(''), 4000)
  }

  // Handle File Upload and Parse
  const handleFileChange = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    setParseError('')
    setSelectedFile(file)

    const ext = '.' + file.name.split('.').pop().toLowerCase()
    const allowed = ['.xlsx', '.xls', '.csv', '.tsv', '.txt', '.docx', '.pdf']
    if (!allowed.includes(ext)) {
      setParseError(`Unsupported file format '${ext}'. Please upload an Excel, CSV, Word, or PDF file.`)
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      setParseError(`File size exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB).`)
      return
    }

    await parseFile(file)
  }

  const parseFile = async (file) => {
    setIsParsing(true)
    setParseError('')
    try {
      const res = await api.parseRosterFile(file)
      if (res && res.success && Array.isArray(res.students)) {
        setExtractedRoster(res.students)
        setDetectedFields(res.detected_fields || [])
        setDuplicateWarnings(res.duplicates || [])
        setIsLowConfidence(Boolean(res.low_confidence))
        setLowConfidenceReason(res.low_confidence_reason || '')
        setReviewConfirmed(false)
        showToastMsg(`Successfully extracted ${res.students.length} student${res.students.length === 1 ? '' : 's'} from ${file.name}. Review list below.`)
      } else {
        setParseError(res?.error || 'Failed to parse student list from file.')
      }
    } catch (err) {
      console.error('[CreateClass] Error parsing file:', err)
      setParseError(err.message || 'Error uploading and analyzing file.')
    } finally {
      setIsParsing(false)
    }
  }

  const handleManualParse = async () => {
    if (!manualText.trim()) {
      setParseError('Please enter or paste student names.')
      return
    }

    setIsParsing(true)
    setParseError('')
    try {
      const res = await api.parseRosterText(manualText)
      if (res && res.success && Array.isArray(res.students)) {
        setExtractedRoster(res.students)
        setDetectedFields(res.detected_fields || [])
        setDuplicateWarnings(res.duplicates || [])
        setIsLowConfidence(Boolean(res.low_confidence))
        setLowConfidenceReason(res.low_confidence_reason || '')
        setReviewConfirmed(false)
        showToastMsg(`Parsed ${res.students.length} student${res.students.length === 1 ? '' : 's'} from text. Review below.`)
      } else {
        setParseError(res?.error || 'Failed to parse student roster text.')
      }
    } catch (err) {
      console.error('[CreateClass] Error parsing manual text:', err)
      setParseError(err.message || 'Error analyzing student text.')
    } finally {
      setIsParsing(false)
    }
  }

  // Row Manipulation in Review Screen
  const handleUpdateStudentRow = (index, field, value) => {
    if (!extractedRoster) return
    const updated = [...extractedRoster]
    updated[index] = { ...updated[index], [field]: value }
    setExtractedRoster(updated)
  }

  const handleRemoveStudentRow = (index) => {
    if (!extractedRoster) return
    const updated = extractedRoster.filter((_, i) => i !== index)
    setExtractedRoster(updated)
  }

  const handleAddStudentRow = () => {
    const newStudent = {
      id: `manual_std_${Date.now()}`,
      name: '',
      rollNo: '',
      email: '',
      section: isSchool ? section : collegeSection,
      order: (extractedRoster ? extractedRoster.length : 0) + 1
    }
    setExtractedRoster(extractedRoster ? [...extractedRoster, newStudent] : [newStudent])
  }

  const handleClearRoster = () => {
    setExtractedRoster(null)
    setDetectedFields([])
    setDuplicateWarnings([])
    setIsLowConfidence(false)
    setLowConfidenceReason('')
    setSelectedFile(null)
    setManualText('')
    setReviewConfirmed(false)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Class Submission
  const handleCreateClass = async (e) => {
    e.preventDefault()

    // Validate class details
    if (isSchool && !schoolClassName.trim()) {
      showToastMsg('Please enter a class name.')
      return
    }
    if (!isSchool && !collegeDept.trim()) {
      showToastMsg('Please enter a department name.')
      return
    }

    // Filter valid students from review screen if available
    let finalizedStudents = []
    if (extractedRoster && extractedRoster.length > 0) {
      finalizedStudents = extractedRoster
        .map((st, idx) => ({
          id: st.id || `std_${Date.now()}_${idx}`,
          name: (st.name || '').trim(),
          rollNo: (st.rollNo || st.roll_number || '').trim(),
          roll_number: (st.rollNo || st.roll_number || '').trim(),
          email: (st.email || '').trim(),
          section: (st.section || (isSchool ? section : collegeSection) || '').trim(),
          order: idx + 1,
          marksHistory: st.marksHistory || []
        }))
        .filter(st => st.name.length > 0)
    }

    setIsSubmitting(true)
    try {
      let created = null
      if (isSchool) {
        const subs = schoolSubjects.split(',').map((s) => s.trim()).filter(Boolean)
        created = addClass({
          level: 'school',
          name: schoolClassName.trim(),
          type: 'School Class',
          board,
          gradeLevel,
          section,
          subjects: subs.length > 0 ? subs : ['Mathematics', 'Science'],
          students_count: finalizedStudents.length,
          students: finalizedStudents
        })
      } else {
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
          students_count: finalizedStudents.length,
          students: finalizedStudents
        })
      }

      if (created) {
        setActiveClassId(created.id)
        showToastMsg(`${isSchool ? 'Class' : 'Department'} "${created.name}" created with ${finalizedStudents.length} students!`)
        setSchoolClassName('')
        setCollegeDept('')
        handleClearRoster()

        setTimeout(() => {
          navigate('/app/dashboard')
        }, 600)
      }
    } catch (err) {
      console.error('[CreateClass] Error saving class:', err)
      showToastMsg('Failed to save class: ' + (err.message || 'Unknown error'))
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleEnterPortal = (clsId) => {
    setActiveClassId(clsId)
    navigate('/app/dashboard')
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
      <main className="flex-1 w-full min-w-0 p-6 md:p-10 space-y-8">
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
              Organize isolated class sections, define subject syllabi, and import your student roster via Excel, CSV, Word, PDF, or manual entry.
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
        <Card className="p-7 md:p-8 space-y-7 border border-[var(--border)] bg-[var(--surface)] shadow-sm">
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
                  ? 'Define class name, education board, grade level, section, and optional student roster.'
                  : 'Define department name, semester, section batch, and optional student roster.'}
              </p>
            </div>
            <Badge tone="accent">
              {isSchool ? 'School Educator Setup' : 'College Professor Setup'}
            </Badge>
          </div>

          <form onSubmit={handleCreateClass} className="space-y-7">
            {/* Form Fields: School vs College */}
            {isSchool ? (
              <div className="space-y-4">
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Class Name *</label>
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
                    <label className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2">Department Name *</label>
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

            {/* OPTIONAL STUDENT-LIST UPLOAD & MANUAL ENTRY SECTION */}
            <div className="pt-2 border-t border-[var(--border)]">
              <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
                <div>
                  <h3 className="text-base font-extrabold text-[var(--text)] flex items-center gap-2">
                    <Users size={18} className="text-[var(--accent)]" />
                    <span>Optional Student Roster Upload</span>
                  </h3>
                  <p className="text-xs text-[var(--text-soft)] mt-0.5">
                    Upload an Excel, CSV, Word, or PDF student list, or enter names manually. Extracted rows are reviewed before saving.
                  </p>
                </div>

                {/* Tab Switcher */}
                <div className="flex items-center bg-[var(--surface-alt)] p-1 rounded-xl border border-[var(--border)]">
                  <button
                    type="button"
                    onClick={() => { setRosterTab('file'); setParseError('') }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      rosterTab === 'file'
                        ? 'bg-[var(--surface)] text-[var(--accent)] shadow-xs'
                        : 'text-[var(--text-soft)] hover:text-[var(--text)]'
                    }`}
                  >
                    File Upload
                  </button>
                  <button
                    type="button"
                    onClick={() => { setRosterTab('manual'); setParseError('') }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      rosterTab === 'manual'
                        ? 'bg-[var(--surface)] text-[var(--accent)] shadow-xs'
                        : 'text-[var(--text-soft)] hover:text-[var(--text)]'
                    }`}
                  >
                    Manual Entry
                  </button>
                </div>
              </div>

              {parseError && (
                <div className="p-3.5 mb-4 rounded-xl bg-[var(--error-soft)] border border-[var(--error)]/30 text-[var(--error)] text-xs font-semibold flex items-center gap-2">
                  <AlertTriangle size={16} className="shrink-0" />
                  <span>{parseError}</span>
                </div>
              )}

              {rosterTab === 'file' ? (
                /* File Upload Dropzone */
                <div className="space-y-3">
                  <div
                    onClick={() => fileInputRef.current?.click()}
                    className="p-6 rounded-2xl border-2 border-dashed border-[var(--border-strong)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/50 hover:bg-[var(--accent-soft)]/20 transition-all text-center cursor-pointer flex flex-col items-center justify-center gap-3"
                  >
                    <input
                      type="file"
                      ref={fileInputRef}
                      onChange={handleFileChange}
                      accept=".xlsx,.xls,.csv,.tsv,.txt,.docx,.pdf"
                      className="hidden"
                      id="roster-file-picker"
                      aria-label="Upload student roster file"
                    />

                    <div className="w-12 h-12 rounded-2xl bg-[var(--surface)] border border-[var(--border)] flex items-center justify-center text-[var(--accent)] shadow-xs">
                      <FileUp size={24} />
                    </div>

                    <div>
                      <div className="text-sm font-bold text-[var(--text)]">
                        {selectedFile ? selectedFile.name : 'Click to upload or drag & drop student list'}
                      </div>
                      <div className="text-xs text-[var(--text-soft)] mt-1 font-medium">
                        Supports Excel (.xlsx, .xls), CSV (.csv), Word (.docx), and PDF (.pdf) • Max 10MB
                      </div>
                    </div>

                    {isParsing && (
                      <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent)] pt-1">
                        <RefreshCw size={14} className="animate-spin" />
                        <span>Extracting student names and identifiers...</span>
                      </div>
                    )}
                  </div>

                  {selectedFile && !isParsing && (
                    <div className="flex items-center justify-between text-xs px-3 py-2 bg-[var(--surface)] rounded-xl border border-[var(--border)]">
                      <span className="font-semibold text-[var(--text)] truncate max-w-sm">
                        📄 {selectedFile.name} ({(selectedFile.size / 1024).toFixed(1)} KB)
                      </span>
                      <button
                        type="button"
                        onClick={() => parseFile(selectedFile)}
                        className="text-[var(--accent)] font-bold hover:underline cursor-pointer flex items-center gap-1"
                      >
                        <RefreshCw size={12} />
                        <span>Re-analyze</span>
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                /* Manual Entry Tab */
                <div className="space-y-3">
                  <textarea
                    rows={4}
                    value={manualText}
                    onChange={(e) => setManualText(e.target.value)}
                    placeholder={
                      isSchool
                        ? "Paste roster list, for example:\n1. John Doe (Roll: 101)\n2. Priya Sharma (Roll: 102)\nOr CSV format: Roll No, Student Name, Email"
                        : "Paste student roster list, for example:\nREG-201, Alex Johnson, alex@university.edu\nREG-202, Brenda Vance, brenda@university.edu"
                    }
                    className="w-full p-3.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-sm font-mono text-[var(--text)] outline-none focus:border-[var(--accent)] transition-all"
                  />
                  <div className="flex justify-end">
                    <Button
                      type="button"
                      size="sm"
                      onClick={handleManualParse}
                      disabled={isParsing || !manualText.trim()}
                      className="font-bold flex items-center gap-1.5"
                    >
                      {isParsing ? <RefreshCw size={14} className="animate-spin" /> : <Sparkles size={14} />}
                      <span>Extract Students from Text</span>
                    </Button>
                  </div>
                </div>
              )}

              {/* REVIEW SCREEN BEFORE SAVING */}
              {extractedRoster && extractedRoster.length > 0 && (
                <div className="mt-6 p-5 rounded-2xl bg-[var(--surface)] border border-[var(--border)] space-y-4 shadow-sm">
                  {/* Review Header & Summary */}
                  <div className="flex items-center justify-between flex-wrap gap-3 pb-3 border-b border-[var(--border)]">
                    <div className="space-y-0.5">
                      <div className="text-sm font-extrabold text-[var(--text)] flex items-center gap-2">
                        <CheckCircle2 size={16} className="text-[var(--accent)]" />
                        <span>Roster Review Screen</span>
                        <span className="text-xs bg-[var(--accent-soft)] text-[var(--accent)] px-2 py-0.5 rounded-full font-bold">
                          {extractedRoster.length} Extracted
                        </span>
                      </div>
                      <div className="text-xs text-[var(--text-soft)]">
                        Verify names, roll numbers, and details before saving. You can edit cells, remove entries, or add rows.
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={handleAddStudentRow}
                        className="px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--surface-hover)] text-xs font-bold text-[var(--accent)] flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <Plus size={13} />
                        <span>Add Row</span>
                      </button>
                      <button
                        type="button"
                        onClick={handleClearRoster}
                        className="px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--error-soft)] text-xs font-bold text-[var(--error)] flex items-center gap-1 cursor-pointer transition-colors"
                      >
                        <X size={13} />
                        <span>Discard Roster</span>
                      </button>
                    </div>
                  </div>

                  {/* Detected Fields Badges */}
                  <div className="flex items-center gap-2 flex-wrap text-xs">
                    <span className="font-bold text-[var(--text-soft)]">Detected Fields:</span>
                    {detectedFields.map((fld) => (
                      <span key={fld} className="px-2 py-0.5 rounded-md bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] font-semibold uppercase text-[10px] tracking-wider">
                        {fld === 'rollNo' ? 'Roll / Register No' : fld}
                      </span>
                    ))}
                  </div>

                  {/* LOW CONFIDENCE / SCANNED DOCUMENT WARNING */}
                  {isLowConfidence && (
                    <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs space-y-1">
                      <div className="font-bold flex items-center gap-1.5">
                        <AlertTriangle size={15} className="text-amber-600 dark:text-amber-400" />
                        <span>Low Confidence Scan / Document Review Needed</span>
                      </div>
                      <p className="text-[11px] leading-relaxed opacity-90">
                        {lowConfidenceReason || 'Some characters or layout structures in this document scan were unclear. Please check and correct student names and identifiers in the table below before confirming.'}
                      </p>
                    </div>
                  )}

                  {/* DUPLICATE IDENTIFIER WARNINGS */}
                  {duplicateWarnings && duplicateWarnings.length > 0 && (
                    <div className="p-3.5 rounded-xl bg-[var(--error-soft)] border border-[var(--error)]/30 text-[var(--error)] text-xs space-y-1">
                      <div className="font-bold flex items-center gap-1.5">
                        <AlertTriangle size={15} />
                        <span>Duplicate Entries Detected ({duplicateWarnings.length})</span>
                      </div>
                      <div className="text-[11px] space-y-0.5">
                        {duplicateWarnings.slice(0, 3).map((w, wIdx) => (
                          <div key={wIdx}>• Row {w.row_index}: &ldquo;{w.name}&rdquo; shares identifier with Row {w.matches_row}</div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Editable Review Table */}
                  <div className="overflow-x-auto max-h-72 overflow-y-auto border border-[var(--border)] rounded-xl scrollbar-thin">
                    <table className="w-full text-xs border-collapse">
                      <thead className="sticky top-0 bg-[var(--surface-alt)] z-10">
                        <tr>
                          <th className="py-2.5 px-3 text-left font-bold text-[var(--text-soft)] uppercase tracking-wider w-12">#</th>
                          <th className="py-2.5 px-3 text-left font-bold text-[var(--text-soft)] uppercase tracking-wider">Student Name *</th>
                          <th className="py-2.5 px-3 text-left font-bold text-[var(--text-soft)] uppercase tracking-wider">Roll / Register No</th>
                          <th className="py-2.5 px-3 text-left font-bold text-[var(--text-soft)] uppercase tracking-wider">Email (Optional)</th>
                          <th className="py-2.5 px-3 text-left font-bold text-[var(--text-soft)] uppercase tracking-wider">Section</th>
                          <th className="py-2.5 px-3 text-center font-bold text-[var(--text-soft)] uppercase tracking-wider w-14">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[var(--border)] bg-[var(--surface)]">
                        {extractedRoster.map((st, idx) => (
                          <tr key={st.id || idx} className="hover:bg-[var(--surface-alt)]/50 transition-colors">
                            <td className="py-2 px-3 text-[var(--text-soft)] font-mono text-[11px]">
                              {idx + 1}
                            </td>
                            <td className="py-2 px-3">
                              <input
                                type="text"
                                value={st.name || ''}
                                onChange={(e) => handleUpdateStudentRow(idx, 'name', e.target.value)}
                                placeholder="Full Name"
                                className={`w-full p-1.5 rounded-lg border font-semibold text-xs outline-none bg-[var(--surface)] ${
                                  !st.name?.trim() ? 'border-[var(--error)] bg-[var(--error-soft)]/20' : 'border-[var(--border)] focus:border-[var(--accent)]'
                                }`}
                              />
                            </td>
                            <td className="py-2 px-3">
                              <input
                                type="text"
                                value={st.rollNo || st.roll_number || ''}
                                onChange={(e) => handleUpdateStudentRow(idx, 'rollNo', e.target.value)}
                                placeholder="Optional"
                                className="w-full p-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] font-mono text-xs outline-none focus:border-[var(--accent)]"
                              />
                            </td>
                            <td className="py-2 px-3">
                              <input
                                type="email"
                                value={st.email || ''}
                                onChange={(e) => handleUpdateStudentRow(idx, 'email', e.target.value)}
                                placeholder="student@example.com"
                                className="w-full p-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-xs outline-none focus:border-[var(--accent)]"
                              />
                            </td>
                            <td className="py-2 px-3">
                              <input
                                type="text"
                                value={st.section || ''}
                                onChange={(e) => handleUpdateStudentRow(idx, 'section', e.target.value)}
                                placeholder="Sec"
                                className="w-20 p-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-xs outline-none focus:border-[var(--accent)]"
                              />
                            </td>
                            <td className="py-2 px-3 text-center">
                              <button
                                type="button"
                                onClick={() => handleRemoveStudentRow(idx)}
                                className="p-1 rounded-md text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors cursor-pointer"
                                title="Remove row"
                                aria-label={`Remove row ${idx + 1}`}
                              >
                                <Trash2 size={14} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  <div className="flex items-center justify-between text-xs text-[var(--text-soft)] pt-1">
                    <span>
                      ✓ Roster will be confirmed and linked when class is created.
                    </span>
                    <span className="font-semibold text-[var(--accent)]">
                      {extractedRoster.filter(s => s.name?.trim()).length} valid rows
                    </span>
                  </div>
                </div>
              )}
            </div>

            {/* Submit Action */}
            <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between flex-wrap gap-4">
              <div className="text-xs text-[var(--text-soft)]">
                {extractedRoster && extractedRoster.length > 0 ? (
                  <span>
                    Ready to attach <strong>{extractedRoster.filter(s => s.name?.trim()).length}</strong> student roster entries.
                  </span>
                ) : (
                  <span>You can create this class now and import or add students later.</span>
                )}
              </div>

              <Button
                type="submit"
                size="lg"
                disabled={isSubmitting}
                className="w-full md:w-auto font-bold flex items-center justify-center gap-2 shadow-sm cursor-pointer"
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" />
                    <span>Saving Class...</span>
                  </>
                ) : (
                  <>
                    <Plus size={18} />
                    <span>
                      {extractedRoster && extractedRoster.length > 0
                        ? `Create Class & Confirm Roster (${extractedRoster.filter(s => s.name?.trim()).length})`
                        : isSchool
                        ? 'Create School Class'
                        : 'Create College Department'}
                    </span>
                  </>
                )}
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
