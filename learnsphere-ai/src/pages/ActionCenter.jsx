import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHead, Card, CardHeader, Badge, Button } from '../components/ui/Primitives.jsx'
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
  RefreshCcw,
  MessageSquare,
  FileText,
  UserX,
  TrendingDown,
  Trash2
} from 'lucide-react'

export default function ActionCenter() {
  const { recordActivity } = useApp()
  const navigate = useNavigate()

  // Items State
  const [items, setItems] = useState(() => {
    try {
      const saved = localStorage.getItem('learnsphere_action_center_items')
      if (saved) {
        const parsed = JSON.parse(saved)
        // Clean out legacy demo items if present
        const cleanItems = parsed.filter(i => !['act-1', 'act-2', 'act-3', 'act-4'].includes(i.id))
        const filtered = cleanItems.filter(i => (i.marks_lost || 0) >= 20 || (i.academic_status && !i.academic_status.includes('On track')))
        return filtered
      }
      return []
    } catch {
      return []
    }
  })

  // Filter States
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState('All') // 'All' | 'New' | 'In Progress' | 'Completed' | 'Follow-up Required'
  const [priorityFilter, setPriorityFilter] = useState('All')
  const [subjectFilter, setSubjectFilter] = useState('All')

  // Modals
  const [detailModalItem, setDetailModalItem] = useState(null)
  const [interventionModalItem, setInterventionModalItem] = useState(null)
  const [interventionNote, setInterventionNote] = useState('')
  const [interventionType, setInterventionType] = useState('worksheet')
  const [toastMessage, setToastMessage] = useState('')

  useEffect(() => {
    try {
      localStorage.setItem('learnsphere_action_center_items', JSON.stringify(items))
    } catch {}
  }, [items])

  useEffect(() => {
    async function fetchBackendItems() {
      try {
        const res = await api.getActionCenterItems()
        if (res && res.success && Array.isArray(res.items) && res.items.length > 0) {
          // Strictly filter out toppers and students with <= 20 marks lost
          const atRiskOnly = res.items.filter(i => (i.marks_lost || 0) >= 20 || (i.academic_status && !i.academic_status.includes('On track')))
          if (atRiskOnly.length > 0) {
            setItems(atRiskOnly)
          }
        }
      } catch (err) {
        console.warn('Action Center API notice:', err)
      }
    }
    fetchBackendItems()
  }, [])

  const handleStatusChange = (id, newStatus) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, status: newStatus } : item))
    )
    api.updateActionCenterStatus(id, newStatus)
    recordActivity('action_center', `Updated Action Item ${id} status to ${newStatus}`)
    showToast(`Status updated to "${newStatus}"`)
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

  const filteredItems = items.filter((item) => {
    if (statusFilter !== 'All' && item.status !== statusFilter) return false
    if (priorityFilter !== 'All' && item.priority !== priorityFilter) return false
    if (subjectFilter !== 'All' && item.subject !== subjectFilter) return false

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      const matchText = (item.student_name + item.subject + item.topic + item.issue + item.misconception).toLowerCase()
      if (!matchText.includes(q)) return false
    }

    return true
  })

  return (
    <>
      <PageHead
        title="Teacher Action Center (At-Risk & Failing Students Only)"
        subtitle="Targets exclusively students who lost > 20 marks and are at high risk of failing. Toppers and above-average students are automatically excluded."
      />

      {/* Target Filtering Rule Banner */}
      <div className="mb-6 p-4 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] text-[13px] text-[var(--text)] flex items-start gap-3">
        <TrendingDown size={22} className="text-[var(--error)] shrink-0 mt-0.5" />
        <div>
          <div className="font-extrabold text-[var(--error)] mb-0.5">Strict Targeting Filter: Marks Lost &gt; 20 & At-Risk Status</div>
          <div className="text-[12.5px] text-[var(--text-soft)]">
            Action Center automatically excludes toppers (Priya Sharma 91%, Sneha Iyer 88%, Arun Kumar 85%). Only students who <strong>lost more than 20 marks</strong> and have a <strong>high chance of failing terminal exams</strong> are gathered below for teacher intervention.
          </div>
        </div>
      </div>

      {/* Toast Notification */}
      {toastMessage && (
        <div className="mb-4 p-3 rounded-xl bg-[var(--success-soft)] border border-[var(--success)] text-[var(--success)] text-[13px] font-bold flex items-center justify-between shadow-sm animate-fade-in">
          <div className="flex items-center gap-2">
            <CheckCircle2 size={16} />
            <span>{toastMessage}</span>
          </div>
          <button onClick={() => setToastMessage('')} className="text-xs opacity-75 hover:opacity-100 font-bold">✕</button>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card className="p-4 border-l-4 border-l-[var(--error)]">
          <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            At-Risk Students (&gt;20 Marks Lost)
          </div>
          <div className="text-[26px] font-extrabold text-[var(--error)]">
            {items.length}
          </div>
          <div className="text-[11.5px] text-[var(--error)] font-semibold mt-1">
            Requires immediate teacher intervention
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-[var(--warning)]">
          <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Excluded Toppers
          </div>
          <div className="text-[26px] font-extrabold text-[var(--success)]">
            Filtered Out
          </div>
          <div className="text-[11.5px] text-[var(--text-soft)] font-medium mt-1">
            Above-average students omitted
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-[var(--gold)]">
          <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Interventions Active
          </div>
          <div className="text-[26px] font-extrabold text-[var(--gold)]">
            {items.filter(i => i.status === 'In Progress').length}
          </div>
          <div className="text-[11.5px] text-[var(--text-soft)] font-medium mt-1">
            In Progress status
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-[var(--success)]">
          <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
            Resolved At-Risk Gaps
          </div>
          <div className="text-[26px] font-extrabold text-[var(--success)]">
            {items.filter(i => i.status === 'Completed').length}
          </div>
          <div className="text-[11.5px] text-[var(--success)] font-semibold mt-1">
            Completed interventions
          </div>
        </Card>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="space-y-3 mb-6 p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Status Tabs */}
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mr-1">Status:</span>
            {[
              { id: 'All', label: 'All Items' },
              { id: 'New', label: '🆕 New' },
              { id: 'In Progress', label: '⏳ In Progress' },
              { id: 'Completed', label: '✅ Completed' },
              { id: 'Follow-up Required', label: '🔁 Follow-up Required' }
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setStatusFilter(id)}
                className={`px-3 py-1 rounded-full text-[12px] font-bold border transition-all ${
                  statusFilter === id
                    ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                    : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                }`}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Search Box */}
          <div className="relative min-w-[240px]">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-faint)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search student, topic, error..."
              className="w-full pl-8 pr-3 py-1.5 rounded-lg border border-[var(--border-strong)] text-[12.5px] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
            />
          </div>
        </div>

        {/* Priority & Subject Selectors */}
        <div className="flex items-center gap-4 pt-2 border-t border-[var(--border)] text-[12px] flex-wrap">
          <div className="flex items-center gap-2">
            <Filter size={13} className="text-[var(--accent)]" />
            <span className="font-bold text-[var(--text-faint)]">Priority:</span>
            <select
              value={priorityFilter}
              onChange={(e) => setPriorityFilter(e.target.value)}
              className="px-2 py-1 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-semibold"
            >
              <option value="All">All Priorities</option>
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
            </select>
          </div>
        </div>
      </div>

      {/* Action Items List */}
      <div className="space-y-4">
        {filteredItems.length === 0 ? (
          <Card className="text-center py-12">
            <CheckSquare size={40} className="mx-auto text-[var(--text-faint)] mb-3" />
            <div className="font-bold text-[15px]">No action items match your current filter criteria.</div>
            <p className="text-xs text-[var(--text-soft)] mt-1 mb-4">Try clearing your search query or setting status filter to "All Items".</p>
            <Button onClick={() => { setSearchQuery(''); setStatusFilter('All'); setPriorityFilter('All'); setSubjectFilter('All'); }}>Reset Filters</Button>
          </Card>
        ) : (
          filteredItems.map((item) => (
            <Card key={item.id} className="relative transition-all hover:border-[var(--accent-dim)] shadow-sm border-l-4 border-l-[var(--error)]">
              <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                <div className="flex-1 space-y-2.5">
                  {/* Header */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <div className="w-8 h-8 rounded-full bg-[var(--error)] text-white text-[12px] font-extrabold flex items-center justify-center shrink-0">
                      {item.student_name.split(' ').map(n=>n[0]).join('')}
                    </div>

                    <span className="text-[16px] font-extrabold text-[var(--text)]">
                      {item.student_name}
                    </span>
                    <span className="text-[12px] font-bold text-[var(--text-faint)]">
                      ({item.roll_number})
                    </span>
                    <span className="text-[13px] font-bold text-[var(--accent)]">
                      — {item.subject}
                    </span>

                    <Badge tone="error">
                      ⚠️ {item.academic_status || 'At Risk'}
                    </Badge>

                    {/* Status Dropdown Picker */}
                    <div className="ml-auto flex items-center gap-1.5">
                      <span className="text-[11px] font-bold uppercase text-[var(--text-faint)]">Status:</span>
                      <select
                        value={item.status}
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

                  {/* Metadata Bar */}
                  <div className="flex items-center gap-4 text-[12.5px] font-semibold text-[var(--text-soft)] flex-wrap bg-[var(--surface-alt)] px-3 py-1.5 rounded-lg border border-[var(--border)]">
                    <span><strong>Topic:</strong> {item.topic}</span>
                    <span>•</span>
                    <span className="text-[var(--error)]"><strong>Wrong in:</strong> {item.question_num}</span>
                    <span>•</span>
                    <span className="text-[var(--error)] font-extrabold bg-[var(--error-soft)] px-2 py-0.5 rounded-md border border-[var(--error)]">
                      <strong>Marks Lost: {item.marks_lost} Marks</strong> (&gt;20 Rule)
                    </span>
                    <span>•</span>
                    <span className="text-[var(--text-faint)]"><strong>Prev Failure:</strong> {item.prev_occurrence}</span>
                  </div>

                  {/* Specific Error & Misconception */}
                  <div className="space-y-1 text-[13px]">
                    <div>
                      <strong className="text-[var(--text)]">Exact Issue:</strong>{' '}
                      <span className="text-[var(--text-soft)]">{item.issue}</span>
                    </div>
                    <div className="text-[12.5px] text-[var(--gold)] font-medium flex items-center gap-1.5 pt-0.5">
                      <AlertTriangle size={14} className="shrink-0" />
                      <span><strong>Detected Misconception:</strong> {item.misconception}</span>
                    </div>
                  </div>

                  {/* Recommended Action */}
                  <div className="p-3 rounded-lg bg-[var(--accent-soft)] border border-[var(--accent)] text-[13px] font-medium text-[var(--text)] flex items-start gap-2">
                    <Zap size={16} className="text-[var(--accent)] shrink-0 mt-0.5" />
                    <div>
                      <strong>Recommended Remedial Action:</strong> {item.action}
                    </div>
                  </div>
                </div>
              </div>

              {/* Footer Action Buttons */}
              <div className="flex items-center justify-end gap-2 pt-3 mt-3 border-t border-[var(--border)]">
                <button
                  onClick={() => {
                    if (window.confirm(`Delete action item for ${item.student_name} permanently?`)) {
                      setItems(prev => prev.filter(i => i.id !== item.id))
                      showToast(`Action item for ${item.student_name} deleted.`)
                    }
                  }}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)] hover:bg-[var(--error)] hover:text-white transition-all"
                  title="Delete Action Item"
                >
                  <Trash2 size={13} />
                  <span>Delete</span>
                </button>

                <button
                  onClick={() => setDetailModalItem(item)}
                  className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-colors"
                >
                  <Eye size={14} />
                  <span>View Details</span>
                </button>

                {(item.is_unreadable || item.academic_status?.includes('Unreadable')) && (
                  <button
                    onClick={() => navigate('/app/history')}
                    className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--gold)] text-white hover:bg-[var(--gold-soft)] hover:text-[var(--gold)] transition-colors shadow-sm"
                  >
                    <span>✏️ Allot Marks Now</span>
                  </button>
                )}

                <button
                  onClick={() => {
                    setInterventionModalItem(item)
                    setInterventionNote(`Assigned remedial revision for ${item.topic} (${item.question_num}). Target: restore passing grade.`)
                  }}
                  className="flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[12px] font-bold bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] transition-colors shadow-sm"
                >
                  <Send size={14} />
                  <span>Create Intervention</span>
                </button>
              </div>
            </Card>
          ))
        )}
      </div>

      {/* MODAL 1: VIEW DETAILS MODAL */}
      {detailModalItem && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4 overflow-y-auto">
          <Card className="max-w-[620px] w-full bg-[var(--surface)] border-2 border-[var(--accent)] shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <div>
                <div className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2">
                  <span>{detailModalItem.student_name}</span>
                  <span className="text-[13px] text-[var(--text-faint)]">({detailModalItem.roll_number})</span>
                  <Badge tone="error">{detailModalItem.academic_status}</Badge>
                </div>
                <div className="text-[12.5px] text-[var(--text-soft)]">
                  Subject: <strong>{detailModalItem.subject} — {detailModalItem.topic}</strong> (Wrong in {detailModalItem.question_num})
                </div>
              </div>
              <button
                onClick={() => setDetailModalItem(null)}
                className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Detailed Question Snippet */}
            {detailModalItem.details && (
              <div className="space-y-3 text-[13px]">
                <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)]">
                  <div className="font-bold text-[var(--text-faint)] text-[11px] uppercase tracking-wider mb-1">
                    Evaluation Question Snippet
                  </div>
                  <div className="font-semibold text-[var(--text)]">{detailModalItem.details.question_text}</div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3 rounded-lg bg-[var(--error-soft)] border border-[var(--error)]">
                    <div className="font-bold text-[var(--error)] text-[11px] uppercase tracking-wider mb-1">
                      Student's Submitted Answer
                    </div>
                    <div className="font-mono text-[12px] text-[var(--text)]">{detailModalItem.details.student_answer}</div>
                  </div>

                  <div className="p-3 rounded-lg bg-[var(--success-soft)] border border-[var(--success)]">
                    <div className="font-bold text-[var(--success)] text-[11px] uppercase tracking-wider mb-1">
                      Correct Academic Solution
                    </div>
                    <div className="font-mono text-[12px] text-[var(--text)]">{detailModalItem.details.correct_answer}</div>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-[var(--gold-soft)] border border-[var(--gold)]">
                  <div className="font-bold text-[var(--gold)] text-[11px] uppercase tracking-wider mb-1">
                    AI Examiner Diagnostic Notes
                  </div>
                  <div className="text-[12.5px] text-[var(--text)] font-medium">{detailModalItem.details.grader_notes}</div>
                </div>
              </div>
            )}

            {/* Diagnostic Summary */}
            <div className="space-y-2 text-[12.5px] bg-[var(--surface-alt)] p-3 rounded-xl border border-[var(--border)]">
              <div><strong>Root Cause Misconception:</strong> {detailModalItem.misconception}</div>
              <div><strong>Total Marks Lost in Assessment:</strong> <span className="text-[var(--error)] font-bold">{detailModalItem.marks_lost} marks</span></div>
              <div><strong>Previous Failure:</strong> {detailModalItem.prev_occurrence}</div>
              <div><strong>Current Action Status:</strong> <Badge tone="accent">{detailModalItem.status}</Badge></div>
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setDetailModalItem(null)}>Close</Button>
              <Button onClick={() => {
                const item = detailModalItem
                setDetailModalItem(null)
                setInterventionModalItem(item)
              }}>Create Intervention</Button>
            </div>
          </Card>
        </div>
      )}

      {/* MODAL 2: CREATE INTERVENTION MODAL */}
      {interventionModalItem && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <Card className="max-w-[540px] w-full bg-[var(--surface)] border-2 border-[var(--accent)] shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <div>
                <div className="text-[17px] font-extrabold text-[var(--text)] flex items-center gap-2">
                  <Zap size={18} className="text-[var(--accent)]" />
                  <span>Create Remedial Intervention</span>
                </div>
                <div className="text-[12.5px] text-[var(--text-soft)]">
                  Target Student: <strong>{interventionModalItem.student_name}</strong> ({interventionModalItem.roll_number}) — {interventionModalItem.subject}
                </div>
              </div>
              <button
                onClick={() => setInterventionModalItem(null)}
                className="w-8 h-8 rounded-lg bg-[var(--surface-alt)] font-bold text-lg flex items-center justify-center hover:bg-[var(--border)] transition-colors"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-[13px]">
              <div>
                <label className="block font-bold text-[var(--text-soft)] mb-1.5 uppercase text-[11px] tracking-wider">
                  Select Intervention Type:
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {[
                    { id: 'worksheet', label: 'Remedial Practice Sheet', icon: FileText, desc: 'Assigns targeted revision set' },
                    { id: '1on1', label: '1-on-1 Remedial Meeting', icon: User, desc: 'Schedules 1-on-1 coaching' },
                    { id: 'parent_notify', label: 'Notify Parent & Student', icon: MessageSquare, desc: 'Alerts Parent Agent of failure risk' },
                    { id: 'class_review', label: 'Classroom Tutorial', icon: BookOpen, desc: 'Flags concept in next lecture' }
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
                <span>Sending this intervention automatically shifts status to <strong>"In Progress"</strong>.</span>
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
