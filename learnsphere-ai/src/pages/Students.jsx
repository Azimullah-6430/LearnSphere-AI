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
      <PageHead title="Students portfolio" subtitle="Student roster tracked live across sections in MongoDB Atlas." />
      <Card>
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <SearchBox placeholder="Search students or section..." value={search} onChange={(e) => setSearch(e.target.value)} />
          <div className="text-xs text-[var(--text-faint)] font-medium">
            Active Students: <strong>{filtered.length}</strong>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                {['Student Name', 'Section', 'Average Score', 'Evaluations Count', 'Status'].map((h) => (
                  <th key={h} className="text-left text-[11.5px] text-[var(--text-faint)] font-bold uppercase tracking-wide pb-2.5 px-3 border-b border-[var(--border)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr key={s.id || i} className="hover:bg-[var(--surface-alt)] transition-colors">
                  <td className="py-3.5 px-3 border-b border-[var(--border)] font-semibold">{s.name}</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)]">{s.section}</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)] font-bold text-[var(--accent)]">{s.average}%</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)]">{s.evaluations || 8} completed</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)]">
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
