import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  Sparkles,
  FileText,
  ArrowRight,
  AlertCircle,
  RefreshCw,
  BookOpen,
  Brain,
  Microscope,
  Trophy,
  Flame,
  Clock,
  TrendingUp,
  Award,
  CheckCircle2,
  ChevronRight,
  ShieldCheck,
  Building2,
  UserCheck,
  Layers,
  GraduationCap
} from 'lucide-react'

export default function Dashboard() {
  const { role, authenticated, authLoading, user } = useApp()

  if (authLoading) {
    return <DashboardLoadingSkeleton />
  }

  if (!authenticated || !user) {
    return <UnauthenticatedState />
  }

  return role === 'teacher' ? <TeacherDashboard /> : <StudentDashboard />
}

// ── Skeletons & Fallback States ───────────────────────────────────────────────

function DashboardLoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading dashboard data">
      <div className="h-28 bg-[var(--surface-alt)] rounded-2xl border border-[var(--border)]" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-24 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]" />
        ))}
      </div>
      <div className="grid md:grid-cols-[1.6fr_1fr] gap-4">
        <div className="h-72 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]" />
        <div className="h-72 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]" />
      </div>
    </div>
  )
}

function UnauthenticatedState() {
  const navigate = useNavigate()
  return (
    <Card className="p-10 text-center my-10 max-w-md mx-auto shadow-sm">
      <AlertCircle size={40} className="text-[var(--warning)] mx-auto mb-3" />
      <h2 className="text-xl font-bold mb-2">Session Required</h2>
      <p className="text-sm text-[var(--text-soft)] mb-6">
        Please sign in to access your learning dashboard.
      </p>
      <Button onClick={() => navigate('/')} className="w-full">
        Sign In to LearnSphere
      </Button>
    </Card>
  )
}

// ── Student Dashboard ─────────────────────────────────────────────────────────

