import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, StatCard, RowItem, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { Sparkles, FileText, ArrowRight, AlertCircle, RefreshCw, BookOpen, Brain, Microscope, Trophy } from 'lucide-react'

export default function Dashboard() {
  const { role, authenticated, authLoading, user } = useApp()

  // 1. Loading User State
  if (authLoading) {
    return <DashboardLoadingSkeleton />
  }

  // 2. Unauthenticated State
  if (!authenticated || !user) {
    return <UnauthenticatedState />
  }

  // 3. Role Validation & Routing
  return role === 'teacher' ? <TeacherDashboard /> : <StudentDashboard />
}

// ── Skeletons & Fallback States ───────────────────────────────────────────────

function DashboardLoadingSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-busy="true" aria-label="Loading dashboard data">
      <div>
        <div className="h-7 w-64 bg-[var(--surface-alt)] rounded-md mb-2" />
        <div className="h-4 w-96 bg-[var(--surface-alt)] rounded-md opacity-60" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="h-24 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]" />
        ))}
      </div>
      <div className="h-64 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]" />
    </div>
  )
}

function UnauthenticatedState() {
  const navigate = useNavigate()
  return (
    <Card className="p-10 text-center my-10 max-w-md mx-auto">
      <AlertCircle size={40} className="text-[var(--warning)] mx-auto mb-3" />
      <h2 className="text-xl font-bold mb-2">Session Required</h2>
      <p className="text-sm text-[var(--text-soft)] mb-6">
        Please log in with your credentials to access your personalized learning dashboard.
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
  const { user } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  
  // Guard against race conditions across user account switches
  const activeUserIdRef = useRef(user?.id || user?._id || user?.email)

  useEffect(() => {
    const currentUserId = user?.id || user?._id || user?.email
    activeUserIdRef.current = currentUserId
    
    async function loadStudentDashboard() {
      setLoading(true)
      setError(null)

      try {
        const res = await api.getDashboardAnalytics('student', user?.name || '')
        // Prevent setting state if user switched while request was in-flight
        if (activeUserIdRef.current !== currentUserId) return

        if (res && res.success) {
          setData(res)
        } else {
          setError(res?.error || 'Failed to load your student dashboard analytics.')
        }
      } catch (err) {
        if (activeUserIdRef.current === currentUserId) {
          setError(err?.message || 'Unable to connect to the analytics server.')
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

  // Profile data extraction (authoritative from MongoDB user object)
  const isCollege = user?.level === 'college'
  const isSchool = user?.level === 'school'

  // Dynamic Academic Format without hardcoded fallbacks
  let academicLevelLabel = 'Not configured'
  if (isCollege) academicLevelLabel = 'COLLEGE'
  else if (isSchool) academicLevelLabel = 'SCHOOL'

  let programSubtitle = 'Profile setup required'
  if (isCollege) {
    const parts = [user?.department || user?.domain || user?.stream, user?.semester ? `Semester ${user.semester}` : null].filter(Boolean)
    programSubtitle = parts.length > 0 ? `College Student · ${parts.join(' - ')}` : 'College Student (Program not configured)'
  } else if (isSchool) {
    const parts = [user?.board, user?.grade_level || user?.classLevel ? `Class ${user.grade_level || user.classLevel}` : null, user?.section ? `Section ${user.section}` : null].filter(Boolean)
    programSubtitle = parts.length > 0 ? `School Student · ${parts.join(' - ')}` : 'School Student (Grade not configured)'
  }

  let programStatValue = 'Not configured'
  if (isCollege) {
    programStatValue = user?.domain || user?.department || user?.stream || 'Higher Education'
  } else if (isSchool) {
    if (user?.grade_level || user?.classLevel) {
      programStatValue = `Class ${user.grade_level || user.classLevel}${user?.section ? ` (${user.section})` : ''}`
    } else if (user?.board) {
      programStatValue = `${user.board} Board`
    }
  }

  const recentEvals = data?.recentEvaluations || []
  const weakTopics = data?.weakTopics || []
  const hasEvaluations = recentEvals.length > 0

  // Calculate average score across authenticated user's graded exams
  const avgScore = hasEvaluations
    ? Math.round(recentEvals.reduce((acc, curr) => acc + (Number(curr.percentage) || 0), 0) / recentEvals.length)
    : null

  // Error Loading State
  if (error && !data) {
    return (
      <div className="py-8">
        <Card className="p-8 text-center max-w-lg mx-auto border-[var(--error)]">
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
    <>
      {/* Personalized Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Welcome back, {user?.name || 'Student'}.</h1>
        <p className="text-[var(--text-soft)] text-sm">
          {programSubtitle}
        </p>
      </div>

      {/* Account Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-5">
        <StatCard 
          label="Account Level" 
          value={academicLevelLabel} 
          delta={isCollege ? (user?.stream || user?.domain || 'University Degree') : (user?.board || 'School Board')} 
          deltaTone={academicLevelLabel !== 'Not configured' ? 'up' : 'neutral'} 
        />
        <StatCard 
          label="Evaluations Graded" 
          value={loading ? '...' : recentEvals.length} 
          delta="Stored in MongoDB" 
        />
        <StatCard 
          label="Mastery Average" 
          value={loading ? '...' : (avgScore !== null ? `${avgScore}%` : 'No data')} 
          delta={avgScore !== null ? (avgScore >= 75 ? 'Strong performance' : 'Areas to improve') : 'Take your first test'} 
          deltaTone={avgScore !== null && avgScore >= 75 ? 'up' : 'neutral'}
        />
        <StatCard 
          label="Academic Program" 
          value={programStatValue} 
          delta={user?.institution_name || user?.school || 'LearnSphere AI'} 
        />
      </div>

      {/* Main Content Area */}
      {loading ? (
        <div className="h-64 bg-[var(--surface)] rounded-xl border border-[var(--border)] flex items-center justify-center text-sm text-[var(--text-soft)] animate-pulse">
          Loading your student evaluation history...
        </div>
      ) : !hasEvaluations ? (
        /* Empty Dashboard State */
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <FileText size={42} className="text-[var(--accent)] mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">No Graded Evaluations Yet</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto mb-5">
            Your personal evaluation record is empty. Upload a Question Paper and handwritten Answer Script to receive instant, strict AI grading and step-by-step feedback.
          </p>
          <div className="flex flex-wrap justify-center gap-3">
            <Button onClick={() => navigate('/app/self-evaluation')} className="flex items-center gap-2">
              Start Self Evaluation <ArrowRight size={14} />
            </Button>
            <Button variant="outline" onClick={() => navigate('/app/trainer')}>
              Practice with AI Trainer
            </Button>
          </div>
        </Card>
      ) : (
        /* Populated Dashboard */
        <div className="grid md:grid-cols-[1.6fr_1fr] gap-4 mb-4">
          <Card>
            <CardHeader 
              title="My Graded Answer Scripts" 
              action={<Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>View all</Button>} 
            />
            <div className="divide-y divide-[var(--border)]">
              {recentEvals.map((e, i) => (
                <RowItem
                  key={e.id || e._id || i}
                  title={`${e.subject || 'Subject'} — ${e.assessment_title || 'Assessment'}`}
                  subtitle={`Graded ${e.created_at || 'Recently'}`}
                  right={
                    <Badge tone={Number(e.percentage) >= 75 ? 'success' : Number(e.percentage) >= 50 ? 'warning' : 'error'}>
                      {e.percentage}% {e.grade ? `(${e.grade})` : ''}
                    </Badge>
                  }
                />
              ))}
            </div>
          </Card>

          <div className="space-y-4">
            {/* Quick Practice Access */}
            <Card className="p-4">
              <h3 className="font-bold text-sm mb-3">Interactive Learning Tools</h3>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => navigate('/app/trainer')}
                  className="p-3 rounded-lg border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group"
                >
                  <Brain size={18} className="text-[var(--accent)] mb-1 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-[var(--text)]">AI Trainer</div>
                  <div className="text-[11px] text-[var(--text-soft)]">Doubt solving</div>
                </button>
                <button
                  onClick={() => navigate('/app/reality-lab')}
                  className="p-3 rounded-lg border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group"
                >
                  <Microscope size={18} className="text-[var(--success)] mb-1 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-[var(--text)]">Reality Lab</div>
                  <div className="text-[11px] text-[var(--text-soft)]">Real scenarios</div>
                </button>
                <button
                  onClick={() => navigate('/app/knowledge-challenge')}
                  className="p-3 rounded-lg border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group"
                >
                  <Trophy size={18} className="text-[var(--warning)] mb-1 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-[var(--text)]">Knowledge Quiz</div>
                  <div className="text-[11px] text-[var(--text-soft)]">Test skills</div>
                </button>
                <button
                  onClick={() => navigate('/app/self-evaluation')}
                  className="p-3 rounded-lg border border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface-alt)] text-left transition-all group"
                >
                  <BookOpen size={18} className="text-[var(--accent)] mb-1 group-hover:scale-110 transition-transform" />
                  <div className="text-xs font-bold text-[var(--text)]">Self Eval</div>
                  <div className="text-[11px] text-[var(--text-soft)]">Grade paper</div>
                </button>
              </div>
            </Card>

            {/* Account Metadata Summary */}
            <Card className="p-4">
              <h3 className="font-bold text-xs uppercase tracking-wider text-[var(--text-faint)] mb-2.5">Account Credentials</h3>
              <div className="text-xs space-y-1.5 text-[var(--text-soft)]">
                <div>Student Name: <strong className="text-[var(--text)]">{user?.name}</strong></div>
                <div>Account ID: <strong className="text-[var(--text)]">{user?.email}</strong></div>
                <div>Institution: <strong className="text-[var(--text)]">{user?.institution_name || user?.school || 'Not configured'}</strong></div>
              </div>
            </Card>
          </div>
        </div>
      )}
    </>
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

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Welcome, {user?.name || 'Teacher'}.</h1>
        <p className="text-[var(--text-soft)] text-sm">
          Teacher Portal · {isCollege ? `College Faculty (${user?.department || 'Higher Education'})` : `School Educator (${user?.board || 'School'})`}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-5">
        <StatCard 
          label="Account Role" 
          value="TEACHER" 
          delta={isCollege ? (user?.department || 'College Dept') : (user?.board || 'School Board')} 
          deltaTone="up" 
        />
        <StatCard label="Evaluations Stored" value={loading ? '...' : recentEvals.length} delta="in Database" />
        <StatCard label="Active Roster" value={loading ? '...' : (recentEvals.length > 0 ? Array.from(new Set(recentEvals.map(e => e.student_name))).length : 0)} delta="Graded Students" />
        <StatCard label="Institution" value={user?.institution_name || 'LearnSphere AI'} delta={isCollege ? 'Higher Education' : (user?.board || 'School')} />
      </div>

      {loading ? (
        <div className="h-64 bg-[var(--surface)] rounded-xl border border-[var(--border)] flex items-center justify-center text-sm text-[var(--text-soft)] animate-pulse">
          Loading your evaluation roster...
        </div>
      ) : !hasEvaluations ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <FileText size={42} className="text-[var(--accent)] mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">No evaluations submitted yet</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto mb-5">
            Go to <strong>Evaluate Answer Script</strong> from the sidebar to upload a Question Paper and handwritten Answer Script for strict AI grading.
          </p>
          <Button onClick={() => navigate('/app/evaluate')} className="mx-auto">
            Go to Evaluation Page
          </Button>
        </Card>
      ) : (
        <div className="grid md:grid-cols-[1.55fr_1fr] gap-3.5 mb-3.5">
          <Card>
            <CardHeader title="Recent Evaluations" action={<Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>View all</Button>} />
            <div className="divide-y divide-[var(--border)]">
              {recentEvals.map((e, i) => (
                <RowItem
                  key={e.id || e._id || i}
                  title={`${e.student_name || 'Student'} — ${e.subject || 'Subject'}`}
                  subtitle={`${e.assessment_title || 'Exam'} · ${e.created_at || 'Recently'}`}
                  right={<Badge tone={Number(e.percentage) >= 75 ? 'success' : 'warning'}>{e.percentage}%</Badge>}
                />
              ))}
            </div>
          </Card>
          <Card>
            <CardHeader title="Account Profile" />
            <div className="p-4 bg-[var(--surface-alt)] rounded-lg text-xs leading-relaxed text-[var(--text-soft)] space-y-1.5">
              <div>Logged in as <strong>{user?.name}</strong> ({user?.email}).</div>
              <div>Institution: <strong>{user?.institution_name || 'Configured Profile'}</strong></div>
              <div>Level: <strong>{isCollege ? 'College Educator' : `School Educator (${user?.board || 'Board'})`}</strong></div>
            </div>
          </Card>
        </div>
      )}
    </>
  )
}
