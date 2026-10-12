import { useState, useEffect } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { X, Sun, Moon } from 'lucide-react'
import Sidebar from './Sidebar.jsx'
import Topbar from './Topbar.jsx'
import SyllabusModal from './SyllabusModal.jsx'
import ClassManagerModal from './ClassManagerModal.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import { useApp } from '../context/AppContext.jsx'

const TITLES = {
  dashboard: ['Dashboard', 'Overview'],
  evaluate: ['Evaluate Script', 'Evaluation & Integrity'],
  history: ['Evaluation History', 'Evaluation & Integrity'],
  plagiarism: ['Academic Integrity Audit', 'Evaluation & Integrity'],
  analytics: ['Student Analytics', 'Intelligence & Actions'],
  reports: ['Academic Reports', 'Intelligence & Actions'],
  students: ['Roster & Students', 'Intelligence & Actions'],
  performance: ['My Performance', 'Learning Progress'],
  trainer: ['Personal Trainer', 'Interactive AI Learning'],
  parent: ['Parent Agent', 'Productivity & Growth'],
  focus: ['Focus Session', 'Productivity & Growth'],
  memory: ['Academic Memory', 'Productivity & Growth'],
  'self-evaluation': ['Self Evaluation', 'Learning Progress'],
  notifications: ['Notifications', 'Curriculum & System'],
  settings: ['Account & Settings', 'Curriculum & System'],
  'action-center': ['Action Center', 'Intelligence & Actions'],
  'misconception-map': ['Misconception Map', 'Intelligence & Actions'],
  'reality-lab': ['Reality Lab', 'Interactive AI Learning'],
  opportunities: ['Current & Opportunities', 'Productivity & Growth'],
  'learn-anywhere': ['Learn from Anywhere', 'Interactive AI Learning'],
  'knowledge-challenge': ['Knowledge Challenge', 'Interactive AI Learning'],
}

function FocusHeader() {
  const { toggleTheme, theme } = useApp()
  const navigate = useNavigate()
  return (
    <header className="h-16 flex items-center justify-between px-4 sm:px-8 border-b border-[var(--border)] bg-[var(--surface)] gap-2">
      <div className="flex items-center gap-2.5 min-w-0">
        <div className="w-8 h-8 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center shadow-xs shrink-0">
          <svg width="20" height="20" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="10.5" stroke="currentColor" strokeWidth="2.5" />
            <circle cx="23" cy="10" r="4.5" fill="currentColor" />
          </svg>
        </div>
        <div className="text-base font-extrabold tracking-tight text-[var(--text)] truncate">
          LearnSphere<span className="text-[var(--accent)] ml-0.5">AI</span>
        </div>
        <span className="hidden sm:inline-flex text-xs px-2.5 py-0.5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-bold ml-1 shrink-0">
          Focus Mode
        </span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={toggleTheme}
          className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
          title="Toggle theme"
          aria-label="Toggle theme"
        >
          {theme === 'dark' ? <Sun size={17} strokeWidth={1.8} /> : <Moon size={17} strokeWidth={1.8} />}
        </button>
        <button
          onClick={() => navigate('/app/dashboard')}
          className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
          title="Exit focus mode"
          aria-label="Exit focus mode"
        >
          <X size={17} strokeWidth={1.8} />
        </button>
      </div>
    </header>
  )
}

export default function AppLayout() {
  const { authenticated, authLoading } = useApp()
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const [syllabusModalOpen, setSyllabusModalOpen] = useState(false)
  const [classModalOpen, setClassModalOpen] = useState(false)

  // Close mobile drawer on route change
  useEffect(() => {
    setMenuOpen(false)
  }, [location.pathname])

  // Lock body scroll and listen for Escape key when mobile menu is open
  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = 'hidden'
    } else {
      document.body.style.overflow = ''
    }

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setMenuOpen(false)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => {
      document.body.style.overflow = ''
      window.removeEventListener('keydown', handleKeyDown)
    }
  }, [menuOpen])

  if (authLoading) return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--bg)]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 rounded-full border-2 border-[var(--accent)] border-t-transparent animate-spin" />
        <div className="text-[var(--text-soft)] text-sm font-medium">Verifying session…</div>
      </div>
    </div>
  )

  if (!authenticated) return <Navigate to="/" replace />

  const key = location.pathname.split('/').pop()
  const [title, crumb] = TITLES[key] || ['Dashboard', 'Overview']
  const isFocusMode = key === 'focus'

  if (isFocusMode) {
    return (
      <div className="min-h-screen flex flex-col bg-[var(--bg)]">
        <FocusHeader />
        <main className="flex-1 px-3 sm:px-6 md:px-8 py-5 sm:py-6 w-full max-w-content mx-auto min-w-0">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen bg-[var(--bg)] overflow-x-hidden">
      {/* Skip to Main Content Link for Keyboard and Screen Readers */}
      <a href="#main-content" className="skip-to-content">
        Skip to main content
      </a>

      {/* Mobile Drawer Backdrop */}
      {menuOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-30 md:hidden backdrop-blur-xs transition-opacity duration-200"
          onClick={() => setMenuOpen(false)}
          aria-hidden="true"
        />
      )}
      <Sidebar
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
        onOpenSyllabusModal={() => setSyllabusModalOpen(true)}
      />
      <div className="flex-1 min-w-0 flex flex-col md:ml-[272px] transition-all">
        <Topbar
          title={title}
          crumb={crumb}
          onMenuClick={() => setMenuOpen((v) => !v)}
          onOpenSyllabusModal={() => setSyllabusModalOpen(true)}
          onOpenClassModal={() => setClassModalOpen(true)}
        />
        <main
          id="main-content"
          tabIndex="-1"
          className="px-3.5 sm:px-6 md:px-8 lg:px-10 pt-5 sm:pt-8 pb-16 safe-bottom w-full max-w-content mx-auto min-w-0 outline-none"
        >
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
      </div>
      <SyllabusModal isOpen={syllabusModalOpen} onClose={() => setSyllabusModalOpen(false)} />
      <ClassManagerModal isOpen={classModalOpen} onClose={() => setClassModalOpen(false)} />
    </div>
  )
}
