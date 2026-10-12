import { useState, useEffect } from 'react'
import { Card, PageHead, SearchBox, Badge } from '../components/ui/Primitives.jsx'
import { api } from '../services/api.js'

export default function Students() {
  const [students, setStudents] = useState([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadStudents() {
      setLoading(true)
      const res = await api.getStudents()
      if (res && res.success && Array.isArray(res.students)) {
        setStudents(res.students)
      } else {
        setStudents([])
      }
      setLoading(false)
    }
    loadStudents()
  }, [])

  const filtered = students.filter(s => 
    s.name.toLowerCase().includes(search.toLowerCase()) || 
    s.section.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <>
      <PageHead
        title="Students Directory"
        subtitle="Class roster performance tracking, evaluation counts, and academic standing."
      />
      <Card className="p-0 overflow-hidden">
        <div className="flex items-center justify-between p-4 sm:p-5 border-b border-[var(--border)] flex-wrap gap-3">
          <SearchBox placeholder="Search students or section..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="text-xs text-[var(--text-faint)] font-bold">
            Active Enrolled: <strong className="text-[var(--text)]">{filtered.length}</strong>
          </div>
        </div>
        <div className="overflow-x-auto scrollbar-thin">
          <table className="w-full min-w-[580px] border-collapse text-xs">
            <thead>
              <tr className="bg-[var(--surface-alt)]">
                {['Student Name', 'Section', 'Average Score', 'Evaluations Count', 'Status'].map((h) => (
                  <th key={h} className="text-left text-xs text-[var(--text-faint)] font-bold uppercase tracking-wider py-3.5 px-4 border-b border-[var(--border)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filtered.map((s, i) => (
                <tr key={s.id || i} className="hover:bg-[var(--surface-alt)] transition-colors">
                  <td className="py-4 px-4 font-bold text-sm text-[var(--text)]">{s.name}</td>
                  <td className="py-4 px-4 text-xs font-semibold text-[var(--text-soft)]">{s.section}</td>
                  <td className="py-4 px-4 font-extrabold text-sm text-[var(--accent)]">{s.average}%</td>
                  <td className="py-4 px-4 text-xs text-[var(--text-soft)]">{s.evaluations ?? 0} completed</td>
                  <td className="py-4 px-4">
                    <Badge tone={s.status === 'On track' ? 'success' : s.status === 'At risk' ? 'error' : 'warning'}>
                      {s.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </>
  )
}
