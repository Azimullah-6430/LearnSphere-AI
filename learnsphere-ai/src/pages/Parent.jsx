import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHead, Card, StatCard, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  Activity,
  Award,
  MessageSquare,
  RefreshCw,
  TrendingUp,
  Zap,
  Clock,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  ArrowRight,
  Sparkles,
  BookOpen,
  Copy,
  Printer,
  FileText
} from 'lucide-react'

const feedTypeColors = {
  session: 'var(--accent)',
  challenge: 'var(--warning)',
  lab: 'var(--success)',
  evaluation: 'var(--accent)',
  trainer: 'var(--accent)'
}

export default function Parent() {
  const navigate = useNavigate()
  const { user, profile, streakDays, activityLog, studySessions, formattedSessionTime } = useApp()
  const [evaluations, setEvaluations] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [reportData, setReportData] = useState(null)
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    async function fetchParentData() {
      setLoading(true)
      try {
        const res = await api.getEvaluations({ student_name: user?.name })
        if (res && res.success && Array.isArray(res.evaluations)) {
          setEvaluations(res.evaluations)
        } else {
          setEvaluations([])
        }
      } catch (err) {
        console.warn('Parent data fetch notice:', err)
        setEvaluations([])
      } finally {
        setLoading(false)
      }
    }
    fetchParentData()
  }, [user])

  // Current session & session history
  const activeSession = studySessions && studySessions.length > 0 ? studySessions[0] : null

  // Combine real activity log & real evaluations for feed
  const combinedFeed = []

  evaluations.forEach((e) => {
    combinedFeed.push({
      type: 'evaluation',
      icon: '📝',
      text: `Completed ${e.subject} evaluation (${e.assessment_title})`,
      when: e.created_at || 'Recently',
      score: e.percentage
    })
  })

  activityLog.forEach((act) => {
    combinedFeed.push({
      type: act.type || 'session',
      icon: act.type === 'trainer' ? '🤖' : act.type === 'challenge' ? '⚡' : '🔬',
      text: act.text,
      when: act.when || 'Today',
      score: act.score ?? null
    })
  })

  const hasData = evaluations.length > 0 || activityLog.length > 0 || (studySessions && studySessions.length > 0)

  // Metrics calculation
  const totalSessionsCount = (studySessions ? studySessions.length : 0) + evaluations.length
  const avgScore = evaluations.length > 0
    ? Math.round(evaluations.reduce((acc, curr) => acc + (Number(curr.percentage) || 0), 0) / evaluations.length)
    : 0

  const handleGenerateReport = async () => {
    setGenerating(true)
    try {
      const res = await api.getParentReport({
        activity_log: activityLog,
        study_sessions: studySessions,
        streak_days: streakDays,
        formatted_session_time: formattedSessionTime
      })
      if (res && res.success) {
        setReportData(res)
      } else {
        setReportData(null)
      }
    } catch (err) {
      console.warn('Generate parent report notice:', err)
    } finally {
      setGenerating(false)
    }
  }

  const handleCopyReport = () => {
    if (!reportData) return
    const textToCopy = `
Academic & Diagnostic Report for ${reportData.student_name}
Institution: ${reportData.institution}
Academic Standing: ${reportData.academic_standing}
Average Score: ${reportData.average_score !== null ? `${reportData.average_score}%` : 'N/A'}
Study Streak: ${reportData.study_streak_days} days

EXECUTIVE SUMMARY:
${reportData.executive_summary}

DEMONSTRATED STRENGTHS:
${reportData.demonstrated_strengths?.map(s => `• ${s.concept} (${s.subject}): ${s.detail}`).join('\n') || 'None'}

AREAS FOR GROWTH & WEAKNESSES:
${reportData.areas_needing_support?.map(w => `• ${w.concept} (${w.subject}): ${w.explanation} (${w.marks_impact || ''})`).join('\n') || 'None'}

HOME ACTION PLAN FOR PARENTS:
${reportData.home_action_plan?.map((a, i) => `${i + 1}. ${a}`).join('\n') || 'None'}

NEXT LEARNING TARGET:
${reportData.next_learning_target}
    `.trim()

    navigator.clipboard.writeText(textToCopy)
    setCopied(true)
    setTimeout(() => setCopied(false), 3000)
  }

  const handlePrint = () => {
    window.print()
  }

  // Token of appreciation badges based on REAL milestones
  const tokenBadges = [
    { id: 1, emoji: '🔥', name: 'Streak Pioneer', description: 'Maintain a 3-day active study streak', earned: streakDays >= 3, progress: Math.min(streakDays, 3), total: 3, condition: 'days' },
    { id: 2, emoji: '📑', name: 'First Evaluation', description: 'Submit & grade 1 answer script', earned: evaluations.length >= 1, progress: Math.min(evaluations.length, 1), total: 1, condition: 'eval' },
    { id: 3, emoji: '🤖', name: 'Trainer Explorer', description: 'Complete 5 AI Personal Trainer sessions', earned: activityLog.filter(a => a.type === 'trainer').length >= 5, progress: Math.min(activityLog.filter(a => a.type === 'trainer').length, 5), total: 5, condition: 'sessions' },
    { id: 4, emoji: '🎯', name: 'High Ranker', description: 'Score 80%+ on any graded assessment', earned: evaluations.some(e => Number(e.percentage) >= 80), progress: evaluations.some(e => Number(e.percentage) >= 80) ? 1 : 0, total: 1, condition: 'test' },
  ]

  return (
    <>
      <PageHead
        title="Parent Overview & Diagnostic Feedback"
        subtitle="Track your child's study routine, exam performance, diagnosed strengths, and home action plans."
        action={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-2 px-3.5 py-1.5 bg-emerald-500/10 border border-emerald-500/20 rounded-full">
              <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-xs font-extrabold text-emerald-700 dark:text-emerald-400">Live Routine Active</span>
            </div>
          </div>
        }
      />

      {/* Live stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-5">
        <StatCard label="Current Session" value={formattedSessionTime || '0s'} delta="Active now" deltaTone="up" icon={Clock} />
        <StatCard label="Total Sessions" value={studySessions ? studySessions.length : 0} delta="Recorded logins" deltaTone="neutral" icon={Zap} />
        <StatCard label="Graded Tests" value={evaluations.length} delta={avgScore > 0 ? `${avgScore}% avg score` : 'Answer scripts'} deltaTone="up" icon={FileText} />
        <StatCard label="Study Streak" value={`${streakDays} days`} delta="Consecutive routine" deltaTone="up" icon={Award} />
      </div>

      {/* Real-time Study Session Duration Audit Card */}
      <Card className="mb-5 border-l-4 border-l-[var(--accent)]">
        <div className="flex items-center justify-between mb-3.5">
          <div className="flex items-center gap-2.5">
            <Clock size={18} className="text-[var(--accent)]" />
            <h3 className="font-extrabold text-sm sm:text-base text-slate-900 dark:text-white">Current Study Session Audit</h3>
          </div>
          <span className="px-3 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded-full text-xs font-extrabold border border-[var(--accent)]/20">
            Real-Time Tracker
          </span>
        </div>

        {activeSession ? (
          <div className="bg-[var(--surface-alt)] p-4 rounded-xl space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
              <div>
                <span className="text-[11px] text-slate-600 dark:text-slate-400 uppercase font-extrabold block mb-0.5">Session Login Time</span>
                <div className="text-sm font-extrabold text-slate-900 dark:text-white">{activeSession.startTime}</div>
              </div>
              <div>
                <span className="text-[11px] text-slate-600 dark:text-slate-400 uppercase font-extrabold block mb-0.5">Last Active / End Time</span>
                <div className="text-sm font-extrabold text-[var(--accent)]">{activeSession.endTime} (Active Now)</div>
              </div>
              <div>
                <span className="text-[11px] text-slate-600 dark:text-slate-400 uppercase font-extrabold block mb-0.5">Total Duration</span>
                <div className="text-sm font-extrabold text-emerald-600 dark:text-emerald-400">{activeSession.durationText}</div>
              </div>
            </div>

            <div>
              <span className="text-[11px] text-slate-600 dark:text-slate-400 uppercase font-extrabold block mb-1">Session Activities Logged</span>
              <div className="flex flex-wrap gap-1.5">
                {(activeSession.activities || ["LoggedIn"]).map((act, idx) => (
                  <span key={idx} className="px-2.5 py-1 bg-[var(--surface)] border border-slate-200 dark:border-slate-800 rounded-md text-[11.5px] font-bold text-slate-800 dark:text-slate-200">
                    {act}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-slate-700 dark:text-slate-300 font-medium p-3.5 bg-[var(--surface-alt)] rounded-xl">
            No active session recorded. Session timer starts automatically when the student logs in.
          </div>
        )}

        {/* Detailed Past Sessions Log */}
        {studySessions && studySessions.length > 1 && (
          <div className="mt-4 pt-3 border-t border-slate-200 dark:border-slate-800">
            <div className="text-xs font-extrabold uppercase text-slate-700 dark:text-slate-300 mb-2">Previous Login Sessions Log</div>
            <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
              {studySessions.slice(1, 6).map((sess, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 bg-[var(--surface)] border border-slate-200 dark:border-slate-800 rounded-lg text-xs">
                  <div>
                    <span className="font-extrabold text-slate-900 dark:text-white">{sess.date}</span>
                    <span className="text-slate-600 dark:text-slate-400 ml-2 font-medium">({sess.startTime} ➔ {sess.endTime})</span>
                  </div>
                  <div className="font-extrabold text-[var(--accent)]">{sess.durationText}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-5">
        {/* Left column: AI Parent Feedback & Activity Feed */}
        <div className="space-y-5">
          {/* AI Parent Diagnostic Feedback Report */}
          <Card className="border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex items-center justify-between mb-4 flex-wrap gap-2 border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-[var(--accent-soft)] flex items-center justify-center text-[var(--accent)]">
                  <MessageSquare size={17} />
                </div>
                <div>
                  <h3 className="text-sm sm:text-base font-extrabold text-slate-900 dark:text-white">
                    AI Parent Diagnostic Feedback Report
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                    Evidence-grounded strengths, weaknesses, and home action plan
                  </p>
                </div>
              </div>

              {reportData && (
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleCopyReport}
                    className="px-2.5 py-1 text-xs font-bold rounded-lg border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:bg-[var(--surface-alt)] text-slate-700 dark:text-slate-300 flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <Copy size={12} /> {copied ? 'Copied!' : 'Copy'}
                  </button>
                  <button
                    onClick={handlePrint}
                    className="px-2.5 py-1 text-xs font-bold rounded-lg border border-slate-200 dark:border-slate-800 bg-[var(--surface)] hover:bg-[var(--surface-alt)] text-slate-700 dark:text-slate-300 flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <Printer size={12} /> Print
                  </button>
                  <button
                    onClick={handleGenerateReport}
                    className="px-2.5 py-1 text-xs font-bold rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] hover:bg-[var(--accent)] hover:text-white flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <RefreshCw size={12} /> Refresh
                  </button>
                </div>
              )}
            </div>

            {/* Not Generated State */}
            {!reportData && !generating && (
              <div className="text-center py-8 px-4">
                <div className="w-14 h-14 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto mb-3 shadow-xs">
                  <Sparkles size={28} />
                </div>
                <h4 className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white mb-1.5">
                  Generate Comprehensive Parent Report
                </h4>
                <p className="text-xs sm:text-sm text-slate-700 dark:text-slate-300 font-medium mb-5 max-w-md mx-auto leading-relaxed">
                  AI analyzes your child's handwritten test answers, scoring patterns, and study habits to present clear strengths, specific weaknesses, and concrete recommendations for home support.
                </p>
                <button
                  onClick={handleGenerateReport}
                  className="px-6 py-2.5 bg-[var(--accent)] text-white font-extrabold text-sm rounded-xl hover:bg-[var(--accent-hover)] transition-all shadow-sm cursor-pointer"
                >
                  Generate Accurate Feedback Report
                </button>
              </div>
            )}

            {/* Generating State */}
            {generating && (
              <div className="flex flex-col items-center justify-center py-10 gap-3">
                <div className="w-7 h-7 border-3 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
                <span className="text-sm font-extrabold text-slate-800 dark:text-slate-200 animate-pulse">
                  Analyzing genuine student test evaluations & learning patterns…
                </span>
                <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
                  Classifying strengths, calculation accuracy, and conceptual understanding
                </span>
              </div>
            )}

            {/* Structured Report View */}
            {reportData && (
              <div className="space-y-4 pt-1">
                {/* Executive Standing & Summary */}
                <div className="p-4 rounded-2xl bg-gradient-to-r from-[var(--surface-alt)] via-[var(--surface)] to-[var(--surface-alt)] border border-slate-200 dark:border-slate-800 space-y-2.5">
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span className="text-xs font-extrabold uppercase tracking-wider text-[var(--accent)]">
                      Academic Overview
                    </span>
                    <span className="px-3 py-0.5 rounded-full text-xs font-extrabold bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/30">
                      {reportData.academic_standing}
                    </span>
                  </div>
                  <p className="text-sm text-slate-800 dark:text-slate-100 font-semibold leading-relaxed">
                    {reportData.executive_summary}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-slate-600 dark:text-slate-400 pt-1 flex-wrap">
                    {reportData.average_score !== null && (
                      <span>Average Score: <strong className="text-slate-900 dark:text-white">{reportData.average_score}%</strong></span>
                    )}
                    <span>Tests Evaluated: <strong className="text-slate-900 dark:text-white">{reportData.total_evaluations_analyzed}</strong></span>
                    <span>Streak: <strong className="text-slate-900 dark:text-white">{reportData.study_streak_days} Days</strong></span>
                  </div>
                </div>

                {/* Demonstrated Strengths */}
                <div className="p-4 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 space-y-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={18} className="text-emerald-700 dark:text-emerald-400" />
                    <h4 className="text-sm font-extrabold uppercase tracking-wider text-emerald-900 dark:text-emerald-300">
                      Demonstrated Academic Strengths (What Your Child Excels At)
                    </h4>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {Array.isArray(reportData.demonstrated_strengths) && reportData.demonstrated_strengths.length > 0 ? (
                      reportData.demonstrated_strengths.map((s, idx) => (
                        <div key={idx} className="p-3 rounded-xl bg-[var(--surface)] border border-emerald-500/30 space-y-1">
                          <div className="flex items-center justify-between gap-1 flex-wrap">
                            <span className="font-extrabold text-xs text-emerald-800 dark:text-emerald-300">
                              ✓ {s.concept || s.area}
                            </span>
                            {s.subject && (
                              <span className="text-[10.5px] px-1.5 py-0.5 rounded bg-[var(--surface-alt)] text-slate-600 dark:text-slate-400 font-bold border border-slate-200 dark:border-slate-800">
                                {s.subject}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium leading-relaxed">
                            {s.detail}
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-600 dark:text-slate-400 font-medium italic">
                        Evaluation data is compiling. As answer papers are submitted, strengths will populate here.
                      </div>
                    )}
                  </div>
                </div>

                {/* Identified Weaknesses & Areas Needing Support */}
                <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/30 space-y-3">
                  <div className="flex items-center gap-2">
                    <AlertTriangle size={18} className="text-amber-700 dark:text-amber-400" />
                    <h4 className="text-sm font-extrabold uppercase tracking-wider text-amber-900 dark:text-amber-300">
                      Specific Areas Needing Support & Weaknesses (Where Marks Were Lost)
                    </h4>
                  </div>
                  <div className="space-y-2.5">
                    {Array.isArray(reportData.areas_needing_support) && reportData.areas_needing_support.length > 0 ? (
                      reportData.areas_needing_support.map((w, idx) => (
                        <div key={idx} className="p-3.5 rounded-xl bg-[var(--surface)] border border-amber-500/30 space-y-1.5">
                          <div className="flex items-center justify-between gap-2 flex-wrap">
                            <div className="flex items-center gap-2">
                              <span className="font-extrabold text-xs text-slate-900 dark:text-white">
                                {w.concept || w.area}
                              </span>
                              {w.gap_type && (
                                <span className="px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-800 dark:text-amber-300 font-extrabold text-[10.5px] border border-amber-500/30">
                                  {w.gap_type}
                                </span>
                              )}
                            </div>
                            {w.marks_impact && (
                              <span className="text-[11px] font-extrabold text-rose-700 dark:text-rose-400">
                                {w.marks_impact}
                              </span>
                            )}
                          </div>
                          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium leading-relaxed">
                            {w.explanation || w.detail}
                          </p>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-slate-600 dark:text-slate-400 font-medium italic">
                        No critical learning deficits detected. All evaluated questions met mastery thresholds.
                      </div>
                    )}
                  </div>
                </div>

                {/* Practical Parent Action Plan at Home */}
                {Array.isArray(reportData.home_action_plan) && reportData.home_action_plan.length > 0 && (
                  <div className="p-4 rounded-2xl bg-[var(--accent-soft)] border border-[var(--accent)]/30 space-y-2.5">
                    <div className="flex items-center gap-2">
                      <Lightbulb size={18} className="text-[var(--accent)]" />
                      <h4 className="text-sm font-extrabold uppercase tracking-wider text-[var(--accent)]">
                        Action Plan: How Parents Can Help at Home
                      </h4>
                    </div>
                    <div className="space-y-2">
                      {reportData.home_action_plan.map((step, idx) => (
                        <div key={idx} className="flex items-start gap-2.5 text-xs text-slate-800 dark:text-slate-200">
                          <span className="w-5 h-5 rounded-full bg-[var(--accent)] text-white font-extrabold text-[11px] flex items-center justify-center shrink-0 mt-0.5">
                            {idx + 1}
                          </span>
                          <span className="font-semibold leading-relaxed">{step}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Next Learning Target */}
                {reportData.next_learning_target && (
                  <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2.5">
                      <ArrowRight size={16} className="text-[var(--accent)] shrink-0" />
                      <div className="text-xs text-slate-700 dark:text-slate-300">
                        <strong className="text-slate-900 dark:text-white">Recommended Next Focus: </strong>
                        <span>{reportData.next_learning_target}</span>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      onClick={() => navigate('/app/trainer')}
                      className="font-extrabold text-xs shrink-0"
                    >
                      Open Personal Trainer
                    </Button>
                  </div>
                )}
              </div>
            )}
          </Card>

          {/* Activity feed */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Activity size={16} className="text-[var(--accent)]" />
              <div className="text-[12px] font-extrabold uppercase tracking-wider text-slate-900 dark:text-white">
                Student Study Activity Feed
              </div>
              <span className="ml-auto text-[11px] text-slate-600 dark:text-slate-400 font-semibold">
                Recorded Events
              </span>
            </div>

            {combinedFeed.length === 0 ? (
              <div className="py-8 text-center border-2 border-dashed border-slate-300 dark:border-slate-800 rounded-xl">
                <Clock size={36} className="text-slate-400 mx-auto mb-2" />
                <div className="text-sm font-extrabold text-slate-900 dark:text-white mb-1">No Activity Recorded Yet</div>
                <div className="text-xs text-slate-700 dark:text-slate-300 font-medium max-w-sm mx-auto">
                  As your child completes study sessions in Personal Trainer or submits evaluations, real updates will appear here automatically.
                </div>
              </div>
            ) : (
              <div className="space-y-0">
                {combinedFeed.slice(0, 8).map((item, i) => (
                  <div key={i} className="flex gap-3 py-3 border-b border-slate-200 dark:border-slate-800 last:border-0">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 mt-0.5"
                      style={{ background: `${feedTypeColors[item.type] || 'var(--accent)'}1a` }}
                    >
                      {item.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] font-bold text-slate-900 dark:text-white leading-relaxed">{item.text}</div>
                      <div className="text-[11px] text-slate-600 dark:text-slate-400 font-medium mt-0.5">{item.when}</div>
                    </div>
                    {item.score !== null && item.score !== undefined && (
                      <div className={`text-[12px] font-extrabold shrink-0 ${
                        item.score >= 80 ? 'text-emerald-700 dark:text-emerald-400' : item.score >= 65 ? 'text-amber-700 dark:text-amber-400' : 'text-rose-700 dark:text-rose-400'
                      }`}>
                        {item.score}%
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Right column: Trends and Badges */}
        <div className="space-y-5">
          {/* Performance Summary */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={16} className="text-[var(--accent)]" />
              <div className="text-[12px] font-extrabold uppercase tracking-wider text-slate-900 dark:text-white">
                Score Trend Summary
              </div>
            </div>
            {evaluations.length === 0 ? (
              <div className="p-4 text-center text-xs text-slate-600 dark:text-slate-400 font-medium">
                No evaluation test data recorded yet.
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs border-b border-slate-200 dark:border-slate-800 pb-2">
                  <span className="font-semibold text-slate-600 dark:text-slate-400">Total Tests Graded:</span>
                  <span className="font-extrabold text-slate-900 dark:text-white">{evaluations.length}</span>
                </div>
                <div className="flex justify-between items-center text-xs border-b border-slate-200 dark:border-slate-800 pb-2">
                  <span className="font-semibold text-slate-600 dark:text-slate-400">Average Score:</span>
                  <span className="font-extrabold text-[var(--accent)]">{avgScore}%</span>
                </div>
                <div className="flex justify-between items-center text-xs pt-1">
                  <span className="font-semibold text-slate-600 dark:text-slate-400">Latest Test Score:</span>
                  <span className="font-extrabold text-emerald-600 dark:text-emerald-400">
                    {evaluations[0]?.percentage}% ({evaluations[0]?.subject})
                  </span>
                </div>
              </div>
            )}
          </Card>

          {/* Tokens of Appreciation */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Award size={16} className="text-amber-600" />
              <div className="text-[12px] font-extrabold uppercase tracking-wider text-slate-900 dark:text-white">
                Milestones & Badges
              </div>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {tokenBadges.map((badge) => (
                <div
                  key={badge.id}
                  className={`relative rounded-xl p-3 border transition-all ${
                    badge.earned
                      ? 'border-amber-400 dark:border-amber-700 bg-amber-50/50 dark:bg-amber-950/20 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 opacity-60'
                  }`}
                >
                  <div className="text-2xl mb-1.5">{badge.emoji}</div>
                  <div className="text-[11.5px] font-extrabold text-slate-900 dark:text-white leading-tight mb-0.5">{badge.name}</div>
                  <div className="text-[10.5px] text-slate-600 dark:text-slate-400 font-medium leading-snug mb-1.5">{badge.description}</div>
                  {badge.earned ? (
                    <div className="text-[10px] font-extrabold text-amber-700 dark:text-amber-400">✓ Unlocked</div>
                  ) : (
                    <div>
                      <div className="h-1 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden mb-1">
                        <div
                          className="h-full bg-[var(--accent)] rounded-full"
                          style={{ width: `${Math.round((badge.progress / badge.total) * 100)}%` }}
                        />
                      </div>
                      <div className="text-[10px] text-slate-600 dark:text-slate-400 font-bold">{badge.progress}/{badge.total} {badge.condition}</div>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </>
  )
}