function StudentDashboard() {
  const navigate = useNavigate()
  const { user, streakDays, formattedSessionTime } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  const activeUserIdRef = useRef(user?.id || user?._id || user?.email)

  useEffect(() => {
    const currentUserId = user?.id || user?._id || user?.email
    activeUserIdRef.current = currentUserId
    
    async function loadStudentDashboard() {
      setLoading(true)
      setError(null)

      try {
        const res = await api.getDashboardAnalytics('student', user?.name || '')
        if (activeUserIdRef.current !== currentUserId) return

        if (res && res.success) {
          setData(res)
        } else {
          setError(res?.error || 'Failed to load dashboard data.')
        }
      } catch (err) {
        if (activeUserIdRef.current === currentUserId) {
          setError(err?.message || 'Unable to connect to the server.')
        }
      } finally {
        if (activeUserIdRef.current === currentUserId) {
          setLoading(false)
        }
      }
    }

    if (user) {
      loadStudentDashboard()
    }
  }, [user])

  const isCollege = user?.level === 'college'
  const isSchool = user?.level === 'school'

  const currentSem = user?.semester !== undefined && user?.semester !== null
    ? user?.semester
    : (user?.current_semester !== undefined && user?.current_semester !== null
        ? user?.current_semester
        : user?.currentSemester ?? null)

  const hasCollegeSemester = isCollege && currentSem !== null && currentSem !== '' && !isNaN(Number(currentSem))

  let academicBadge = 'Student'
  if (isCollege) {
    academicBadge = `College · ${user?.department || user?.branch || 'Engineering'} · Sem ${currentSem || '—'}`
  } else if (isSchool) {
    academicBadge = `School · ${user?.board || 'Board'} · Class ${user?.grade_level || user?.classLevel || '—'}`
  }

  const recentEvals = data?.recentEvaluations || []
  const hasEvaluations = recentEvals.length > 0

  const avgScore = hasEvaluations
    ? Math.round(recentEvals.reduce((acc, curr) => acc + (Number(curr.percentage) || 0), 0) / recentEvals.length)
    : null

  if (error && !data) {
    return (
      <div className="py-8">
        <Card className="p-8 text-center max-w-lg mx-auto border-[var(--error)] shadow-sm">
          <AlertCircle size={36} className="text-[var(--error)] mx-auto mb-3" />
          <h2 className="text-lg font-bold mb-1">Error Loading Dashboard</h2>
          <p className="text-sm text-[var(--text-soft)] mb-5">{error}</p>
          <Button onClick={() => window.location.reload()} className="mx-auto flex items-center gap-2">
            <RefreshCw size={14} /> Retry Connection
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Executive Welcome Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[var(--surface)] via-[var(--surface)] to-[var(--surface-alt)] border border-[var(--border)] p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)] flex items-center gap-1.5">
                <GraduationCap size={13} /> {academicBadge}
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1">
                <Flame size={13} className="text-amber-500" /> {streakDays || 1} Day Streak
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <Clock size={13} /> Session: {formattedSessionTime || '0m'}
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[var(--text)]">
              Welcome back, {user?.name || 'Student'}
            </h1>
            <p className="text-xs md:text-sm text-[var(--text-soft)] mt-1 font-medium">
              {user?.institution_name || user?.school || user?.college || 'LearnSphere AI'}
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <Button onClick={() => navigate('/app/self-evaluation')} className="flex items-center gap-2 shadow-sm">
              <BookOpen size={15} /> Self-Evaluation
            </Button>
            <Button variant="secondary" onClick={() => navigate('/app/trainer')} className="flex items-center gap-2">
              <Brain size={15} /> AI Tutor
            </Button>
          </div>
        </div>
      </div>

      {/* College Semester Incomplete Notice */}
      {isCollege && !hasCollegeSemester && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-800 rounded-xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="text-amber-600 shrink-0" />
            <div className="text-xs font-bold text-amber-900 dark:text-amber-300">
              Please set your current semester in Settings to align curriculum subjects and assessments.
            </div>
          </div>
          <Button size="sm" onClick={() => navigate('/app/settings')} className="shrink-0">
            Configure Semester
          </Button>
        </div>
      )}

      {/* Metric Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Evaluations</span>
            <FileText size={16} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl lg:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            {loading ? '...' : recentEvals.length}
          </div>
          <div className="text-xs font-semibold text-[var(--text-soft)] mt-1 flex items-center gap-1">
            <CheckCircle2 size={12} className="text-[var(--success)]" /> Completed assessments
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Mastery Average</span>
            <TrendingUp size={16} className="text-emerald-500" />
          </div>
          <div className="text-2xl lg:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            {loading ? '...' : (avgScore !== null ? `${avgScore}%` : '—')}
          </div>
          <div className="text-xs font-semibold mt-1">
            {avgScore !== null ? (
              <span className={avgScore >= 75 ? 'text-[var(--success)]' : avgScore >= 50 ? 'text-[var(--warning)]' : 'text-[var(--error)]'}>
                {avgScore >= 75 ? 'Distinction Tier' : avgScore >= 50 ? 'Passing Tier' : 'Needs Practice'}
              </span>
            ) : (
              <span className="text-[var(--text-faint)]">Awaiting first test</span>
            )}
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Daily Streak</span>
            <Flame size={16} className="text-amber-500" />
          </div>
          <div className="text-2xl lg:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            {streakDays || 1} <span className="text-base font-medium text-[var(--text-soft)]">{streakDays === 1 ? 'day' : 'days'}</span>
          </div>
          <div className="text-xs font-semibold text-amber-600 dark:text-amber-400 mt-1 flex items-center gap-1">
            Active daily study
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Academic Status</span>
            <ShieldCheck size={16} className="text-[var(--accent)]" />
          </div>
          <div className="text-lg lg:text-xl font-extrabold text-[var(--text)] truncate">
            {isCollege ? (user?.degree || 'Undergraduate') : (user?.board ? `${user.board}` : 'Enrolled')}
          </div>
          <div className="text-xs font-semibold text-[var(--text-soft)] mt-1 truncate">
            {isCollege ? (user?.department || 'Active Semester') : `Class ${user?.grade_level || user?.classLevel || '—'}`}
          </div>
        </div>
      </div>

      {/* Main Grid: Graded Scripts + Quick Launch */}
      <div className="grid lg:grid-cols-[1.6fr_1fr] gap-6">
        {/* Left Column: Recent Graded Evaluations */}
        <Card className="shadow-sm">
          <CardHeader
            title="Recent Evaluated Papers"
            action={
              <Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>
                View all <ChevronRight size={13} className="ml-1" />
              </Button>
            }
          />

          {loading ? (
            <div className="py-12 text-center text-xs text-[var(--text-soft)] animate-pulse">
              Loading evaluations...
            </div>
          ) : !hasEvaluations ? (
            <div className="py-10 text-center border border-dashed border-[var(--border)] rounded-xl p-6">
              <FileText size={36} className="text-[var(--accent)] mx-auto mb-2.5 opacity-70" />
              <div className="text-sm font-bold text-[var(--text)] mb-1">No Evaluated Papers Found</div>
              <p className="text-xs text-[var(--text-soft)] max-w-xs mx-auto mb-4">
                Submit a Question Paper and Answer Script to view instant detailed grading and feedback.
              </p>
              <Button size="sm" onClick={() => navigate('/app/self-evaluation')} className="mx-auto">
                Start Self-Evaluation
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {recentEvals.slice(0, 5).map((e, idx) => {
                const pct = Number(e.percentage) || 0
                return (
                  <div
                    key={e.id || e._id || idx}
                    onClick={() => navigate('/app/history')}
                    className="py-3.5 flex items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-2 rounded-lg cursor-pointer transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-xs md:text-sm font-bold text-[var(--text)] truncate">
                        {e.subject || 'Subject'}
                      </div>
                      <div className="text-[11px] text-[var(--text-soft)] mt-0.5 truncate">
                        {e.assessment_title || 'Assessment'} · {e.created_at || 'Recently'}
                      </div>
                    </div>
                    <div className="shrink-0 flex items-center gap-2">
                      <Badge tone={pct >= 75 ? 'success' : pct >= 50 ? 'warning' : 'error'}>
                        {pct}% {e.grade ? `(${e.grade})` : ''}
                      </Badge>
                      <ChevronRight size={14} className="text-[var(--text-faint)]" />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>

        {/* Right Column: Learning Hub Modules */}
        <div className="space-y-4">
          <Card className="shadow-sm">
            <CardHeader title="Learning Modules" />
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => navigate('/app/trainer')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <Brain size={20} className="text-[var(--accent)] mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">AI Academic Tutor</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Syllabus Coaching</div>
              </button>

              <button
                onClick={() => navigate('/app/reality-lab')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <Microscope size={20} className="text-emerald-500 mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Reality Lab</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Practical Scenarios</div>
              </button>

              <button
                onClick={() => navigate('/app/knowledge-challenge')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <Trophy size={20} className="text-amber-500 mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Knowledge Challenge</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Module Drills</div>
              </button>

              <button
                onClick={() => navigate('/app/self-evaluation')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <BookOpen size={20} className="text-[var(--accent)] mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Self-Evaluation</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Grade Script</div>
              </button>
            </div>
          </Card>

          {/* Account Profile Summary */}
          <Card className="p-4 shadow-sm">
            <div className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider mb-3">
              Profile Summary
            </div>
            <div className="text-xs space-y-2 text-[var(--text-soft)]">
              <div className="flex justify-between items-center py-1 border-b border-[var(--border)]">
                <span>Account Name</span>
                <span className="font-bold text-[var(--text)]">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-[var(--border)]">
                <span>Email ID</span>
                <span className="font-bold text-[var(--text)]">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span>Institution</span>
                <span className="font-bold text-[var(--text)]">{user?.institution_name || user?.school || user?.college || 'Configured'}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

// ── Teacher Dashboard ─────────────────────────────────────────────────────────

function TeacherDashboard() {
  const navigate = useNavigate()
  const { user } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadTeacherAnalytics() {
      setLoading(true)
      try {
        const res = await api.getDashboardAnalytics('teacher', user?.name || '')
        if (res && res.success) {
          setData(res)
        }
      } catch (err) {
        console.warn('Teacher analytics load notice:', err)
      } finally {
        setLoading(false)
      }
    }
    if (user) {
      loadTeacherAnalytics()
    }
  }, [user])

  const recentEvals = data?.recentEvaluations || []
  const hasEvaluations = recentEvals.length > 0
  const isCollege = user?.level === 'college' || user?.teacher_level === 'college'

  const activeStudents = Array.from(new Set(recentEvals.map(e => e.student_name).filter(Boolean)))

  return (
    <div className="space-y-6">
      {/* Executive Teacher Header */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-[var(--surface)] via-[var(--surface)] to-[var(--surface-alt)] border border-[var(--border)] p-6 shadow-sm">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)] flex items-center gap-1.5">
                <Building2 size={13} /> {isCollege ? 'Higher Education Faculty' : 'School Educator'}
              </span>
              <span className="px-2.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                <UserCheck size={13} /> Faculty Verified
              </span>
            </div>
            <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight text-[var(--text)]">
              Welcome, {user?.name || 'Faculty'}
            </h1>
            <p className="text-xs md:text-sm text-[var(--text-soft)] mt-1 font-medium">
              {user?.institution_name || 'LearnSphere Academic Portal'} · {isCollege ? (user?.department || 'Department') : (user?.board || 'Board')}
            </p>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <Button onClick={() => navigate('/app/evaluate')} className="flex items-center gap-2 shadow-sm">
              <FileText size={15} /> Evaluate Script
            </Button>
            <Button variant="secondary" onClick={() => navigate('/app/action-center')} className="flex items-center gap-2">
              <Layers size={15} /> Action Center
            </Button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Evaluations Graded</span>
            <FileText size={16} className="text-[var(--accent)]" />
          </div>
          <div className="text-2xl lg:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            {loading ? '...' : recentEvals.length}
          </div>
          <div className="text-xs font-semibold text-[var(--text-soft)] mt-1">
            Stored evaluation records
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Active Students</span>
            <UserCheck size={16} className="text-emerald-500" />
          </div>
          <div className="text-2xl lg:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            {loading ? '...' : activeStudents.length}
          </div>
          <div className="text-xs font-semibold text-[var(--text-soft)] mt-1">
            Graded student roster
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Department / Level</span>
            <Building2 size={16} className="text-[var(--accent)]" />
          </div>
          <div className="text-base lg:text-lg font-extrabold text-[var(--text)] truncate">
            {isCollege ? (user?.department || 'Higher Ed') : (user?.board || 'School')}
          </div>
          <div className="text-xs font-semibold text-[var(--text-soft)] mt-1">
            Institutional branch
          </div>
        </div>

        <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--border)] shadow-sm hover:border-[var(--accent)] transition-all">
          <div className="flex items-center justify-between text-xs text-[var(--text-faint)] font-bold mb-2">
            <span>Institution</span>
            <ShieldCheck size={16} className="text-amber-500" />
          </div>
          <div className="text-base lg:text-lg font-extrabold text-[var(--text)] truncate">
            {user?.institution_name || 'LearnSphere AI'}
          </div>
          <div className="text-xs font-semibold text-[var(--text-soft)] mt-1">
            Authoritative portal
          </div>
        </div>
      </div>

      {/* Main Grid: Evaluation Roster + Quick Tools */}
      <div className="grid lg:grid-cols-[1.6fr_1fr] gap-6">
        <Card className="shadow-sm">
          <CardHeader
            title="Recent Student Evaluations"
            action={
              <Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>
                View all <ChevronRight size={13} className="ml-1" />
              </Button>
            }
          />

          {loading ? (
            <div className="py-12 text-center text-xs text-[var(--text-soft)] animate-pulse">
              Loading student evaluations...
            </div>
          ) : !hasEvaluations ? (
            <div className="py-10 text-center border border-dashed border-[var(--border)] rounded-xl p-6">
              <FileText size={36} className="text-[var(--accent)] mx-auto mb-2.5 opacity-70" />
              <div className="text-sm font-bold text-[var(--text)] mb-1">No Evaluated Scripts Yet</div>
              <p className="text-xs text-[var(--text-soft)] max-w-xs mx-auto mb-4">
                Upload Question Papers and Student Answer Scripts in Evaluate to generate question-level marks and misconception analysis.
              </p>
              <Button size="sm" onClick={() => navigate('/app/evaluate')} className="mx-auto">
                Evaluate Answer Script
              </Button>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {recentEvals.slice(0, 5).map((e, idx) => {
                const pct = Number(e.percentage) || 0
                return (
                  <div
                    key={e.id || e._id || idx}
                    onClick={() => navigate('/app/history')}
                    className="py-3.5 flex items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-2 rounded-lg cursor-pointer transition-colors"
                  >
                    <div className="min-w-0">
                      <div className="text-xs md:text-sm font-bold text-[var(--text)] truncate">
                        {e.student_name || 'Student'} — {e.subject || 'Subject'}
                      </div>
                      <div className="text-[11px] text-[var(--text-soft)] mt-0.5 truncate">
                        {e.assessment_title || 'Exam'} · {e.created_at || 'Recently'}
                      </div>
                    </div>
                    <div className="shrink-0 flex items-center gap-2">
                      <Badge tone={pct >= 75 ? 'success' : 'warning'}>
                        {pct}%
                      </Badge>
                      <ChevronRight size={14} className="text-[var(--text-faint)]" />
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </Card>

        {/* Right Tools Column */}
        <div className="space-y-4">
          <Card className="shadow-sm">
            <CardHeader title="Faculty Tools" />
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => navigate('/app/evaluate')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <FileText size={20} className="text-[var(--accent)] mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Evaluate Scripts</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Strict Grading</div>
              </button>

              <button
                onClick={() => navigate('/app/action-center')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <Layers size={20} className="text-amber-500 mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Action Center</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Interventions</div>
              </button>

              <button
                onClick={() => navigate('/app/misconceptions')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <Brain size={20} className="text-[var(--accent)] mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Misconceptions</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Concept Gaps</div>
              </button>

              <button
                onClick={() => navigate('/app/analytics')}
                className="p-3.5 rounded-xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group shadow-2xs hover:shadow-xs"
              >
                <TrendingUp size={20} className="text-emerald-500 mb-2 group-hover:scale-110 transition-transform" />
                <div className="text-xs font-bold text-[var(--text)]">Class Analytics</div>
                <div className="text-[11px] text-[var(--text-soft)] mt-0.5">Performance</div>
              </button>
            </div>
          </Card>

          <Card className="p-4 shadow-sm">
            <div className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider mb-3">
              Faculty Profile
            </div>
            <div className="text-xs space-y-2 text-[var(--text-soft)]">
              <div className="flex justify-between items-center py-1 border-b border-[var(--border)]">
                <span>Faculty Name</span>
                <span className="font-bold text-[var(--text)]">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center py-1 border-b border-[var(--border)]">
                <span>Email ID</span>
                <span className="font-bold text-[var(--text)]">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center py-1">
                <span>Institution</span>
                <span className="font-bold text-[var(--text)]">{user?.institution_name || 'LearnSphere AI'}</span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}

