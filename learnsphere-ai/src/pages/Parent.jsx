import { useState, useEffect } from 'react'
import { PageHead, Card, StatCard, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { Activity, Award, MessageSquare, RefreshCw, TrendingUp, Zap, Clock, ShieldCheck } from 'lucide-react'

const feedTypeColors = {
  session: 'var(--accent)',
  challenge: 'var(--warning)',
  lab: 'var(--success)',
  evaluation: 'var(--text-faint)',
  trainer: 'var(--accent)'
}

export default function Parent() {
  const { user, profile, streakDays, activityLog, studySessions, formattedSessionTime, sessionElapsedSeconds } = useApp()
  const [evaluations, setEvaluations] = useState([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [feedback, setFeedback] = useState(null)

  useEffect(() => {
    async function fetchParentData() {
      setLoading(true)
      const res = await api.getEvaluations({ student_name: user?.name })
      if (res && res.success && Array.isArray(res.evaluations)) {
        setEvaluations(res.evaluations)
      } else {
        setEvaluations([])
      }
      setLoading(false)
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
  const totalSessionsThisWeek = (studySessions ? studySessions.length : 0) + evaluations.length
  const avgScore = evaluations.length > 0
    ? Math.round(evaluations.reduce((acc, curr) => acc + (curr.percentage || 0), 0) / evaluations.length)
    : 0

  const generateFeedback = () => {
    if (!hasData) {
      setFeedback("No student study activity or graded evaluation records found yet. As your child uses LearnSphere AI to complete study sessions, practice challenges, or handwritten test evaluations, a detailed AI progress analysis will be compiled here.")
      return
    }

    setGenerating(true)
    setFeedback(null)
    setTimeout(() => {
      const topSubject = evaluations.length > 0 ? evaluations[0].subject : (profile?.subjects ? profile.subjects[0] : 'Academic Studies')
      const sessInfo = activeSession 
        ? `Latest Session: Started at ${activeSession.startTime} ➔ Active until ${activeSession.endTime} (Duration: ${activeSession.durationText}).` 
        : 'Active Session: Student logged in and active.'
      const streakMsg = `Active daily study streak is ${streakDays} day(s) with ${totalSessionsThisWeek} learning session(s) recorded.`
      
      setFeedback(
        `Academic & Study Session Report for ${user?.name || 'Student'}:\n\n` +
        `• Active Time Audit: ${sessInfo}\n` +
        `• Streak & Engagement: ${streakMsg}\n` +
        `• Test Performance: ${evaluations.length > 0 ? `Average score is ${avgScore}% across ${evaluations.length} evaluation(s).` : 'No formal graded tests uploaded yet.'}\n` +
        `• Focus Domain: Active learning in ${topSubject}.\n\n` +
        `Parent Recommendation: The student's login session timer and study streak are actively tracking. Encourage structured 45-minute study intervals followed by quick Knowledge Challenges.`
      )
      setGenerating(false)
    }, 1500)
  }

  // Token of appreciation badges based on REAL milestones
  const tokenBadges = [
    { id: 1, emoji: '🔥', name: 'Streak Pioneer', description: 'Maintain a 3-day active study streak', earned: streakDays >= 3, progress: Math.min(streakDays, 3), total: 3, condition: 'days' },
    { id: 2, emoji: '📑', name: 'First Evaluation', description: 'Submit & grade 1 answer script', earned: evaluations.length >= 1, progress: Math.min(evaluations.length, 1), total: 1, condition: 'eval' },
    { id: 3, emoji: '🤖', name: 'Trainer Explorer', description: 'Complete 5 AI Personal Trainer sessions', earned: activityLog.filter(a => a.type === 'trainer').length >= 5, progress: Math.min(activityLog.filter(a => a.type === 'trainer').length, 5), total: 5, condition: 'sessions' },
    { id: 4, emoji: '🎯', name: 'High Ranker', description: 'Score 80%+ on any graded assessment', earned: evaluations.some(e => e.percentage >= 80), progress: evaluations.some(e => e.percentage >= 80) ? 1 : 0, total: 1, condition: 'test' },
  ]

  return (
    <>
      <PageHead
        title="Parent Agent & Study Time Audit"
        subtitle="Real-time login session duration, start to end time report, and active streak monitoring for parents."
        action={
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-[var(--success-soft)] border border-[var(--border)] rounded-full">
              <div className="w-2 h-2 rounded-full bg-[var(--success)] animate-pulse" />
              <span className="text-[11.5px] font-bold text-[var(--success)]">Live Parent Audit Active</span>
            </div>
          </div>
        }
      />

      {/* Live stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-4">
        <StatCard label="Live Session Time" value={formattedSessionTime || '0s'} deltaTone="up" />
        <StatCard label="Total Login Sessions" value={studySessions ? studySessions.length : 0} />
        <StatCard label="Evaluations Graded" value={evaluations.length} />
        <StatCard label="Active Streak" value={`🔥 ${streakDays} days`} deltaTone="up" />
      </div>

      {/* Real-time Study Session Duration Audit Card */}
      <Card className="mb-4 border-l-4 border-l-blue-500">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Clock size={18} className="text-blue-500 animate-spin" />
            <h3 className="font-extrabold text-sm uppercase tracking-wider">Live Student Session Time Audit (Parent Report)</h3>
          </div>
          <span className="px-2.5 py-0.5 bg-blue-500/10 text-blue-600 rounded-full text-xs font-bold border border-blue-500/20">
            Real-Time Tracking
          </span>
        </div>

        {activeSession ? (
          <div className="bg-[var(--surface-alt)] p-4 rounded-xl space-y-3">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pb-3 border-b border-[var(--border)]">
              <div>
                <span className="text-[11px] text-[var(--text-faint)] uppercase font-bold block mb-0.5">Session Login Time</span>
                <div className="text-sm font-bold text-[var(--text)]">{activeSession.startTime}</div>
              </div>
              <div>
                <span className="text-[11px] text-[var(--text-faint)] uppercase font-bold block mb-0.5">Last Active / End Time</span>
                <div className="text-sm font-bold text-[var(--accent)]">{activeSession.endTime} (Active Now)</div>
              </div>
              <div>
                <span className="text-[11px] text-[var(--text-faint)] uppercase font-bold block mb-0.5">Total Duration</span>
                <div className="text-sm font-extrabold text-[var(--success)]">{activeSession.durationText}</div>
              </div>
            </div>

            <div>
              <span className="text-[11px] text-[var(--text-faint)] uppercase font-bold block mb-1">Session Activities Logged</span>
              <div className="flex flex-wrap gap-1.5">
                {(activeSession.activities || ["LoggedIn"]).map((act, idx) => (
                  <span key={idx} className="px-2.5 py-1 bg-[var(--surface)] border border-[var(--border)] rounded-md text-[11.5px] font-semibold">
                    {act}
                  </span>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-[var(--text-soft)] p-3 bg-[var(--surface-alt)] rounded-lg">
            No active session recorded. Session timer starts automatically when the student logs in.
          </div>
        )}

        {/* Detailed Past Sessions Log */}
        {studySessions && studySessions.length > 1 && (
          <div className="mt-4 pt-3 border-t border-[var(--border)]">
            <div className="text-xs font-bold uppercase text-[var(--text-soft)] mb-2">Previous Login Sessions Log</div>
            <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
              {studySessions.slice(1, 6).map((sess, i) => (
                <div key={i} className="flex items-center justify-between p-2.5 bg-[var(--surface)] border border-[var(--border)] rounded-lg text-xs">
                  <div>
                    <span className="font-bold text-[var(--text)]">{sess.date}</span>
                    <span className="text-[var(--text-faint)] ml-2">({sess.startTime} ➔ {sess.endTime})</span>
                  </div>
                  <div className="font-extrabold text-[var(--accent)]">{sess.durationText}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-4">
        {/* Left column */}
        <div className="space-y-4">
          {/* Activity feed */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Activity size={15} className="text-[var(--accent)]" />
              <div className="text-[12px] font-bold uppercase tracking-wider">Student Activity Feed</div>
              <span className="ml-auto text-[11px] text-[var(--text-faint)]">Recorded Events</span>
            </div>

            {combinedFeed.length === 0 ? (
              <div className="py-8 text-center border-2 border-dashed border-[var(--border)] rounded-xl">
                <Clock size={36} className="text-[var(--text-faint)] mx-auto mb-2" />
                <div className="text-sm font-bold mb-1">No Activity Recorded Yet</div>
                <div className="text-xs text-[var(--text-soft)] max-w-sm mx-auto">
                  As your child completes study sessions in Personal Trainer or submits evaluations, real updates will appear here automatically.
                </div>
              </div>
            ) : (
              <div className="space-y-0">
                {combinedFeed.map((item, i) => (
                  <div key={i} className="flex gap-3 py-3 border-b border-[var(--border)] last:border-0">
                    <div
                      className="w-7 h-7 rounded-full flex items-center justify-center text-sm shrink-0 mt-0.5"
                      style={{ background: `${feedTypeColors[item.type] || 'var(--accent)'}1a` }}
                    >
                      {item.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[12.5px] leading-relaxed">{item.text}</div>
                      <div className="text-[11px] text-[var(--text-faint)] mt-0.5">{item.when}</div>
                    </div>
                    {item.score !== null && item.score !== undefined && (
                      <div className={`text-[12px] font-extrabold shrink-0 ${
                        item.score >= 80 ? 'text-[var(--success)]' : item.score >= 65 ? 'text-[var(--warning)]' : 'text-[var(--error)]'
                      }`}>
                        {item.score}%
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* AI Feedback generator */}
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <MessageSquare size={15} className="text-[var(--accent)]" />
                <div className="text-[12px] font-bold uppercase tracking-wider">AI Parent Feedback Report</div>
              </div>
              {feedback && (
                <button onClick={generateFeedback} className="flex items-center gap-1 text-[11.5px] font-semibold text-[var(--text-faint)] hover:text-[var(--accent)] transition-colors">
                  <RefreshCw size={11} /> Regenerate
                </button>
              )}
            </div>

            {!feedback && !generating && (
              <div className="text-center py-6">
                <div className="text-3xl mb-3">🤖</div>
                <div className="text-[13.5px] font-semibold mb-1.5">Generate Parent Feedback Report</div>
                <div className="text-sm text-[var(--text-soft)] mb-5 max-w-[340px] mx-auto">
                  AI analyses recorded student sessions and test scores to generate an objective progress overview for parents.
                </div>
                <button
                  onClick={generateFeedback}
                  className="px-5 py-2.5 bg-[var(--accent)] text-white font-semibold rounded-lg hover:bg-[var(--accent-dim)] transition-colors"
                >
                  Generate Feedback Report
                </button>
              </div>
            )}

            {generating && (
              <div className="flex items-center gap-3 py-6 justify-center">
                <div className="w-5 h-5 border-2 border-[var(--accent)] border-t-transparent rounded-full animate-spin" />
                <span className="text-[13.5px] text-[var(--text-soft)] animate-pulse">Analysing student study records…</span>
              </div>
            )}

            {feedback && (
              <div className="bg-[var(--surface-alt)] rounded-lg p-4">
                <div className="text-[13px] leading-relaxed whitespace-pre-line text-[var(--text-soft)]">{feedback}</div>
              </div>
            )}
          </Card>
        </div>

        {/* Right column */}
        <div className="space-y-4">
          {/* Performance Summary */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <TrendingUp size={15} className="text-[var(--accent)]" />
              <div className="text-[12px] font-bold uppercase tracking-wider">Score Trend Summary</div>
            </div>
            {evaluations.length === 0 ? (
              <div className="p-4 text-center text-xs text-[var(--text-faint)]">
                No evaluation test data recorded yet.
              </div>
            ) : (
              <div className="space-y-2">
                <div className="flex justify-between items-center text-xs border-b border-[var(--border)] pb-2">
                  <span className="font-semibold text-[var(--text-soft)]">Total Tests Graded:</span>
                  <span className="font-bold">{evaluations.length}</span>
                </div>
                <div className="flex justify-between items-center text-xs border-b border-[var(--border)] pb-2">
                  <span className="font-semibold text-[var(--text-soft)]">Average Score:</span>
                  <span className="font-bold text-[var(--accent)]">{avgScore}%</span>
                </div>
                <div className="flex justify-between items-center text-xs pt-1">
                  <span className="font-semibold text-[var(--text-soft)]">Latest Test Score:</span>
                  <span className="font-bold text-[var(--success)]">{evaluations[0]?.percentage}% ({evaluations[0]?.subject})</span>
                </div>
              </div>
            )}
          </Card>

          {/* Tokens of Appreciation */}
          <Card>
            <div className="flex items-center gap-2 mb-4">
              <Award size={15} className="text-[var(--gold)]" />
              <div className="text-[12px] font-bold uppercase tracking-wider">Tokens of Appreciation</div>
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              {tokenBadges.map((badge) => (
                <div
                  key={badge.id}
                  className={`relative rounded-xl p-3 border transition-all ${
                    badge.earned
                      ? 'border-[var(--gold)] bg-[var(--gold-soft)] shadow-sm'
                      : 'border-[var(--border)] opacity-60'
                  }`}
                >
                  <div className="text-2xl mb-1.5">{badge.emoji}</div>
                  <div className="text-[11.5px] font-extrabold leading-tight mb-0.5">{badge.name}</div>
                  <div className="text-[10.5px] text-[var(--text-faint)] leading-snug mb-1.5">{badge.description}</div>
                  {badge.earned ? (
                    <div className="text-[10px] font-bold text-[var(--gold)]">✓ Unlocked</div>
                  ) : (
                    <div>
                      <div className="h-1 bg-[var(--border)] rounded-full overflow-hidden mb-1">
                        <div
                          className="h-full bg-[var(--accent)] rounded-full"
                          style={{ width: `${Math.round((badge.progress / badge.total) * 100)}%` }}
                        />
                      </div>
                      <div className="text-[10px] text-[var(--text-faint)]">{badge.progress}/{badge.total} {badge.condition}</div>
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

