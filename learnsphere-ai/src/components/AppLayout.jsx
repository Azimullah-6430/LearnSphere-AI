import { useState } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { X } from 'lucide-react'
import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'
import SyllabusModal from './SyllabusModal.jsx'
import ClassManagerModal from './ClassManagerModal.jsx'
import { useApp } from '../context/AppContext.jsx'

const TITLES = {
  dashboard: ['Dashboard', 'Overview'],
  evaluate: ['New Evaluation', 'Evaluation'],
  history: ['Evaluation History', 'Evaluation'],
  plagiarism: ['Academic Integrity', 'Integrity'],
  analytics: ['Student Analytics', 'Analytics'],
  reports: ['Reports', 'Analytics'],
  students: ['Students', 'Management'],
  performance: ['Performance', 'My Learning'],
  trainer: ['Personal Trainer', 'AI Support'],
  parent: ['Parent Agent', 'AI Support'],
  focus: ['Focus Session', 'Productivity'],
  memory: ['Academic Memory', 'My Learning'],
  'self-evaluation': ['Self Evaluation', 'My Learning'],
  notifications: ['Notifications', 'System'],
  settings: ['Settings', 'System'],
  'action-center': ['Action Center', 'Analytics'],
  'misconception-map': ['Misconception Map', 'Analytics'],
  'reality-lab': ['Reality Lab', 'AI Support'],
  opportunities: ['Current & Opportunities', 'Productivity & Growth'],
}

function FocusHeader() {
  const { toggleTheme, theme } = useApp()
  const navigate = useNavigate()
  return (
    <header className="h-16 flex items-center justify-between px-7">
      <div className="flex items-center gap-2.5">
        <svg width="26" height="26" viewBox="0 0 32 32" fill="none">
          <circle cx="16" cy="16" r="10.5" stroke="var(--accent)" strokeWidth="2" />
          <circle cx="24" cy="9" r="4" fill="var(--accent)" />
        </svg>
        <div className="text-sm font-extrabold tracking-tight">
          LearnSphere<small className="font-semibold text-[var(--accent)] text-[11px] ml-0.5">AI</small>
        </div>
      </div>
      <div className="flex items-center gap-2.5">
        <button
          onClick={toggleTheme}
          className="w-9 h-9 flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] transition-colors"
        >
          {theme === 'dark' ? '☀' : '☾'}
        </button>
        <button
          onClick={() => navigate('/app/dashboard')}
          className="w-9 h-9 flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] transition-colors"
          title="Exit focus mode"
        >
          <X size={16} strokeWidth={1.8} />
        </button>
      </div>
    </header>
  )
}

export default function AppLayout() {
  const { authenticated } = useApp()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [syllabusModalOpen, setSyllabusModalOpen] = useState(false)
  const [classModalOpen, setClassModalOpen] = useState(false)

  if (!authenticated) return <Navigate to="/" replace />

  const key = location.pathname.split('/').pop()
  const [title, crumb] = TITLES[key] || ['Dashboard', 'Overview']
  const isFocusMode = key === 'focus'

  if (isFocusMode) {
    return (
      <div className="min-h-screen flex flex-col bg-[var(--bg)]">
        <FocusHeader />
        <main className="flex-1 px-[18px]">
          <Outlet />
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen">
      {menuOpen && <div className="fixed inset-0 bg-black/40 z-30 md:hidden backdrop-blur-sm" onClick={() => setMenuOpen(false)} />}
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} onOpenSyllabusModal={() => setSyllabusModalOpen(true)} />
      <div className="flex-1 min-w-0 flex flex-col md:ml-[264px]">
        <Topbar
          title={title}
          crumb={crumb}
          onMenuClick={() => setMenuOpen((v) => !v)}
          onOpenSyllabusModal={() => setSyllabusModalOpen(true)}
          onOpenClassModal={() => setClassModalOpen(true)}
        />
        <main className="px-3.5 sm:px-6 md:px-[34px] pt-5 sm:pt-[30px] pb-12 sm:pb-[60px] w-full max-w-content mx-auto">
          <Outlet />
        </main>
      </div>
      <SyllabusModal isOpen={syllabusModalOpen} onClose={() => setSyllabusModalOpen(false)} />
      <ClassManagerModal isOpen={classModalOpen} onClose={() => setClassModalOpen(false)} />
    </div>
  )
}
