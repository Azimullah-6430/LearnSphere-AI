import { useState } from 'react'
import { Card, PageHead, Button } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { UploadCloud, FileText, CheckCircle2 } from 'lucide-react'

export default function Settings() {
  const { user } = useApp()
  const [syllabusFile, setSyllabusFile] = useState(null)
  const [savedMsg, setSavedMsg] = useState(false)

  const handleSave = (e) => {
    e.preventDefault()
    setSavedMsg(true)
    setTimeout(() => setSavedMsg(false), 3000)
  }

  return (
    <>
      <PageHead title="Settings & Profile" subtitle="Manage your account, preferences, and syllabus document." />
      
      <div className="grid md:grid-cols-2 gap-6 max-w-[900px]">
        <Card>
          <h3 className="font-bold text-base mb-4">Account Profile</h3>
          <form onSubmit={handleSave}>
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Full name</label>
              <input defaultValue={user?.name || ''} className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
            </div>
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Email address</label>
              <input defaultValue={user?.email || ''} className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
            </div>
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Portal Role</label>
              <input value={user?.role === 'teacher' ? 'Teacher Portal' : 'Student Portal'} disabled className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface-sunken)] text-sm text-[var(--text-soft)] capitalize" />
            </div>
            <div className="mb-5">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Time zone</label>
              <input defaultValue="Asia/Kolkata (GMT+5:30)" className="w-full px-3.5 py-[11px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-sm" />
            </div>
            <Button type="submit">Save changes</Button>
            {savedMsg && (
              <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-600 font-semibold">
                <CheckCircle2 size={16} /> Profile settings saved successfully!
              </div>
            )}
          </form>
        </Card>

        <Card>
          <h3 className="font-bold text-base mb-1">Upload Course Syllabus</h3>
          <p className="text-xs text-[var(--text-soft)] mb-4">Upload your official course syllabus PDF or image to personalize AI evaluations and study guides.</p>
          
          <div className="border-2 border-dashed border-[var(--border-strong)] rounded-xl p-6 text-center bg-[var(--surface)] hover:border-[var(--accent)] transition-colors cursor-pointer relative">
            <input 
              type="file" 
              accept=".pdf,.png,.jpg,.jpeg" 
              className="absolute inset-0 opacity-0 cursor-pointer"
              onChange={(e) => e.target.files[0] && setSyllabusFile(e.target.files[0])}
            />
            <div className="w-12 h-12 mx-auto mb-3 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
              <UploadCloud size={24} />
            </div>
            <div className="font-semibold text-sm mb-1">{syllabusFile ? syllabusFile.name : 'Click or drop syllabus PDF / image'}</div>
            <div className="text-xs text-[var(--text-faint)]">Supports PDF, PNG, JPG (Max 25MB)</div>
          </div>

          {syllabusFile && (
            <div className="mt-4 p-3 bg-[var(--accent-soft)] rounded-lg flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-[var(--accent)]">
                <FileText size={16} />
                <span>{syllabusFile.name}</span>
              </div>
              <button onClick={() => setSyllabusFile(null)} className="text-xs text-red-600 font-semibold hover:underline">Remove</button>
            </div>
          )}

          <div className="mt-5">
            <Button variant="secondary" onClick={() => { if (syllabusFile) alert('Syllabus updated successfully!') }}>
              Upload & Save Syllabus
            </Button>
          </div>
        </Card>
      </div>
    </>
  )
}

