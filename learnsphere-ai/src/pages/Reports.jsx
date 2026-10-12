import { useState, useEffect } from 'react'
import { Card, PageHead, Button, Badge } from '../components/ui/Primitives.jsx'
import { api } from '../services/api.js'
import { FileText, Download, Loader2, Trash2 } from 'lucide-react'

export default function Reports() {
  const [reports, setReports] = useState([])
  const [loading, setLoading] = useState(true)

  const loadReports = async () => {
    try {
      const res = await api.getEvaluations()
      if (res && res.success && Array.isArray(res.evaluations)) {
        setReports(res.evaluations)
      } else {
        setReports([])
      }
    } catch (err) {
      console.error('Failed to load evaluation reports:', err)
      setReports([])
    }
  }

  useEffect(() => {
    setLoading(true)
    loadReports().finally(() => setLoading(false))
  }, [])

  const handleDownload = (evalId) => {
    api.downloadEvaluationPdf(evalId)
  }

  const handleDelete = async (evalId, e) => {
    if (e) e.stopPropagation()
    if (!evalId) return
    if (!window.confirm("Are you sure you want to delete this evaluation report?")) {
      return
    }
    const targetId = String(evalId)
    try {
      await api.deleteEvaluation(targetId)
    } catch (err) {
      console.error('Delete error:', err)
    }
    setReports(prev => prev.filter(r => String(r.id || r._id) !== targetId))
  }

  return (
    <>
      <PageHead
        title="Academic Reports"
        subtitle="Export verified assessment reports, grade summaries, and detailed evaluation transcripts."
      />
      
      {loading ? (
        <Card className="p-12 text-center text-[var(--text-soft)]">
          <Loader2 className="animate-spin mx-auto mb-2.5 text-[var(--accent)]" size={30} />
          <span className="text-xs font-semibold">Fetching real evaluation reports from database...</span>
        </Card>
      ) : reports.length === 0 ? (
        <Card className="p-12 text-center my-4 border-dashed border-2">
          <FileText size={44} className="text-[var(--text-faint)] mx-auto mb-3" />
          <h3 className="text-base font-bold mb-1 text-[var(--text)]">No evaluation reports generated yet</h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto mb-4 leading-relaxed">
            Upload and evaluate student question papers & answer scripts in the <strong>Evaluate Answer Script</strong> page. Real reports will automatically generate here upon evaluation.
          </p>
        </Card>
      ) : (
        <Card className="p-0 overflow-hidden">
          <div className="overflow-x-auto scrollbar-thin">
            <table className="w-full min-w-[580px] border-collapse text-xs">
              <thead>
                <tr className="bg-[var(--surface-alt)]">
                  {['Student Name', 'Subject & Exam', 'Score & Grade', 'Date Generated', 'Actions'].map((h) => (
                    <th key={h} className="text-left text-xs text-[var(--text-faint)] font-bold uppercase tracking-wider py-3.5 px-4 border-b border-[var(--border)]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border)]">
                {reports.map((r) => {
                  const evalId = r.id || r._id
                  return (
                    <tr key={evalId} className="hover:bg-[var(--surface-alt)] transition-colors">
                      <td className="py-4 px-4 font-bold text-sm text-[var(--text)]">{r.student_name} <span className="text-xs font-normal text-[var(--text-faint)]">({r.roll_number || 'N/A'})</span></td>
                      <td className="py-4 px-4 text-xs font-semibold text-[var(--text-soft)]">{r.subject} — {r.assessment_title || 'Examination'}</td>
                      <td className="py-4 px-4">
                        <Badge tone={r.status || 'success'}>{r.obtained_marks}/{r.total_marks} ({r.percentage}%) · Grade {r.grade}</Badge>
                      </td>
                      <td className="py-4 px-4 text-xs text-[var(--text-faint)]">{r.created_at || 'Recently'}</td>
                      <td className="py-4 px-4">
                        <div className="flex items-center gap-2">
                          <Button variant="secondary" size="sm" onClick={() => handleDownload(evalId)}>
                            <Download size={14} className="mr-1.5" /> PDF Report
                          </Button>
                          <button
                            onClick={(e) => handleDelete(evalId, e)}
                            className="p-2 rounded-xl border border-[var(--error-soft)] text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                            title="Delete Evaluation Report"
                            aria-label="Delete evaluation report"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </>
  )
}
