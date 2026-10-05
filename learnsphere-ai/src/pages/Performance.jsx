import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, CardHeader, PageHead, Button, Badge } from '../components/ui/Primitives.jsx'
import { TrendChart, SubjectBarChart } from '../components/charts/Charts.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  FileText, ArrowRight, TrendingUp, TrendingDown, Award,
  CheckCircle2, AlertTriangle, AlertCircle, BookOpen, Brain,
  Sparkles, History, Eye, X, HelpCircle, Layers
} from 'lucide-react'

export default function Performance() {
  const { user } = useApp()
  const navigate = useNavigate()
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedEvalDetail, setSelectedEvalDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    async function loadAnalytics() {
      setLoading(true)
      try {
        const res = await api.getStudentAnalytics()
        if (res && res.success) {
          setAnalytics(res)
        } else {
          setAnalytics(null)
        }
      } catch (err) {
        console.warn('Analytics API error:', err)
        setAnalytics(null)
      } finally {
        setLoading(false)
      }
    }
    loadAnalytics()
  }, [user])

  const handleViewEvaluation = async (evalId) => {
    if (!evalId) return
    setDetailLoading(true)
    try {
      const res = await api.getEvaluationDetail(evalId)
      if (res && res.success && res.evaluation) {
        setSelectedEvalDetail(res.evaluation)
      } else {
        alert('Could not retrieve evaluation details.')
      }
    } catch (err) {
      alert('Error fetching evaluation: ' + err.message)
    } finally {
      setDetailLoading(false)
    }
  }

  const hasData = analytics && analytics.has_data && analytics.total_evaluations > 0

  // Chart data
  const trendData = (analytics?.score_history || []).map((e, i) => ({
    label: `${e.subject?.slice(0, 4) || 'Ev'}${i + 1}`,
    value: e.percentage,
  }))

  const subjectChartData = Object.values(analytics?.subject_wise_performance || {}).map((s) => ({
    label: s.subject,
    value: s.average_percentage,
  }))

  const trendDelta = analytics?.improvement_trend?.delta_percentage || 0
  const isImproving = analytics?.improvement_trend?.direction === 'improving'
  const isDeclining = analytics?.improvement_trend?.direction === 'declining'

  return (
    <>
      <PageHead
        title="Student Analytics & Performance Trends"
        subtitle="Quantitative mastery trends, subject breakdown, question-wise accuracy, and concept diagnostics derived strictly from your stored evaluations."
      />

      {loading ? (
        <Card className="p-12 text-center my-6">
          <div className="animate-spin text-[var(--accent)] text-2xl mx-auto mb-3">⏳</div>
          <div className="text-sm font-semibold text-[var(--text-soft)]">Loading evaluation analytics...</div>
        </Card>
      ) : !hasData ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <FileText size={44} className="text-[var(--accent)] mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">No Evaluation Data Recorded Yet</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto mb-5">
            You haven't completed any graded evaluations yet. Submit an exam question paper and answer script in Self-Evaluation to generate your performance analytics.
          </p>
          <Button onClick={() => navigate('/app/self-evaluation')} className="mx-auto flex items-center gap-2">
            Run Your First Self-Evaluation <ArrowRight size={14} />
          </Button>
        </Card>
      ) : (
        <div className="space-y-6">
          {/* Executive Metrics Strip */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="p-4 border-l-4 border-l-[var(--accent)] shadow-sm">
              <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
                Completed Evaluations
              </div>
              <div className="text-[28px] font-black text-[var(--text)]">
                {analytics.total_evaluations}
              </div>
              <div className="text-[11.5px] text-[var(--text-soft)] font-medium mt-1">
                Stored in academic database
              </div>
            </Card>

            <Card className="p-4 border-l-4 border-l-[var(--success)] shadow-sm">
              <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
                Average Score
              </div>
              <div className="text-[28px] font-black text-[var(--success)]">
                {analytics.average_percentage}%
              </div>
              <div className="text-[11.5px] text-[var(--text-soft)] font-medium mt-1">
                Mean marks: {analytics.average_marks} pts
              </div>
            </Card>

            <Card className={`p-4 border-l-4 ${isImproving ? 'border-l-emerald-500' : isDeclining ? 'border-l-[var(--error)]' : 'border-l-[var(--gold)]'} shadow-sm`}>
              <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
                Improvement Trend
              </div>
              <div className="text-[28px] font-black flex items-center gap-1">
                {isImproving ? (
                  <span className="text-emerald-500 flex items-center gap-1">
                    +{trendDelta}% <TrendingUp size={20} />
                  </span>
                ) : isDeclining ? (
                  <span className="text-[var(--error)] flex items-center gap-1">
                    {trendDelta}% <TrendingDown size={20} />
                  </span>
                ) : (
                  <span className="text-[var(--text-soft)]">Stable</span>
                )}
              </div>
              <div className="text-[11.5px] text-[var(--text-soft)] font-medium mt-1">
                {isImproving ? 'Performance improving across assessments' : isDeclining ? 'Recent score drop detected' : 'Steady score trajectory'}
              </div>
            </Card>

            <Card className="p-4 border-l-4 border-l-[var(--gold)] shadow-sm">
              <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
                Flagged Misconceptions
              </div>
              <div className="text-[28px] font-black text-[var(--gold)]">
                {analytics.recurring_misconceptions?.length || 0}
              </div>
              <div className="text-[11.5px] text-[var(--text-soft)] font-medium mt-1">
                Requires concept practice
              </div>
            </Card>
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card className="shadow-sm">
              <CardHeader title="Score History Progression" subtitle="Percentage trajectory across completed evaluations" />
              <TrendChart data={trendData} />
            </Card>
            <Card className="shadow-sm">
              <CardHeader title="Subject-Wise Performance" subtitle="Average percentage by evaluated academic subject" />
              <SubjectBarChart data={subjectChartData} />
            </Card>
          </div>

          {/* Question-Wise Performance Breakdown Table */}
          {Object.keys(analytics.question_wise_performance || {}).length > 0 && (
            <Card className="shadow-sm space-y-3">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
                <div>
                  <h3 className="text-sm font-extrabold text-[var(--text)]">Question-Wise Accuracy Breakdown</h3>
                  <p className="text-xs text-[var(--text-soft)]">Aggregated accuracy and average marks awarded across question numbers</p>
                </div>
                <Badge tone="accent">Exam Question Analytics</Badge>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-[var(--text-faint)] uppercase text-[11px] tracking-wider bg-[var(--surface-alt)]">
                      <th className="py-2.5 px-3">Question No.</th>
                      <th className="py-2.5 px-3">Evaluations</th>
                      <th className="py-2.5 px-3">Avg Awarded</th>
                      <th className="py-2.5 px-3">Avg Max Marks</th>
                      <th className="py-2.5 px-3">Accuracy</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--border)]">
                    {Object.values(analytics.question_wise_performance).map((q, idx) => {
                      const acc = q.accuracy_percentage
                      const isHighAcc = acc >= 75
                      const isLowAcc = acc < 50

                      return (
                        <tr key={idx} className="hover:bg-[var(--surface-alt)] transition-colors">
                          <td className="py-2.5 px-3 font-extrabold text-[var(--accent)]">
                            Question {q.question_number}
                          </td>
                          <td className="py-2.5 px-3 font-medium text-[var(--text)]">
                            {q.attempts} assessment{q.attempts > 1 ? 's' : ''}
                          </td>
                          <td className="py-2.5 px-3 font-semibold text-[var(--text)]">
                            {q.average_awarded} pts
                          </td>
                          <td className="py-2.5 px-3 text-[var(--text-soft)]">
                            {q.average_maximum} pts
                          </td>
                          <td className="py-2.5 px-3 font-black">
                            <span className={isHighAcc ? 'text-emerald-500' : isLowAcc ? 'text-[var(--error)]' : 'text-amber-500'}>
                              {acc}%
                            </span>
                          </td>
                          <td className="py-2.5 px-3">
                            <Badge tone={isHighAcc ? 'success' : isLowAcc ? 'error' : 'warning'}>
                              {isHighAcc ? 'Mastered' : isLowAcc ? 'Needs Practice' : 'Moderate'}
                            </Badge>
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* Concepts Analysis Row: Frequently Weak vs Frequently Strong Concepts */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Frequently Weak Concepts */}
            <Card className="shadow-sm space-y-3 border-l-4 border-l-[var(--error)]">
              <div className="flex items-center gap-2 text-[var(--error)] font-extrabold text-sm">
                <AlertTriangle size={17} />
                <span>Frequently Weak Concepts (Priority Revision)</span>
              </div>
              {analytics.frequently_weak_concepts?.length > 0 ? (
                <div className="space-y-2">
                  {analytics.frequently_weak_concepts.map((c, idx) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-[var(--error-soft)] border border-[var(--error)] flex items-center justify-between text-xs">
                      <div>
                        <strong className="text-[var(--text)]">{c.concept}</strong>
                        <span className="text-[11px] text-[var(--text-soft)] block">Marks dropped in {c.frequency} question{c.frequency > 1 ? 's' : ''}</span>
                      </div>
                      <button
                        onClick={() => navigate('/app/trainer', { state: { concept: c.concept } })}
                        className="px-2.5 py-1 rounded-lg bg-[var(--error)] text-white text-[11px] font-bold hover:opacity-90 flex items-center gap-1"
                      >
                        <Sparkles size={12} /> Practice
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[var(--text-soft)] italic">No recurring weak concepts detected.</p>
              )}
            </Card>

            {/* Frequently Strong Concepts */}
            <Card className="shadow-sm space-y-3 border-l-4 border-l-emerald-500">
              <div className="flex items-center gap-2 text-emerald-500 font-extrabold text-sm">
                <Award size={17} />
                <span>Frequently Strong Concepts (Mastered)</span>
              </div>
              {analytics.frequently_strong_concepts?.length > 0 ? (
                <div className="space-y-2">
                  {analytics.frequently_strong_concepts.map((c, idx) => (
                    <div key={idx} className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-between text-xs">
                      <div>
                        <strong className="text-[var(--text)]">{c.concept}</strong>
                        <span className="text-[11px] text-[var(--text-soft)] block">Scored full marks in {c.frequency} question{c.frequency > 1 ? 's' : ''}</span>
                      </div>
                      <Badge tone="success">Mastered</Badge>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-xs text-[var(--text-soft)] italic">Complete more assessments to demonstrate recurring mastery.</p>
              )}
            </Card>
          </div>

          {/* Stored Evaluation History List with "View Evaluation" Option */}
          <Card className="shadow-sm space-y-3">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5 flex-wrap gap-2">
              <div>
                <h3 className="text-sm font-extrabold text-[var(--text)] flex items-center gap-2">
                  <History size={16} className="text-[var(--accent)]" />
                  <span>Evaluation History & Complete Stored Records</span>
                </h3>
                <p className="text-xs text-[var(--text-soft)]">Click "View Evaluation" to inspect the original questions, answers, and feedback</p>
              </div>
              <Badge tone="accent">{analytics.evaluation_history?.length || 0} Total Records</Badge>
            </div>

            <div className="divide-y divide-[var(--border)]">
              {analytics.evaluation_history?.map((e, idx) => (
                <div key={idx} className="py-3 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 hover:bg-[var(--surface-alt)] px-2 rounded-xl transition-colors">
                  <div className="space-y-0.5">
                    <div className="text-[14px] font-extrabold text-[var(--text)] flex items-center gap-2">
                      <span>{e.subject}</span>
                      <span className="text-xs text-[var(--accent)] font-semibold">— {e.assessment_title}</span>
                      <Badge tone="neutral">{e.grade || 'Graded'}</Badge>
                    </div>
                    <div className="text-xs text-[var(--text-soft)] flex items-center gap-2">
                      <span>Date: {e.date}</span>
                      <span>&bull;</span>
                      <span className="font-mono">ID: {e.evaluation_id}</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 self-end sm:self-center">
                    <div className="text-right">
                      <div className="font-black text-sm text-[var(--accent)]">
                        {e.obtained_marks} / {e.total_marks} marks
                      </div>
                      <div className="text-xs font-bold text-[var(--text-soft)]">
                        {e.percentage}%
                      </div>
                    </div>

                    <Button
                      onClick={() => handleViewEvaluation(e.evaluation_id)}
                      disabled={detailLoading}
                      className="text-xs px-3 py-1.5 flex items-center gap-1.5"
                    >
                      <Eye size={13} />
                      <span>View Evaluation</span>
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* VIEW EVALUATION MODAL (Pulls original stored evaluation result) */}
      {selectedEvalDetail && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-4 shadow-2xl">
            {/* Header */}
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-extrabold text-[var(--text)]">
                    Original Evaluation: {selectedEvalDetail.subject}
                  </h3>
                  <Badge tone="accent">{selectedEvalDetail.assessment_title || 'Assessment Record'}</Badge>
                </div>
                <p className="text-xs text-[var(--text-soft)] mt-0.5">
                  ID: <span className="font-mono">{selectedEvalDetail.id || selectedEvalDetail._id || selectedEvalDetail.evaluation_id}</span> &bull; {selectedEvalDetail.student_name}
                </p>
              </div>
              <button onClick={() => setSelectedEvalDetail(null)} className="p-1 rounded-lg text-[var(--text-faint)] hover:text-[var(--text)]">
                <X size={18} />
              </button>
            </div>

            {/* Score Strip */}
            <div className="grid grid-cols-3 gap-2 p-3 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs text-center">
              <div>
                <span className="text-[var(--text-faint)] block text-[11px] uppercase font-bold">Total Score</span>
                <strong className="text-sm font-black text-[var(--accent)]">
                  {selectedEvalDetail.obtained_marks} / {selectedEvalDetail.total_marks}
                </strong>
              </div>
              <div>
                <span className="text-[var(--text-faint)] block text-[11px] uppercase font-bold">Percentage</span>
                <strong className="text-sm font-black text-emerald-500">
                  {selectedEvalDetail.percentage}%
                </strong>
              </div>
              <div>
                <span className="text-[var(--text-faint)] block text-[11px] uppercase font-bold">Assigned Grade</span>
                <strong className="text-sm font-black text-[var(--text)]">
                  {selectedEvalDetail.grade || 'N/A'}
                </strong>
              </div>
            </div>

            {/* Overall Teacher Assessment */}
            {(selectedEvalDetail.overall_teacher_comment || selectedEvalDetail.overall_feedback) && (
              <div className="p-3 bg-[var(--accent-soft)] rounded-xl border border-[var(--accent)] text-xs space-y-1">
                <span className="font-bold text-[var(--accent)] uppercase tracking-wider block text-[11px]">
                  Teacher Executive Assessment:
                </span>
                <p className="text-[var(--text)] leading-relaxed">{selectedEvalDetail.overall_teacher_comment || selectedEvalDetail.overall_feedback}</p>
              </div>
            )}

            {/* Question Breakdown List */}
            <div className="space-y-3 pt-2">
              <h4 className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)]">
                Question-Wise Feedback & Mark Allocations
              </h4>

              {(selectedEvalDetail.evaluations || selectedEvalDetail.questions || []).map((q, idx) => (
                <div key={idx} className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2 text-xs">
                  <div className="flex items-center justify-between border-b border-[var(--border)] pb-2 flex-wrap gap-2">
                    <span className="font-extrabold text-[var(--text)] text-[13px]">
                      Question {q.question_number || idx + 1}
                    </span>
                    <Badge tone={q.awarded_marks >= (q.maximum_marks || 0) && (q.maximum_marks || 0) > 0 ? 'success' : q.awarded_marks > 0 ? 'warning' : 'error'}>
                      {q.awarded_marks} / {q.maximum_marks} marks
                    </Badge>
                  </div>

                  {q.question_text && (
                    <div className="font-semibold text-[var(--text)] bg-[var(--surface)] p-2 rounded-lg border border-[var(--border)]">
                      {q.question_text}
                    </div>
                  )}

                  {(q.student_answer || q.answer_summary) && (
                    <div className="space-y-0.5">
                      <span className="text-[11px] font-bold text-[var(--text-faint)] block">Your Written Answer:</span>
                      <p className="font-mono italic text-[11.5px] bg-[var(--surface)] p-2 rounded-lg border border-[var(--border)] text-[var(--text)]">
                        &ldquo;{q.student_answer || q.answer_summary}&rdquo;
                      </p>
                    </div>
                  )}

                  {(q.teacher_feedback || q.evaluation_reason) && (
                    <div className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] space-y-0.5">
                      <strong className="text-[var(--accent)] text-[11px] uppercase block">Teacher Feedback:</strong>
                      <p className="text-[var(--text)] leading-relaxed">{q.teacher_feedback || q.evaluation_reason}</p>
                    </div>
                  )}

                  {(q.what_student_should_have_written || q.correct_answer_or_expected_points || q.feedback?.expected_answer) && (
                    <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-0.5">
                      <strong className="text-emerald-500 text-[11px] uppercase block">Expected Academic Solution:</strong>
                      <p className="text-[var(--text)] font-mono whitespace-pre-line text-[11.5px]">
                        {q.what_student_should_have_written || q.correct_answer_or_expected_points || q.feedback?.expected_answer}
                      </p>
                    </div>
                  )}

                  {(q.conceptual_mistake || (q.misconception_detected && q.misconception)) && (
                    <div className="p-2.5 rounded-lg bg-[var(--error-soft)] border border-[var(--error)] space-y-0.5">
                      <strong className="text-[var(--error)] text-[11px] uppercase block">Conceptual Misunderstanding:</strong>
                      <p className="text-[var(--text)] font-semibold">{q.conceptual_mistake || q.misconception}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {/* Modal Footer */}
            <div className="flex justify-end gap-2 pt-2 border-t border-[var(--border)]">
              <Button variant="secondary" onClick={() => setSelectedEvalDetail(null)}>Close</Button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
