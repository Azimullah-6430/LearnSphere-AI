import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  FileUp,
  History,
  ShieldCheck,
  BarChart3,
  FileText,
  Users,
  LineChart,
  Bot,
  HeartHandshake,
  Timer,
  BookOpen,
  CheckCircle2,
  Bell,
  Settings,
  Sparkles,
  FlaskConical,
  Map,
  UploadCloud,
  Globe,
  Zap,
  Compass,
  X,
  LogOut,
  GraduationCap,
  Building2,
  ChevronRight
} from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'

const navItemClass = ({ isActive }) =>
  `relative group flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm sm:text-[14.5px] font-semibold transition-all duration-150 cursor-pointer ${
    isActive
      ? 'bg-[var(--accent-soft)] text-[var(--accent)] font-bold shadow-xs border border-[var(--accent)]/20'
      : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
  }`

function NavLabel({ children }) {
  return (
    <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] px-3.5 pt-4 pb-1.5 flex items-center justify-between">
      <span>{children}</span>
    </div>
  )
}

function Item({ to, icon: Icon, children, onClick, badge }) {
  return (
    <NavLink to={to} className={navItemClass} onClick={onClick}>
      <Icon size={19} strokeWidth={1.8} className="shrink-0 opacity-90 transition-transform group-hover:scale-105" />
      <span className="truncate flex-1">{children}</span>
      {badge && (
        <span className="text-[11px] font-bold uppercase tracking-wide px-2 py-0.5 rounded-md bg-[var(--accent)]/10 text-[var(--accent)]">
          {badge}
        </span>
      )}
    </NavLink>
  )
}

