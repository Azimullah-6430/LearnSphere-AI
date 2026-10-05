import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, StatCard, RowItem, Badge, Button } from '../components/ui/Primitives.jsx'
import { TrendChart, SubjectBarChart } from '../components/charts/Charts.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { Sparkles, FileText, ArrowRight } from 'lucide-react'

export default function Dashboard() {
  const { role } = useApp()
  return role === 'teacher' ? <TeacherDashboard /> : <StudentDashboard />
}

function TeacherDashboard() {
  const navigate = useNavigate()
  const { user } = useApp()
  const [data, setData] = useState(null)

  useEffect(() => {
    async function loadAnalytics() {
      const res = await api.getDashboardAnalytics('teacher', user?.name || '')
      if (res && res.success) {
        setData(res)
      }
    }
    loadAnalytics()
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
        <StatCard label="Evaluations Stored" value={recentEvals.length} delta="in Database" />
        <StatCard label="Active Roster" value={recentEvals.length > 0 ? Array.from(new Set(recentEvals.map(e => e.student_name))).length : 0} delta="Graded Students" />
        <StatCard label="Institution" value={user?.institution_name || 'LearnSphere AI'} delta={isCollege ? 'Higher Education' : (user?.board || 'School')} />
      </div>

      {!hasEvaluations ? (
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
            {recentEvals.map((e, i) => (
              <RowItem
                key={e.id || i}
                title={`${e.student_name} — ${e.subject}`}
                subtitle={`${e.assessment_title || 'Exam'} · ${e.created_at || 'Recently'}`}
                right={<Badge tone={e.status || 'success'}>{e.percentage}%</Badge>}
              />
            ))}
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

function StudentDashboard() {
  const navigate = useNavigate()
  const { user } = useApp()
  const [data, setData] = useState(null)

  useEffect(() => {
    async function loadAnalytics() {
      const res = await api.getDashboardAnalytics('student', user?.name || '')
      if (res && res.success) {
        setData(res)
      }
    }
    loadAnalytics()
  }, [user])

  const recentEvals = data?.recentEvaluations || []
  const hasEvaluations = recentEvals.length > 0
  const isCollege = user?.level === 'college'

  return (
    <>
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-1">Welcome back, {user?.name || 'Student'}.</h1>
        <p className="text-[var(--text-soft)] text-sm">
          Student Portal · {isCollege ? `College Student (${[user?.stream, user?.domain].filter(Boolean).join(' - ') || 'Higher Education'})` : `School Student (${[user?.board, user?.grade_level ? `Class ${user.grade_level}` : null].filter(Boolean).join(' - ') || 'General Education'})`}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-5">
        <StatCard 
          label="Account Level" 
          value={isCollege ? 'COLLEGE' : 'SCHOOL'} 
          delta={isCollege ? (user?.stream || user?.domain || 'University Degree') : (user?.board || 'School Board')} 
          deltaTone="up" 
        />
        <StatCard label="Evaluations Graded" value={recentEvals.length} delta="stored in Database" />
        <StatCard label="Registered Email" value={user?.email || 'Student'} delta="Permanent ID" />
        <StatCard label="Academic Program" value={isCollege ? (user?.domain || user?.stream || user?.department || 'College Program') : (user?.grade_level ? `Class ${user.grade_level}` : (user?.board ? `${user.board} School` : 'School Program'))} />
      </div>

      {!hasEvaluations ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <FileText size={42} className="text-[var(--accent)] mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">Welcome to LearnSphere AI</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto mb-5">
            You don't have any graded exam papers yet. Navigate to <strong>Self Evaluation</strong> or <strong>My Evaluations</strong> in the sidebar to upload a Question Paper and Answer Script for strict AI grading.
          </p>
          <Button onClick={() => navigate('/app/self-evaluation')} className="mx-auto flex items-center gap-2">
            Start Your First Evaluation <ArrowRight size={14} />
          </Button>
        </Card>
      ) : (
        <Card className="mb-3.5">
          <CardHeader title="My Graded Answer Scripts" action={<Button variant="ghost" size="sm" onClick={() => navigate('/app/history')}>View all</Button>} />
          {recentEvals.map((e, i) => (
            <RowItem
              key={e.id || i}
              title={`${e.subject} — ${e.assessment_title}`}
              subtitle={`Graded ${e.created_at || 'Recently'}`}
              right={<Badge tone={e.percentage >= 75 ? 'success' : 'warning'}>{e.percentage}% (Grade {e.grade})</Badge>}
            />
          ))}
        </Card>
      )}
    </>
  )
}
