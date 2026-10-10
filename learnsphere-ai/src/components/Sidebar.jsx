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
} from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'

const navItemClass = ({ isActive }) =>
  `flex items-center gap-[11px] px-3 py-[9px] rounded-lg text-[13.5px] font-medium mb-px transition-colors ${
    isActive ? 'bg-[var(--accent-soft)] text-[var(--accent)] font-bold' : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
  }`

function NavLabel({ children }) {
  return <div className="text-[10.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] px-3 pt-[14px] pb-1.5">{children}</div>
}

function Item({ to, icon: Icon, children, onClick }) {
  return (
    <NavLink to={to} className={navItemClass} onClick={onClick}>
      <Icon size={17} strokeWidth={1.7} className="shrink-0 opacity-90" />
      {children}
    </NavLink>
  )
}

export default function Sidebar({ open, onClose, onOpenSyllabusModal }) {
  const { role, user } = useApp()

  return (
    <aside
      className={`w-[264px] shrink-0 bg-[var(--surface)] border-r border-[var(--border)] flex flex-col fixed top-0 bottom-0 left-0 overflow-y-auto z-40 transition-transform md:translate-x-0 ${
        open ? 'translate-x-0 shadow-xl' : '-translate-x-full'
      }`}
    >
      <div className="px-[22px] pt-[22px] pb-[18px] border-b border-[var(--border)]">
        <div className="flex items-center gap-2.5">
          <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="10.5" stroke="var(--accent)" strokeWidth="2" />
            <circle cx="24" cy="9" r="4" fill="var(--accent)" />
          </svg>
          <div className="text-base font-extrabold tracking-tight">
            LearnSphere<small className="font-semibold text-[var(--accent)] text-xs ml-0.5">AI</small>
          </div>
        </div>
      </div>

      <nav className="px-3 py-[14px] flex-1" onClick={() => onClose && onClose()}>
        <NavLabel>Overview</NavLabel>
        <Item to="/app/dashboard" icon={LayoutDashboard}>
          Dashboard
        </Item>

        {role === 'teacher' && (
          <>
            <NavLabel>Evaluation</NavLabel>
            <Item to="/app/evaluate" icon={FileUp}>
              Evaluate Answer Script
            </Item>
            <Item to="/app/history" icon={History}>
              Evaluation History
            </Item>
            <NavLabel>Integrity</NavLabel>
            <Item to="/app/plagiarism" icon={ShieldCheck}>
              Plagiarism
            </Item>
            <NavLabel>Analytics</NavLabel>
            <Item to="/app/analytics" icon={BarChart3}>
              Student Analytics
            </Item>
            <Item to="/app/misconception-map" icon={Map}>
              Misconception Map
            </Item>
            <Item to="/app/action-center" icon={Zap}>
              Action Center
            </Item>
            <Item to="/app/reports" icon={FileText}>
              Reports
            </Item>
            <NavLabel>Management</NavLabel>
            <Item to="/app/students" icon={Users}>
              Students
            </Item>
          </>
        )}

        {role === 'student' && (
          <>
            <NavLabel>My Learning</NavLabel>
            <Item to="/app/performance" icon={LineChart}>
              Performance
            </Item>
            <Item to="/app/history" icon={History}>
              My Evaluations
            </Item>
            <NavLabel>AI Support</NavLabel>
            <Item to="/app/trainer" icon={Bot}>
              Personal Trainer
            </Item>
            <Item to="/app/parent" icon={HeartHandshake}>
              Parent Agent
            </Item>
            <Item to="/app/knowledge-challenge" icon={Sparkles}>
              Knowledge Challenge
            </Item>
            <Item to="/app/reality-lab" icon={FlaskConical}>
              Reality Lab
            </Item>
            <Item to="/app/learn-anywhere" icon={Compass}>
              Learn from Anywhere
            </Item>
            <NavLabel>Productivity & Growth</NavLabel>
            <Item to="/app/opportunities" icon={Globe}>
              Current & Opportunities
            </Item>
            <Item to="/app/focus" icon={Timer}>
              Focus Session
            </Item>
            <Item to="/app/memory" icon={BookOpen}>
              Academic Memory
            </Item>
            <Item to="/app/self-evaluation" icon={CheckCircle2}>
              Self Evaluation
            </Item>
          </>
        )}

        <NavLabel>System</NavLabel>
        <button
          onClick={onOpenSyllabusModal}
          className="w-full flex items-center gap-[11px] px-3 py-[9px] rounded-lg text-[13.5px] font-medium mb-px text-[var(--accent)] bg-[var(--accent-soft)] hover:bg-[var(--accent)] hover:text-white transition-colors"
        >
          <UploadCloud size={17} strokeWidth={1.7} className="shrink-0" />
          <span>Upload Syllabus</span>
        </button>
        <Item to="/app/notifications" icon={Bell}>
          Notifications
        </Item>
        <Item to="/app/settings" icon={Settings}>
          Settings
        </Item>
      </nav>

      <div className="px-[22px] py-4 border-t border-[var(--border)]">
        <div className="flex items-center gap-2.5">
          <div className="w-[34px] h-[34px] rounded-full bg-[var(--accent)] text-white font-bold text-[13px] flex items-center justify-center shrink-0">
            {user?.initials || 'US'}
          </div>
          <div>
            <div className="text-[13px] font-bold">{user?.name || 'User'}</div>
            <div className="text-[11.5px] text-[var(--text-faint)] capitalize">{user?.role || 'Portal'}</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