export default function Sidebar({ open, onClose, onOpenSyllabusModal }) {
  const { role, user, logout } = useApp()
  const isTeacher = role === 'teacher'

  return (
    <aside
      role="navigation"
      aria-label="Main sidebar navigation"
      className={`w-[260px] shrink-0 bg-[var(--surface)] border-r border-[var(--border)] flex flex-col fixed top-0 bottom-0 left-0 overflow-y-auto z-40 transition-transform duration-200 md:translate-x-0 scrollbar-thin ${
        open ? 'translate-x-0 shadow-2xl' : '-translate-x-full'
      }`}
      style={{
        paddingTop: 'max(0.5rem, env(safe-area-inset-top))',
        paddingBottom: 'max(0.5rem, env(safe-area-inset-bottom))'
      }}
    >
      {/* Brand Header & Role Identifier */}
      <div className="px-5 py-4 border-b border-[var(--border)]">
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3 min-w-0">
            <img src="/learnsphere-icon.png" alt="LearnSphere AI" className="w-10 h-10 rounded-xl object-contain shrink-0 shadow-xs" />
            <div className="min-w-0">
              <div className="text-lg font-extrabold tracking-tight text-[var(--text)] leading-none truncate">
                LearnSphere<span className="text-[var(--accent)] ml-0.5">AI</span>
              </div>
              <div className="text-xs text-[var(--text-faint)] font-medium mt-1 truncate">
                Education Intelligence
              </div>
            </div>
          </div>

          {/* Mobile Close Button */}
          <button
            onClick={onClose}
            className="md:hidden w-8 h-8 flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] text-[var(--text-soft)] hover:text-[var(--text)] transition-colors cursor-pointer shrink-0"
            aria-label="Close navigation menu"
          >
            <X size={16} />
          </button>
        </div>

        {/* Workspace Portal Pill */}
        <div className={`px-2.5 py-1.5 rounded-xl border flex items-center justify-between text-xs font-bold transition-all ${
          isTeacher
            ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-800 dark:text-emerald-300'
            : 'bg-teal-500/10 border-teal-500/25 text-teal-800 dark:text-teal-300'
        }`}>
          <div className="flex items-center gap-1.5 truncate">
            {isTeacher ? <Building2 size={13} className="shrink-0" /> : <GraduationCap size={14} className="shrink-0" />}
            <span className="truncate">{isTeacher ? 'Faculty Workspace' : 'Student Workspace'}</span>
          </div>
          <span className="text-[10px] font-extrabold px-1.5 py-0.2 rounded bg-white/40 dark:bg-black/30 shrink-0">
            {isTeacher ? 'TEACHER' : 'STUDENT'}
          </span>
        </div>
      </div>

      {/* Navigation Links List */}
      <nav className="px-3.5 py-3 flex-1 scrollbar-thin space-y-0.5" onClick={() => onClose && onClose()}>
        <NavLabel>Overview</NavLabel>
        <Item to="/app/dashboard" icon={LayoutDashboard}>
          Dashboard
        </Item>

        {isTeacher && (
          <>
            <NavLabel>Assessment & Audit</NavLabel>
            <Item to="/app/evaluate" icon={FileUp} badge="AI OCR">
              Evaluate Script
            </Item>
            <Item to="/app/history" icon={History}>
              Evaluation History
            </Item>
            <Item to="/app/plagiarism" icon={ShieldCheck}>
              Plagiarism Audit
            </Item>

            <NavLabel>Class Intelligence</NavLabel>
            <Item to="/app/action-center" icon={Zap} badge="Priority">
              Action Center
            </Item>
            <Item to="/app/misconception-map" icon={Map}>
              Misconception Map
            </Item>
            <Item to="/app/analytics" icon={BarChart3}>
              Class Analytics
            </Item>
            <Item to="/app/reports" icon={FileText}>
              Academic Reports
            </Item>
            <Item to="/app/students" icon={Users}>
              Class Roster
            </Item>
          </>
        )}

        {!isTeacher && (
          <>
            <NavLabel>My Academics</NavLabel>
            <Item to="/app/self-evaluation" icon={CheckCircle2} badge="Grading">
              Self Evaluation
            </Item>
            <Item to="/app/performance" icon={LineChart}>
              My Performance
            </Item>
            <Item to="/app/history" icon={History}>
              My Evaluated Papers
            </Item>

            <NavLabel>AI Learning Studios</NavLabel>
            <Item to="/app/trainer" icon={Bot} badge="Tutor">
              Personal Trainer
            </Item>
            <Item to="/app/learn-anywhere" icon={Compass}>
              Learn from Anywhere
            </Item>
            <Item to="/app/reality-lab" icon={FlaskConical}>
              Reality Lab
            </Item>
            <Item to="/app/knowledge-challenge" icon={Sparkles}>
              Knowledge Challenge
            </Item>

            <NavLabel>Productivity & Growth</NavLabel>
            <Item to="/app/opportunities" icon={Globe}>
              Opportunities & News
            </Item>
            <Item to="/app/focus" icon={Timer}>
              Focus Session
            </Item>
            <Item to="/app/memory" icon={BookOpen}>
              Academic Memory
            </Item>
            <Item to="/app/parent" icon={HeartHandshake}>
              Parent Agent
            </Item>
          </>
        )}

        <NavLabel>Curriculum & Platform</NavLabel>
        <button
          onClick={onOpenSyllabusModal}
          className="w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-semibold mb-1 text-[var(--accent)] bg-[var(--accent-soft)] hover:bg-[var(--accent)] hover:text-white transition-all border border-[var(--accent)]/20 cursor-pointer"
        >
          <UploadCloud size={17} strokeWidth={1.8} className="shrink-0" />
          <span>Upload Syllabus</span>
        </button>
        <Item to="/app/notifications" icon={Bell}>
          Notifications
        </Item>
        <Item to="/app/settings" icon={Settings}>
          Settings
        </Item>
      </nav>

      {/* User Profile Card */}
      <div className="p-3.5 border-t border-[var(--border)] bg-[var(--surface-alt)]/50">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-[var(--accent)] text-white font-bold text-xs flex items-center justify-center shrink-0 shadow-xs">
            {user?.initials || user?.name?.slice(0, 2).toUpperCase() || 'US'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs sm:text-sm font-bold text-[var(--text)] truncate">{user?.name || 'Educator'}</div>
            <div className="text-[11px] text-[var(--text-soft)] capitalize truncate">
              {user?.role || 'Portal'} {user?.level ? `· ${user.level}` : ''}
            </div>
          </div>
          <button
            onClick={() => {
              if (onClose) onClose()
              logout()
            }}
            className="w-8 h-8 flex items-center justify-center rounded-lg border border-[var(--border)] text-[var(--text-soft)] hover:text-[var(--error)] hover:bg-[var(--error-soft)] transition-colors cursor-pointer shrink-0"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={15} strokeWidth={1.8} />
          </button>
        </div>
      </div>
    </aside>
  )
}
