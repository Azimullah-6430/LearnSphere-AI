import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHead, Card, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  User,
  Search,
  Filter,
  Eye,
  Send,
  Zap,
  BookOpen,
  ArrowRight,
  ShieldAlert,
  Flame,
  CheckSquare,
  MessageSquare,
  FileText,
  TrendingDown,
  Trash2,
  Sparkles,
  ChevronRight,
  Layers,
  HelpCircle,
  X
} from 'lucide-react'

export default function ActionCenter() {
  const { user, activeClass, recordActivity } = useApp()
  const navigate = useNavigate()

  // Items State
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  // Filter States
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('All') // 'All' | 'New' | 'In Progress' | 'Completed' | 'Follow-up Required'
  const [priorityFilter, setPriorityFilter] = useState('All')
  const [subjectFilter, setSubjectFilter] = useState('All')
  const [categoryFilter, setCategoryFilter] = useState('All')

  // Modals
  const [traceModalItem, setTraceModalItem] = useState(null)
  const [interventionModalItem, setInterventionModalItem] = useState(null)
  const [interventionNote, setInterventionNote] = useState('')
  const [interventionType, setInterventionType] = useState('worksheet')
  const [toastMessage, setToastMessage] = useState('')

  useEffect(() => {
    async function fetchBackendItems() {
      setLoading(true)
      try {
        const params = activeClass?.id ? { class_id: activeClass.id } : {}
        const res = await api.getActionCenterItems(params)
        if (res && res.success && Array.isArray(res.items)) {
          setItems(res.items)
        } else {
          setItems([])
        }
      } catch (err) {
        console.warn('Action Center API notice:', err)
        setItems([])
      } finally {
        setLoading(false)
      }
    }
    fetchBackendItems()
  }, [user, activeClass?.id])

  useEffect(() => {
    if (!traceModalItem && !interventionModalItem) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        if (traceModalItem) setTraceModalItem(null)
        if (interventionModalItem) setInterventionModalItem(null)
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [traceModalItem, interventionModalItem])

  const handleStatusChange = (id, newStatus) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: newStatus } : item))
    )
    api.updateActionCenterStatus(id, newStatus)
    recordActivity('action_center', `Updated Action Item ${id} status to ${newStatus}`)
    showToast(`Status updated to "${newStatus}"`)
  }

  const handleDismiss = async (item) => {
    if (!item?.id) return
    const id = item.id
    try {
      await api.deleteActionCenterItem(id)
    } catch (err) {
      console.warn('Dismiss error:', err)
    }
    setItems((prev) => prev.filter((i) => i.id !== id))
    recordActivity('action_center', `Dismissed Action Item for ${item.student_name}: ${item.topic || item.subject}`)
    showToast(`Action item dismissed with audit record.`)
  }

  const showToast = (msg) => {
    setToastMessage(msg)
    setTimeout(() => setToastMessage(''), 3500)
  }

  const handleSendIntervention = () => {
    if (!interventionModalItem) return
    const id = interventionModalItem.id

    handleStatusChange(id, 'In Progress')
    recordActivity('intervention', `Created ${interventionType} intervention for ${interventionModalItem.student_name}: ${interventionModalItem.topic}`)
    
    showToast(`Remedial intervention dispatched for ${interventionModalItem.student_name}!`)
    setInterventionModalItem(null)
    setInterventionNote('')
  }

  const handleMasterInTrainer = (item) => {
    navigate('/app/trainer', {
      state: {
        subject: item.subject,
        concept: item.misconception || item.topic
      }
    })
  }

  const filteredItems = items.filter((item) => {
    if (statusFilter !== 'All' && item.status !== statusFilter) return false
    if (priorityFilter !== 'All' && (item.priority || item.severity) !== priorityFilter) return false
    if (subjectFilter !== 'All' && item.subject !== subjectFilter) return false
    if (categoryFilter !== 'All' && item.category !== categoryFilter) return false

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchText = (
        (item.student_name || '') +
        (item.student_id || '') +
        (item.class_name || '') +
        (item.evaluation_id || '') +
        (item.subject || '') +
        (item.assessment_title || '') +
        (item.topic || '') +
        (item.skill_or_topic || '') +
        (item.priority_reason || '') +
        (item.issue || '') +
        (item.misconception || '') +
        (item.student_answer || '')
      ).toLowerCase()
      if (!matchText.includes(q)) return false
    }

    return true
  })

  // Summary Metrics
  const atRiskCount = items.filter(i => (i.marks_lost || 0) > 20 || i.category === 'excessive_marks_lost' || (i.loss_ratio || 0) >= 35).length
  const misconceptionCount = items.filter(i => i.category === 'severe_misconception' || i.category === 'repeated_concept_loss' || i.misconception).length
  const inProgressCount = items.filter(i => i.status === 'In Progress').length
  const completedCount = items.filter(i => i.status === 'Completed').length

  return (
    <>
      <PageHead
        title="Action Center"
        subtitle="Prioritized pedagogical interventions based on evaluated student scripts and diagnosed learning deficits."
      />

      {/* Toast Notification */}
      {toastMessage && (
        <div className="mb-4 p-3.5 rounded-2xl bg-[var(--success-soft)] border border-[var(--success)] text-[var(--success)] text-sm font-bold flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center gap-2.5">
            <CheckCircle2 size={18} />
            <span>{toastMessage}</span>
          </div>
          <button onClick={() => setToastMessage('')} className="text-xs opacity-75 hover:opacity-100 font-bold p-1 cursor-pointer">✕</button>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-5 border-l-4 border-l-[var(--error)]">
          <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Significant Deficit
          </div>
          <div className="text-3xl font-extrabold text-[var(--error)]">
            {atRiskCount}
          </div>
          <div className="text-xs text-[var(--error)] font-semibold mt-1">
            Lost &gt; 20 marks on test
          </div>
        </Card>

        <Card className="p-5 border-l-4 border-l-[var(--gold)]">
          <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Conceptual Misconceptions
          </div>
          <div className="text-3xl font-extrabold text-[var(--gold)]">
            {misconceptionCount}
          </div>
          <div className="text-xs text-[var(--text-soft)] font-medium mt-1">
            Linked to Misconception Map
          </div>
        </Card>

        <Card className="p-5 border-l-4 border-l-[var(--accent)]">
          <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Active Interventions
          </div>
          <div className="text-3xl font-extrabold text-[var(--accent)]">
            {inProgressCount}
          </div>
          <div className="text-xs text-[var(--text-soft)] font-medium mt-1">
            In Progress status
          </div>
        </Card>

        <Card className="p-5 border-l-4 border-l-[var(--success)]">
          <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Resolved Deficits
          </div>
          <div className="text-3xl font-extrabold text-[var(--success)]">
            {completedCount}
          </div>
          <div className="text-xs text-[var(--success)] font-semibold mt-1">
            Completed interventions
          </div>
        </Card>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="space-y-3.5 mb-6 p-4 bg-[var(--surface)] rounded-2xl border border-[var(--border)] shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mr-1">Status:</span>
            {[
              { id: 'All', label: 'All Items' },
              { id: 'New', label: 'New' },
              { id: 'In Progress', label: 'In Progress' },
              { id: 'Completed', label: 'Completed' },
              { id: 'Follow-up Required', label: 'Follow-up' }
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setStatusFilter(id)}
                className={`px-3 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                  statusFilter === id
                    ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-xs'
                    : 'bg-[var(--surface-alt)] border-[var(--border)] text-[var(--text-soft)] hover:border-[var(--accent-dim)] hover:text-[var(--text)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative w-full md:w-auto md:min-w-[260px]">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--text-faint)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search student, question, concept..."
              className="w-full pl-9 pr-3.5 py-2 rounded-xl border border-[var(--border)] text-xs bg-[var(--surface-alt)] text-[var(--text)] focus:bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
        </div>

        {/* Priority, Subject & Category Selectors */}
        <div className="flex items-center gap-4 pt-3 border-t border-[var(--border)] text-xs flex-wrap">
          <div className="flex items-center gap-2">
            <Filter size={13} className="text-[var(--accent)]" />
            <span className="font-bold text-[var(--text-faint)]">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-2 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold"
            >
              <option value="All">All Priorities</option>
              <option value="Critical">Critical</option>
              <option value="High">High Priority</option>
              <option value="Medium">Medium Priority</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <BookOpen size={13} className="text-[var(--accent)]" />
            <span className="font-bold text-[var(--text-faint)]">Subject:</span>
            <select
              value={subjectFilter}
              onChange={(e) => setSubjectFilter(e.target.value)}
              className="px-2 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold"
            >
              <option value="All">All Subjects</option>
              <option value="Mathematics">Mathematics</option>
              <option value="Physics">Physics</option>
              <option value="Chemistry">Chemistry</option>
              <option value="Computer Science">Computer Science</option>
              <option value="General">General</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <Layers size={13} className="text-[var(--accent)]" />
            <span className="font-bold text-[var(--text-faint)]">Deficit Type:</span>
            <select
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              className="px-2 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold"
            >
              <option value="All">All Deficit Types</option>
              <option value="excessive_marks_lost">&gt;20 Marks Lost</option>
              <option value="severe_misconception">Severe Misconception</option>
              <option value="repeated_concept_loss">Repeated Concept Loss</option>
              <option value="incomplete_answers">Incomplete Answers</option>
            </select>
          </div>
        </div>
      </div>

      {/* Action Items List */}
      <div className="space-y-4">
        {loading ? (
          <Card className="text-center py-12">
            <div className="animate-spin text-[var(--accent)] mx-auto mb-2 text-xl">⏳</div>
            <div className="text-sm font-semibold text-[var(--text-soft)]">Loading evaluation action items...</div>
          </Card>
        ) : filteredItems.length === 0 ? (
          items.length === 0 ? (
            <Card className="text-center py-14 border-dashed border-2 bg-[var(--surface-alt)] space-y-3">
              <CheckCircle2 size={46} className="mx-auto text-[var(--success)] mb-2" />
              <h3 className="font-extrabold text-[18px] text-[var(--text)]">
                All Students on Track &mdash; No Support Actions Required
              </h3>
              <p className="text-xs text-[var(--text-soft)] max-w-lg mx-auto leading-relaxed">
                Support action items are dynamically derived from completed, authorized teacher evaluations when students encounter verified marks loss, repeated conceptual difficulties, or unreadable scripts. No active intervention flags currently require attention.
              </p>
              <div className="flex items-center justify-center gap-3 pt-2">
                <Button variant="secondary" onClick={() => navigate('/app/evaluate')}>
                  Upload New Evaluation Scripts
                </Button>
                <Button variant="secondary" onClick={() => navigate('/app/history')}>
                  Browse Evaluation History
                </Button>
              </div>
            </Card>
          ) : (
            <Card className="text-center py-12 border-dashed border-2">
              <CheckSquare size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
              <div className="font-bold text-[15px]">No action items match your current filter criteria.</div>
              <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">
                Try adjusting your status, subject, priority, or search term filters to view remaining items.
              </p>
              <Button onClick={() => { setSearchQuery(''); setStatusFilter('All'); setPriorityFilter('All'); setSubjectFilter('All'); setCategoryFilter('All'); }}>
                Reset Filters
              </Button>
            </Card>
          )
        ) : (
          filteredItems.map((item) => {
            const isCritical = item.priority === 'Critical' || item.severity === 'Critical'
            const isHigh = item.priority === 'High' || item.severity === 'High'
            const marksLost = item.marks_lost !== undefined ? item.marks_lost : ((item.maximum_marks || 0) - (item.total_marks || 0))
            const affectedQs = Array.isArray(item.affected_questions) ? item.affected_questions : (item.affected_questions ? [item.affected_questions] : [])
            const marksPerQ = item.marks_lost_per_question && typeof item.marks_lost_per_question === 'object' ? item.marks_lost_per_question : {}
            const studentId = item.student_id || item.roll_number || 'N/A'
            const evalId = item.evaluation_id || item.eval_id || 'N/A'
            const className = item.class_name || (activeClass?.name || 'Class Scope')
            const assessmentTitle = item.assessment_title || item.topic || `${item.subject} Evaluation`
            const questionNum = item.question_num || 'Overall Examination'
            const focusTopic = item.skill_or_topic || item.topic || item.misconception || 'Curriculum Competency'
            const marksAwardedVsMax = item.marks_awarded_vs_max || (item.question_max_marks !== undefined ? `${item.question_awarded_marks} / ${item.question_max_marks} marks` : `${item.total_marks || 0} / ${item.maximum_marks || 0} marks`)
            const priorityReason = item.priority_reason || item.issue || 'Identified learning deficit from completed evaluation.'
            const recommendedAction = item.recommended_action || item.action || 'Assign targeted remediation worksheet and schedule review.'

            return (
              <Card
                key={item.id}
                className={`relative transition-all hover:border-[var(--accent-dim)] shadow-md border-l-4 ${
                  item.status === 'Completed'
                    ? 'border-l-gray-400 opacity-80'
                    : isCritical
                    ? 'border-l-[var(--error)] bg-[var(--surface)]'
                    : isHigh
                    ? 'border-l-[var(--gold)] bg-[var(--surface)]'
                    : 'border-l-[var(--accent)] bg-[var(--surface)]'
                }`}
              >
                <div className="space-y-3.5">
                  {/* Header: Student Name, Class, ID, Assessment, Evaluation ID, Subject, Status */}
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-3 border-b border-[var(--border)] pb-3">
                    <div className="flex items-center gap-3 flex-wrap">
                      <div className="w-10 h-10 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] text-[13px] font-extrabold flex items-center justify-center shrink-0 shadow-xs">
                        {item.student_name ? item.student_name.split(' ').map(n => n[0]).join('') : 'S'}
                      </div>

                      <div>
                        <div className="text-[16px] font-extrabold text-[var(--text)] flex items-center gap-2 flex-wrap">
                          <span>{item.student_name}</span>
                          <span className="text-[12px] font-bold text-[var(--text-faint)] bg-[var(--surface-alt)] px-2 py-0.5 rounded-md border border-[var(--border)]">
                            Class: {className}
                          </span>
                          <span className="text-[12px] font-mono text-[var(--text-faint)]">
                            [ID: {studentId}]
                          </span>
                          <span className="text-[13px] font-bold text-[var(--accent)]">
                            — {item.subject}
                          </span>
                          <Badge tone={isCritical ? 'error' : isHigh ? 'warning' : 'accent'}>
                            {item.academic_status || 'Support Priority'}
                          </Badge>
                        </div>
                        <div className="text-[11.5px] text-[var(--text-soft)] font-semibold mt-1 flex items-center gap-2 flex-wrap">
                          <span>Assessment: <strong className="text-[var(--text)]">{assessmentTitle}</strong></span>
                          <span>&bull;</span>
                          <span>Evaluation ID: <span className="font-mono text-[var(--text)]">{evalId}</span></span>
                          <span>&bull;</span>
                          <span>Target: <strong className="text-[var(--accent)]">{focusTopic}</strong> ({questionNum})</span>
                        </div>
                      </div>
                    </div>

                    {/* Status & Priority Controls */}
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge tone={isCritical ? 'error' : isHigh ? 'warning' : 'accent'}>
                        {item.priority || item.severity || 'Medium'} Priority
                      </Badge>

                      <select
                        value={item.status || 'New'}
                        onChange={(e) => handleStatusChange(item.id, e.target.value)}
                        className={`px-2.5 py-1 rounded-lg text-[12px] font-extrabold border transition-colors cursor-pointer ${
                          item.status === 'Completed'
                            ? 'bg-[var(--success-soft)] text-[var(--success)] border-[var(--success)]'
                            : item.status === 'In Progress'
                            ? 'bg-[var(--gold-soft)] text-[var(--gold)] border-[var(--gold)]'
                            : item.status === 'Follow-up Required'
                            ? 'bg-[var(--warning-soft)] text-[var(--warning)] border-[var(--warning)]'
                            : 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent)]'
                        }`}
                      >
                        <option value="New">New</option>
                        <option value="In Progress">In Progress</option>
                        <option value="Completed">Completed</option>
                        <option value="Follow-up Required">Follow-up Required</option>
                      </select>
                    </div>
                  </div>

                  {/* Explicit Explainable Prioritization Rule Strip */}
                  <div className="p-2.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-[12px] flex items-center gap-2">
                    <div className="font-bold text-[var(--text-faint)] uppercase tracking-wider text-[10.5px] shrink-0">
                      Priority Basis:
                    </div>
                    <div className="font-semibold text-[var(--text)] flex-1">
                      {priorityReason}
                    </div>
                  </div>

                  {/* Quantitative Marks Breakdown Strip */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[12px] bg-[var(--surface-alt)] p-2.5 rounded-xl border border-[var(--border)]">
                    <div className="flex items-center justify-between sm:justify-start gap-1.5">
                      <span className="text-[var(--text-faint)] font-bold">Question Marks:</span>
                      <strong className="text-[var(--text)] bg-[var(--surface)] px-2 py-0.5 rounded border border-[var(--border)]">
                        {item.question_max_marks !== undefined ? `${item.question_awarded_marks} / ${item.question_max_marks} marks` : marksAwardedVsMax}
                      </strong>
                    </div>

                    <div className="flex items-center justify-between sm:justify-start gap-1.5">
                      <span className="text-[var(--text-faint)] font-bold">Paper Score / Total:</span>
                      <strong className="text-[var(--text)]">
                        {item.total_marks || 0} / {item.maximum_marks || 0} marks
                      </strong>
                    </div>

                    <div className="flex items-center justify-between sm:justify-start gap-1.5">
                      <span className="text-[var(--error)] font-bold">Total Marks Lost:</span>
                      <strong className="text-[var(--error)] bg-[var(--error-soft)] px-2 py-0.5 rounded-md border border-[var(--error)]">
                        &minus;{marksLost} Marks {item.loss_ratio ? `(${item.loss_ratio}% loss)` : ''}
                      </strong>
                    </div>
                  </div>

                  {/* Student Answer & Misconception Diagnosis */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[12.5px]">
                    {item.student_answer ? (
                      <div className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-1">
                        <span className="font-bold text-[var(--text-faint)] text-[11px] uppercase tracking-wider block">
                          Student's Actual Written Response ({questionNum}):
                        </span>
                        <p className="font-mono text-[11.5px] text-[var(--text)] italic bg-[var(--surface)] p-2 rounded-lg border border-[var(--border)] line-clamp-2">
                          &ldquo;{item.student_answer}&rdquo;
                        </p>
                      </div>
                    ) : (
                      <div className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-1">
                        <span className="font-bold text-[var(--text-faint)] text-[11px] uppercase tracking-wider block">
                          Specific Focus Area:
                        </span>
                        <p className="font-semibold text-[12px] text-[var(--text)] bg-[var(--surface)] p-2 rounded-lg border border-[var(--border)]">
                          {focusTopic} &mdash; Question {questionNum}
                        </p>
                      </div>
                    )}

                    {item.misconception ? (
                      <div className="p-3 rounded-xl bg-[var(--gold-soft)] border border-[var(--gold)] space-y-1">
                        <span className="font-extrabold text-[var(--gold)] text-[11px] uppercase tracking-wider flex items-center gap-1">
                          <AlertTriangle size={13} />
                          <span>Diagnosed Misconception:</span>
                        </span>
                        <p className="font-semibold text-[var(--text)] text-[12px] leading-snug line-clamp-2">
                          {item.misconception}
                        </p>
                      </div>
                    ) : (
                      <div className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-1">
                        <span className="font-bold text-[var(--text-faint)] text-[11px] uppercase tracking-wider block">
                          Evaluation Diagnosis:
                        </span>
                        <p className="text-[12px] text-[var(--text)] font-semibold line-clamp-2">
                          {item.issue || 'Identified performance gap from completed evaluation.'}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Concise Suggested Follow-up Action */}
                  <div className="p-3 rounded-xl bg-[var(--accent-soft)] border border-[var(--accent)] text-[12.5px] font-medium text-[var(--text)] flex items-start gap-2">
                    <Zap size={16} className="text-[var(--accent)] shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-[var(--accent)]">Suggested Follow-up Action:</strong>{' '}
                      <span>{recommendedAction}</span>
                    </div>
                  </div>

                  {/* Traceability, Source Links & Action Toolbar */}
                  <div className="flex flex-wrap items-center justify-between gap-2.5 pt-3 border-t border-[var(--border)]">
                    <div className="flex items-center gap-2 flex-wrap">
                      {/* Source Link to Evaluation Record */}
                      <button
                        onClick={() => navigate('/app/history', { state: { selectedEvalId: item.evaluation_id } })}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-bold border border-[var(--accent-dim)] bg-[var(--accent-soft)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white transition-all shadow-xs"
                        title="View Source Evaluation Record"
                      >
                        <FileText size={13} />
                        <span>Evaluation Record</span>
                      </button>

                      {/* Source Link to Misconception Record if present */}
                      {item.misconception && (
                        <button
                          onClick={() => navigate('/app/misconceptions', { state: { concept: item.misconception || focusTopic, class_id: item.class_id } })}
                          className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-bold border border-[var(--gold)] bg-[var(--gold-soft)] text-[var(--gold)] hover:bg-[var(--gold)] hover:text-white transition-all shadow-xs"
                          title="View Misconception Record in Misconception Map"
                        >
                          <AlertTriangle size={13} />
                          <span>Misconception Record</span>
                        </button>
                      )}

                      {/* AI Trainer Practice */}
                      <button
                        onClick={() => handleMasterInTrainer(item)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-bold bg-gradient-to-r from-[var(--accent)] to-[var(--accent-dim)] text-white hover:shadow-md transition-all"
                      >
                        <Sparkles size={13} />
                        <span>AI Trainer Practice</span>
                      </button>

                      {/* Review Evidence Trace */}
                      <button
                        onClick={() => setTraceModalItem(item)}
                        className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[12px] font-bold border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-colors"
                      >
                        <Eye size={13} />
                        <span>Review Evidence Trace</span>
                      </button>
                    </div>

                    <div className="flex items-center gap-2">
                      {/* Dispatch Intervention */}
                      <button
                        onClick={() => {
                          setInterventionModalItem(item)
                          setInterventionNote(`Assigned remedial revision for ${item.subject}: ${focusTopic || 'Key concepts'}.`)
                        }}
                        className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl text-[12px] font-bold bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] transition-colors shadow-sm"
                      >
                        <Send size={13} />
                        <span>Create Intervention</span>
                      </button>

                      {/* Mark Completed Button if not completed */}
                      {item.status !== 'Completed' && (
                        <button
                          onClick={() => handleStatusChange(item.id, 'Completed')}
                          className="flex items-center gap-1 px-3 py-1.5 rounded-xl text-[12px] font-bold border border-[var(--success)] bg-[var(--success-soft)] text-[var(--success)] hover:bg-[var(--success)] hover:text-white transition-colors"
                          title="Mark Action Completed"
                        >
                          <CheckCircle2 size={13} />
                          <span>Complete</span>
                        </button>
                      )}

                      {/* Dismiss Action Item */}
                      <button
                        onClick={() => {
                          if (window.confirm(`Dismiss action item for ${item.student_name}? This will archive the item with an audit entry.`)) {
                            handleDismiss(item)
                          }
                        }}
                        className="flex items-center gap-1 px-2.5 py-1.5 rounded-xl text-[12px] font-bold border border-[var(--border)] text-[var(--text-faint)] hover:text-[var(--error)] hover:border-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                        title="Dismiss Action Item"
                        aria-label={`Dismiss action item for ${item.student_name}`}
                      >
                        <Trash2 size={13} />
                        <span className="hidden sm:inline">Dismiss</span>
                      </button>
                    </div>
                  </div>
                </div>
              </Card>
            )
          })
        )}
      </div>

      {/* MODAL 1: FULL TRACEABILITY MODAL */}
      {traceModalItem && (
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setTraceModalItem(null); }}
        >
          <div 
            role="dialog"
            aria-modal="true"
            aria-labelledby="trace-modal-title"
            className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <div>
                <h3 id="trace-modal-title" className="text-base font-extrabold text-[var(--text)] flex items-center gap-2">
                  <span>Audit Trail & Evidence Trace</span>
                  <Badge tone="accent">Action Center Trace</Badge>
                </h3>
                <p className="text-xs text-[var(--text-soft)]">
                  Student: <strong>{traceModalItem.student_name}</strong> &bull; Class: <strong>{traceModalItem.class_name || 'Class Scope'}</strong> &bull; Assessment: <strong>{traceModalItem.assessment_title || traceModalItem.topic}</strong>
                </p>
              </div>
              <button 
                onClick={() => setTraceModalItem(null)} 
                aria-label="Close trace audit modal"
                className="p-1 rounded-lg text-[var(--text-faint)] hover:text-[var(--text)]"
              >
                <X size={18} />
              </button>
            </div>

            {/* Trace Step Indicator */}
            <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] flex items-center justify-between text-[11px] font-bold text-[var(--text-soft)] overflow-x-auto gap-2">
              <span className="text-[var(--accent)]">Action Center</span>
              <ChevronRight size={14} />
              <span>Student</span>
              <ChevronRight size={14} />
              <span>Evaluation</span>
              <ChevronRight size={14} />
              <span>Question</span>
              <ChevronRight size={14} />
              <span>Answer</span>
              <ChevronRight size={14} />
              <span className="text-[var(--gold)]">Misconception</span>
            </div>

            {/* Evaluation Context */}
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
                <span className="font-bold text-[var(--text-faint)] block mb-0.5">Evaluation ID:</span>
                <span className="font-mono text-[var(--text)] font-semibold">{traceModalItem.evaluation_id || traceModalItem.eval_id || 'N/A'}</span>
              </div>
              <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
                <span className="font-bold text-[var(--text-faint)] block mb-0.5">Score Breakdown:</span>
                <span className="text-[var(--error)] font-bold">
                  {traceModalItem.question_max_marks !== undefined ? `Question: ${traceModalItem.question_awarded_marks}/${traceModalItem.question_max_marks}m | ` : ''}
                  Paper: {traceModalItem.total_marks || 0}/{traceModalItem.maximum_marks || 0}m (&minus;{traceModalItem.marks_lost}m)
                </span>
              </div>
            </div>

            {/* Priority Reason */}
            {traceModalItem.priority_reason && (
              <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs">
                <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block text-[10.5px] mb-1">
                  Prioritization Basis:
                </span>
                <p className="text-[var(--text)] font-semibold">{traceModalItem.priority_reason}</p>
              </div>
            )}

            {/* Official Question */}
            {traceModalItem.exact_question && (
              <div className="p-3.5 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs space-y-1">
                <span className="font-bold text-[var(--accent)] uppercase tracking-wider block text-[11px]">
                  Official Evaluated Question ({traceModalItem.question_num || 'Assessment Scope'}):
                </span>
                <p className="text-[var(--text)] font-semibold leading-relaxed">{traceModalItem.exact_question}</p>
              </div>
            )}

            {/* Student's Actual Answer */}
            <div className="p-3.5 bg-[var(--error-soft)] rounded-xl border border-[var(--error)] text-xs space-y-1">
              <span className="font-bold text-[var(--error)] uppercase tracking-wider block text-[11px]">
                Student's Actual Answer on Script:
              </span>
              <p className="text-[var(--text)] font-mono leading-relaxed italic bg-[var(--surface)] p-2.5 rounded-lg border border-[var(--border)]">
                {traceModalItem.student_answer || 'Extracted written answer from uploaded answer script.'}
              </p>
            </div>

            {/* Teacher Feedback & Misconception */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              <div className="p-3 bg-[var(--gold-soft)] rounded-xl border border-[var(--gold)] space-y-1">
                <span className="font-bold text-[var(--gold)] uppercase tracking-wider block text-[11px]">
                  Conceptual Misconception:
                </span>
                <p className="text-[var(--text)] font-semibold leading-snug">
                  {traceModalItem.misconception || 'Deficit identified from evaluation mark breakdown.'}
                </p>
              </div>

              <div className="p-3 bg-[var(--success-soft)] rounded-xl border border-[var(--success)] space-y-1">
                <span className="font-bold text-[var(--success)] uppercase tracking-wider block text-[11px]">
                  Expected Academic Model:
                </span>
                <p className="text-[var(--text)] leading-snug">
                  {traceModalItem.correct_understanding || 'Comprehensive standard curriculum solution.'}
                </p>
              </div>
            </div>

            {/* Teacher Diagnostic Issue */}
            <div className="p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs space-y-1">
              <span className="font-bold text-[var(--text-faint)] uppercase tracking-wider block text-[11px]">
                Diagnostic Examiner Note:
              </span>
              <p className="text-[var(--text)] font-medium leading-relaxed">
                {traceModalItem.issue || traceModalItem.evidence || 'Complete question-level diagnostic available in evaluation history.'}
              </p>
            </div>

            {/* Modal Controls */}
            <div className="flex flex-wrap items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setTraceModalItem(null)}>Close Trace</Button>
              {traceModalItem.misconception && (
                <Button variant="secondary" onClick={() => {
                  const mConcept = traceModalItem.misconception
                  const mClassId = traceModalItem.class_id
                  setTraceModalItem(null)
                  navigate('/app/misconceptions', { state: { concept: mConcept, class_id: mClassId } })
                }}>
                  View Misconception Record
                </Button>
              )}
              <Button onClick={() => {
                const eId = traceModalItem.evaluation_id
                setTraceModalItem(null)
                navigate('/app/history', { state: { selectedEvalId: eId } })
              }}>
                View Evaluation Record
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* MODAL 2: CREATE INTERVENTION MODAL */}
      {interventionModalItem && (
        <div 
          className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setInterventionModalItem(null); }}
        >
          <Card 
            role="dialog"
            aria-modal="true"
            aria-labelledby="intervention-modal-title"
            className="max-w-[540px] w-full bg-[var(--surface)] border-2 border-[var(--accent)] shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <div>
                <h3 id="intervention-modal-title" className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2">
                  <Zap size={18} className="text-[var(--accent)]" />
                  <span>Dispatch Remedial Intervention</span>
                </h3>
                <div className="text-[12.5px] text-[var(--text-soft)]">
                  Student: <strong>{interventionModalItem.student_name}</strong> &bull; {interventionModalItem.subject}
                </div>
              </div>
              <button
                onClick={() => setInterventionModalItem(null)}
                aria-label="Close intervention dispatch modal"
                className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-[13px]">
              <div>
                <label className="block font-bold text-[var(--text-soft)] mb-1.5 uppercase text-[11px] tracking-wider">
                  Select Intervention Action:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'worksheet', label: 'Remedial Practice Sheet', icon: FileText, desc: 'Assign targeted revision set' },
                    { id: '1on1', label: '1-on-1 Remedial Meeting', icon: User, desc: 'Schedule 1-on-1 coaching' },
                    { id: 'parent_notify', label: 'Notify Parent & Student', icon: MessageSquare, desc: 'Alert parent agent of risk' },
                    { id: 'class_review', label: 'Classroom Tutorial', icon: BookOpen, desc: 'Flag concept in next class' }
                  ].map(({ id, label, icon: Icon, desc }) => (
                    <button
                      key={id}
                      onClick={() => setInterventionType(id)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        interventionType === id
                          ? 'bg-[var(--accent-soft)] border-[var(--accent)] text-[var(--accent)] font-bold'
                          : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                      }`}
                    >
                      <div className="flex items-center gap-1.5 mb-1">
                        <Icon size={15} />
                        <span>{label}</span>
                      </div>
                      <div className="text-[11px] opacity-80 font-normal">{desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block font-bold text-[var(--text-soft)] mb-1.5 uppercase text-[11px] tracking-wider">
                  Teacher Instructions / Notes:
                </label>
                <textarea
                  rows={3}
                  value={interventionNote}
                  onChange={(e) => setInterventionNote(e.target.value)}
                  placeholder="Enter specific instructions or practice questions to send..."
                  className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[13px] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                />
              </div>

              <div className="p-3 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-[12px] text-[var(--text-soft)] flex items-center gap-2">
                <CheckCircle2 size={16} className="text-[var(--success)] shrink-0" />
                <span>Dispatching this intervention automatically shifts status to <strong>"In Progress"</strong>.</span>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setInterventionModalItem(null)}>Cancel</Button>
              <Button onClick={handleSendIntervention} className="flex items-center gap-1.5">
                <Send size={14} />
                <span>Dispatch Intervention</span>
              </Button>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
