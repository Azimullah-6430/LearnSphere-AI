import { Card, PageHead, Button } from '../components/ui/Primitives.jsx'
import { reports } from '../data/mockData.js'

export default function Reports() {
  return (
    <>
      <PageHead title="Reports" subtitle="Generated summaries ready to share or export." />
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-[13px]">
            <thead>
              <tr>
                {['Report', 'Scope', 'Generated', ''].map((h) => (
                  <th key={h} className="text-left text-[11.5px] text-[var(--text-faint)] font-bold uppercase tracking-wide pb-2.5 px-3 border-b border-[var(--border)]">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {reports.map((r, i) => (
                <tr key={i} className="hover:bg-[var(--surface-alt)]">
                  <td className="py-3.5 px-3 border-b border-[var(--border)]">{r.title}</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)]">{r.scope}</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)] text-[var(--text-faint)]">{r.when}</td>
                  <td className="py-3.5 px-3 border-b border-[var(--border)]">
                    <Button variant="secondary" size="sm">Download</Button>
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
