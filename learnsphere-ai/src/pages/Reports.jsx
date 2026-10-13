import { useState, useEffect, useMemo } from 'react'
import { Card, PageHead, Button, Badge } from '../components/ui/Primitives.jsx'
import { api } from '../services/api.js'
import {
  FileText,
  Download,
  Loader2,
  Trash2,
  Users,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Award,
  BookOpen,
  Filter,
  RefreshCw,
  Printer,
  ChevronDown,
  ChevronRight,
  Info
} from 'lucide-react'

export default function Reports() {
  const [activeTab, setActiveTab] = useState('class') // 'class' | 'individual'
  const [classes, setClasses] = useState([])
  const [selectedClassId, setSelectedClassId] = useState('')
  const [selectedAssessment, setSelectedAssessment] = useState('')
  
  // Class report state
  const [classReport, setClassReport] = useState(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [reportError, setReportError] = useState(null)
  
  // Individual evaluations state
  const [individualReports, setIndividualReports] = useState([])
  const [loadingIndividual, setLoadingIndividual] = useState(false)
  const [expandedStudent, setExpandedStudent] = useState(null)

  // Load teacher's authorized classes
  useEffect(() => {
    const fetchClasses = async () => {
      try {
        const res = await api.getTeacherClasses()
        if (res && res.success && Array.isArray(res.classes)) {
          setClasses(res.classes)
          if (res.classes.length > 0) {
            setSelectedClassId(String(res.classes[0].id || res.classes[0]._id))
          }
        }
      } catch (err) {
        console.error('Failed to load teacher classes:', err)
      }
    }
    fetchClasses()
  }, [])

  // Load class report when selectedClassId or selectedAssessment changes
  const loadClassReport = async (classId, assessmentFilter = '') => {
    if (!classId) return
    setLoadingReport(true)
    setReportError(null)
    try {
      const res = await api.getClassReport(classId, assessmentFilter || null)
      if (res && res.success && res.report) {
        setClassReport(res.report)
      } else {
        setReportError(res?.error || 'Failed to generate class report.')
        setClassReport(null)
      }
    } catch (err) {
      console.error('Class report fetch error:', err)
      setReportError(err?.message || 'Server connection error.')
      setClassReport(null)
    } finally {
      setLoadingReport(false)
    }
  }

  useEffect(() => {
    if (selectedClassId && activeTab === 'class') {
      loadClassReport(selectedClassId, selectedAssessment)
    }
  }, [selectedClassId, selectedAssessment, activeTab])

  // Load individual evaluations list
  const loadIndividualReports = async () => {
    setLoadingIndividual(true)
    try {
      const res = await api.getEvaluations()
      if (res && res.success && Array.isArray(res.evaluations)) {
        setIndividualReports(res.evaluations)
      } else {
        setIndividualReports([])
      }
    } catch (err) {
      console.error('Failed to load evaluation reports:', err)
      setIndividualReports([])
    } finally {
      setLoadingIndividual(false)
    }
  }

  useEffect(() => {
    if (activeTab === 'individual') {
      loadIndividualReports()
    }
  }, [activeTab])

  const handleDownloadClassPdf = () => {
    if (!selectedClassId) return
    api.downloadClassReportPdf(selectedClassId, selectedAssessment || null)
  }

  const handlePrint = () => {
    window.print()
  }

  const handleDownloadIndividual = (evalId) => {
    api.downloadEvaluationPdf(evalId)
  }

  const handleDeleteIndividual = async (evalId, e) => {
    if (e) e.stopPropagation()
    if (!evalId) return
    if (!window.confirm("Are you sure you want to delete this evaluation report?")) {
      return
    }
    const targetId = String(evalId)
    try {
      await api.deleteEvaluation(targetId)
      setIndividualReports(prev => prev.filter(r => String(r.id || r._id) !== targetId))
      // Also refresh class report if in sync
      if (selectedClassId) {
        loadClassReport(selectedClassId, selectedAssessment)
      }
    } catch (err) {
      console.error('Delete error:', err)
    }
  }

  return (
    <div className="space-y-6 w-full min-w-0 pb-12 print:p-0 print:space-y-4">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 print:hidden">
        <PageHead
          title="Academic Reports"
          subtitle="Evidence-based class performance summaries derived from verified evaluations and class membership."
        />
        
        {/* Tab switcher */}
        <div className="flex items-center gap-1.5 p-1 bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl self-start sm:self-auto">
          <button
            onClick={() => setActiveTab('class')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'class'
                ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs border border-[var(--border)]'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            Class Academic Report
          </button>
          <button
            onClick={() => setActiveTab('individual')}
            className={`px-3.5 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              activeTab === 'individual'
                ? 'bg-[var(--surface)] text-[var(--text)] shadow-xs border border-[var(--border)]'
                : 'text-[var(--text-soft)] hover:text-[var(--text)]'
            }`}
          >
            Individual Transcripts
          </button>
        </div>
      </div>

      {activeTab === 'class' ? (
        <div className="space-y-6">
          {/* Controls Bar */}
          <Card className="p-4 print:hidden">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="flex flex-wrap items-center gap-3">
                {/* Class selector */}
                <div className="flex items-center gap-2">
                  <label htmlFor="class-select" className="text-xs font-bold text-[var(--text-soft)] flex items-center gap-1.5">
                    <Users size={14} /> Class:
                  </label>
                  <select
                    id="class-select"
                    value={selectedClassId}
                    onChange={(e) => {
                      setSelectedClassId(e.target.value)
                      setSelectedAssessment('')
                    }}
                    className="text-xs font-semibold bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl px-3 py-1.5 text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                  >
                    {classes.length === 0 ? (
                      <option value="">No classes found</option>
                    ) : (
                      classes.map((c) => (
                        <option key={c.id || c._id} value={c.id || c._id}>
                          {c.name || c.grade_level || 'Untitled Class'} {c.section ? `(${c.section})` : ''}
                        </option>
                      ))
                    )}
                  </select>
                </div>

                {/* Assessment filter */}
                {classReport?.assessment_titles?.length > 1 && (
                  <div className="flex items-center gap-2">
                    <label htmlFor="assessment-filter" className="text-xs font-bold text-[var(--text-soft)] flex items-center gap-1.5">
                      <Filter size={14} /> Assessment:
                    </label>
                    <select
                      id="assessment-filter"
                      value={selectedAssessment}
                      onChange={(e) => setSelectedAssessment(e.target.value)}
                      className="text-xs font-semibold bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl px-3 py-1.5 text-[var(--text)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                    >
                      <option value="">All Assessments ({classReport.assessment_titles.length})</option>
                      {classReport.assessment_titles.map((t) => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                )}

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => loadClassReport(selectedClassId, selectedAssessment)}
                  disabled={loadingReport}
                  title="Refresh report"
                >
                  <RefreshCw size={13} className={loadingReport ? 'animate-spin' : ''} />
                  <span className="hidden sm:inline">Refresh</span>
                </Button>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={handlePrint}
                  disabled={!classReport || classReport.status === 'no_evaluations'}
                >
                  <Printer size={14} className="mr-1.5" /> Print View
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleDownloadClassPdf}
                  disabled={!classReport || classReport.status === 'no_evaluations'}
                >
                  <Download size={14} className="mr-1.5" /> Export PDF
                </Button>
              </div>
            </div>
          </Card>

          {/* Loading or Error states */}
          {loadingReport ? (
            <Card className="p-12 text-center text-[var(--text-soft)]">
              <Loader2 className="animate-spin mx-auto mb-3 text-[var(--accent)]" size={32} />
              <h4 className="text-sm font-bold text-[var(--text)]">Deriving Class Academic Report...</h4>
              <p className="text-xs text-[var(--text-soft)] mt-1">
                Aggregating completed teacher evaluations, question-level scores, and roster coverage.
              </p>
            </Card>
          ) : reportError ? (
            <Card className="p-8 text-center border-[var(--error)]/30 bg-[var(--error-soft)]/20">
              <AlertCircle size={36} className="text-[var(--error)] mx-auto mb-2" />
              <h4 className="text-sm font-bold text-[var(--error)]">Unable to load report</h4>
              <p className="text-xs text-[var(--text-soft)] mt-1">{reportError}</p>
            </Card>
          ) : !classReport ? (
            <Card className="p-10 text-center border-dashed border-2">
              <Users size={36} className="text-[var(--text-faint)] mx-auto mb-2" />
              <h4 className="text-sm font-bold text-[var(--text)]">Select a class to generate report</h4>
              <p className="text-xs text-[var(--text-soft)] mt-1">
                Reports are generated automatically from real evaluations of enrolled students.
              </p>
            </Card>
          ) : classReport.status === 'no_evaluations' ? (
            <Card className="p-10 text-center border-dashed border-2">
              <FileText size={40} className="text-[var(--text-faint)] mx-auto mb-3" />
              <h3 className="text-base font-bold text-[var(--text)] mb-1">
                No Completed Evaluations Found for {classReport.class_name}
              </h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto mb-4 leading-relaxed">
                There are {classReport.enrolled_count || 0} students enrolled in this class roster, but none have completed evaluations yet. 
                Complete evaluations in the <strong>Evaluate Answer Script</strong> tool to see class metrics here.
              </p>
              {classReport.not_evaluated_students?.length > 0 && (
                <div className="mt-4 max-w-lg mx-auto text-left p-3.5 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs">
                  <span className="font-bold text-[var(--text)] block mb-1.5">Enrolled Roster (Pending Evaluation):</span>
                  <div className="flex flex-wrap gap-1.5">
                    {classReport.not_evaluated_students.map((s, idx) => (
                      <span key={idx} className="bg-[var(--surface)] px-2 py-0.5 rounded border border-[var(--border)] text-[var(--text-soft)]">
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Card>
          ) : (
            /* Active Report View */
            <div className="space-y-6">
              {/* Report Header Metadata */}
              <Card className="p-5 border-l-4 border-l-[var(--accent)]">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <h2 className="text-lg font-bold text-[var(--text)]">{classReport.class_name}</h2>
                      {classReport.section && (
                        <Badge tone="accent">Section {classReport.section}</Badge>
                      )}
                      {classReport.subjects && (
                        <Badge tone="neutral">{classReport.subjects}</Badge>
                      )}
                    </div>
                    <p className="text-xs text-[var(--text-soft)] mt-1">
                      Reporting Period / Assessments: <strong>{classReport.reporting_period}</strong> &bull; Generated: {classReport.generated_at}
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <span className="text-[11px] font-semibold text-[var(--text-faint)] uppercase tracking-wider block">
                      Evidence Source
                    </span>
                    <span className="text-xs font-bold text-[var(--text)]">
                      {classReport.total_valid_records} Verified Assessment Records
                    </span>
                  </div>
                </div>
              </Card>

              {/* 4 Stat Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--text-soft)]">Roster Enrollment</span>
                    <Users size={16} className="text-[var(--text-faint)]" />
                  </div>
                  <div className="text-2xl font-black text-[var(--text)] mt-2">
                    {classReport.enrolled_count}
                  </div>
                  <div className="text-[11px] text-[var(--text-soft)] mt-1 flex items-center justify-between">
                    <span>Enrolled in class</span>
                    <span className="font-semibold text-[var(--text)]">{classReport.evaluated_count} evaluated</span>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--text-soft)]">Evaluation Coverage</span>
                    <CheckCircle2 size={16} className={classReport.not_evaluated_count === 0 ? "text-[var(--success)]" : "text-[var(--warning)]"} />
                  </div>
                  <div className="text-2xl font-black text-[var(--text)] mt-2">
                    {classReport.enrolled_count > 0 
                      ? Math.round((classReport.evaluated_count / classReport.enrolled_count) * 100) 
                      : 0}%
                  </div>
                  <div className="text-[11px] text-[var(--text-soft)] mt-1">
                    {classReport.not_evaluated_count === 0 ? (
                      <span className="text-[var(--success)] font-semibold">100% of roster evaluated</span>
                    ) : (
                      <span className="text-[var(--warning)] font-semibold">{classReport.not_evaluated_count} student(s) pending</span>
                    )}
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--text-soft)]">Class Average Score</span>
                    <Award size={16} className="text-[var(--accent)]" />
                  </div>
                  <div className="text-2xl font-black text-[var(--accent)] mt-2">
                    {classReport.class_avg_pct !== null ? `${classReport.class_avg_pct}%` : 'N/A'}
                  </div>
                  <div className="text-[11px] text-[var(--text-soft)] mt-1 flex items-center justify-between">
                    <span>Overall Grade: <strong className="text-[var(--text)]">{classReport.class_avg_grade}</strong></span>
                    <span title={classReport.avg_calculation_method} className="cursor-help text-[var(--text-faint)] underline">
                      formula
                    </span>
                  </div>
                </Card>

                <Card className="p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-[var(--text-soft)]">Grade Spread</span>
                    <TrendingUp size={16} className="text-[var(--text-faint)]" />
                  </div>
                  <div className="flex items-center gap-1.5 mt-2.5">
                    {Object.entries(classReport.score_distribution || {}).map(([grd, count]) => (
                      <div key={grd} className="flex-1 text-center bg-[var(--surface-alt)] py-1 rounded-md border border-[var(--border)]">
                        <div className="text-[10px] font-bold text-[var(--text-soft)]">{grd}</div>
                        <div className="text-xs font-black text-[var(--text)]">{count}</div>
                      </div>
                    ))}
                  </div>
                  <div className="text-[10px] text-[var(--text-faint)] mt-1 text-right">
                    Calculated from valid marks
                  </div>
                </Card>
              </div>

              {/* Distinction Banner: Non-Evaluated Students */}
              {classReport.not_evaluated_students?.length > 0 && (
                <div className="p-4 rounded-xl border border-[var(--warning)]/30 bg-[var(--warning-soft)]/20 text-xs flex items-start gap-3">
                  <Info size={16} className="text-[var(--warning)] shrink-0 mt-0.5" />
                  <div className="space-y-1">
                    <div className="font-bold text-[var(--text)]">
                      Explicit Distinction: {classReport.not_evaluated_count} Enrolled Student(s) Not Yet Evaluated
                    </div>
                    <p className="text-[var(--text-soft)] leading-relaxed">
                      Missing evaluation records are <strong>never treated as 0% or failing grades</strong>. 
                      They are tracked separately so class statistics reflect only completed, verified evaluations.
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {classReport.not_evaluated_students.map((name, i) => (
                        <span key={i} className="bg-[var(--surface)] text-[var(--text)] px-2 py-0.5 rounded border border-[var(--border)] text-[11px] font-medium">
                          {name}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* 2-Column: Strengths & Improvements */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Strengths */}
                <Card className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <CheckCircle2 size={16} className="text-[var(--success)]" />
                    <h3 className="text-sm font-bold text-[var(--text)]">Class-Wide Mastery & Strengths</h3>
                  </div>
                  <p className="text-xs text-[var(--text-soft)] mb-3">
                    Concepts with &ge; 75% average score across recurring student responses.
                  </p>
                  {classReport.strengths?.length === 0 ? (
                    <div className="text-xs text-[var(--text-faint)] p-4 bg-[var(--surface-alt)] rounded-xl text-center">
                      No topics currently meet the 75%+ mastery threshold across multiple students.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {classReport.strengths.map((str, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between gap-2">
                          <div>
                            <span className="text-xs font-bold text-[var(--text)] block">{str.concept}</span>
                            <span className="text-[11px] text-[var(--text-soft)]">
                              Supported by {str.evidence_count} evaluated responses
                            </span>
                          </div>
                          <Badge tone="success">{str.avg_score_pct}% avg</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                {/* Improvements */}
                <Card className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <AlertCircle size={16} className="text-[var(--warning)]" />
                    <h3 className="text-sm font-bold text-[var(--text)]">Topics Requiring Attention</h3>
                  </div>
                  <p className="text-xs text-[var(--text-soft)] mb-3">
                    Concepts with &lt; 60% average score or recurring detected misconceptions.
                  </p>
                  {classReport.improvement_areas?.length === 0 ? (
                    <div className="text-xs text-[var(--text-faint)] p-4 bg-[var(--surface-alt)] rounded-xl text-center">
                      No critical systemic weaknesses or recurring misconception patterns identified.
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {classReport.improvement_areas.map((imp, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between gap-2">
                          <div>
                            <span className="text-xs font-bold text-[var(--text)] block">{imp.concept}</span>
                            <span className="text-[11px] text-[var(--text-soft)]">
                              {imp.misconception_count > 0 
                                ? `${imp.misconception_count} misconception(s) flagged · ${imp.evidence_count} responses`
                                : `${imp.evidence_count} evaluated responses`}
                            </span>
                          </div>
                          <Badge tone="warning">{imp.avg_score_pct}% avg</Badge>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>

              {/* Students Needing Support */}
              <Card className="p-5">
                <div className="flex items-center gap-2 mb-3">
                  <Users size={16} className="text-[var(--error)]" />
                  <h3 className="text-sm font-bold text-[var(--text)]">Targeted Support Recommendations</h3>
                </div>
                <p className="text-xs text-[var(--text-soft)] mb-3">
                  Identified through sustained patterns (&lt; 50% across &ge; 2 assessments or multiple misconceptions). 
                  Single mistakes are never used to categorize a student as struggling.
                </p>

                {classReport.students_needing_support?.length === 0 ? (
                  <div className="text-xs text-[var(--success)] p-4 bg-[var(--success-soft)]/20 rounded-xl border border-[var(--success)]/30 text-center font-medium">
                    No students currently meet the multi-assessment low-performance threshold.
                  </div>
                ) : (
                  <div className="space-y-2.5">
                    {classReport.students_needing_support.map((sup, idx) => (
                      <div key={idx} className="p-3.5 rounded-xl border border-[var(--error-soft)] bg-[var(--error-soft)]/10 flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-[var(--text)]">{sup.student_name}</span>
                            {sup.roll_number && (
                              <span className="text-[11px] text-[var(--text-faint)]">({sup.roll_number})</span>
                            )}
                          </div>
                          <div className="text-xs text-[var(--text-soft)]">{sup.evidence}</div>
                        </div>
                        <div className="md:text-right shrink-0">
                          <span className="text-[10px] font-bold text-[var(--text-faint)] uppercase block">Next Step</span>
                          <span className="text-xs font-semibold text-[var(--accent)]">{sup.recommended_next_step}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Insufficient Evidence List */}
                {classReport.insufficient_evidence_students?.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-[var(--border)] text-xs text-[var(--text-soft)]">
                    <span className="font-semibold text-[var(--text)]">Monitoring Notice (Insufficient Longitudinal Evidence): </span>
                    {classReport.insufficient_evidence_students.map(s => s.student_name).join(', ')} scored under 50% on a single assessment. Additional evaluations required before formal intervention is advised.
                  </div>
                )}
              </Card>

              {/* Longitudinal Progress */}
              {classReport.progress_notes?.length > 0 && (
                <Card className="p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <TrendingUp size={16} className="text-[var(--accent)]" />
                    <h3 className="text-sm font-bold text-[var(--text)]">Notable Progress Across Comparable Assessments</h3>
                  </div>
                  <div className="space-y-2">
                    {classReport.progress_notes.map((prog, idx) => (
                      <div key={idx} className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between text-xs">
                        <span className="font-bold text-[var(--text)]">{prog.student_name}</span>
                        <div className="flex items-center gap-3">
                          <span className="text-[var(--text-soft)]">{prog.trend}</span>
                          <Badge tone={prog.change > 0 ? "success" : prog.change < 0 ? "error" : "neutral"}>
                            {prog.change > 0 ? `+${prog.change}%` : `${prog.change}%`}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                </Card>
              )}

              {/* Complete Student-Wise Breakdown Table */}
              <Card className="p-0 overflow-hidden">
                <div className="p-4 border-b border-[var(--border)] flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-bold text-[var(--text)]">Student-Wise Results & Roster Breakdown</h3>
                    <p className="text-xs text-[var(--text-soft)]">
                      Linked directly to official class roster identities and evaluation transcripts.
                    </p>
                  </div>
                  <Badge tone="neutral">{classReport.student_results?.length || 0} students</Badge>
                </div>

                <div className="overflow-x-auto scrollbar-thin">
                  <table className="w-full min-w-[650px] border-collapse text-xs">
                    <thead>
                      <tr className="bg-[var(--surface-alt)]">
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Student Name</th>
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Roll / ID</th>
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Status</th>
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Assessments</th>
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Average %</th>
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Grade</th>
                        <th className="py-3 px-4 text-left font-bold text-[var(--text-faint)] uppercase tracking-wider">Details</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--border)]">
                      {classReport.student_results?.map((s, idx) => {
                        const isPending = s.evaluation_status === 'not_evaluated'
                        const isExpanded = expandedStudent === s.student_name

                        return (
                          <tbody key={idx} className="group">
                            <tr className="hover:bg-[var(--surface-alt)]/60 transition-colors">
                              <td className="py-3.5 px-4 font-bold text-[var(--text)]">
                                {s.student_name}
                              </td>
                              <td className="py-3.5 px-4 text-[var(--text-soft)]">
                                {s.roll_number || '—'}
                              </td>
                              <td className="py-3.5 px-4">
                                {isPending ? (
                                  <Badge tone="warning">Pending Evaluation</Badge>
                                ) : (
                                  <Badge tone="success">Evaluated ({s.num_assessments})</Badge>
                                )}
                              </td>
                              <td className="py-3.5 px-4 text-[var(--text-soft)]">
                                {isPending ? '0' : s.num_assessments}
                              </td>
                              <td className="py-3.5 px-4 font-bold text-[var(--text)]">
                                {isPending ? (
                                  <span className="text-[var(--text-faint)] font-normal italic">N/A</span>
                                ) : (
                                  `${s.average_pct}%`
                                )}
                              </td>
                              <td className="py-3.5 px-4">
                                {isPending ? (
                                  <span className="text-[var(--text-faint)] italic">—</span>
                                ) : (
                                  <Badge tone={s.average_pct >= 70 ? 'success' : s.average_pct >= 50 ? 'warning' : 'error'}>
                                    {s.grade}
                                  </Badge>
                                )}
                              </td>
                              <td className="py-3.5 px-4">
                                {!isPending && s.assessments?.length > 0 ? (
                                  <button
                                    onClick={() => setExpandedStudent(isExpanded ? null : s.student_name)}
                                    className="inline-flex items-center gap-1 text-[var(--accent)] hover:underline font-semibold"
                                  >
                                    {isExpanded ? 'Hide' : 'View'} ({s.assessments.length})
                                    {isExpanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
                                  </button>
                                ) : (
                                  <span className="text-[var(--text-faint)] text-[11px]">No script</span>
                                )}
                              </td>
                            </tr>

                            {/* Expanded individual assessments */}
                            {isExpanded && s.assessments && (
                              <tr className="bg-[var(--surface-alt)]/40">
                                <td colSpan={7} className="p-3 px-6">
                                  <div className="space-y-2 border-l-2 border-[var(--accent)] pl-3 my-1">
                                    <span className="text-[11px] font-bold text-[var(--text-soft)] block uppercase tracking-wider">
                                      Evaluated Assessment Records for {s.student_name}:
                                    </span>
                                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                                      {s.assessments.map((ev, aIdx) => (
                                        <div key={aIdx} className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] flex items-center justify-between text-xs">
                                          <div>
                                            <div className="font-semibold text-[var(--text)]">{ev.title}</div>
                                            <div className="text-[11px] text-[var(--text-faint)]">{ev.date}</div>
                                          </div>
                                          <div className="flex items-center gap-2">
                                            <Badge tone="neutral">
                                              {ev.obtained_marks}/{ev.total_marks} ({ev.percentage}%)
                                            </Badge>
                                            <Button
                                              variant="secondary"
                                              size="sm"
                                              onClick={() => handleDownloadIndividual(ev.evaluation_id)}
                                              title="Download Script PDF"
                                            >
                                              <Download size={12} />
                                            </Button>
                                          </div>
                                        </div>
                                      ))}
                                    </div>
                                  </div>
                                </td>
                              </tr>
                            )}
                          </tbody>
                        )
                      })}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Data Transparency & Limitations Footer */}
              <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs space-y-2">
                <div className="font-bold text-[var(--text)] flex items-center gap-1.5">
                  <Info size={14} className="text-[var(--accent)]" />
                  Auditability & Methodological Transparency
                </div>
                <p className="text-[var(--text-soft)] leading-relaxed">
                  {classReport.fact_vs_interpretation_note}
                </p>
                {classReport.limitations?.length > 0 && (
                  <ul className="list-disc list-inside space-y-1 text-[var(--text-faint)] text-[11px] pt-1">
                    {classReport.limitations.map((lim, lIdx) => (
                      <li key={lIdx}>{lim}</li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}
        </div>
      ) : (
        /* Individual Evaluation Transcripts Tab */
        <div className="space-y-4">
          <Card className="p-4 flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-[var(--text)]">Individual Evaluation Transcripts</h3>
              <p className="text-xs text-[var(--text-soft)]">
                Direct transcripts and evaluation records generated from uploaded answer scripts.
              </p>
            </div>
            <Button variant="ghost" size="sm" onClick={loadIndividualReports} disabled={loadingIndividual}>
              <RefreshCw size={13} className={loadingIndividual ? 'animate-spin' : ''} />
              Refresh
            </Button>
          </Card>

          {loadingIndividual ? (
            <Card className="p-12 text-center text-[var(--text-soft)]">
              <Loader2 className="animate-spin mx-auto mb-2.5 text-[var(--accent)]" size={30} />
              <span className="text-xs font-semibold">Loading evaluation records...</span>
            </Card>
          ) : individualReports.length === 0 ? (
            <Card className="p-12 text-center my-4 border-dashed border-2">
              <FileText size={44} className="text-[var(--text-faint)] mx-auto mb-3" />
              <h3 className="text-base font-bold mb-1 text-[var(--text)]">No evaluation reports generated yet</h3>
              <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto mb-4 leading-relaxed">
                Upload and evaluate student question papers & answer scripts in the <strong>Evaluate Answer Script</strong> page. Real reports will automatically generate here upon evaluation.
              </p>
            </Card>
          ) : (
            <Card className="p-0 overflow-hidden">
              <div className="overflow-x-auto scrollbar-thin">
                <table className="w-full min-w-[580px] border-collapse text-xs">
                  <thead>
                    <tr className="bg-[var(--surface-alt)]">
                      {['Student Name', 'Subject & Exam', 'Score & Grade', 'Date Generated', 'Actions'].map((h) => (
                        <th key={h} className="text-left text-xs text-[var(--text-faint)] font-bold uppercase tracking-wider py-3.5 px-4 border-b border-[var(--border)]">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {individualReports.map((r) => {
                      const evalId = r.id || r._id
                      return (
                        <tr key={evalId} className="hover:bg-[var(--surface-alt)] transition-colors">
                          <td className="py-4 px-4 font-bold text-sm text-[var(--text)]">
                            {r.student_name}{' '}
                            <span className="text-xs font-normal text-[var(--text-faint)]">
                              ({r.roll_number || 'N/A'})
                            </span>
                          </td>
                          <td className="py-4 px-4 text-xs font-semibold text-[var(--text-soft)]">
                            {r.subject} — {r.assessment_title || 'Examination'}
                          </td>
                          <td className="py-4 px-4">
                            <Badge tone={r.status || 'success'}>
                              {r.obtained_marks}/{r.total_marks} ({r.percentage}%) · Grade {r.grade}
                            </Badge>
                          </td>
                          <td className="py-4 px-4 text-xs text-[var(--text-faint)]">{r.created_at || 'Recently'}</td>
                          <td className="py-4 px-4">
                            <div className="flex items-center gap-2">
                              <Button variant="secondary" size="sm" onClick={() => handleDownloadIndividual(evalId)}>
                                <Download size={14} className="mr-1.5" /> PDF Transcript
                              </Button>
                              <button
                                onClick={(e) => handleDeleteIndividual(evalId, e)}
                                className="p-2 rounded-xl border border-[var(--error-soft)] text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                                title="Delete Evaluation Report"
                                aria-label="Delete evaluation report"
                              >
                                <Trash2 size={14} />
                              </button>
                            </div>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}
