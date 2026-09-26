import { useState, useEffect } from 'react'
import { Card, CardHeader, PageHead, Button } from '../components/ui/Primitives.jsx'
import { TrendChart, SubjectBarChart } from '../components/charts/Charts.jsx'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { FileText, ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

export default function Performance() {
  const { user } = useApp()
  const navigate = useNavigate()
  const [evaluations, setEvaluations] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadUserPerformance() {
      setLoading(true)
      const res = await api.getEvaluations({ student_name: user?.name })
      if (res && res.success && Array.isArray(res.evaluations)) {
        setEvaluations(res.evaluations)
      } else {
        setEvaluations([])
      }
      setLoading(false)
    }
    loadUserPerformance()
  }, [user])

  const hasData = evaluations.length > 0

  // Build chart data dynamically from real user evaluations
  const trendData = evaluations.map((e, i) => ({
    label: `Eval ${i + 1}`,
    value: e.percentage
  }))

  const subjectMap = {}
  evaluations.forEach(e => {
    if (!subjectMap[e.subject]) subjectMap[e.subject] = { total: 0, count: 0 }
    subjectMap[e.subject].total += e.percentage
    subjectMap[e.subject].count += 1
  })

  const subjectPerformanceData = Object.keys(subjectMap).map(subj => ({
    label: subj,
    value: Math.round(subjectMap[subj].total / subjectMap[subj].count)
  }))

  return (
    <>
      <PageHead title="Your learning progress" subtitle="Analytics derived strictly from your submitted evaluations." />

      {!hasData ? (
        <Card className="p-8 text-center my-6 border-dashed border-2">
          <FileText size={42} className="text-[var(--accent)] mx-auto mb-3" />
          <h3 className="text-lg font-bold mb-1">No Performance Analytics Recorded</h3>
          <p className="text-sm text-[var(--text-soft)] max-w-md mx-auto mb-5">
            You haven't completed any graded evaluations yet. Submit a Question Paper and Answer Script to view your progress trends and subject breakdown.
          </p>
          <Button onClick={() => navigate('/app/self-evaluation')} className="mx-auto flex items-center gap-2">
            Run Your First Evaluation <ArrowRight size={14} />
          </Button>
        </Card>
      ) : (
        <>
          <div className="grid md:grid-cols-2 gap-3.5 mb-3.5">
            <Card>
              <CardHeader title="Overall Performance Trend" />
              <TrendChart data={trendData} />
            </Card>
            <Card>
              <CardHeader title="Performance By Subject" />
              <SubjectBarChart data={subjectPerformanceData} />
            </Card>
          </div>

          <Card>
            <CardHeader title="Recent Evaluation History" />
            {evaluations.map((e, i) => (
              <div key={i} className="flex items-center justify-between py-3 border-b border-[var(--border)] last:border-0">
                <div>
                  <div className="text-[13.5px] font-semibold">{e.subject} — {e.assessment_title}</div>
                  <div className="text-xs text-[var(--text-faint)] mt-0.5">Grade {e.grade} · {e.created_at || 'Recently'}</div>
                </div>
                <div className="font-extrabold text-sm text-[var(--accent)]">
                  {e.percentage}%
                </div>
              </div>
            ))}
          </Card>
        </>
      )}
    </>
  )
}
