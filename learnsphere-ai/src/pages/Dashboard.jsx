import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api.js'
import { useApp } from '../context/AppContext.jsx'
import { Card, CardHeader, Badge, Button, StatCard } from '../components/ui/Primitives.jsx'
import {
  Brain,
  FileText,
  TrendingUp,
  Clock,
  CheckCircle2,
  ChevronRight,
  ShieldCheck,
  Building2,
  UserCheck,
  GraduationCap,
  Zap,
  Map,
  Compass,
  Microscope,
  Trophy,
  Flame,
  CircleChevronUp,
  ArrowRight,
  FileCheck,
  AlertCircle,
  RefreshCw,
  BookOpen,
  Users,
  Timer,
  Globe,
  PlusCircle,
  BarChart3,
  Sparkles
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
      <div className="h-32 bg-[var(--surface-alt)] rounded-2xl border border-[var(--border)]" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 bg-[var(--surface-alt)] rounded-2xl border border-[var(--border)]" />
        ))}
      </div>
      <div className="grid lg:grid-cols-[1.6fr_1fr] gap-6">
        <div className="h-80 bg-[var(--surface-alt)] rounded-2xl border border-[var(--border)]" />
        <div className="h-80 bg-[var(--surface-alt)] rounded-2xl border border-[var(--border)]" />
      </div>
    </div>
  )
}

