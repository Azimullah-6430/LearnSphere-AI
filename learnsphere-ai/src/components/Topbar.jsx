import { Bell, Menu, Moon, Search, Sun, UploadCloud, Flame, Clock, Building, Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext.jsx'

export default function Topbar({ title, crumb, onMenuClick, onOpenSyllabusModal, onOpenClassModal }) {
  const { theme, toggleTheme, logout, role, streakDays, formattedSessionTime, teacherClasses, activeClassId, setActiveClassId, isUserActive, institutionMode } = useApp()
  const navigate = useNavigate()

  return (
    <header className="min-h-[4rem] border-b border-[var(--border)] flex items-center justify-between px-3.5 sm:px-7 py-2.5 sticky top-0 bg-[var(--bg)]/95 backdrop-blur z-30 flex-wrap sm:flex-nowrap gap-2">
      <div className="flex items-center gap-3">
        <button className="md:hidden w-9 h-9 flex items-center justify-center rounded-lg border border-[var(--border)]" onClick={onMenuClick}>
          <Menu size={17} />
        </button>
        <div>
          <div className="text-[15px] font-bold">{title}</div>
          <div className="text-xs text-[var(--text-faint)] mt-px">{crumb}</div>
        </div>
      </div>
      <div className="flex items-center gap-2.5">
        {role === 'teacher' && (
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg border border-[var(--accent)] bg-[var(--accent-soft)] text-[var(--accent)] text-xs font-bold shadow-sm">
              <Building size={14} />
              <span>{institutionMode === 'school' ? 'Active Class:' : 'Active Dept:'}</span>
              {teacherClasses.length > 0 ? (
                <select
                  value={activeClassId || teacherClasses[0]?.id}
                  onChange={(e) => setActiveClassId(e.target.value)}
                  className="bg-transparent font-extrabold text-[var(--text)] focus:outline-none cursor-pointer text-[12.5px]"
                >
                  {teacherClasses.map((cls) => (
                    <option key={cls.id} value={cls.id}>
                      {cls.name} ({cls.students ? cls.students.length : 0} std)
                    </option>
                  ))}
                </select>
              ) : (
                <span className="text-[12px] opacity-75 font-normal">
                  (No {institutionMode === 'school' ? 'Classes' : 'Departments'})
                </span>
              )}
            </div>

            <button
              onClick={() => navigate('/create-class')}
              title="Go to Class & Department Creation Page"
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] font-bold text-xs hover:bg-[var(--surface-alt)] transition-colors"
            >
              <Building size={14} className="text-[var(--accent)]" />
              <span>{institutionMode === 'school' ? 'My Classes' : 'My Departments'}</span>
            </button>
          </div>
        )}

        {role === 'student' && (
          <div className="flex items-center gap-2">
            <div
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold transition-all ${
                isUserActive
                  ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-600'
                  : 'border-amber-500/40 bg-amber-500/10 text-amber-600 opacity-80'
              }`}
              title={isUserActive ? 'Active Feature Usage (Cursor Movement Detected)' : 'Time Recording Paused (Cursor Stationary / Idle)'}
            >
              <Clock size={14} className={isUserActive ? 'text-emerald-500 animate-spin' : 'text-amber-500'} />
              <span>⏱️ {formattedSessionTime || '0s'} {isUserActive ? '(Active)' : '(Paused)'}</span>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 text-amber-600 font-bold text-xs" title="Daily Active Study Streak">
              <Flame size={15} className="text-amber-500 animate-pulse" />
              <span>🔥 {streakDays || 1} {streakDays === 1 ? 'Day' : 'Days'}</span>
            </div>
          </div>
        )}

        <button
          onClick={onOpenSyllabusModal}
          title="Upload & Analyze Syllabus"
          className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-[var(--border-strong)] bg-[var(--accent-soft)] text-[var(--accent)] font-semibold text-xs hover:bg-[var(--accent)] hover:text-white transition-colors"
        >
          <UploadCloud size={15} />
          <span>Upload Syllabus</span>
        </button>

        <button
          onClick={toggleTheme}
          title="Toggle theme"
          className="w-9 h-9 flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-colors"
        >
          {theme === 'dark' ? <Sun size={17} strokeWidth={1.7} /> : <Moon size={17} strokeWidth={1.7} />}
        </button>

        <button
          onClick={() => navigate('/app/notifications')}
          title="View notifications"
          className="relative w-9 h-9 flex items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] transition-colors"
        >
          <Bell size={17} strokeWidth={1.7} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-[var(--accent)] animate-pulse" />
        </button>

        <button
          onClick={() => {
            logout()
            navigate('/')
          }}
          className="px-[13px] py-[7px] text-[12.5px] font-semibold rounded-[7px] bg-[var(--surface)] border border-[var(--border-strong)] hover:bg-[var(--surface-alt)] transition-colors"
        >
          Sign out
        </button>
      </div>
    </header>
  )
}
