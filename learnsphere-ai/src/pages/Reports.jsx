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
      <PageHead title="Evaluation & Academic Reports" subtitle="Real-time evaluation summaries derived from submitted student papers." />
      
      {loading ? (
        <Card className="p-8 text-center text-[var(--text-soft)]">
          <Loader2 className="animate-spin mx-auto mb-2 text-[var(--accent)]" size={28} />
          Fetching real evaluation reports from database...
        </Card>
      ) : reports.length === 0 ? (
        <Card className="p-8 text-center my-4 border-dashed border-2">
          <FileText size={40} className="text-[var(--text-faint)] mx-auto mb-3" />
          <h3 className="text-base font-bold mb-1">No evaluation reports generated yet</h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto mb-4">
            Upload and evaluate student question papers & answer scripts in the <strong>Evaluate Answer Script</strong> page. Real reports will automatically generate here upon evaluation.
          </p>
        </Card>
      ) : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-[13px]">
              <thead>
                <tr>
                  {['Student Name', 'Subject & Exam', 'Score & Grade', 'Date Generated', 'Actions'].map((h) => (
                    <th key={h} className="text-left text-[11.5px] text-[var(--text-faint)] font-bold uppercase tracking-wide pb-2.5 px-3 border-b border-[var(--border)]">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => {
                  const evalId = r.id || r._id
                  return (
                    <tr key={evalId} className="hover:bg-[var(--surface-alt)]">
                      <td className="py-3.5 px-3 border-b border-[var(--border)] font-semibold">{r.student_name} ({r.roll_number || 'N/A'})</td>
                      <td className="py-3.5 px-3 border-b border-[var(--border)]">{r.subject} — {r.assessment_title || 'Examination'}</td>
                      <td className="py-3.5 px-3 border-b border-[var(--border)]">
                        <Badge tone={r.status || 'success'}>{r.obtained_marks}/{r.total_marks} ({r.percentage}%) · Grade {r.grade}</Badge>
                      </td>
                      <td className="py-3.5 px-3 border-b border-[var(--border)] text-[var(--text-faint)]">{r.created_at || 'Recently'}</td>
                      <td className="py-3.5 px-3 border-b border-[var(--border)]">
                        <div className="flex items-center gap-1.5">
                          <Button variant="secondary" size="sm" onClick={() => handleDownload(evalId)}>
                            <Download size={14} className="mr-1" /> PDF Report
                          </Button>
                          <button
                            onClick={(e) => handleDelete(evalId, e)}
                            className="p-1.5 rounded-lg border border-[var(--error-soft)] text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors"
                            title="Delete Evaluation Report"
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
