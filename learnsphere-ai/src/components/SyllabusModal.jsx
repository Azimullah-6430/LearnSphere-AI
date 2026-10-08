import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  UploadCloud, FileText, Sparkles, X, CheckCircle2, 
  AlertTriangle, AlertCircle, BookOpen, RefreshCw, ShieldAlert, Check,
  Layers, Award, Clock, FileCheck, ShieldCheck, ChevronDown, ChevronUp, 
  CheckSquare, FileSearch, ArrowRight, Loader2
} from 'lucide-react'
import { api } from '../services/api.js'
import { useApp } from '../context/AppContext.jsx'

/**
 * Valid Curriculum Processing States:
 * - NOT_UPLOADED: Initial state, file upload / text paste form visible
 * - UPLOADING: File payload received, upload confirmed
 * - PROCESSING: PDF text extraction, OCR verification, table detection
 * - VALIDATING: 13-point curriculum completeness & integrity validation
 * - READY: Backend confirmed curriculumStatus = VALID, curriculum retrieved once
 * - NEEDS_REVIEW: Incomplete, uncertain, or semester mismatch detected
 * - FAILED: Processing failed with actual error details and retry option
 */
export default function SyllabusModal({ isOpen, onClose }) {
  const { user, profile, studentProfile, setSyllabusData } = useApp()
  const navigate = useNavigate()
  
  const activeProfile = { ...user, ...profile, ...studentProfile }
  const isCollege = activeProfile.isCollege ?? (activeProfile.level === 'college')
  const activeSemester = activeProfile.semester ?? activeProfile.current_semester ?? activeProfile.currentSemester ?? null

  const [file, setFile] = useState(null)
  const [pastedText, setPastedText] = useState('')
  const [processState, setProcessState] = useState('NOT_UPLOADED')
  const [uploadInfo, setUploadInfo] = useState(null)
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
  const [error, setError] = useState('')
  const [overrideSuccess, setOverrideSuccess] = useState(false)
  const [showChecklist, setShowChecklist] = useState(false)
  const [selectedEvidenceIndex, setSelectedEvidenceIndex] = useState(null)

  const pollingRef = useRef(null)

  useEffect(() => {
    return () => {
      if (pollingRef.current) {
        clearTimeout(pollingRef.current)
      }
    }
  }, [])

  if (!isOpen) return null

  const handleResetForm = () => {
    if (pollingRef.current) clearTimeout(pollingRef.current)
    setFile(null)
    setPastedText('')
    setProcessState('NOT_UPLOADED')
    setUploadInfo(null)
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

    setError('')
    setOverrideSuccess(false)

    // Immediate Upload Confirmation
    const sourceName = file ? file.name : 'Pasted Syllabus Text'
    const sourceSize = file ? `${(file.size / 1024).toFixed(1)} KB` : `${pastedText.length} characters`
    setUploadInfo({ name: sourceName, size: sourceSize, time: new Date().toLocaleTimeString() })
    setProcessState('UPLOADING')

    // Invalidate old curriculum in app context
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

      // Invalidate existing curriculum state immediately upon new syllabus upload
      if (setSyllabusData) {
        setSyllabusData({ status: 'UPLOADING', curriculumStatus: 'UPLOADING', isValid: false, is_valid: false, subjects: [], topics: [] })
      }
      setProcessState('PROCESSING')

      let res = await api.analyzeSyllabus(formData)

      // Handle async background processing if queued
      if (res && res.success && res.status === 'PROCESSING' && res.syllabus_id) {
        setProcessState('PROCESSING')
        let attempts = 0
        const maxAttempts = 25
        while (attempts < maxAttempts && res.status === 'PROCESSING') {
          await new Promise(r => setTimeout(r, 1200))
          setProcessState(attempts > 3 ? 'VALIDATING' : 'PROCESSING')
          const poll = await api.getSyllabusStatus(res.syllabus_id)
          if (poll && poll.success && poll.status !== 'PROCESSING') {
            res = { ...res, ...poll, analysis: poll.analysis || poll.syllabus?.analysis || res.analysis }
            break
          }
          attempts++
        }
        if (attempts >= maxAttempts && res.status === 'PROCESSING') {
          throw new Error('Syllabus processing timed out. Please try uploading a cleaner PDF or smaller section.')
        }
      }

      if (res && res.success && (res.analysis || res.syllabus)) {
        setProcessState('VALIDATING')
        const analysisData = res.analysis || res.syllabus?.analysis || res.syllabus
        setResult(analysisData)
        setSyllabusId(res.syllabus_id || res.syllabus?.syllabus_id)
        
        const report = res.validation_report || res.validationReport || res.syllabus?.validation_report || null
        setValidationReport(report)
        const vStatus = (res.curriculumStatus || report?.status || res.validation_status || res.validationStatus || analysisData?.validation_status || 'VALID').toUpperCase()
        setValidationStatus(vStatus)
        setMismatchReason(report?.summary || res.mismatch_reason || analysisData?.mismatch_reason || '')
        setDetectedSemesters(res.detected_semesters || analysisData?.detected_semesters || [])
        setExplicitIdentifier(res.explicit_semester_identifier || analysisData?.explicit_semester_identifier || '')
        setExtractedSubjectCount(report?.subjects_detected || analysisData?.extracted_subject_count || (analysisData?.extracted_subjects || []).length)
        setExpectedSubjectCount(analysisData?.expected_subject_count || (analysisData?.extracted_subjects || []).length)
        setCompletenessVerified(report?.is_valid ?? analysisData?.completeness_verified ?? true)

        if (vStatus === 'VALID') {
          // Retrieve the saved curriculum ONCE from authoritative active curriculum endpoint
          const activeCur = await api.getActiveCurriculum()
          if (activeCur && activeCur.success && activeCur.is_valid) {
            setResult(activeCur)
            if (setSyllabusData) {
              setSyllabusData(activeCur)
            }
          } else if (setSyllabusData) {
            setSyllabusData(analysisData)
          }
          setProcessState('READY')
        } else {
          setProcessState('NEEDS_REVIEW')
          if (setSyllabusData) {
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
        }
      } else {
        setProcessState('FAILED')
        setError(res?.error || 'Failed to extract syllabus document. Please check the file and try again.')
      }
    } catch (err) {
      setProcessState('FAILED')
      setError(err?.message || 'Error occurred while processing syllabus document.')
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
        setProcessState('READY')
        const activeCur = await api.getActiveCurriculum()
        if (activeCur && activeCur.success && activeCur.is_valid) {
          setResult(activeCur)
          if (setSyllabusData) setSyllabusData(activeCur)
        } else if (setSyllabusData && result) {
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
              <h3 className="font-bold text-base">Syllabus & Curriculum Analyzer</h3>
              <p className="text-xs text-[var(--text-soft)]">Authoritative semester extraction, completeness verification & curriculum activation</p>
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

        {/* State 1: Upload Confirmation Banner (Shown immediately after submit) */}
        {uploadInfo && (processState === 'UPLOADING' || processState === 'PROCESSING' || processState === 'VALIDATING') && (
          <div className="mt-3.5 p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)]/30 text-xs flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileCheck size={16} className="text-[var(--accent)] shrink-0" />
              <div>
                <span className="font-bold text-[var(--text)]">Upload Confirmed: </span>
                <span className="font-mono text-[var(--accent)]">{uploadInfo.name}</span>
                <span className="text-[var(--text-soft)]"> ({uploadInfo.size})</span>
              </div>
            </div>
            <span className="text-[10.5px] font-mono text-[var(--text-faint)]">{uploadInfo.time}</span>
          </div>
        )}

        {/* State 2: Processing & Validating Indicators */}
        {(processState === 'UPLOADING' || processState === 'PROCESSING' || processState === 'VALIDATING') && (
          <div className="mt-4 p-6 rounded-xl bg-[var(--surface-alt)] border border-[var(--border-strong)] text-center space-y-3 animate-fadeIn">
            <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto animate-pulse">
              <Loader2 size={24} className="animate-spin" />
            </div>
            <div>
              <div className="font-extrabold text-sm text-[var(--text)]">
                {processState === 'UPLOADING' && 'Receiving & Storing Syllabus Payload...'}
                {processState === 'PROCESSING' && 'Extracting Academic Structure & Subject Tables...'}
                {processState === 'VALIDATING' && 'Running 13-Point Curriculum Completeness Validator...'}
              </div>
              <p className="text-xs text-[var(--text-soft)] mt-1">
                {processState === 'UPLOADING' && 'Creating cryptographic hash and initializing extraction stage.'}
                {processState === 'PROCESSING' && `Locating Semester ${activeSemester || ''} curriculum section and extracting theory & lab courses.`}
                {processState === 'VALIDATING' && 'Verifying source evidence, course codes, and integrity before activation.'}
              </p>
            </div>

            {/* Clear Step Status Indicator (No fake percentages) */}
            <div className="pt-2 flex items-center justify-center gap-4 text-[11px] font-bold text-[var(--text-soft)]">
              <div className={`flex items-center gap-1.5 ${processState !== 'UPLOADING' ? 'text-emerald-500' : 'text-[var(--accent)]'}`}>
                <CheckCircle2 size={13} />
                <span>Upload</span>
              </div>
              <span className="text-[var(--border-strong)]">&rarr;</span>
              <div className={`flex items-center gap-1.5 ${processState === 'VALIDATING' ? 'text-emerald-500' : processState === 'PROCESSING' ? 'text-[var(--accent)]' : 'opacity-40'}`}>
                <FileText size={13} />
                <span>Extract</span>
              </div>
              <span className="text-[var(--border-strong)]">&rarr;</span>
              <div className={`flex items-center gap-1.5 ${processState === 'VALIDATING' ? 'text-[var(--accent)]' : 'opacity-40'}`}>
                <ShieldCheck size={13} />
                <span>Validate</span>
              </div>
            </div>
          </div>
        )}

        {/* State 3: Failure State */}
        {processState === 'FAILED' && error && (
          <div className="mt-4 p-4 bg-red-500/10 border border-red-500/30 text-xs text-red-500 rounded-xl space-y-2.5 animate-fadeIn">
            <div className="flex items-start gap-2.5">
              <AlertTriangle size={18} className="shrink-0 mt-0.5" />
              <div>
                <strong className="font-bold block text-[13px]">Extraction Failed</strong>
                <p className="mt-0.5 leading-relaxed text-red-600 dark:text-red-400">{error}</p>
              </div>
            </div>
            <div className="pt-1 flex justify-end">
              <button
                type="button"
                onClick={handleResetForm}
                className="px-3.5 py-1.5 bg-red-600 text-white rounded-lg text-xs font-bold hover:bg-red-700 flex items-center gap-1.5 shadow-xs"
              >
                <RefreshCw size={13} /> Retry Upload
              </button>
            </div>
          </div>
        )}

        {/* State 4: NOT_UPLOADED Form */}
        {processState === 'NOT_UPLOADED' && (
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
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] flex items-center gap-2 shadow-sm"
              >
                <Sparkles size={15} />
                Extract & Validate Curriculum
              </button>
            </div>
          </form>
        )}

        {/* State 5 & 6: READY or NEEDS_REVIEW (Only displays subjects once backend confirms validation) */}
        {(processState === 'READY' || processState === 'NEEDS_REVIEW') && result && (
          <div className="mt-4 space-y-4 animate-fadeIn">
            
            {/* Needs Review State Banner */}
            {processState === 'NEEDS_REVIEW' && !overrideSuccess && (
              <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-xs space-y-2">
                <div className="flex items-start gap-2.5">
                  <AlertCircle size={20} className="text-amber-500 shrink-0 mt-0.5" />
                  <div>
                    <strong className="font-extrabold text-[13px] block text-amber-600 dark:text-amber-400">
                      Curriculum Completeness Review Required — Not Activated
                    </strong>
                    <p className="mt-1 leading-relaxed">
                      {mismatchReason || `Missing subjects or uncertain extractions detected. Incomplete curriculum is not exposed to learning features.`}
                    </p>
                    {detectedSemesters.length > 0 && (
                      <div className="mt-1 text-[11px] font-mono text-amber-700 dark:text-amber-300">
                        Detected in document: Semester {detectedSemesters.join(', ')}
                      </div>
                    )}
                  </div>
                </div>

                <div className="pt-2 flex items-center gap-2 flex-wrap border-t border-amber-500/20">
                  <button
                    onClick={handleConfirmOverride}
                    disabled={confirming}
                    className="px-3.5 py-1.5 bg-amber-600 text-white rounded-lg text-xs font-bold hover:bg-amber-700 flex items-center gap-1.5 shadow-xs"
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

            {/* READY State Banner */}
            {(processState === 'READY' || overrideSuccess) && (
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
                  {extractedSubjectCount || (result.subjects || []).length} Subjects Verified
                </div>
              </div>
            )}

            {/* Summary Highlights Card */}
            <div className="bg-[var(--surface-alt)] p-4 rounded-xl text-xs space-y-3 border border-[var(--border-strong)] shadow-xs">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
                <div className="flex items-center gap-2">
                  <ShieldCheck size={18} className="text-[var(--accent)]" />
                  <div>
                    <span className="font-bold text-[12px] text-[var(--text)]">Curriculum Completeness & Integrity Summary</span>
                    <span className="text-[10.5px] text-[var(--text-faint)] block">Authoritative extraction derived from uploaded syllabus</span>
                  </div>
                </div>
                <span className={`px-2.5 py-1 rounded-md text-[11px] font-mono font-bold ${
                  (processState === 'READY' || overrideSuccess)
                    ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30'
                    : 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30'
                }`}>
                  Curriculum Status: {overrideSuccess ? 'VALID' : validationStatus}
                </span>
              </div>

              {/* Verified Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 font-mono text-[11.5px]">
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Semester</div>
                  <div className="font-extrabold text-[var(--text)] text-sm">Semester {validationReport?.semester ?? activeSemester ?? 'N/A'}</div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Total Subjects</div>
                  <div className="font-extrabold text-[var(--accent)] text-sm">{extractedSubjectCount || (result.subjects || []).length}</div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Theory Courses</div>
                  <div className="font-extrabold text-[var(--text)] text-sm">{validationReport?.course_types_breakdown?.theory ?? (result.subjects || []).filter(s => !(s.type||s.name||'').toLowerCase().includes('lab')).length}</div>
                </div>
                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-[10px] uppercase font-sans text-[var(--text-faint)]">Laboratories</div>
                  <div className="font-extrabold text-emerald-600 dark:text-emerald-400 text-sm">{validationReport?.course_types_breakdown?.lab ?? (result.subjects || []).filter(s => (s.type||s.name||'').toLowerCase().includes('lab')).length}</div>
                </div>
              </div>

              {/* Collapsible 13-Point Checklist */}
              {validationReport?.checks && validationReport.checks.length > 0 && (
                <div className="pt-2 border-t border-[var(--border)]">
                  <button
                    type="button"
                    onClick={() => setShowChecklist(!showChecklist)}
                    className="w-full flex items-center justify-between text-[11px] font-bold text-[var(--accent)] hover:underline py-1"
                  >
                    <span className="flex items-center gap-1.5">
                      <CheckSquare size={13} />
                      Completeness Verification Checklist ({validationReport.checks.filter(c => c.passed).length}/{validationReport.checks.length} Passed)
                    </span>
                    {showChecklist ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </button>

                  {showChecklist && (
                    <div className="mt-2 space-y-1.5 max-h-[200px] overflow-y-auto pr-1">
                      {validationReport.checks.map((chk, idx) => (
                        <div key={idx} className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] flex items-start gap-2 text-[11px]">
                          {chk.passed ? (
                            <CheckCircle2 size={14} className="text-emerald-500 shrink-0 mt-0.5" />
                          ) : (
                            <AlertTriangle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                          )}
                          <div className="flex-1 min-w-0">
                            <div className="font-bold text-[var(--text)] flex items-center justify-between">
                              <span>{chk.number || idx + 1}. {chk.name}</span>
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

            {/* Extracted Validated Course Inventory List */}
            <div className="bg-[var(--surface-alt)] p-4 rounded-xl text-xs space-y-3.5 border border-[var(--border)]">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
                <div>
                  <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block text-[10.5px]">Curriculum Title</span>
                  <div className="font-bold text-sm text-[var(--accent)]">{result.course_title || result.program || activeProfile.degree || 'Semester Course Blueprint'}</div>
                </div>
                <div className="text-right">
                  <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block text-[10.5px]">Total Verified</span>
                  <span className="font-black text-xs text-[var(--text)]">{extractedSubjectCount || (result.subjects || []).length} Subjects</span>
                </div>
              </div>

              {/* Subject Detailed Grid / List */}
              <div>
                <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block mb-2 text-[11px]">
                  Verified Subjects & Course Codes {isCollege ? `(Semester ${activeSemester || ''})` : ''}
                </span>

                {result.subjects && result.subjects.length > 0 ? (
                  <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1">
                    {result.subjects.map((sub, i) => {
                      const isExpanded = selectedEvidenceIndex === i
                      const sName = sub.name || sub.subjectName
                      const sCode = sub.code || sub.subjectCode
                      const sType = sub.type || sub.courseType || sub.category || 'Theory Core'
                      return (
                        <div key={i} className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] transition-all shadow-xs">
                          <div className="flex items-start justify-between gap-2">
                            <div className="space-y-1 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                {sCode && (
                                  <span className="px-1.5 py-0.5 bg-[var(--accent-soft)] text-[var(--accent)] rounded font-mono text-[10.5px] font-bold">
                                    {sCode}
                                  </span>
                                )}
                                <span className="font-bold text-[12.5px] text-[var(--text)]">{sName}</span>
                              </div>
                              <div className="text-[11px] text-[var(--text-soft)] flex items-center gap-3 flex-wrap">
                                <span>{sType}</span>
                                {sub.credits !== null && sub.credits !== undefined && (
                                  <span>&bull; {sub.credits} Credits</span>
                                )}
                              </div>
                            </div>
                            
                            {(sub.source_text || sub.sourceText || sub.source_section || sub.sourceSection) && (
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
                            )}
                          </div>

                          {/* Evidence Drawer */}
                          {isExpanded && (
                            <div className="mt-2.5 pt-2.5 border-t border-[var(--border)] bg-[var(--surface-alt)]/60 -mx-3 -mb-3 p-3 rounded-b-xl space-y-2 text-[11px] animate-fadeIn">
                              <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-[var(--text-faint)]">
                                <span className="flex items-center gap-1 text-[var(--accent)]">
                                  <ShieldCheck size={13} />
                                  Authoritative Syllabus Evidence
                                </span>
                                <span className="text-emerald-600 dark:text-emerald-400 font-mono">
                                  Verified Evidence
                                </span>
                              </div>

                              <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] font-mono text-[11px] text-[var(--text)]">
                                <div className="text-[10px] text-[var(--text-faint)] font-sans uppercase font-bold">Document Provenance</div>
                                <div className="mt-0.5 flex items-center gap-2 flex-wrap">
                                  <span className="font-bold text-[var(--accent)]">
                                    📄 {sub.source_document_name || uploadInfo?.name || file?.name || 'Syllabus Document'}
                                  </span>
                                  <span>&rarr;</span>
                                  <span className="px-1.5 py-0.5 bg-[var(--surface-alt)] rounded text-[10px]">
                                    Page {sub.source_page_numbers ? sub.source_page_numbers.join(', ') : (sub.sourcePages ? sub.sourcePages.join(', ') : (sub.source_page || 1))}
                                  </span>
                                  <span>&rarr;</span>
                                  <span className="text-[var(--text-soft)]">{sub.source_section || sub.sourceSection || 'Scheme Table'}</span>
                                </div>
                              </div>

                              {(sub.source_text || sub.sourceText) && (
                                <div className="p-2 rounded-lg bg-[var(--surface)] border border-[var(--border)]">
                                  <div className="text-[10px] text-[var(--text-faint)] font-sans uppercase font-bold">Exact Document Excerpt</div>
                                  <p className="mt-0.5 font-mono text-[10.5px] text-[var(--text-soft)] italic bg-[var(--surface-alt)] p-1.5 rounded">
                                    &ldquo;{sub.source_text || sub.sourceText}&rdquo;
                                  </p>
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
            </div>

            <div className="pt-2 flex justify-between items-center">
              <button
                type="button"
                onClick={handleResetForm}
                className="text-xs font-semibold text-[var(--text-soft)] hover:text-[var(--text)]"
              >
                ← Upload Another Syllabus
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
