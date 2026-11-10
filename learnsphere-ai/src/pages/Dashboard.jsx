import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../services/api.js'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
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
  Sparkles,
  Headphones,
  Volume2,
  VolumeX,
  Mic,
  Target,
  Award,
  ListChecks,
  ArrowUpRight
} from 'lucide-react'
import { speakText, stopSpeech, narrateMathClient } from '../utils/blindAudio.js'

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
      <div className="h-32 bg-[var(--surface-alt)] rounded-3xl border border-[var(--border)]" />
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
      <AlertCircle size={40} className="text-amber-600 mx-auto mb-3" />
      <h2 className="text-xl font-extrabold mb-2 text-slate-900 dark:text-white">Session Required</h2>
      <p className="text-sm text-slate-700 dark:text-slate-300 font-medium mb-6">
        Please sign in to access your personalized learning dashboard.
      </p>
      <Button onClick={() => navigate('/')} className="w-full font-bold">
        Sign In to LearnSphere
      </Button>
    </Card>
  )
}

// ── Student Dashboard ─────────────────────────────────────────────────────────

function StudentDashboard() {
  const navigate = useNavigate()
  const { user, streakDays, formattedSessionTime } = useApp()
  const { curriculum, subjects } = useAuthoritativeCurriculum()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Blind Learning Companion Integration (Prompt 6)
  const isBlindCompanionEnabled = Boolean(user?.is_disabled_student || user?.blind_companion_enabled)
  const [blindGaps, setBlindGaps] = useState([])
  const [blindLearningPath, setBlindLearningPath] = useState(null)
  const [isSpeakingOverview, setIsSpeakingOverview] = useState(false)

  useEffect(() => {
    if (isBlindCompanionEnabled) {
      api.getBlindLearningGaps().then(res => {
        if (res && res.success && Array.isArray(res.learning_gaps)) {
          setBlindGaps(res.learning_gaps)
        }
      }).catch(() => {})

      api.getBlindLearningPath().then(res => {
        if (res && res.success && res.learning_path) {
          setBlindLearningPath(res.learning_path)
        }
      }).catch(() => {})
    }
  }, [isBlindCompanionEnabled])

  useEffect(() => {
    async function loadStudentDashboard() {
      setLoading(true)
      try {
        const res = await api.getDashboardAnalytics('student', user?.name || '')
        if (res && res.success) {
          setData(res)
        } else {
          setData({ recentEvaluations: [], stats: {} })
        }
      } catch (err) {
        console.warn('Student dashboard load notice:', err)
        setError('Could not connect to cloud records. Operating in local mode.')
        setData({ recentEvaluations: [], stats: {} })
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

  const currentSem =
    user?.semester !== undefined && user?.semester !== null
      ? user?.semester
      : user?.current_semester !== undefined && user?.current_semester !== null
      ? user?.current_semester
      : user?.currentSemester ?? null

  const hasCollegeSemester = isCollege && currentSem !== null && currentSem !== '' && !isNaN(Number(currentSem))

  let academicBadge = 'Student'
  if (isCollege) {
    academicBadge = `College · ${user?.degree || 'Undergrad'} · ${user?.department || user?.branch || 'Engineering'}${currentSem ? ` · Sem ${currentSem}` : ''}`
  } else if (isSchool) {
    academicBadge = `School · ${user?.board || 'CBSE'} · Class ${user?.grade_level || user?.classLevel || '12'}`
  }

  const recentEvals = data?.recentEvaluations || []
  const hasEvaluations = recentEvals.length > 0
  const stats = data?.stats || {}

  const totalEvalsCount = stats.total_evaluations ?? recentEvals.length

  const avgScore =
    stats.average_mastery !== undefined && stats.average_mastery !== null
      ? stats.average_mastery
      : hasEvaluations
      ? Math.round(recentEvals.reduce((acc, curr) => acc + (Number(curr.percentage) || 0), 0) / recentEvals.length)
      : null

  const topWeakConcept = stats.top_practice_concept || (data?.weakTopics?.[0]?.concept || data?.weakTopics?.[0]?.identified_concept || '')

  if (error && !data) {
    return (
      <div className="py-8">
        <Card className="p-8 text-center max-w-lg mx-auto border-rose-300 dark:border-rose-900 shadow-sm">
          <AlertCircle size={36} className="text-rose-600 mx-auto mb-3" />
          <h2 className="text-xl font-extrabold mb-1 text-slate-900 dark:text-white">Error Loading Dashboard</h2>
          <p className="text-sm text-slate-700 dark:text-slate-300 font-medium mb-5">{error}</p>
          <Button onClick={() => window.location.reload()} className="mx-auto flex items-center gap-2 font-bold">
            <RefreshCw size={14} /> Retry Connection
          </Button>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Accessible Blind Learning Hub (Prompt 6 - Exclusive to disabled/blind students) */}
      {isBlindCompanionEnabled && (
        <div className="p-6 sm:p-7 rounded-3xl bg-indigo-50/90 dark:bg-indigo-950/40 border-2 border-indigo-300 dark:border-indigo-800 space-y-6 shadow-sm">
          {/* Accessible Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-indigo-200 dark:border-indigo-800">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                <Headphones size={24} />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-extrabold uppercase tracking-wider text-indigo-700 dark:text-indigo-300">
                    Blind Learning Companion
                  </span>
                  <Badge tone="accent">Accessible Hub</Badge>
                </div>
                <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white">
                  Accessible Learning Dashboard
                </h2>
              </div>
            </div>

            {/* Spoken Overview Button */}
            <button
              type="button"
              onClick={() => {
                if (isSpeakingOverview) {
                  stopSpeech()
                  setIsSpeakingOverview(false)
                } else {
                  const nextStepDesc = blindLearningPath?.steps?.[0]?.title || 'Personal Tutor Lesson'
                  const gapsCount = blindGaps.length
                  const syllabusText = subjects.length ? `Your enrolled subjects are: ${subjects.join(', ')}.` : 'No uploaded syllabus found.'
                  const speech = `Welcome to your Accessible Learning Hub. ${syllabusText} You have ${gapsCount} diagnosed concept areas to improve. Your recommended next lesson is: ${nextStepDesc}. Average mastery: ${avgScore ?? 75} percent.`
                  speakText(speech, 'Accessible Hub Overview')
                  setIsSpeakingOverview(true)
                }
              }}
              className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-bold flex items-center gap-2 cursor-pointer shadow-xs shrink-0"
              aria-label="Listen to Accessible Dashboard Summary aloud"
            >
              {isSpeakingOverview ? <VolumeX size={16} /> : <Volume2 size={16} />}
              <span>{isSpeakingOverview ? 'Stop Speech' : 'Listen Dashboard Overview'}</span>
            </button>
          </div>

          {/* Section 1 & 2: Uploaded Syllabus & Recommended Next Lesson */}
          <div className="grid md:grid-cols-2 gap-4">
            {/* My Uploaded Syllabus */}
            <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800/80 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-400">
                  <BookOpen size={15} />
                  <span>My Uploaded Syllabus</span>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    const text = subjects.length
                      ? `Uploaded Syllabus contains ${subjects.length} subjects: ${subjects.join(', ')}.`
                      : 'No syllabus uploaded yet.'
                    speakText(text, 'Uploaded Syllabus')
                  }}
                  className="text-xs font-bold px-2 py-1 rounded bg-indigo-100 dark:bg-indigo-950 text-indigo-800 dark:text-indigo-300 flex items-center gap-1 cursor-pointer"
                  aria-label="Read uploaded syllabus details"
                >
                  <Volume2 size={12} />
                  <span>Listen</span>
                </button>
              </div>
              <div>
                <div className="text-base font-bold text-slate-900 dark:text-white">
                  {curriculum?.board_or_university || curriculum?.institution_name || (subjects.length > 0 ? `${subjects.length} Enrolled Courses` : 'No Syllabus Uploaded')}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                  {subjects.length > 0 ? `Subjects: ${subjects.join(', ')}` : 'Upload your semester syllabus to unlock automated concept breakdowns.'}
                </p>
              </div>
              <div className="pt-2 flex items-center gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => navigate('/app/settings')}
                  className="text-xs font-bold"
                >
                  Manage Syllabus
                </Button>
              </div>
            </div>

            {/* Recommended Next Lesson (from authentic adaptive_learning_path) */}
            <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800/80 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                  <Sparkles size={15} />
                  <span>Recommended Next Lesson</span>
                </div>
                {blindLearningPath?.steps?.[0] && (
                  <button
                    type="button"
                    onClick={() => {
                      const s = blindLearningPath.steps[0]
                      speakText(`Next recommended lesson: ${s.title}. Reason: ${s.reason || s.description || 'Targeted concept understanding'}.`, 'Next Lesson')
                    }}
                    className="text-xs font-bold px-2 py-1 rounded bg-emerald-100 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-300 flex items-center gap-1 cursor-pointer"
                  >
                    <Volume2 size={12} />
                    <span>Listen</span>
                  </button>
                )}
              </div>
              <div>
                <div className="text-base font-bold text-slate-900 dark:text-white leading-snug">
                  {blindLearningPath?.steps?.[0]?.title || (blindGaps[0]?.topic ? `Reinforce: ${blindGaps[0].topic}` : 'Study Core Concepts with Personal Trainer')}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                  {blindLearningPath?.steps?.[0]?.reason || (blindGaps[0]?.observed_gap ? `Diagnosed gap: ${blindGaps[0].observed_gap}` : 'Personalized based on your validated syllabus.')}
                </p>
              </div>
              <div className="pt-2 flex items-center gap-2">
                <Button
                  size="sm"
                  onClick={() => {
                    const targetTopic = blindLearningPath?.steps?.[0]?.topic || blindGaps[0]?.topic || ''
                    const targetSubject = blindLearningPath?.steps?.[0]?.subject || blindGaps[0]?.subject || subjects[0] || ''
                    navigate('/app/trainer', { state: { topic: targetTopic, subject: targetSubject } })
                  }}
                  className="text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700"
                >
                  Start Audio Lesson <ArrowRight size={13} className="ml-1" />
                </Button>
              </div>
            </div>
          </div>

          {/* Section 3: Concepts I Need to Improve (from authentic blind_learning_gaps) */}
          <div className="p-5 rounded-2xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800/80 space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-amber-600 dark:text-amber-400">
                <Target size={15} />
                <span>Concepts I Need to Improve ({blindGaps.length})</span>
              </div>
              {blindGaps.length > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    const text = `You have ${blindGaps.length} concept areas diagnosed with gaps: ${blindGaps.map((g, i) => `Concept ${i + 1}: ${g.topic || g.concept}. ${g.observed_gap || ''}`).join('. ')}`
                    speakText(text, 'Diagnosed Learning Gaps')
                  }}
                  className="text-xs font-bold px-2 py-1 rounded bg-amber-100 dark:bg-amber-950 text-amber-800 dark:text-amber-300 flex items-center gap-1 cursor-pointer"
                >
                  <Volume2 size={12} />
                  <span>Listen All Gaps</span>
                </button>
              )}
            </div>

            {blindGaps.length === 0 ? (
              <p className="text-xs text-slate-500 py-1">
                No learning gaps identified yet. Complete tests or challenges to detect areas needing reinforcement.
              </p>
            ) : (
              <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-3 pt-1">
                {blindGaps.slice(0, 6).map((gap, gIdx) => (
                  <div
                    key={gIdx}
                    className="p-3.5 rounded-xl border border-amber-200 dark:border-amber-800/60 bg-amber-50/50 dark:bg-amber-950/20 space-y-2 flex flex-col justify-between"
                  >
                    <div>
                      <div className="flex items-center justify-between text-[11px] font-bold text-amber-800 dark:text-amber-300">
                        <span className="truncate">{gap.subject || 'Syllabus'}</span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-200/60 dark:bg-amber-900/40 text-[10px]">
                          {gap.status || 'Needs Practice'}
                        </span>
                      </div>
                      <h4 className="text-xs font-extrabold text-slate-900 dark:text-white mt-1 line-clamp-1">
                        {gap.topic || gap.concept}
                      </h4>
                      {gap.observed_gap && (
                        <p className="text-[11px] text-slate-600 dark:text-slate-300 mt-1 line-clamp-2">
                          {gap.observed_gap}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center justify-between pt-2 border-t border-amber-200/60 dark:border-amber-800/40">
                      <button
                        type="button"
                        onClick={() => {
                          const speech = `Subject: ${gap.subject}. Topic: ${gap.topic}. Diagnosed gap: ${gap.observed_gap || 'Concept needs more guided practice'}.`
                          speakText(speech, `Gap: ${gap.topic}`)
                        }}
                        className="text-[11px] font-bold text-indigo-600 dark:text-indigo-400 flex items-center gap-1 hover:underline cursor-pointer"
                      >
                        <Volume2 size={11} />
                        <span>Listen</span>
                      </button>
                      <button
                        type="button"
                        onClick={() => navigate('/app/trainer', { state: { topic: gap.topic, subject: gap.subject } })}
                        className="text-[11px] font-bold text-amber-700 dark:text-amber-300 flex items-center gap-0.5 hover:underline cursor-pointer"
                      >
                        <span>Practice</span>
                        <ChevronRight size={12} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Section 4: Practice and Mastery Accessible Suite */}
          <div className="space-y-2">
            <div className="text-xs font-bold uppercase tracking-wider text-indigo-900 dark:text-indigo-300 flex items-center gap-1.5">
              <Award size={14} />
              <span>Practice &amp; Mastery Suite (Accessible)</span>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-2.5">
              {[
                { label: 'Personal Trainer', path: '/app/trainer', desc: 'Audio lesson tutor', icon: Brain },
                { label: 'Reality Lab', path: '/app/reality-lab', desc: 'Audio lab experiments', icon: Microscope },
                { label: 'Learn From Anywhere', path: '/app/learn-anywhere', desc: 'Low cost practicals', icon: Compass },
                { label: 'Knowledge Challenge', path: '/app/knowledge-challenge', desc: 'Spoken Q&A', icon: Zap },
                { label: 'Memory Cards', path: '/app/memory', desc: 'Audio revision cards', icon: BookOpen }
              ].map((item, idx) => {
                const Icon = item.icon
                return (
                  <button
                    key={idx}
                    type="button"
                    onClick={() => navigate(item.path)}
                    className="p-3 rounded-xl bg-white dark:bg-slate-900 border border-indigo-200 dark:border-indigo-800/80 hover:border-indigo-500 text-left transition-all cursor-pointer shadow-2xs group"
                    aria-label={`Open ${item.label}`}
                  >
                    <Icon size={18} className="text-indigo-600 dark:text-indigo-400 mb-1 group-hover:scale-110 transition-transform" />
                    <div className="text-xs font-bold text-slate-900 dark:text-white leading-tight">{item.label}</div>
                    <div className="text-[10px] text-slate-500 mt-0.5">{item.desc}</div>
                  </button>
                )
              })}
            </div>
          </div>
        </div>
      )}

      {/* Executive Student Header Banner */}
      <div className="relative overflow-hidden rounded-3xl bg-[var(--surface)] border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-2.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-extrabold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20 flex items-center gap-1.5">
                <GraduationCap size={16} /> {academicBadge}
              </span>
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-extrabold bg-amber-500/15 text-amber-900 dark:text-amber-200 border border-amber-500/30 flex items-center gap-1.5 whitespace-nowrap shadow-xs">
                <Flame size={16} className="text-amber-600 dark:text-amber-400 shrink-0" strokeWidth={2} /> 🔥 {streakDays || 1} {streakDays === 1 ? 'Day' : 'Days'} Streak
              </span>
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-extrabold bg-emerald-500/15 text-emerald-900 dark:text-emerald-200 border border-emerald-500/30 flex items-center gap-1.5 whitespace-nowrap shadow-xs">
                <CircleChevronUp size={16} className="text-emerald-600 dark:text-emerald-400 shrink-0" strokeWidth={2.2} /> ⏱️ {formattedSessionTime || '0s'} Active
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl md:text-[34px] font-extrabold tracking-tight text-slate-900 dark:text-white">
              Welcome back, {user?.name || 'Student'}
            </h1>
            <p className="text-sm sm:text-base text-slate-700 dark:text-slate-300 font-semibold">
              {user?.institution_name || user?.school || user?.college || 'LearnSphere Academic Network'}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            {!isBlindCompanionEnabled ? (
              <Button
                onClick={() => navigate('/app/self-evaluation')}
                className="flex items-center gap-2 shadow-xs px-4 sm:px-5 py-2.5 text-sm sm:text-base font-extrabold"
              >
                <FileCheck size={18} /> Self-Evaluation
              </Button>
            ) : (
              <Button
                onClick={() => navigate('/app/blind-companion')}
                className="flex items-center gap-2 shadow-xs px-4 sm:px-5 py-2.5 text-sm sm:text-base font-extrabold bg-indigo-600 hover:bg-indigo-700 text-white"
              >
                <Headphones size={18} /> Blind Companion
              </Button>
            )}
            <Button
              variant="secondary"
              onClick={() => navigate('/app/trainer')}
              className="flex items-center gap-2 px-4 sm:px-5 py-2.5 text-sm sm:text-base font-extrabold"
            >
              <Brain size={18} /> Personal Trainer
            </Button>
          </div>
        </div>
      </div>

      {/* Recommended Next Action Banner */}
      <div className="p-5 sm:p-6 rounded-2xl bg-gradient-to-r from-[var(--accent-soft)] via-[var(--surface)] to-[var(--surface-alt)] border border-[var(--accent)]/30 flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center shrink-0 shadow-xs mt-0.5">
            <Sparkles size={24} />
          </div>
          <div>
            <div className="text-xs sm:text-[13px] font-extrabold uppercase tracking-wider text-[var(--accent)] mb-1">
              Recommended Next Action
            </div>
            <div className="text-base sm:text-lg md:text-xl font-extrabold text-slate-900 dark:text-white leading-snug">
              {topWeakConcept
                ? `Targeted Concept Review: ${topWeakConcept}`
                : isBlindCompanionEnabled
                ? (blindLearningPath?.steps?.[0]?.title || 'Advance Syllabus Mastery with Audio Companion')
                : !hasEvaluations
                ? 'Upload and Grade Your Handwritten Exam Script'
                : 'Advance Syllabus Mastery with Personal AI Trainer'}
            </div>
            <div className="text-xs sm:text-sm md:text-[15px] text-slate-700 dark:text-slate-300 font-medium mt-1 leading-relaxed max-w-2xl">
              {topWeakConcept
                ? (isBlindCompanionEnabled
                    ? `Audio diagnostic identified a concept to reinforce: "${topWeakConcept}". Listen to step-by-step audio explanations and test understanding.`
                    : `Diagnostic evaluations identified a learning gap in "${topWeakConcept}". Review foundational principles and step-by-step solutions to secure full credit.`)
                : isBlindCompanionEnabled
                ? 'Listen to interactive audio explanations, intuitive real-world analogies, and spoken concept checks for your syllabus topics.'
                : !hasEvaluations
                ? 'Use automated OCR and rubric evaluation to grade your paper against curriculum marking schemes and detect knowledge gaps.'
                : 'Get interactive Feynman derivations, intuitive real-world examples, and practice questions for your current syllabus topics.'}
            </div>
          </div>
        </div>

        <button
          onClick={() => {
            if (topWeakConcept) {
              navigate('/app/trainer', {
                state: {
                  subject: recentEvals[0]?.subject || subjects[0] || 'General',
                  concept: topWeakConcept,
                },
              })
            } else if (isBlindCompanionEnabled) {
              navigate('/app/blind-companion')
            } else if (!hasEvaluations) {
              navigate('/app/self-evaluation')
            } else {
              navigate('/app/trainer')
            }
          }}
          className="px-6 py-3 rounded-xl bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] transition-all font-extrabold text-sm sm:text-base flex items-center justify-center gap-2.5 shrink-0 shadow-sm cursor-pointer"
        >
          <span>
            {topWeakConcept
              ? `Master ${topWeakConcept.length > 20 ? topWeakConcept.slice(0, 18) + '…' : topWeakConcept}`
              : isBlindCompanionEnabled
              ? 'Start Audio Learning'
              : !hasEvaluations
              ? 'Start First Evaluation'
              : 'Resume AI Tutoring'}
          </span>
          <ArrowRight size={17} />
        </button>
      </div>

      {/* College Semester Incomplete Notice */}
      {isCollege && !hasCollegeSemester && (
        <div className="p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-300 dark:border-amber-800 rounded-2xl flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <AlertCircle size={20} className="text-amber-600 shrink-0" />
            <div className="text-xs sm:text-sm font-extrabold text-amber-900 dark:text-amber-300">
              Please configure your current semester in Settings to synchronize your course syllabus.
            </div>
          </div>
          <Button size="sm" onClick={() => navigate('/app/settings')} className="shrink-0 font-bold">
            Set Semester
          </Button>
        </div>
      )}

      {/* Metric Cards Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        {!isBlindCompanionEnabled ? (
          <StatCard
            label="Graded Papers"
            value={loading ? '…' : totalEvalsCount}
            delta="Verified answer scripts"
            deltaTone="up"
            icon={FileText}
          />
        ) : (
          <StatCard
            label="Accessible Topics"
            value={loading ? '…' : (blindGaps.length > 0 ? `${blindGaps.length} In Progress` : (subjects.length > 0 ? `${subjects.length} Enrolled` : 'Ready'))}
            delta="Audio-enabled syllabus"
            deltaTone="up"
            icon={Headphones}
          />
        )}
        <StatCard
          label="Mastery Average"
          value={loading ? '…' : avgScore !== null ? `${avgScore}%` : '—'}
          delta={
            avgScore !== null
              ? avgScore >= 75
                ? 'Distinction Tier (75%+)'
                : avgScore >= 60
                ? 'Proficient Tier (60%+)'
                : avgScore >= 40
                ? 'Passing Tier (40%+)'
                : 'Needs Support (<40%)'
              : isBlindCompanionEnabled
              ? 'Awaiting first audio quiz'
              : 'Awaiting first evaluation'
          }
          deltaTone={avgScore >= 75 ? 'up' : avgScore >= 50 ? 'warning' : 'down'}
          icon={TrendingUp}
        />
        <StatCard
          label="Study Streak"
          value={`${streakDays || 1} Days`}
          delta="Consecutive daily learning"
          deltaTone="up"
          icon={Flame}
        />
        <StatCard
          label="Academic Track"
          value={isCollege ? (user?.degree || 'Undergrad') : (user?.board || 'School')}
          delta={isCollege ? (user?.department || 'Engineering') : `Class ${user?.grade_level || user?.classLevel || '12'}`}
          deltaTone="neutral"
          icon={GraduationCap}
        />
      </div>

      {/* Main Grid: Interactive Learning Studios + Recent Evaluated Papers */}
      <div className="grid lg:grid-cols-[1.55fr_1fr] gap-6">
        {/* Left Column: Interactive AI Learning Studios */}
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Interactive AI Learning Studios"
              subtitle="Syllabus-aligned adaptive learning, experimental labs, and speed drills"
            />
            <div className="grid sm:grid-cols-2 gap-4">
              <button
                onClick={() => navigate('/app/trainer')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-[var(--accent-soft)] flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Brain size={24} className="text-[var(--accent)]" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-[var(--accent)] transition-colors">
                  Personal AI Trainer
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Conversational tutor with step-by-step Feynman derivations and syllabus mastery.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/learn-anywhere')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-teal-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Compass size={24} className="text-teal-600 dark:text-teal-400" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-teal-600 transition-colors">
                  Learn from Anywhere
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Low-resource experiential learning using everyday local materials and household items.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/reality-lab')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Microscope size={24} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-emerald-600 transition-colors">
                  Reality Lab
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Virtual science simulations and interactive hypothesis testing environments.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/knowledge-challenge')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Trophy size={24} className="text-amber-600 dark:text-amber-400" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-amber-600 transition-colors">
                  Knowledge Challenge
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Adaptive syllabus quizzes and timed speed drills for exam preparation.
                </div>
              </button>
            </div>
          </Card>

          {/* Productivity & Review Hub */}
          <div className="grid sm:grid-cols-3 gap-3.5">
            <button
              onClick={() => navigate('/app/focus')}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <Timer size={20} className="text-[var(--accent)]" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400">Timer</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">Focus Session</div>
              <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-0.5">Pomodoro & Soundscape</div>
            </button>

            <button
              onClick={() => navigate('/app/memory')}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <BookOpen size={20} className="text-teal-600 dark:text-teal-400" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400">Recall</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">Academic Memory</div>
              <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-0.5">Spaced Flashcards</div>
            </button>

            <button
              onClick={() => navigate('/app/opportunities')}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <Globe size={20} className="text-amber-600 dark:text-amber-400" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400">Feeds</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">Opportunities</div>
              <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-0.5">Contests & Fellowships</div>
            </button>
          </div>
        </div>

        {/* Right Column: Accessible Learning Hub (for blind students) or Evaluated Papers (for non-blind) */}
        <div className="space-y-6">
          {isBlindCompanionEnabled ? (
            <Card className="p-5 sm:p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white">Accessible Learning Hub</h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">Syllabus-guided audio learning &amp; practice</p>
                </div>
                <Badge tone="accent">Audio Mode</Badge>
              </div>

              <div className="space-y-3">
                <button
                  type="button"
                  onClick={() => navigate('/app/blind-companion')}
                  className="w-full p-4 rounded-2xl border border-indigo-200 dark:border-indigo-800 bg-indigo-50/50 dark:bg-indigo-950/30 hover:border-indigo-500 text-left transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0">
                      <Headphones size={20} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 transition-colors">
                        Blind Companion
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 truncate">
                        10-step audio lessons, equation narration &amp; concept diagrams
                      </div>
                    </div>
                    <ChevronRight size={16} className="text-indigo-500 shrink-0" />
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/app/knowledge-challenge')}
                  className="w-full p-4 rounded-2xl border border-amber-200 dark:border-amber-800 bg-amber-50/50 dark:bg-amber-950/30 hover:border-amber-500 text-left transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-amber-500 text-white flex items-center justify-center shrink-0">
                      <Sparkles size={20} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-amber-600 transition-colors">
                        Knowledge Challenge
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 truncate">
                        Spoken adaptive quizzes with voice &amp; keyboard responses
                      </div>
                    </div>
                    <ChevronRight size={16} className="text-amber-500 shrink-0" />
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => navigate('/app/trainer')}
                  className="w-full p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface-alt)]/60 hover:border-[var(--accent)] text-left transition-all cursor-pointer group"
                >
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0">
                      <Brain size={20} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-[var(--accent)] transition-colors">
                        Personal AI Trainer
                      </div>
                      <div className="text-xs text-slate-600 dark:text-slate-400 truncate">
                        Audio Feynman lessons and gap-targeted practice
                      </div>
                    </div>
                    <ChevronRight size={16} className="text-slate-400 shrink-0" />
                  </div>
                </button>
              </div>
            </Card>
          ) : (
            <Card>
              <CardHeader
                title="Recent Evaluated Papers"
                subtitle="Verified scores and diagnostic breakdown"
                action={
                  <Button variant="ghost" size="sm" onClick={() => navigate('/app/history')} className="font-bold">
                    View all <ChevronRight size={15} className="ml-1" />
                  </Button>
                }
              />

              {loading ? (
                <div className="py-12 text-center text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-semibold animate-pulse">
                  Loading recent evaluation records…
                </div>
              ) : !hasEvaluations ? (
                <div className="py-10 text-center border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl p-6 bg-[var(--surface-alt)]/30">
                  <FileText size={40} className="text-[var(--accent)] mx-auto mb-2.5 opacity-80" />
                  <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white mb-1">
                    No Evaluated Papers Found
                  </div>
                  <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium max-w-xs mx-auto mb-4 leading-relaxed">
                    Upload a Question Paper and your Handwritten Answer Script in Self-Evaluation for instant step-by-step grading.
                  </p>
                  <Button size="sm" onClick={() => navigate('/app/self-evaluation')} className="mx-auto text-xs sm:text-sm font-extrabold">
                    Start First Evaluation
                  </Button>
                </div>
              ) : (
                <div className="divide-y divide-slate-200 dark:divide-slate-800">
                  {recentEvals.slice(0, 5).map((e, idx) => {
                    const pct = Number(e.percentage) || 0
                    return (
                      <div
                        key={e.id || e._id || idx}
                        onClick={() => navigate('/app/history')}
                        className="py-3.5 flex items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-3 rounded-xl cursor-pointer transition-colors"
                      >
                        <div className="min-w-0 flex items-center gap-3">
                          <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 font-extrabold text-xs">
                            <FileText size={18} />
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white truncate">
                              {e.subject || 'Subject'}
                            </div>
                            <div className="text-xs sm:text-[13px] text-slate-600 dark:text-slate-400 font-semibold mt-0.5 truncate">
                              {e.assessment_title || 'Assessment'} · {e.created_at || 'Recently'}
                            </div>
                          </div>
                        </div>
                        <div className="shrink-0 flex items-center gap-2">
                          <Badge tone={pct >= 75 ? 'success' : pct >= 50 ? 'warning' : 'error'}>
                            {pct}%
                          </Badge>
                          <ChevronRight size={15} className="text-slate-500" />
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}
            </Card>
          )}

          {/* Academic Profile Tile */}
          <Card className="p-5 sm:p-6">
            <div className="text-xs sm:text-sm font-extrabold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3.5">
              Verified Student Profile
            </div>
            <div className="text-xs sm:text-sm space-y-2.5 text-slate-700 dark:text-slate-300">
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-800">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Account Name</span>
                <span className="font-extrabold text-slate-900 dark:text-white">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-800">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Email ID</span>
                <span className="font-extrabold text-slate-900 dark:text-white truncate max-w-[200px]">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Institution</span>
                <span className="font-extrabold text-slate-900 dark:text-white truncate max-w-[200px]">
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
          setData({ recentEvaluations: [], stats: {} })
        }
      } catch (err) {
        console.warn('Teacher analytics load notice:', err)
        setData({ recentEvaluations: [], stats: {} })
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
  const stats = data?.stats || {}

  const activeStudents = Array.from(new Set(recentEvals.map((e) => e.student_name).filter(Boolean)))
  const totalGradedCount = stats.total_evaluations ?? recentEvals.length
  const totalStudentsCount = stats.active_students_count ?? activeStudents.length
  const pendingActionsCount = stats.pending_action_items_count ?? 0
  const activeMisconceptionsCount = stats.active_misconceptions_count ?? 0

  return (
    <div className="space-y-6 sm:space-y-8">
      {/* Executive Teacher Header */}
      <div className="relative overflow-hidden rounded-3xl bg-[var(--surface)] border border-slate-200 dark:border-slate-800 p-6 sm:p-8 shadow-xs">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-5">
          <div className="space-y-2.5">
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-extrabold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20 flex items-center gap-1.5">
                <Building2 size={16} /> {isCollege ? 'Higher Education Faculty' : 'School Educator'}
              </span>
              <span className="px-3.5 py-1.5 rounded-full text-xs sm:text-sm font-extrabold bg-emerald-500/15 text-emerald-900 dark:text-emerald-200 border border-emerald-500/30 flex items-center gap-1.5">
                <UserCheck size={16} /> Faculty Verified Portal
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl md:text-[34px] font-extrabold tracking-tight text-slate-900 dark:text-white">
              Welcome, {user?.name || 'Faculty'}
            </h1>
            <p className="text-sm sm:text-base text-slate-700 dark:text-slate-300 font-semibold">
              {user?.institution_name || 'LearnSphere Academic Network'} · {isCollege ? (user?.department || 'Department') : (user?.board || 'Board')}
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0 flex-wrap">
            <Button
              onClick={() => navigate('/app/evaluate')}
              className="flex items-center gap-2 shadow-xs px-4 sm:px-5 py-2.5 text-sm sm:text-base font-extrabold"
            >
              <FileText size={18} /> Evaluate Script
            </Button>
            <Button
              variant="secondary"
              onClick={() => navigate('/app/action-center')}
              className="flex items-center gap-2 px-4 sm:px-5 py-2.5 text-sm sm:text-base font-extrabold"
            >
              <Zap size={18} /> Action Center
            </Button>
          </div>
        </div>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
        <StatCard
          label="Evaluations Graded"
          value={loading ? '…' : totalGradedCount}
          delta="Stored answer scripts"
          deltaTone="up"
          icon={FileText}
        />
        <StatCard
          label="Active Students"
          value={loading ? '…' : totalStudentsCount}
          delta="Graded student cohort"
          deltaTone="up"
          icon={UserCheck}
        />
        <StatCard
          label="Pending Interventions"
          value={loading ? '…' : pendingActionsCount}
          delta={pendingActionsCount > 0 ? `${pendingActionsCount} students require action` : 'All students on track'}
          deltaTone={pendingActionsCount > 0 ? 'warning' : 'up'}
          icon={Zap}
        />
        <StatCard
          label="Diagnosed Misconceptions"
          value={loading ? '…' : activeMisconceptionsCount}
          delta={activeMisconceptionsCount > 0 ? `${activeMisconceptionsCount} concept gaps active` : 'No active misconceptions'}
          deltaTone={activeMisconceptionsCount > 0 ? 'down' : 'up'}
          icon={Map}
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
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-[var(--accent)] bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-[var(--accent-soft)] flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <FileText size={24} className="text-[var(--accent)]" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-[var(--accent)] transition-colors">
                  Evaluate Answer Scripts
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Upload question papers and student scripts for verified OCR evaluation and rubrics.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/action-center')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-amber-500 bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer relative"
              >
                {pendingActionsCount > 0 && (
                  <span className="absolute top-4 right-4 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-800 dark:text-amber-300 border border-amber-500/40 text-[11px] font-extrabold">
                    {pendingActionsCount} Active
                  </span>
                )}
                <div className="w-12 h-12 rounded-xl bg-amber-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Zap size={24} className="text-amber-600 dark:text-amber-400" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-amber-600 transition-colors">
                  Action Center
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Consolidated student interventions, feedback assignments, and remediation workflows.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/misconceptions')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-indigo-500 bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer relative"
              >
                {activeMisconceptionsCount > 0 && (
                  <span className="absolute top-4 right-4 px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-800 dark:text-indigo-300 border border-indigo-500/40 text-[11px] font-extrabold">
                    {activeMisconceptionsCount} Gaps
                  </span>
                )}
                <div className="w-12 h-12 rounded-xl bg-indigo-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <Map size={24} className="text-indigo-600 dark:text-indigo-400" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-indigo-600 transition-colors">
                  Misconception Map
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Identify specific syllabus concept flaws and question-level error patterns across classes.
                </div>
              </button>

              <button
                onClick={() => navigate('/app/analytics')}
                className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 hover:border-emerald-500 bg-[var(--surface-alt)]/60 text-left transition-all group hover:shadow-xs cursor-pointer"
              >
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 flex items-center justify-center mb-3.5 group-hover:scale-105 transition-transform">
                  <TrendingUp size={24} className="text-emerald-600 dark:text-emerald-400" />
                </div>
                <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white group-hover:text-emerald-600 transition-colors">
                  Class Analytics
                </div>
                <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-1.5 leading-relaxed">
                  Score distributions, question-level accuracy tiers, and longitudinal trends.
                </div>
              </button>
            </div>
          </Card>

          {/* Quick Shortcuts */}
          <div className="grid sm:grid-cols-3 gap-3.5">
            <button
              onClick={() => navigate('/app/students')}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <Users size={20} className="text-[var(--accent)]" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400">Roster</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">Student Roster</div>
              <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-0.5">Enrolled cohort</div>
            </button>

            <button
              onClick={() => navigate('/app/reports')}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <FileText size={20} className="text-teal-600 dark:text-teal-400" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400">Reports</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">Academic Reports</div>
              <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-0.5">PDF report downloads</div>
            </button>

            <button
              onClick={() => navigate('/app/plagiarism')}
              className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:border-[var(--accent)] text-left transition-all group cursor-pointer"
            >
              <div className="flex items-center justify-between mb-2">
                <ShieldCheck size={20} className="text-amber-600 dark:text-amber-400" />
                <span className="text-xs font-extrabold uppercase tracking-wider text-slate-600 dark:text-slate-400">Audit</span>
              </div>
              <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">Plagiarism Audit</div>
              <div className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mt-0.5">Similarity checks</div>
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
                <Button variant="ghost" size="sm" onClick={() => navigate('/app/history')} className="font-bold">
                  View all <ChevronRight size={15} className="ml-1" />
                </Button>
              }
            />

            {loading ? (
              <div className="py-12 text-center text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-semibold animate-pulse">
                Loading graded scripts…
              </div>
            ) : !hasEvaluations ? (
              <div className="py-10 text-center border border-dashed border-slate-300 dark:border-slate-800 rounded-2xl p-6 bg-[var(--surface-alt)]/30">
                <FileText size={40} className="text-[var(--accent)] mx-auto mb-2.5 opacity-80" />
                <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white mb-1">
                  No Evaluated Scripts Yet
                </div>
                <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium max-w-xs mx-auto mb-4 leading-relaxed">
                  Upload Question Papers and Student Answer Scripts in Evaluate to generate automated grading, rubrics, and diagnostic reports.
                </p>
                <Button size="sm" onClick={() => navigate('/app/evaluate')} className="mx-auto text-xs sm:text-sm font-extrabold">
                  Evaluate First Script
                </Button>
              </div>
            ) : (
              <div className="divide-y divide-slate-200 dark:divide-slate-800">
                {recentEvals.slice(0, 5).map((e, idx) => {
                  const pct = Number(e.percentage) || 0
                  return (
                    <div
                      key={e.id || e._id || idx}
                      onClick={() => navigate('/app/history')}
                      className="py-3.5 flex items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-3 rounded-xl cursor-pointer transition-colors"
                    >
                      <div className="min-w-0 flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 font-extrabold text-xs">
                          <FileText size={18} />
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white truncate">
                            {e.student_name || 'Student'} — {e.subject || 'Subject'}
                          </div>
                          <div className="text-xs sm:text-[13px] text-slate-600 dark:text-slate-400 font-semibold mt-0.5 truncate">
                            {e.assessment_title || 'Exam'} · {e.created_at || 'Recently'}
                          </div>
                        </div>
                      </div>
                      <div className="shrink-0 flex items-center gap-2">
                        <Badge tone={pct >= 75 ? 'success' : pct >= 50 ? 'warning' : 'error'}>
                          {pct}%
                        </Badge>
                        <ChevronRight size={15} className="text-slate-500" />
                      </div>
                    </div>
                  )
                })}
              </div>
            )}
          </Card>

          {/* Faculty Profile Summary */}
          <Card className="p-5 sm:p-6">
            <div className="text-xs sm:text-sm font-extrabold text-slate-700 dark:text-slate-300 uppercase tracking-wider mb-3.5">
              Verified Faculty Profile
            </div>
            <div className="text-xs sm:text-sm space-y-2.5 text-slate-700 dark:text-slate-300">
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-800">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Faculty Name</span>
                <span className="font-extrabold text-slate-900 dark:text-white">{user?.name}</span>
              </div>
              <div className="flex justify-between items-center py-2 border-b border-slate-200 dark:border-slate-800">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Email ID</span>
                <span className="font-extrabold text-slate-900 dark:text-white truncate max-w-[200px]">{user?.email}</span>
              </div>
              <div className="flex justify-between items-center py-2">
                <span className="font-semibold text-slate-600 dark:text-slate-400">Institution</span>
                <span className="font-extrabold text-slate-900 dark:text-white truncate max-w-[200px]">
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