function UnauthenticatedState() {
  const navigate = useNavigate()
  return (
    <Card className="p-8 sm:p-10 text-center my-12 max-w-md mx-auto shadow-sm">
      <AlertCircle size={40} className="text-[var(--warning)] mx-auto mb-3" />
      <h2 className="text-xl font-bold mb-2 text-[var(--text)]">Session Required</h2>
      <p className="text-sm text-[var(--text-soft)] mb-6">
        Please sign in to access your personalized learning dashboard.
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

  useEffect(() => {
    async function loadStudentDashboard() {
      setLoading(true)
      try {
        const res = await api.getDashboardAnalytics('student', user?.name || '')
        if (res && res.success) {
          setData(res)
        } else {
          setData({ recentEvaluations: [] })
        }
      } catch (err) {
        console.warn('Student dashboard load notice:', err)
        setError('Could not connect to cloud records. Operating in local mode.')
        setData({ recentEvaluations: [] })
      } finally {
        setLoading(false)
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
          <h2 className="text-xl font-bold mb-1 text-[var(--text)]">Error Loading Dashboard</h2>
          <p className="text-sm text-[var(--text-soft)] mb-5">{error}</p>
          <Button onClick={() => window.location.reload()} className="mx-auto flex items-center gap-2">
            <RefreshCw size={14} /> Retry Connection
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Executive Student Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-[var(--surface)] border border-[var(--border)] p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-2.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-bold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20 flex items-center gap-1.5">
                <GraduationCap size={15} /> {academicBadge}
              </span>
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 flex items-center gap-1.5 whitespace-nowrap shadow-xs">
                <Flame size={15} className="text-amber-500 shrink-0" strokeWidth={1.8} /> 🔥 {streakDays || 1} {streakDays === 1 ? 'Day' : 'Days'}
              </span>
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30 flex items-center gap-1.5 whitespace-nowrap shadow-xs">
                <CircleChevronUp size={15} className="text-emerald-500 shrink-0" strokeWidth={2} /> ⏱️ {formattedSessionTime || '0s'} (Active)
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl md:text-[32px] font-extrabold tracking-tight text-[var(--text)]">
              Welcome back, {user?.name || 'Student'}
            </h1>
            <p className="text-sm sm:text-base text-[var(--text-soft)] font-medium">
              {user?.institution_name || user?.school || user?.college || 'LearnSphere Academic Network'}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <Button onClick={() => navigate('/app/self-evaluation')} className="flex items-center gap-2 shadow-xs px-4 sm:px-5 py-2.5 text-sm sm:text-base font-bold">
              <FileCheck size={18} /> Self-Evaluation
            </Button>
            <Button variant="secondary" onClick={() => navigate('/app/trainer')} className="flex items-center gap-2 px-4 sm:px-5 py-2.5 text-sm sm:text-base font-bold">
              <Brain size={18} /> Personal Trainer
            </Button>
          </div>
        </div>
      </div>

      {/* Recommended Next Action Banner */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-[var(--accent-soft)] via-[var(--surface)] to-[var(--surface-alt)] border border-[var(--accent)]/30 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-start gap-4">
          <div className="w-11 h-11 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
            <Sparkles size={22} />
          </div>
          <div>
            <div className="text-xs sm:text-[13px] font-bold uppercase tracking-wider text-[var(--accent)] mb-1">
              Recommended Next Action
            </div>
            <div className="text-base sm:text-lg md:text-xl font-bold text-[var(--text)] leading-snug">
              {!hasEvaluations
                ? 'Upload and grade your handwritten exam script'
                : 'Master concepts with the Syllabus-Aligned AI Tutor'}
            </div>
            <div className="text-xs sm:text-sm md:text-[15px] text-[var(--text-soft)] mt-1 leading-relaxed max-w-2xl">
              {!hasEvaluations
                ? 'Use computer vision to evaluate your paper against marking schemes and diagnose knowledge gaps.'
                : 'Get step-by-step Feynman explanations, derivations, and practice questions for your subjects.'}
            </div>
          </div>
        </div>

        <button
          onClick={() => navigate(!hasEvaluations ? '/app/self-evaluation' : '/app/trainer')}
          className="px-6 py-3 rounded-xl bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-all font-bold text-sm sm:text-base flex items-center justify-center gap-2.5 shrink-0 shadow-sm cursor-pointer"
        >
          <span>{!hasEvaluations ? 'Start First Evaluation' : 'Resume AI Tutoring'}</span>
          <ArrowRight size={17} />
        </button>
      </div>

      {/* College Semester Incomplete Notice */}
      {isCollege && !hasCollegeSemester && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-800 rounded-2xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="text-amber-600 shrink-0" />
            <div className="text-xs sm:text-sm font-bold text-amber-900 dark:text-amber-300">
              Please configure your current semester in Settings to synchronize your course syllabus.
            </div>
          </div>
          <Button size="sm" onClick={() => navigate('/app/settings')} className="shrink-0">
            Set Semester
          </Button>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <StatCard
          label="Evaluations"
          value={loading ? '…' : recentEvals.length}
          delta="Graded answer scripts"
          deltaTone="up"
          icon={FileText}
        />
        <StatCard
          label="Mastery Average"
          value={loading ? '…' : avgScore !== null ? `${avgScore}%` : '—'}
          delta={avgScore !== null ? (avgScore >= 75 ? 'Distinction Tier' : avgScore >= 50 ? 'Passing Tier' : 'Needs Revision') : 'Awaiting first test'}
          deltaTone={avgScore >= 75 ? 'up' : avgScore >= 50 ? 'neutral' : 'down'}
          icon={TrendingUp}
        />
        <StatCard
          label="Study Streak"
          value={`${streakDays || 1} d`}
          delta="Consecutive learning"
          deltaTone="up"
          icon={Flame}
        />
        <StatCard
          label="Academic Level"
          value={isCollege ? (user?.degree || 'Undergrad') : (user?.board || 'School')}
          delta={isCollege ? (user?.department || 'Degree') : `Class ${user?.grade_level || user?.classLevel || '12'}`}
          deltaTone="neutral"
          icon={ShieldCheck}
        />
      </div>

      {/* Main Grid: Interactive Learning Studios + Recent Evaluated Papers */}
      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-6">
        {/* Left Column: Interactive AI Learning Studios */}
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Interactive AI Learning Studios"
              subtitle="Syllabus-aligned adaptive learning and experiential practice engines"
            />
            <div className="grid sm:grid-cols-2 gap-4">
              <button
                onClick={() => navigate('/app/trainer')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-[var(--accent-soft)] flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Brain size={24} className="text-[var(--accent)]" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Personal AI Trainer</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Conversational tutor with step-by-step Feynman derivations and syllabus mastery.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/learn-anywhere')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-teal-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Compass size={24} className="text-teal-600 dark:text-teal-400" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Learn from Anywhere</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Low-resource experiential learning using everyday local materials and household items.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/reality-lab')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Microscope size={24} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Reality Lab</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Virtual science simulations and interactive hypothesis testing environments.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/knowledge-challenge')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Trophy size={24} className="text-amber-600 dark:text-amber-400" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Knowledge Challenge</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Adaptive syllabus quizzes and timed speed drills for exam preparation.
                </div>
              </button>
            </div>
          </Card>

          {/* Productivity & Review Hub */}
          <div className="grid sm:grid-cols-3 gap-3.5">
            <button
              onClick={() => navigate('/app/focus')}
              className="p-4 sm:p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <Timer size={20} className="text-[var(--accent)]" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">Timer</span>
              </div>
              <div className="text-sm sm:text-base font-bold text-[var(--text)]">Focus Session</div>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-0.5">Pomodoro & Audio</div>
            </button>

            <button
              onClick={() => navigate('/app/memory')}
              className="p-4 sm:p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <BookOpen size={20} className="text-teal-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">Recall</span>
              </div>
              <div className="text-sm sm:text-base font-bold text-[var(--text)]">Academic Memory</div>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-0.5">Spaced Flashcards</div>
            </button>

            <button
              onClick={() => navigate('/app/opportunities')}
              className="p-4 sm:p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <Globe size={20} className="text-amber-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">Feeds</span>
              </div>
              <div className="text-sm sm:text-base font-bold text-[var(--text)]">Opportunities</div>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-0.5">Contests & News</div>
            </button>
          </div>
        </div>

        {/* Right Column: Recent Evaluated Papers */}
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Recent Evaluated Papers"
              subtitle="Verified scores and diagnostic breakdown"
              action={
                <Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>
                  View all <ChevronRight size={15} className="ml-1" />
                </Button>
              }
            />

            {loading ? (
              <div className="py-12 text-center text-xs sm:text-sm text-[var(--text-soft)] animate-pulse">
                Loading recent evaluation records…
              </div>
            ) : !hasEvaluations ? (
              <div className="py-10 text-center border border-dashed border-[var(--border)] rounded-2xl p-6 bg-[var(--surface-alt)]/30">
                <FileText size={40} className="text-[var(--accent)] mx-auto mb-2.5 opacity-80" />
                <div className="text-sm sm:text-base font-bold text-[var(--text)] mb-1">No Evaluated Papers Found</div>
                <p className="text-xs sm:text-sm text-[var(--text-soft)] max-w-xs mx-auto mb-4 leading-relaxed">
                  Upload a Question Paper and your Handwritten Answer Script in Self-Evaluation for instant step-by-step grading.
                </p>
                <Button size="sm" onClick={() => navigate('/app/self-evaluation')} className="mx-auto text-xs sm:text-sm font-semibold">
                  Start First Evaluation
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
                      className="py-3.5 flex items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-3 rounded-xl cursor-pointer transition-colors"
                    >
                      <div className="min-w-0 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 font-bold text-xs">
                          <FileText size={18} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm sm:text-base font-bold text-[var(--text)] truncate">
                            {e.subject || 'Subject'}
                          </div>
                          <div className="text-xs sm:text-[13px] text-[var(--text-soft)] mt-0.5 truncate">
                            {e.assessment_title || 'Assessment'} · {e.created_at || 'Recently'}
                          </div>
                        </div>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <Badge tone={pct >= 75 ? 'success' : pct >= 50 ? 'warning' : 'error'}>
                          {pct}%
                        </Badge>
                        <ChevronRight size={15} className="text-[var(--text-faint)]" />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>

          {/* Academic Profile Tile */}
          <Card className="p-5 sm:p-6">
            <div className="text-xs sm:text-sm font-bold text-[var(--text-faint)] uppercase tracking-wider mb-3.5">
              Student Profile Verification
            </div>
            <div className="text-xs sm:text-sm space-y-2.5 text-[var(--text-soft)]">
              <div className="flex justify-between items-center py-2 border-b border-[var(--border)]">
                <span>Account Name</span>
                <span className="font-bold text-[var(--text)]">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-[var(--border)]">
                <span>Email ID</span>
                <span className="font-bold text-[var(--text)] truncate max-w-[200px]">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span>Institution</span>
                <span className="font-bold text-[var(--text)] truncate max-w-[200px]">
                  {user?.institution_name || user?.school || user?.college || 'Registered'}
                </span>
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
        } else {
          setData({ recentEvaluations: [] })
        }
      } catch (err) {
        console.warn('Teacher analytics load notice:', err)
        setData({ recentEvaluations: [] })
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

  const activeStudents = Array.from(new Set(recentEvals.map((e) => e.student_name).filter(Boolean)))

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Executive Teacher Header */}
      <div className="relative overflow-hidden rounded-3xl bg-[var(--surface)] border border-[var(--border)] p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-2.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-bold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20 flex items-center gap-1.5">
                <Building2 size={15} /> {isCollege ? 'Higher Education Faculty' : 'School Educator'}
              </span>
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 flex items-center gap-1.5">
                <UserCheck size={15} /> Faculty Verified
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl md:text-[32px] font-extrabold tracking-tight text-[var(--text)]">
              Welcome, {user?.name || 'Faculty'}
            </h1>
            <p className="text-sm sm:text-base text-[var(--text-soft)] font-medium">
              {user?.institution_name || 'LearnSphere Academic Network'} · {isCollege ? (user?.department || 'Department') : (user?.board || 'Board')}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <Button onClick={() => navigate('/app/evaluate')} className="flex items-center gap-2 shadow-xs px-4 sm:px-5 py-2.5 text-sm sm:text-base font-bold">
              <FileText size={18} /> Evaluate Script
            </Button>
            <Button variant="secondary" onClick={() => navigate('/app/action-center')} className="flex items-center gap-2 px-4 sm:px-5 py-2.5 text-sm sm:text-base font-bold">
              <Zap size={18} /> Action Center
            </Button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <StatCard
          label="Evaluations Graded"
          value={loading ? '…' : recentEvals.length}
          delta="Stored answer scripts"
          deltaTone="up"
          icon={FileText}
        />
        <StatCard
          label="Active Students"
          value={loading ? '…' : activeStudents.length}
          delta="Graded student roster"
          deltaTone="up"
          icon={UserCheck}
        />
        <StatCard
          label="Department / Level"
          value={isCollege ? (user?.department || 'Higher Ed') : (user?.board || 'School')}
          delta="Institutional branch"
          deltaTone="neutral"
          icon={Building2}
        />
        <StatCard
          label="Institution"
          value={user?.institution_name ? user.institution_name.slice(0, 16) : 'LearnSphere'}
          delta="Verified faculty portal"
          deltaTone="neutral"
          icon={ShieldCheck}
        />
      </div>

      {/* Main Grid: Teaching Workflow Tools + Evaluation Roster */}
      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-6">
        {/* Left Column: Faculty Intelligence Hub */}
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Faculty Command Suite"
              subtitle="Deterministic script grading, diagnostic heatmaps & remediation workflows"
            />
            <div className="grid sm:grid-cols-2 gap-4">
              <button
                onClick={() => navigate('/app/evaluate')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-[var(--accent-soft)] flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <FileText size={24} className="text-[var(--accent)]" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Evaluate Answer Scripts</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Upload question papers and student scripts for verified OCR evaluation and rubrics.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/action-center')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Zap size={24} className="text-amber-600 dark:text-amber-400" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Action Center</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Prioritized student interventions, feedback assignments, and remediation workflows.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/misconception-map')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Map size={24} className="text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Misconception Heatmap</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Identify specific syllabus concept flaws and question-level error patterns across the class.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/analytics')}
                className="p-5 sm:p-6 rounded-2xl border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <TrendingUp size={24} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-base sm:text-lg font-bold text-[var(--text)]">Class Analytics</div>
                <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-1.5 leading-relaxed">
                  Score distributions, question-level accuracy tiers, and longitudinal trends.
                </div>
              </button>
            </div>
          </Card>

          {/* Quick Shortcuts */}
          <div className="grid sm:grid-cols-3 gap-3.5">
            <button
              onClick={() => navigate('/app/students')}
              className="p-4 sm:p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <Users size={20} className="text-[var(--accent)]" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">Roster</span>
              </div>
              <div className="text-sm sm:text-base font-bold text-[var(--text)]">Student Roster</div>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-0.5">Enrolled cohort</div>
            </button>

            <button
              onClick={() => navigate('/app/reports')}
              className="p-4 sm:p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <FileText size={20} className="text-teal-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">Reports</span>
              </div>
              <div className="text-sm sm:text-base font-bold text-[var(--text)]">Academic Reports</div>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-0.5">PDF report downloads</div>
            </button>

            <button
              onClick={() => navigate('/app/plagiarism')}
              className="p-4 sm:p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <ShieldCheck size={20} className="text-amber-600" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">Audit</span>
              </div>
              <div className="text-sm sm:text-base font-bold text-[var(--text)]">Plagiarism Audit</div>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] mt-0.5">Similarity checks</div>
            </button>
          </div>
        </div>

        {/* Right Column: Recent Evaluated Scripts */}
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Recent Evaluated Scripts"
              subtitle="Graded answer papers with verified marks"
              action={
                <Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>
                  View all <ChevronRight size={15} className="ml-1" />
                </Button>
              }
            />

            {loading ? (
              <div className="py-12 text-center text-xs sm:text-sm text-[var(--text-soft)] animate-pulse">
                Loading graded scripts…
              </div>
            ) : !hasEvaluations ? (
              <div className="py-10 text-center border border-dashed border-[var(--border)] rounded-2xl p-6 bg-[var(--surface-alt)]/30">
                <FileText size={40} className="text-[var(--accent)] mx-auto mb-2.5 opacity-80" />
                <div className="text-sm sm:text-base font-bold text-[var(--text)] mb-1">No Evaluated Scripts Yet</div>
                <p className="text-xs sm:text-sm text-[var(--text-soft)] max-w-xs mx-auto mb-4 leading-relaxed">
                  Upload Question Papers and Student Answer Scripts in Evaluate to generate automated grading, rubrics, and diagnostic reports.
                </p>
                <Button size="sm" onClick={() => navigate('/app/evaluate')} className="mx-auto text-xs sm:text-sm font-semibold">
                  Evaluate First Script
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
                      className="py-3.5 flex items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-3 rounded-xl cursor-pointer transition-colors"
                    >
                      <div className="min-w-0 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 font-bold text-xs">
                          <FileText size={18} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm sm:text-base font-bold text-[var(--text)] truncate">
                            {e.student_name || 'Student'} — {e.subject || 'Subject'}
                          </div>
                          <div className="text-xs sm:text-[13px] text-[var(--text-soft)] mt-0.5 truncate">
                            {e.assessment_title || 'Exam'} · {e.created_at || 'Recently'}
                          </div>
                        </div>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <Badge tone={pct >= 75 ? 'success' : 'warning'}>
                          {pct}%
                        </Badge>
                        <ChevronRight size={15} className="text-[var(--text-faint)]" />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>

          {/* Faculty Profile Summary */}
          <Card className="p-5 sm:p-6">
            <div className="text-xs sm:text-sm font-bold text-[var(--text-faint)] uppercase tracking-wider mb-3.5">
              Faculty Profile Details
            </div>
            <div className="text-xs sm:text-sm space-y-2.5 text-[var(--text-soft)]">
              <div className="flex justify-between items-center py-2 border-b border-[var(--border)]">
                <span>Faculty Name</span>
                <span className="font-bold text-[var(--text)]">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-[var(--border)]">
                <span>Email ID</span>
                <span className="font-bold text-[var(--text)] truncate max-w-[200px]">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span>Institution</span>
                <span className="font-bold text-[var(--text)] truncate max-w-[200px]">
                  {user?.institution_name || 'LearnSphere Academic Portal'}
                </span>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
