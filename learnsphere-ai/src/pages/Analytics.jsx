import { useState } from 'react'
import { useApp } from '../context/AppContext.jsx'
import { Card, CardHeader, PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { TrendChart, SubjectBarChart } from '../components/charts/Charts.jsx'
import { Award, AlertTriangle, XCircle, TrendingUp, Users, CheckCircle2, Building, ShieldAlert, Sparkles, Plus } from 'lucide-react'
import ClassManagerModal from '../components/ClassManagerModal.jsx'

export default function Analytics() {
  const { teacherClasses, activeClassId, activeClass, setActiveClassId } = useApp()
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [filterCategory, setFilterCategory] = useState('all') // 'all' | 'toppers' | 'average' | 'slow' | 'failed'

  // Filter student rosters strictly by activeClass
  const selectedClass = activeClass || (teacherClasses.length > 0 ? teacherClasses[0] : null)
  const relevantClasses = selectedClass ? [selectedClass] : []

  // Consolidate all students across relevant classes with computed metrics
  const processedStudents = []
  relevantClasses.forEach((cls) => {
    const classStudents = cls.students || []
    classStudents.forEach((std) => {
      const history = std.marksHistory || []
      const hasMarks = history.length > 0
      const totalPercentage = hasMarks
        ? Math.round(history.reduce((acc, m) => acc + m.percentage, 0) / history.length)
        : null

      let category = 'unrated'
      if (totalPercentage !== null) {
        if (totalPercentage >= 85) category = 'toppers'
        else if (totalPercentage >= 60) category = 'average'
        else if (totalPercentage >= 40) category = 'slow'
        else category = 'failed'
      }

      // Find lowest scoring subject
      let weakestSubject = 'N/A'
      if (hasMarks) {
        const sorted = [...history].sort((a, b) => a.percentage - b.percentage)
        weakestSubject = `${sorted[0].subject} (${sorted[0].percentage}%)`
      }

      processedStudents.push({
        ...std,
        className: cls.name,
        classLevel: cls.level,
        classId: cls.id,
        totalPercentage,
        category,
        weakestSubject,
        marksHistory: history
      })
    })
  })

  // Metric counts
  const totalStudentsCount = processedStudents.length
  const toppers = processedStudents.filter((s) => s.category === 'toppers')
  const averageLearners = processedStudents.filter((s) => s.category === 'average')
  const slowLearners = processedStudents.filter((s) => s.category === 'slow')
  const failedStudents = processedStudents.filter((s) => s.category === 'failed')
  const unratedCount = processedStudents.filter((s) => s.category === 'unrated').length

  const evaluatedCount = totalStudentsCount - unratedCount
  const passedCount = toppers.length + averageLearners.length + slowLearners.length
  const passRate = evaluatedCount > 0 ? Math.round((passedCount / evaluatedCount) * 100) : 0

  // Chart data calculation
  const categoryDistributionData = [
    { label: 'Toppers (≥85%)', value: toppers.length },
    { label: 'Average (60-84%)', value: averageLearners.length },
    { label: 'Slow Learners (40-59%)', value: slowLearners.length },
    { label: 'Failed (<40%)', value: failedStudents.length }
  ]

  // Subject performance map across filtered classes
  const subjectScores = {}
  processedStudents.forEach((std) => {
    std.marksHistory.forEach((m) => {
      if (!subjectScores[m.subject]) subjectScores[m.subject] = { total: 0, count: 0 }
      subjectScores[m.subject].total += m.percentage
      subjectScores[m.subject].count += 1
    })
  })

  const subjectChartData = Object.keys(subjectScores).map((sub) => ({
    label: sub,
    value: Math.round(subjectScores[sub].total / subjectScores[sub].count)
  }))

  const displayedStudents = processedStudents.filter((s) => {
    if (filterCategory === 'all') return true
    return s.category === filterCategory
  })

  return (
    <>
      <PageHead title="Class Student Analytics" />

      {/* Active Class Indicator & Switcher Bar */}
      <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] mb-4 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-[13.5px] font-extrabold text-[var(--text)]">
          <Building size={18} className="text-[var(--accent)]" />
          <span>Active Class:</span>
          <span className="px-2.5 py-1 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] font-extrabold border border-[var(--accent)]">
            {selectedClass ? selectedClass.name : 'No Class Selected'}
          </span>
          <span className="text-[12px] text-[var(--text-soft)] font-medium">({totalStudentsCount} Enrolled Students)</span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[12px] font-bold text-[var(--text-soft)]">Switch Class:</span>
          <select
            value={selectedClass?.id || ''}
            onChange={(e) => setActiveClassId(e.target.value)}
            className="px-3 py-1.5 rounded-lg text-[12.5px] font-bold border border-[var(--border)] bg-[var(--surface-alt)] text-[var(--text)] outline-none cursor-pointer"
          >
            {teacherClasses.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name} ({c.students ? c.students.length : 0} std)
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Overview Stat Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3.5 mb-5">
        <Card className="p-4 border-l-4 border-l-[var(--accent)] bg-[var(--surface)]">
          <div className="text-[11px] font-bold text-[var(--text-soft)] uppercase tracking-wider mb-1">Total Enrolled</div>
          <div className="text-2xl font-extrabold text-[var(--text)] flex items-center justify-between">
            <span>{totalStudentsCount}</span>
            <Users size={22} className="text-[var(--accent)] opacity-80" />
          </div>
          <div className="text-[11px] text-[var(--text-faint)] mt-1 font-medium">{evaluatedCount} Evaluated</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-emerald-500 bg-[var(--surface)]">
          <div className="text-[11px] font-bold text-emerald-600 uppercase tracking-wider mb-1">🥇 Toppers (≥85%)</div>
          <div className="text-2xl font-extrabold text-emerald-600 flex items-center justify-between">
            <span>{toppers.length}</span>
            <Award size={22} className="text-emerald-500 opacity-80" />
          </div>
          <div className="text-[11px] text-emerald-600/80 mt-1 font-bold">
            {totalStudentsCount > 0 ? Math.round((toppers.length / totalStudentsCount) * 100) : 0}% of Class
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-blue-500 bg-[var(--surface)]">
          <div className="text-[11px] font-bold text-blue-600 uppercase tracking-wider mb-1">📈 Average (60-84%)</div>
          <div className="text-2xl font-extrabold text-blue-600 flex items-center justify-between">
            <span>{averageLearners.length}</span>
            <TrendingUp size={22} className="text-blue-500 opacity-80" />
          </div>
          <div className="text-[11px] text-blue-600/80 mt-1 font-bold">
            {totalStudentsCount > 0 ? Math.round((averageLearners.length / totalStudentsCount) * 100) : 0}% of Class
          </div>
        </Card>

        <Card className="p-4 border-l-4 border-l-amber-500 bg-[var(--surface)]">
          <div className="text-[11px] font-bold text-amber-600 uppercase tracking-wider mb-1">🥉 Slow Learners (40-59%)</div>
          <div className="text-2xl font-extrabold text-amber-600 flex items-center justify-between">
            <span>{slowLearners.length}</span>
            <AlertTriangle size={22} className="text-amber-500 opacity-80" />
          </div>
          <div className="text-[11px] text-amber-600/80 mt-1 font-bold">Needs Revision</div>
        </Card>

        <Card className="p-4 border-l-4 border-l-red-500 bg-[var(--surface)]">
          <div className="text-[11px] font-bold text-red-600 uppercase tracking-wider mb-1">⚠️ Failed (&lt;40%)</div>
          <div className="text-2xl font-extrabold text-red-600 flex items-center justify-between">
            <span>{failedStudents.length}</span>
            <XCircle size={22} className="text-red-500 opacity-80" />
          </div>
          <div className="text-[11px] text-red-600/80 mt-1 font-bold">Critical Action Needed</div>
        </Card>
      </div>

      {/* Target Intervention Lists: Toppers vs Slow Learners vs Failed */}
      <div className="grid lg:grid-cols-3 gap-4 mb-5">
        {/* TOPPERS ROSTER */}
        <Card className="p-4 space-y-3 border border-emerald-500/30 bg-emerald-500/5">
          <div className="flex items-center justify-between border-b border-emerald-500/20 pb-2">
            <div className="flex items-center gap-2 text-[14px] font-extrabold text-emerald-700">
              <Award size={18} />
              <span>Topper Performers ({toppers.length})</span>
            </div>
            <Badge tone="success">Top Rank</Badge>
          </div>

          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 text-[12.5px]">
            {toppers.length === 0 ? (
              <div className="text-center py-4 text-[var(--text-soft)] italic">No toppers recorded yet</div>
            ) : (
              toppers.map((st, i) => (
                <div key={st.id || i} className="p-2.5 rounded-lg bg-[var(--surface)] border border-emerald-500/20 flex items-center justify-between">
                  <div>
                    <div className="font-extrabold text-[var(--text)]">{st.name}</div>
                    <div className="text-[11px] text-[var(--text-soft)]">{st.rollNo} • {st.className}</div>
                  </div>
                  <div className="text-right font-extrabold text-emerald-600 text-[14px]">
                    {st.totalPercentage}%
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* SLOW LEARNERS ROSTER */}
        <Card className="p-4 space-y-3 border border-amber-500/30 bg-amber-500/5">
          <div className="flex items-center justify-between border-b border-amber-500/20 pb-2">
            <div className="flex items-center gap-2 text-[14px] font-extrabold text-amber-700">
              <AlertTriangle size={18} />
              <span>Slow Learners ({slowLearners.length})</span>
            </div>
            <Badge tone="warning">Need Attention</Badge>
          </div>

          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 text-[12.5px]">
            {slowLearners.length === 0 ? (
              <div className="text-center py-4 text-[var(--text-soft)] italic">No slow learners in this class</div>
            ) : (
              slowLearners.map((st, i) => (
                <div key={st.id || i} className="p-2.5 rounded-lg bg-[var(--surface)] border border-amber-500/20 flex items-center justify-between">
                  <div>
                    <div className="font-extrabold text-[var(--text)]">{st.name}</div>
                    <div className="text-[11px] text-amber-700 font-medium">Weakest: {st.weakestSubject}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-amber-600 text-[14px] block">{st.totalPercentage}%</span>
                    <span className="text-[10px] text-[var(--text-faint)] font-bold">Target Revision</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        {/* FAILED STUDENTS ROSTER */}
        <Card className="p-4 space-y-3 border border-red-500/30 bg-red-500/5">
          <div className="flex items-center justify-between border-b border-red-500/20 pb-2">
            <div className="flex items-center gap-2 text-[14px] font-extrabold text-red-700">
              <ShieldAlert size={18} />
              <span>Failed / At-Risk ({failedStudents.length})</span>
            </div>
            <Badge tone="error">Failing Tier</Badge>
          </div>

          <div className="space-y-2 max-h-[220px] overflow-y-auto pr-1 text-[12.5px]">
            {failedStudents.length === 0 ? (
              <div className="text-center py-4 text-[var(--text-soft)] italic">Zero failed students! All passing 🎉</div>
            ) : (
              failedStudents.map((st, i) => (
                <div key={st.id || i} className="p-2.5 rounded-lg bg-[var(--surface)] border border-red-500/20 flex items-center justify-between">
                  <div>
                    <div className="font-extrabold text-[var(--text)]">{st.name} ({st.rollNo})</div>
                    <div className="text-[11px] text-red-600 font-bold">Failed in: {st.weakestSubject}</div>
                  </div>
                  <div className="text-right">
                    <span className="font-extrabold text-red-600 text-[14px] block">{st.totalPercentage}%</span>
                    <span className="text-[10px] bg-red-500/10 text-red-600 px-1.5 py-0.5 rounded font-bold">Parent Alert</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>
      </div>

      {/* Analytics Charts */}
      <div className="grid md:grid-cols-2 gap-3.5 mb-5">
        <Card>
          <CardHeader title="Performance Tier Breakdown" />
          <SubjectBarChart data={categoryDistributionData} />
        </Card>
        <Card>
          <CardHeader title="Subject Performance Average (%)" />
          <SubjectBarChart data={subjectChartData.length > 0 ? subjectChartData : [{ label: 'No Subject Data', value: 0 }]} />
        </Card>
      </div>

      {/* Full Class Roster & Marks Table */}
      <Card>
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)] mb-3 flex-wrap gap-2">
          <CardHeader title="Stored Class Roster & Evaluated Marks Ledger" />

          {/* Filter buttons */}
          <div className="flex gap-1.5 text-[12px] font-bold">
            <button
              onClick={() => setFilterCategory('all')}
              className={`px-2.5 py-1 rounded-lg border transition-all ${
                filterCategory === 'all'
                  ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                  : 'bg-[var(--surface-alt)] text-[var(--text-soft)] border-[var(--border)]'
              }`}
            >
              All ({totalStudentsCount})
            </button>
            <button
              onClick={() => setFilterCategory('toppers')}
              className={`px-2.5 py-1 rounded-lg border transition-all ${
                filterCategory === 'toppers'
                  ? 'bg-emerald-600 text-white border-emerald-600'
                  : 'bg-[var(--surface-alt)] text-emerald-600 border-[var(--border)]'
              }`}
            >
              Toppers ({toppers.length})
            </button>
            <button
              onClick={() => setFilterCategory('average')}
              className={`px-2.5 py-1 rounded-lg border transition-all ${
                filterCategory === 'average'
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-[var(--surface-alt)] text-blue-600 border-[var(--border)]'
              }`}
            >
              Average ({averageLearners.length})
            </button>
            <button
              onClick={() => setFilterCategory('slow')}
              className={`px-2.5 py-1 rounded-lg border transition-all ${
                filterCategory === 'slow'
                  ? 'bg-amber-600 text-white border-amber-600'
                  : 'bg-[var(--surface-alt)] text-amber-600 border-[var(--border)]'
              }`}
            >
              Slow Learners ({slowLearners.length})
            </button>
            <button
              onClick={() => setFilterCategory('failed')}
              className={`px-2.5 py-1 rounded-lg border transition-all ${
                filterCategory === 'failed'
                  ? 'bg-red-600 text-white border-red-600'
                  : 'bg-[var(--surface-alt)] text-red-600 border-[var(--border)]'
              }`}
            >
              Failed ({failedStudents.length})
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr className="bg-[var(--surface-alt)] border-b border-[var(--border)]">
                <th className="py-3 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">#</th>
                <th className="py-3 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Roll No / RRN</th>
                <th className="py-3 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Student Name & Initial</th>
                <th className="py-3 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Class / Dept</th>
                <th className="py-3 px-3 text-left font-bold text-[var(--text-faint)] uppercase text-[11px]">Evaluated Subject Marks</th>
                <th className="py-3 px-3 text-center font-bold text-[var(--text-faint)] uppercase text-[11px]">Overall %</th>
                <th className="py-3 px-3 text-center font-bold text-[var(--text-faint)] uppercase text-[11px]">Performance Tier</th>
              </tr>
            </thead>
            <tbody>
              {displayedStudents.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-[var(--text-soft)] font-medium">
                    No students match the selected filter category.
                  </td>
                </tr>
              ) : (
                displayedStudents.map((st, i) => (
                  <tr key={st.id || i} className="border-b border-[var(--border)] hover:bg-[var(--surface-alt)]">
                    <td className="py-3.5 px-3 font-bold text-[var(--text-faint)] text-[12px]">{st.order || i + 1}</td>
                    <td className="py-3.5 px-3 font-mono font-bold text-[var(--text)]">{st.rollNo}</td>
                    <td className="py-3.5 px-3 font-extrabold text-[var(--text)]">{st.name}</td>
                    <td className="py-3.5 px-3 text-[12px] text-[var(--text-soft)] font-medium">{st.className}</td>
                    <td className="py-3.5 px-3">
                      {st.marksHistory.length === 0 ? (
                        <span className="text-[11px] text-[var(--text-soft)] italic">Pending evaluation</span>
                      ) : (
                        <div className="flex flex-wrap gap-1.5">
                          {st.marksHistory.map((m, mIdx) => (
                            <span
                              key={mIdx}
                              className={`px-2 py-0.5 rounded text-[11px] font-bold border ${
                                m.percentage >= 85
                                  ? 'bg-emerald-500/10 text-emerald-600 border-emerald-500/30'
                                  : m.percentage >= 60
                                  ? 'bg-blue-500/10 text-blue-600 border-blue-500/30'
                                  : m.percentage >= 40
                                  ? 'bg-amber-500/10 text-amber-600 border-amber-500/30'
                                  : 'bg-red-500/10 text-red-600 border-red-500/30'
                              }`}
                            >
                              {m.subject}: {m.percentage}%
                            </span>
                          ))}
                        </div>
                      )}
                    </td>
                    <td className="py-3.5 px-3 text-center font-extrabold text-[15px] text-[var(--accent)]">
                      {st.totalPercentage !== null ? `${st.totalPercentage}%` : 'N/A'}
                    </td>
                    <td className="py-3.5 px-3 text-center">
                      {st.category === 'toppers' && <Badge tone="success">🥇 Topper</Badge>}
                      {st.category === 'average' && <Badge tone="accent">📈 Average</Badge>}
                      {st.category === 'slow' && <Badge tone="warning">🥉 Slow Learner</Badge>}
                      {st.category === 'failed' && <Badge tone="error">⚠️ Failed</Badge>}
                      {st.category === 'unrated' && <Badge tone="neutral">Unrated</Badge>}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <ClassManagerModal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} />
    </>
  )
}
