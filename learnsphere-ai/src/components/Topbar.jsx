import { Bell, Menu, Moon, Sun, UploadCloud, Flame, Clock, Building, LogOut, GraduationCap, Building2, CircleChevronUp } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'

export default function Topbar({ title, crumb, onMenuClick, onOpenSyllabusModal }) {
  const { theme, toggleTheme, logout, role, streakDays, formattedSessionTime, teacherClasses, activeClassId, setActiveClassId, isUserActive, institutionMode } = useApp()
  const navigate = useNavigate()
  const isTeacher = role === 'teacher'

  return (
    <header className="min-h-[4rem] border-b border-[var(--border)] flex items-center justify-between px-3.5 sm:px-6 lg:px-8 py-2.5 sticky top-0 bg-[var(--surface)]/95 backdrop-blur-md z-30 gap-2 sm:gap-4 shadow-xs safe-top">
      {/* Title & Mobile Hamburger */}
      <div className="flex items-center gap-2.5 sm:gap-3.5 min-w-0 max-w-[60%] sm:max-w-none">
        <button
          className="md:hidden w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] cursor-pointer shrink-0"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
        >
          <Menu size={18} />
        </button>

        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-sm sm:text-base md:text-lg font-bold text-[var(--text)] tracking-tight truncate leading-tight">
              {title}
            </h1>
            <span className={`hidden sm:inline-flex text-[10px] font-extrabold px-2 py-0.5 rounded-full border ${
              isTeacher
                ? 'bg-emerald-500/10 border-emerald-500/25 text-emerald-800 dark:text-emerald-300'
                : 'bg-teal-500/10 border-teal-500/25 text-teal-800 dark:text-teal-300'
            }`}>
              {isTeacher ? 'TEACHER' : 'STUDENT'}
            </span>
          </div>
          {crumb && (
            <div className="text-[11px] sm:text-xs text-[var(--text-soft)] font-medium mt-0.5 truncate hidden xs:block">
              {crumb}
            </div>
          )}
        </div>
      </div>

      {/* Actions & Status Controls */}
      <div className="flex items-center gap-1.5 sm:gap-2.5 ml-auto shrink-0">
        {isTeacher && (
          <div className="flex items-center gap-1.5 sm:gap-2">
            <div className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-[var(--text)] text-xs sm:text-sm font-semibold shadow-xs max-w-[130px] sm:max-w-[220px]">
              <Building2 size={14} className="text-[var(--accent)] shrink-0" />
              <span className="text-[var(--text-soft)] hidden lg:inline">{institutionMode === 'school' ? 'Class:' : 'Dept:'}</span>
              {teacherClasses.length > 0 ? (
                <select
                  aria-label={institutionMode === 'school' ? 'Select active school class' : 'Select active college department'}
                  value={activeClassId || teacherClasses[0]?.id}
                  onChange={(e) => setActiveClassId(e.target.value)}
                  className="bg-transparent font-bold text-[var(--text)] focus:outline-none cursor-pointer text-xs sm:text-sm truncate w-full"
                >
                  {teacherClasses.map((cls) => (
                    <option key={cls.id} value={cls.id} className="bg-[var(--surface)] text-[var(--text)]">
                      {cls.name} ({cls.students ? cls.students.length : 0} std)
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-xs sm:text-sm text-[var(--text-faint)]">None</span>
              )}
            </div>

            <button
              onClick={() => navigate('/create-class')}
              title="Manage Classes & Departments"
              className="hidden lg:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text)] font-semibold text-xs sm:text-sm hover:bg-[var(--surface-alt)] hover:border-[var(--border-strong)] transition-all shadow-xs cursor-pointer"
            >
              <Building size={14} className="text-[var(--accent)]" />
              <span>{institutionMode === 'school' ? 'Classes' : 'Departments'}</span>
            </button>
          </div>
        )}

        {!isTeacher && (
          <div className="flex items-center gap-1.5 sm:gap-2">
            <div
              className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-bold text-xs sm:text-[13px] shadow-xs transition-all whitespace-nowrap"
              title="Active session study timer"
            >
              <CircleChevronUp size={14} className="text-emerald-500 shrink-0" strokeWidth={2} />
              <span>⏱️ {formattedSessionTime || '0s'} (Active)</span>
            </div>

            <div
              className="flex items-center gap-1.5 px-2.5 sm:px-3 py-1 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300 font-bold text-xs sm:text-[13px] shadow-xs transition-all whitespace-nowrap"
              title="Consecutive daily study streak"
            >
              <Flame size={14} className="text-amber-500 shrink-0" strokeWidth={1.8} />
              <span>🔥 {streakDays || 1} {streakDays === 1 ? 'Day' : 'Days'}</span>
            </div>
          </div>
        )}

        <button
          onClick={onOpenSyllabusModal}
          title="Upload or review syllabus"
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl border border-[var(--accent)]/30 bg-[var(--accent-soft)] text-[var(--accent)] font-semibold text-xs sm:text-sm hover:bg-[var(--accent)] hover:text-white transition-all shadow-xs cursor-pointer"
        >
          <UploadCloud size={15} />
          <span>Syllabus</span>
        </button>

        <button
          onClick={toggleTheme}
          title="Toggle light/dark theme"
          aria-label="Toggle light/dark theme"
          className="w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-all shadow-xs cursor-pointer"
        >
          {theme === 'dark' ? <Sun size={16} strokeWidth={1.8} /> : <Moon size={16} strokeWidth={1.8} />}
        </button>

        <button
          onClick={() => navigate('/app/notifications')}
          title="View notifications"
          aria-label="View notifications"
          className="relative w-9 h-9 flex items-center justify-center rounded-xl border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-all shadow-xs cursor-pointer"
        >
          <Bell size={16} strokeWidth={1.8} />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
        </button>

        <button
          onClick={() => {
            logout()
            navigate('/')
          }}
          className="hidden sm:inline-flex px-3 py-1.5 text-xs sm:text-sm font-semibold rounded-xl bg-[var(--surface)] border border-[var(--border-strong)] text-[var(--text)] hover:bg-[var(--surface-alt)] transition-all shadow-xs cursor-pointer"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
