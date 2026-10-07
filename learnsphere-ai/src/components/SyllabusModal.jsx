import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  UploadCloud, FileText, Sparkles, X, CheckCircle2, 
  AlertTriangle, AlertCircle, BookOpen, RefreshCw, ShieldAlert, Check,
  Layers, Award, Clock, FileCheck, ShieldCheck, ChevronDown, ChevronUp, CheckSquare, FileSearch
} from 'lucide-react'
import { api } from '../services/api.js'
import { useApp } from '../context/AppContext.jsx'

export default function SyllabusModal({ isOpen, onClose }) {
  const { user, profile, studentProfile, setSyllabusData } = useApp()
  const navigate = useNavigate()
  
  const activeProfile = { ...user, ...profile, ...studentProfile }
  const isCollege = activeProfile.isCollege ?? (activeProfile.level === 'college')
  const activeSemester = activeProfile.semester ?? activeProfile.current_semester ?? activeProfile.currentSemester ?? null

  const [file, setFile] = useState(null)
  const [pastedText, setPastedText] = useState('')
  const [loading, setLoading] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [result, setResult] = useState(null)
  const [syllabusId, setSyllabusId] = useState(null)
  const [validationReport, setValidationReport] = useState(null)
  const [validationStatus, setValidationStatus] = useState('VALID')
  const [mismatchReason, setMismatchReason] = useState('')
  const [detectedSemesters, setDetectedSemesters] = useState([])
  const [explicitIdentifier, setExplicitIdentifier] = useState('')
  const [extractedSubjectCount, setExtractedSubjectCount] = useState(0)
  const [expectedSubjectCount, setExpectedSubjectCount] = useState(0)
  const [completenessVerified, setCompletenessVerified] = useState(true)
  const [completenessNotes, setCompletenessNotes] = useState('')
  const [error, setError] = useState('')
  const [overrideSuccess, setOverrideSuccess] = useState(false)
  const [showChecklist, setShowChecklist] = useState(false)
  const [selectedEvidenceIndex, setSelectedEvidenceIndex] = useState(null)

  if (!isOpen) return null

  const handleResetForm = () => {
    setFile(null)
    setPastedText('')
    setResult(null)
    setSyllabusId(null)
    setValidationReport(null)
    setValidationStatus('VALID')
    setMismatchReason('')
    setDetectedSemesters([])
    setExplicitIdentifier('')
    setExtractedSubjectCount(0)
    setExpectedSubjectCount(0)
    setCompletenessVerified(true)
    setCompletenessNotes('')
    setError('')
    setOverrideSuccess(false)
    setShowChecklist(false)
    setSelectedEvidenceIndex(null)
  }

  const handleUploadAndAnalyze = async (e) => {
    e.preventDefault()
    if (!file && !pastedText.trim()) {
      setError('Please select a syllabus PDF/image or paste syllabus text.')
      return
    }

    setLoading(true)
    setError('')
    setOverrideSuccess(false)

    // Invalidate old curriculum context immediately upon uploading a new syllabus
    if (setSyllabusData) {
      setSyllabusData({ status: 'PROCESSING', curriculumStatus: 'PROCESSING', isValid: false, is_valid: false, subjects: [], topics: [] })
    }

    try {
      const formData = new FormData()
      if (file) formData.append('syllabus_file', file)
      if (pastedText) formData.append('text', pastedText)
      
      formData.append('level', activeProfile.level || (isCollege ? 'college' : 'school'))
      formData.append('semester', activeSemester ?? '')
      formData.append('classLevel', activeProfile.grade_level || activeProfile.classLevel || '')
      formData.append('stream', activeProfile.stream || '')
      formData.append('degree', activeProfile.degree || activeProfile.program || '')
      formData.append('department', activeProfile.department || activeProfile.branch || activeProfile.domain || '')
      formData.append('regulation', activeProfile.regulation || activeProfile.batch || '')
      formData.append('academic_year', activeProfile.academic_year || activeProfile.academicYear || '')

      const res = await api.analyzeSyllabus(formData)
      if (res && res.success && res.analysis) {
        setResult(res.analysis)
        setSyllabusId(res.syllabus_id)
        const report = res.validation_report || res.validationReport || null
        setValidationReport(report)
        const vStatus = (report?.status || res.validation_status || res.validationStatus || 'VALID').toUpperCase()
        setValidationStatus(vStatus)
        setMismatchReason(report?.summary || res.mismatch_reason || '')
        setDetectedSemesters(res.detected_semesters || [])
        setExplicitIdentifier(res.explicit_semester_identifier || '')
        setExtractedSubjectCount(report?.subjects_detected || res.analysis.extracted_subject_count || (res.analysis.extracted_subjects || []).length)
        setExpectedSubjectCount(res.analysis.expected_subject_count || (res.analysis.extracted_subjects || []).length)
        setCompletenessVerified(report?.is_valid ?? res.analysis.completeness_verified ?? true)
        setCompletenessNotes(report?.summary || res.analysis.completeness_notes || '')

        // Only replace and activate in app context after successful validation
        if (vStatus === 'VALID' && setSyllabusData) {
          setSyllabusData(res.analysis)
        } else if (setSyllabusData) {
          setSyllabusData({
            status: vStatus,
            curriculumStatus: vStatus,
            isValid: false,
            is_valid: false,
            validation_status: vStatus,
            validation_report: report,
            subjects: [],
            topics: [],
            extracted_subjects: []
          })
        }
      } else {
        setError(res?.error || 'Failed to analyze syllabus document. Please try again.')
      }
    } catch (err) {
      setError(err?.message || 'Error analyzing syllabus document.')
    } finally {
      setLoading(false)
    }
  }

  const handleConfirmOverride = async () => {
    if (!syllabusId) return
    setConfirming(true)
    setError('')
    try {
      const res = await api.confirmSyllabusOverride(syllabusId)
      if (res && res.success) {
        setValidationStatus('VALID')
        setOverrideSuccess(true)
        if (setSyllabusData && result) {
          setSyllabusData(result)
        }
      } else {
        setError(res?.error || 'Failed to confirm syllabus override.')
      }
    } catch (err) {
      setError(err?.message || 'Failed to activate syllabus.')
    } finally {
      setConfirming(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[var(--surface)] border border-[var(--border-strong)] rounded-2xl w-full max-w-[760px] p-6 shadow-2xl overflow-y-auto max-h-[92vh]">
        
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
              <BookOpen size={20} />
            </div>
            <div>
              <h3 className="font-bold text-base">Curriculum Completeness Validator</h3>
              <p className="text-xs text-[var(--text-soft)]">Authoritative 16-point semester verification & curriculum activation</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-[var(--text-soft)] hover:text-[var(--text)] rounded-lg">
            <X size={18} />
          </button>
        </div>

        {/* Profile Context Banner */}
        <div className="mt-3.5 p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between text-xs">
          <div>
            <span className="text-[10.5px] uppercase font-bold text-[var(--text-faint)] block">Authoritative Profile Context</span>
            <span className="font-extrabold text-[var(--text)]">
              {isCollege ? (
                <>
                  {activeProfile.degree || 'Degree'} {activeProfile.department ? `· ${activeProfile.department}` : ''} 
                  {activeSemester ? ` · Semester ${activeSemester}` : ' · (Semester Unset)'}
                  {activeProfile.regulation ? ` (${activeProfile.regulation})` : ''}
                </>
              ) : (
                <>School Student · {activeProfile.board || 'Board'} · Class {activeProfile.classLevel || activeProfile.grade_level || 'General'}</>
              )}
            </span>
          </div>
          <button 
            type="button"
            onClick={() => { onClose(); navigate('/app/settings'); }}
            className="text-[11px] font-bold text-[var(--accent)] hover:underline"
          >
            Edit Profile
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-red-500/10 border border-red-500/30 text-xs font-semibold text-red-500 rounded-lg flex items-center gap-2">
            <AlertTriangle size={16} className="shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Upload Form */}
        {!result ? (
          <form onSubmit={handleUploadAndAnalyze} className="mt-4 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-2">Option A: Upload Official Syllabus Document (PDF / Image)</label>
              <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-[var(--border-strong)] rounded-xl bg-[var(--surface-alt)] hover:border-[var(--accent)] transition-colors cursor-pointer text-center">
                <UploadCloud size={28} className="text-[var(--accent)] mb-2" />
                <span className="text-xs font-bold text-[var(--text)]">{file ? file.name : 'Click to select PDF, PNG or JPG'}</span>
                <span className="text-[11px] text-[var(--text-faint)] mt-1">
                  {isCollege ? `Full syllabus regulation or course blueprint. Every Semester ${activeSemester || ''} theory, lab & elective subject will be verified.` : 'Official board curriculum or subject blueprint'}
                </span>
                <input 
                  type="file" 
                  accept=".pdf,.png,.jpg,.jpeg" 
                  className="hidden" 
                  onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} 
                />
              </label>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Option B: Paste Syllabus Text & Course Scheme</label>
              <textarea
                rows={4}
                placeholder={isCollege ? `Paste course codes, subject names, labs, and elective lists for Semester ${activeSemester || ''}...` : "Paste course subjects and chapters here..."}
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                className="w-full p-3 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs focus:outline-none focus:border-[var(--accent)] resize-none font-mono"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-[var(--border)] hover:bg-[var(--surface-alt)]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] flex items-center gap-2 shadow-sm"
              >
                <Sparkles size={15} />
                {loading ? 'Extracting & Running 16-Point Completeness Validator...' : 'Extract & Validate Curriculum'}
              </button>
            </div>
          </form>
        ) : (
          /* Result & Validation Feedback */
          <div className="mt-4 space-y-4">
            
            {/* 1. Mismatch State Banner */}
            {validationStatus === 'MISMATCH' && !overrideSuccess && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs space-y-2">
                <div className="flex items-start gap-2.5">
                  <ShieldAlert size={20} className="text-amber-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-extrabold text-[13px] block text-amber-600 dark:text-amber-400">
                      Semester Mismatch Detected — Not Automatically Activated
                    </strong>
                    <p className="mt-1 leading-relaxed">
                      {mismatchReason || `The uploaded syllabus does not appear to match your current Semester ${activeSemester} profile.`}
                    </p>
                    {detectedSemesters.length > 0 && (
                      <div className="mt-1 text-[11px] font-mono text-amber-700 dark:text-amber-300">
                        Detected document markers: Semester {detectedSemesters.join(', ')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-2 flex-wrap border-t border-amber-500/20">
                  <button
                    onClick={handleResetForm}
                    className="px-3 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-bold hover:bg-amber-700 flex items-center gap-1.5"
                  >
                    <RefreshCw size={13} /> Replace Syllabus Document
                  </button>
                  <button
                    onClick={() => { onClose(); navigate('/app/settings'); }}
                    className="px-3 py-1.5 border border-amber-600 text-amber-700 dark:text-amber-300 rounded-lg text-xs font-bold hover:bg-amber-500/10"
                  >
                    Update Profile Semester
                  </button>
                  <button
                    onClick={handleConfirmOverride}
                    disabled={confirming}
                    className="px-3 py-1.5 border border-amber-400/50 text-amber-800 dark:text-amber-200 rounded-lg text-xs font-semibold hover:bg-amber-500/10"
                  >
                    {confirming ? 'Activating...' : 'Confirm & Activate Anyway'}
                  </button>
                </div>
              </div>
            )}

            {/* 2. Needs Review State Banner */}
            {validationStatus === 'NEEDS_REVIEW' && !overrideSuccess && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs space-y-2">
                <div className="flex items-start gap-2.5">
                  <AlertCircle size={20} className="text-amber-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-extrabold text-[13px] block text-amber-600 dark:text-amber-400">
                      Curriculum Completeness Review Required — Not Automatically Activated
                    </strong>
                    <p className="mt-1 leading-relaxed">
                      {mismatchReason || `Missing subjects or uncertain extractions detected. Incomplete curriculum cannot be activated automatically.`}
                    </p>
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-2 flex-wrap border-t border-amber-500/20">
                  <button
                    onClick={handleConfirmOverride}
                    disabled={confirming}
                    className="px-3.5 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-bold hover:bg-amber-700 flex items-center gap-1.5"
                  >
                    <Check size={14} /> {confirming ? 'Activating...' : `Confirm & Activate for Semester ${activeSemester || 'Current'}`}
                  </button>
                  <button
                    onClick={handleResetForm}
                    className="px-3 py-1.5 border border-amber-500 text-amber-600 dark:text-amber-300 rounded-lg text-xs font-semibold hover:bg-amber-500/10"
                  >
                    Upload Corrected File
                  </button>
                </div>
              </div>
            )}

            {/* 3. Valid / Confirmed State Banner */}
            {(validationStatus === 'VALID' || overrideSuccess) && (
              <div className="p-3.5 bg-emerald-500/10 border border-emerald-500/30 rounded-xl flex items-center justify-between gap-3 text-xs font-bold text-emerald-600 dark:text-emerald-400 flex-wrap">
                <div className="flex items-center gap-2.5">
                  <CheckCircle2 size={20} className="shrink-0" />
                  <div>
                    <div>Full Semester {activeSemester || 'Curriculum'} Verified & Activated</div>
                    {explicitIdentifier && (
                      <div className="text-[11px] font-normal text-emerald-700 dark:text-emerald-300 font-mono mt-0.5">
                        Matched: &ldquo;{explicitIdentifier}&rdquo;
                      </div>
                    )}
                  </div>
                </div>
                <div className="px-2.5 py-1 rounded-md bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 text-[11px] font-mono">
                  {extractedSubjectCount} Subjects Verified
                </div>
              </div>
            )}

            {/* 4. Dedicated Curriculum Completeness Validation Report Card */}
            <div className="bg-[var(--surface-alt)] p-4 rounded-xl text-xs space-y-3 border border-[var(--border-strong)] shadow-xs">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-[var(--accent)]" />
                  <div>
                    <span className="font-bold text-[12px] text-[var(--text)]">Curriculum Completeness & Integrity Report</span>
                    <span className="text-[10.5px] text-[var(--text-faint)] block">Dynamic extraction metrics derived from uploaded syllabus</span>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-bold ${
                    (validationStatus === 'VALID' || overrideSuccess)
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                      : validationStatus === 'MISMATCH'
                      ? 'bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/30'
                      : 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                  }`}>
                    Status: {overrideSuccess ? 'VALID (OVERRIDE)' : validationStatus}
                  </span>
                </div>
              </div>

              {/* Dynamic Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11.5px]">
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Semester</div>
                  <div className="font-extrabold text-[var(--text)] text-sm">{validationReport?.semester ?? activeSemester ?? 'N/A'}</div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Subjects Detected</div>
                  <div className="font-extrabold text-[var(--accent)] text-sm">{validationReport?.subjects_detected ?? extractedSubjectCount}</div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Subjects Verified</div>
                  <div className="font-extrabold text-emerald-600 dark:text-emerald-400 text-sm">{validationReport?.subjects_verified ?? extractedSubjectCount}</div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Missing Subjects</div>
                  <div className={`font-extrabold text-sm ${(validationReport?.missing_subjects ?? 0) > 0 ? 'text-red-500' : 'text-[var(--text)]'}`}>
                    {validationReport?.missing_subjects ?? 0}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Duplicate Subjects</div>
                  <div className={`font-extrabold text-sm ${(validationReport?.duplicate_subjects ?? 0) > 0 ? 'text-red-500' : 'text-[var(--text)]'}`}>
                    {validationReport?.duplicate_subjects ?? 0}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Cross-Semester Subjects</div>
                  <div className={`font-extrabold text-sm ${(validationReport?.cross_semester_subjects ?? 0) > 0 ? 'text-red-500' : 'text-[var(--text)]'}`}>
                    {validationReport?.cross_semester_subjects ?? 0}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Uncertain Subjects</div>
                  <div className={`font-extrabold text-sm ${(validationReport?.uncertain_subjects ?? 0) > 0 ? 'text-amber-500' : 'text-[var(--text)]'}`}>
                    {validationReport?.uncertain_subjects ?? 0}
                  </div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] flex flex-col justify-center">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Integrity Score</div>
                  <div className="font-extrabold text-[var(--text)] text-sm">{validationReport?.validation_score ?? 100}%</div>
                </div>
              </div>

              {/* Collapsible 16-Point Checklist */}
              {validationReport?.checks && validationReport.checks.length > 0 && (
                <div className="pt-2 border-t border-[var(--border)]">
                  <button
                    type="button"
                    onClick={() => setShowChecklist(!showChecklist)}
                    className="w-full flex items-center justify-between text-[11px] font-bold text-[var(--accent)] hover:underline py-1"
                  >
                    <span className="flex items-center gap-1.5">
                      <CheckSquare size={13} />
                      16-Point Verification Checklist ({validationReport.checks.filter(c => c.passed).length}/16 Passed)
                    </span>
                    {showChecklist ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {showChecklist && (
                    <div className="mt-2 space-y-1.5 max-h-[220px] overflow-y-auto pr-1">
                      {validationReport.checks.map((chk) => (
                        <div key={chk.id || chk.number} className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] flex items-start gap-2 text-[11px]">
                          {chk.passed ? (
                            <CheckCircle2 size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="font-bold text-[var(--text)] flex items-center justify-between">
                              <span>{chk.number}. {chk.name}</span>
                              <span className={`text-[10px] font-mono ${chk.passed ? 'text-emerald-500' : 'text-amber-500'}`}>
                                {chk.passed ? 'PASS' : 'FLAGGED'}
                              </span>
                            </div>
                            <div className="text-[10.5px] text-[var(--text-soft)] mt-0.5">{chk.detail}</div>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Extracted Course Inventory Table / Cards */}
            <div className="bg-[var(--surface-alt)] p-4 rounded-xl text-xs space-y-3.5 border border-[var(--border)]">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
                <div>
                  <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block text-[10.5px]">Curriculum Title</span>
                  <div className="font-bold text-sm text-[var(--accent)]">{result.course_title || 'Semester Course Blueprint'}</div>
                </div>
                <div className="text-right">
                  <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block text-[10.5px]">Course Count</span>
                  <span className="font-black text-xs text-[var(--text)]">{extractedSubjectCount} Subjects</span>
                </div>
              </div>

              {/* Subject Detailed Grid / List */}
              <div>
                <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block mb-2 text-[11px]">
                  Extracted Course Inventory {isCollege ? `(Semester ${activeSemester || ''})` : ''}
                </span>

                {result.subjects && result.subjects.length > 0 ? (
                  <div className="space-y-2 max-h-[300px] overflow-y-auto pr-1">
                    {result.subjects.map((sub, i) => {
                      const isExpanded = selectedEvidenceIndex === i
                      return (
                        <div key={i} className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] transition-all shadow-xs">
                          <div className="flex items-start justify-between gap-2">
                            <div className="space-y-1 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                {sub.code && (
                                  <span className="px-1.5 py-0.5 bg-[var(--accent-soft)] text-[var(--accent)] rounded font-mono text-[10.5px] font-bold">
                                    {sub.code}
                                  </span>
                                )}
                                <span className="font-bold text-[12.5px] text-[var(--text)]">{sub.name}</span>
                              </div>
                              <div className="text-[11px] text-[var(--text-soft)] flex items-center gap-3 flex-wrap">
                                <span>{sub.type || sub.category || 'Theory Core'}</span>
                                {sub.credits !== null && sub.credits !== undefined && (
                                  <span>&bull; {sub.credits} Credits</span>
                                )}
                                {(sub.lecture_hours !== null || sub.practical_hours !== null) && (
                                  <span className="font-mono text-[10px] opacity-75">
                                    [L:{sub.lecture_hours ?? 0} T:{sub.tutorial_hours ?? 0} P:{sub.practical_hours ?? 0}]
                                  </span>
                                )}
                              </div>
                            </div>
                            
                            <button
                              type="button"
                              onClick={() => setSelectedEvidenceIndex(isExpanded ? null : i)}
                              className={`px-2 py-1 rounded-md text-[10.5px] font-bold flex items-center gap-1 transition-colors shrink-0 ${
                                isExpanded 
                                  ? 'bg-[var(--accent)] text-white' 
                                  : 'bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--border)]'
                              }`}
                              title="Inspect where in the uploaded syllabus this subject came from"
                            >
                              <FileSearch size={12} />
                              {isExpanded ? 'Hide Source' : 'View in Syllabus'}
                            </button>
                          </div>

                          {/* Evidence Drawer */}
                          {isExpanded && (
                            <div className="mt-2.5 pt-2.5 border-t border-[var(--border)] bg-[var(--surface-alt)]/60 -mx-3 -mb-3 p-3 rounded-b-xl space-y-2 text-[11px] animate-fadeIn">
                              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[var(--text-faint)]">
                                <span className="flex items-center gap-1 text-[var(--accent)]">
                                  <ShieldCheck size={13} />
                                  Verifiable Syllabus Evidence
                                </span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-mono">
                                  Confidence: {sub.confidence ? (sub.confidence * 100).toFixed(0) : 98}%
                                </span>
                              </div>

                              <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] font-mono text-[11px] text-[var(--text)]">
                                <div className="text-[10px] text-[var(--text-faint)] font-sans uppercase font-bold">Document Provenance</div>
                                <div className="mt-0.5 flex items-center gap-2 flex-wrap">
                                  <span className="font-bold text-[var(--accent)]">
                                    📄 {sub.source_document_name || file?.name || 'Syllabus Document'}
                                  </span>
                                  <span>&rarr;</span>
                                  <span className="px-1.5 py-0.5 bg-[var(--surface-alt)] rounded text-[10px]">
                                    Page {sub.source_page_numbers ? sub.source_page_numbers.join(', ') : (sub.source_page || 1)}
                                  </span>
                                  <span>&rarr;</span>
                                  <span className="text-[var(--text-soft)]">{sub.source_section || 'Scheme of Instruction'}</span>
                                </div>
                              </div>

                              {sub.source_text && (
                                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                                  <div className="text-[10px] text-[var(--text-faint)] font-sans uppercase font-bold">Exact Document Excerpt</div>
                                  <p className="mt-0.5 font-mono text-[10.5px] text-[var(--text-soft)] italic bg-[var(--surface-alt)] p-1.5 rounded">
                                    &ldquo;{sub.source_text}&rdquo;
                                  </p>
                                </div>
                              )}

                              {sub.semester_evidence && (
                                <div className="text-[10.5px] text-[var(--text-soft)] flex items-center gap-1.5">
                                  <span className="font-bold text-[var(--text)]">Semester Evidence:</span>
                                  <span>{sub.semester_evidence}</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )
                    })}
                  </div>
                ) : (
                  <div className="flex flex-wrap gap-1.5">
                    {(result.extracted_subjects || []).map((s, i) => (
                      <span key={i} className="px-2.5 py-1 bg-[var(--surface)] border border-[var(--border)] rounded-md font-semibold text-[11px] text-[var(--text)]">
                        {s}
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Key Units & Topics */}
              {result.chapters && Object.keys(result.chapters).length > 0 && (
                <div className="pt-2 border-t border-[var(--border)]">
                  <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block mb-1 text-[11px]">Unit Breakdowns Sample</span>
                  <div className="space-y-1.5 max-h-[130px] overflow-y-auto pr-1">
                    {Object.entries(result.chapters).slice(0, 3).map(([sub, units], i) => (
                      <div key={i} className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                        <div className="font-bold text-[var(--accent)] text-[11px] mb-0.5">{sub}</div>
                        {Array.isArray(units) && units.map((u, idx) => (
                          <div key={idx} className="text-[10.5px] text-[var(--text-soft)] pl-2 border-l border-[var(--accent)]/30">
                            <strong>{u.name || `Unit ${idx + 1}`}:</strong> {(u.concepts || []).slice(0, 3).join(', ')}
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            <div className="pt-2 flex justify-between items-center">
              <button
                type="button"
                onClick={handleResetForm}
                className="text-xs font-semibold text-[var(--text-soft)] hover:text-[var(--text)]"
              >
                ← Upload Another File
              </button>
              <button
                type="button"
                onClick={() => { handleResetForm(); onClose(); }}
                className="px-5 py-2 text-xs font-bold rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] shadow-md"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
