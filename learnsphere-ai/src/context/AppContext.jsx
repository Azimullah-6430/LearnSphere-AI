/**
 * LearnSphere AI - Application Context
 *
 * Auth source of truth: server session via /api/auth/me
 * localStorage is used ONLY for UI preferences (theme) and non-sensitive
 * UI cache (teacher classes layout). It is NEVER the auth source of truth.
 *
 * Fixes applied:
 *   - Removed undefined DEFAULT_USERS references (was crashing app)
 *   - /api/auth/me called on every app load to validate session
 *   - login() stores user from server response, not from localStorage
 *   - logout() calls backend, then clears all auth state
 *   - role defaults to null until server confirms it
 *   - syllabus fetched from /api/syllabus on login (server-persisted)
 *   - streak tracked per user email to avoid cross-user bleed
 *   - teacher classes stored in localStorage only as UI layout cache
 *     (they are NOT the authoritative data source)
 */

import { createContext, useContext, useEffect, useRef, useState, useCallback } from 'react'
import { api } from '../services/api.js'

const AppContext = createContext(null)

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDuration(totalSeconds) {
  if (!totalSeconds || totalSeconds <= 0) return '0s'
  const hrs  = Math.floor(totalSeconds / 3600)
  const mins = Math.floor((totalSeconds % 3600) / 60)
  const secs = totalSeconds % 60
  if (hrs > 0)  return `${hrs}h ${mins}m ${secs}s`
  if (mins > 0) return `${mins}m ${secs}s`
  return `${secs}s`
}

function formatClockTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function getTodayStr()     { return new Date().toISOString().split('T')[0] }
function getYesterdayStr() {
  const d = new Date(); d.setDate(d.getDate() - 1); return d.toISOString().split('T')[0]
}

function safeParse(key, fallback = null) {
  try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback } catch { return fallback }
}
function safeSet(key, value) {
  try { localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value)) } catch {}
}
function safeRemove(key) { try { localStorage.removeItem(key) } catch {} }

// ── Provider ──────────────────────────────────────────────────────────────────

export function AppProvider({ children }) {
  // ── Auth state — server is authoritative ─────────────────────────────────
  const [authenticated, setAuthenticated] = useState(false)
  const [authLoading,   setAuthLoading]   = useState(true)   // true while /api/auth/me in flight
  const [role,          setRole]          = useState(null)   // null until server confirms
  const [currentUser,   setCurrentUser]   = useState(null)

  // ── UI prefs (localStorage is fine for these) ─────────────────────────────
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('ls-theme') || 'light' } catch { return 'light' }
  })

  // ── Syllabus — fetched from server after login ────────────────────────────
  const [syllabusData, setSyllabusDataState] = useState(null)

  // ── Study session timer ───────────────────────────────────────────────────
  const [studySessions,        setStudySessions]        = useState([])
  const [currentSessionId,     setCurrentSessionId]     = useState(null)
  const [sessionElapsedSeconds,setSessionElapsedSeconds]= useState(0)
  const [activityLog,          setActivityLog]          = useState([])
  const [isUserActive,         setIsUserActive]         = useState(true)
  const lastActivityRef = useRef(Date.now())

  // ── Streak (per-user, keyed by email to prevent cross-user bleed) ─────────
  const [streakDays,    setStreakDays]    = useState(1)
  const [lastActiveDate,setLastActiveDate]= useState(getTodayStr())

  // ── Teacher class layout cache (user-scoped to prevent cross-user bleed) ───
  const [institutionMode, setInstitutionModeState] = useState('school')
  const [teacherClasses, setTeacherClasses] = useState([])
  const [activeClassId, setActiveClassIdState] = useState('')

  // ═══════════════════════════════════════════════════════════════════════════
  // USER-SCORED LOCALSTORAGE SYNC & SESSION VALIDATION
  // ═══════════════════════════════════════════════════════════════════════════

  useEffect(() => {
    if (role === 'teacher' && currentUser?.email) {
      const email = currentUser.email
      const keyClasses = `learnsphere_teacher_classes_${email}`
      const keyActiveClass = `learnsphere_active_class_id_${email}`
      const keyMode = `learnsphere_institution_mode_${email}`

      const mode = localStorage.getItem(keyMode) || currentUser?.teacher_level || currentUser?.teacherLevel || 'school'
      setInstitutionModeState(mode)

      const savedClasses = localStorage.getItem(keyClasses)
      if (savedClasses) {
        try { setTeacherClasses(JSON.parse(savedClasses)) } catch {}
      } else {
        setTeacherClasses([])
      }

      const savedClassId = localStorage.getItem(keyActiveClass) || ''
      setActiveClassIdState(savedClassId)
    } else {
      setTeacherClasses([])
      setActiveClassIdState('')
    }
  }, [role, currentUser])

  useEffect(() => {
    if (role === 'teacher' && currentUser?.email) {
      const email = currentUser.email
      safeSet(`learnsphere_teacher_classes_${email}`, teacherClasses)
    }
  }, [teacherClasses, role, currentUser?.email])

  useEffect(() => {
    async function validateSession() {
      setAuthLoading(true)
      try {
        const res = await api.authMe()
        if (res && res.success && res.authenticated && res.user) {
          const user = res.user
          setCurrentUser(user)
          setRole(user.role || null)
          setAuthenticated(true)
          _applyInstitutionMode(user)
          _fetchSyllabus()
          _restoreStreak(user.email)
          _startSession()
        } else {
          _clearAuthState()
        }
      } catch {
        _clearAuthState()
      } finally {
        setAuthLoading(false)
      }
    }
    validateSession()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // ── Theme sync ────────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    safeSet('ls-theme', theme)
  }, [theme])

  // ═══════════════════════════════════════════════════════════════════════════
  // INTERNAL HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  function _clearAuthState() {
    setAuthenticated(false)
    setRole(null)
    setCurrentUser(null)
    setSyllabusDataState(null)
    setStudySessions([])
    setCurrentSessionId(null)
    setSessionElapsedSeconds(0)
    setActivityLog([])
    setStreakDays(1)
    setTeacherClasses([])
    setActiveClassIdState('')
  }

  function _applyInstitutionMode(user) {
    const mode = user?.teacher_level || user?.teacherLevel || user?.level || 'school'
    setInstitutionModeState(mode)
    if (user?.email) {
      safeSet(`learnsphere_institution_mode_${user.email}`, mode)
    }
  }

  async function _fetchSyllabus() {
    try {
      const res = await api.getMySyllabus()
      if (res && res.success && res.syllabus) {
        setSyllabusDataState(res.syllabus.analysis || res.syllabus)
      }
    } catch {
      // Non-fatal: user simply hasn't uploaded a syllabus yet
    }
  }

  function _restoreStreak(userEmail) {
    if (!userEmail) return
    const keyStreak   = `ls-streak-${userEmail}`
    const keyLastDate = `ls-last-active-date-${userEmail}`
    const today       = getTodayStr()
    const yesterday   = getYesterdayStr()
    const savedDate   = localStorage.getItem(keyLastDate) || ''
    const savedStreak = parseInt(localStorage.getItem(keyStreak) || '1', 10)

    let streak = savedStreak
    if (!savedDate || savedDate === today) {
      streak = savedStreak || 1
    } else if (savedDate === yesterday) {
      streak = savedStreak + 1
    } else {
      streak = 1
    }
    safeSet(keyStreak, streak.toString())
    safeSet(keyLastDate, today)
    setStreakDays(streak)
    setLastActiveDate(today)
  }

  function _startSession() {
    const nowStr     = formatClockTime()
    const todayStr   = getTodayStr()
    const newSessId  = `sess_${Date.now()}`
    const newSession = {
      id: newSessId, date: todayStr,
      startTime: nowStr, endTime: nowStr,
      durationSeconds: 0, durationText: '0s',
      activities: [`Logged in at ${nowStr}`],
    }
    setCurrentSessionId(newSessId)
    setSessionElapsedSeconds(0)
    setStudySessions([newSession])
  }

  // ═══════════════════════════════════════════════════════════════════════════
  // ACTIVITY TRACKING
  // ═══════════════════════════════════════════════════════════════════════════

  useEffect(() => {
    if (!authenticated) return
    const handle = () => { lastActivityRef.current = Date.now(); setIsUserActive(true) }
    const evts = ['mousemove','mousedown','keydown','scroll','touchstart','click']
    evts.forEach(e => window.addEventListener(e, handle, { passive: true }))
    return () => evts.forEach(e => window.removeEventListener(e, handle))
  }, [authenticated])

  useEffect(() => {
    if (!authenticated) return
    const IDLE_MS = 15000
    const timer = setInterval(() => {
      const active = (Date.now() - lastActivityRef.current) < IDLE_MS
      setIsUserActive(active)
      if (!active) return
      setSessionElapsedSeconds(prev => {
        const next = prev + 1
        const nowTime = formatClockTime()
        setStudySessions(prev => prev.map((s, i) => i === 0
          ? { ...s, endTime: nowTime, durationSeconds: (s.durationSeconds || 0) + 1, durationText: formatDuration((s.durationSeconds || 0) + 1) }
          : s
        ))
        return next
      })
    }, 1000)
    return () => clearInterval(timer)
  }, [authenticated])

  // ═══════════════════════════════════════════════════════════════════════════
  // PUBLIC API
  // ═══════════════════════════════════════════════════════════════════════════

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  /**
   * updateProfile() — updates student/teacher profile directly in MongoDB via backend API.
   */
  const updateProfile = useCallback(async (profileData) => {
    const res = await api.updateProfile(profileData)
    if (res && res.success && res.user) {
      setCurrentUser(res.user)
      if (res.user.role) setRole(res.user.role)
      return res.user
    }
    throw new Error(res?.error || 'Failed to update profile')
  }, [])

  /**
   * login() — called after a successful /api/auth/login or /api/auth/register response.
   * userData comes from the server — MongoDB is single source of truth.
   */
  const login = useCallback(async (serverRole, userData) => {
    if (!userData) throw new Error('No user data returned from server.')

    _clearAuthState()
    setAuthLoading(true)

    const user = {
      ...userData,
      initials: userData.initials || (userData.name
        ? userData.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
        : 'US'),
    }

    setCurrentUser(user)
    setRole(serverRole || user.role || 'student')
    setAuthenticated(true)
    _applyInstitutionMode(user)
    _restoreStreak(user.email)
    _startSession()

    await _fetchSyllabus()
    setAuthLoading(false)
  }, [])  // eslint-disable-line react-hooks/exhaustive-deps

  /**
   * logout() — calls backend to invalidate session, then clears all state.
   */
  const logout = useCallback(async () => {
    const email = currentUser?.email
    if (studySessions.length > 0) {
      const finalTime = formatClockTime()
      setStudySessions(prev => prev.map((s, i) => i === 0 ? { ...s, endTime: finalTime } : s))
    }
    try { await api.logout() } catch { /* best effort */ }
    _clearAuthState()
    if (email) {
      safeRemove(`learnsphere_teacher_classes_${email}`)
      safeRemove(`learnsphere_active_class_id_${email}`)
      safeRemove(`learnsphere_institution_mode_${email}`)
    }
    safeRemove('learnsphere_teacher_classes')
    safeRemove('learnsphere_active_class_id')
    safeRemove('learnsphere_institution_mode')
  }, [studySessions, currentUser?.email])  // eslint-disable-line react-hooks/exhaustive-deps

  const recordActivity = useCallback((type, title, details = {}) => {
    _restoreStreak(currentUser?.email)
    const nowTime  = formatClockTime()
    const todayStr = getTodayStr()
    setStudySessions(prev => prev.map((s, i) => i === 0
      ? { ...s, endTime: nowTime, activities: [title, ...(s.activities || [])].slice(0, 10) }
      : s
    ))
    const newItem = { id: Date.now().toString(), type, text: title, when: nowTime, date: todayStr, ...details }
    setActivityLog(prev => [newItem, ...prev].slice(0, 50))
  }, [currentUser?.email])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Syllabus ──────────────────────────────────────────────────────────────
  const setSyllabusData = useCallback((data) => {
    setSyllabusDataState(data)
  }, [])

  // ── Institution mode ──────────────────────────────────────────────────────
  const setInstitutionMode = (mode) => {
    setInstitutionModeState(mode)
    if (currentUser?.email) {
      safeSet(`learnsphere_institution_mode_${currentUser.email}`, mode)
    }
  }

  // ── Teacher class management (user-scoped layout cache) ───────────────────
  const setActiveClassId = (id) => {
    setActiveClassIdState(id)
    if (currentUser?.email) {
      safeSet(`learnsphere_active_class_id_${currentUser.email}`, id)
    }
  }

  const addClass = (newCls) => {
    const created = { id: `cls_${Date.now()}`, created_at: getTodayStr(), ...newCls }
    setTeacherClasses(prev => [created, ...prev])
    setActiveClassId(created.id)
    return created
  }

  const deleteClass = (classId) => {
    setTeacherClasses(prev => prev.filter(c => c.id !== classId))
    if (activeClassId === classId) setActiveClassId('')
  }

  const uploadStudentRoster = (classId, newStudentsList) => {
    setTeacherClasses(prev => prev.map(cls => {
      if (cls.id !== classId) return cls
      const updated = newStudentsList.map((st, idx) => ({
        id: st.id || `std_${Date.now()}_${idx}`,
        rollNo: st.rollNo || `ROLL-${idx + 1}`,
        name: st.name, order: idx + 1, marksHistory: st.marksHistory || [],
      }))
      return { ...cls, students: updated, students_count: updated.length }
    }))
  }

  const addOrUpdateStudentMarks = (classId, studentId, markEntry) => {
    setTeacherClasses(prev => prev.map(cls => {
      if (cls.id !== classId) return cls
      const students = (cls.students || []).map(std => {
        if (std.id !== studentId && std.rollNo !== studentId && std.name !== studentId) return std
        const history = std.marksHistory || []
        const idx = history.findIndex(m => m.subject === markEntry.subject && m.assessment === markEntry.assessment)
        const nextHistory = idx >= 0
          ? history.map((m, i) => i === idx ? markEntry : m)
          : [markEntry, ...history]
        return { ...std, marksHistory: nextHistory }
      })
      return { ...cls, students }
    }))
  }

  const deleteStudentFromClass = (classId, studentId) => {
    setTeacherClasses(prev => prev.map(cls => {
      if (cls.id !== classId) return cls
      const students = (cls.students || []).filter(s => s.id !== studentId)
      return { ...cls, students, students_count: students.length }
    }))
  }

  // ── Derived values ────────────────────────────────────────────────────────
  const filteredTeacherClasses = role === 'teacher' ? teacherClasses.filter(c => c.level === institutionMode) : []
  const activeClass = role === 'teacher'
    ? (filteredTeacherClasses.find(c => c.id === activeClassId) || (filteredTeacherClasses.length > 0 ? filteredTeacherClasses[0] : null))
    : null

  const userWithInitials = currentUser ? {
    ...currentUser,
    initials: currentUser.initials
      || (currentUser.name
        ? currentUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
        : 'US'),
  } : null

  const formattedSessionTime = formatDuration(sessionElapsedSeconds)

  // ── Context value ─────────────────────────────────────────────────────────
  const value = {
    // Auth
    authenticated, authLoading, role, setRole,
    user: userWithInitials,
    login, logout,
    // Profile (MongoDB user object is single source of truth)
    profile: userWithInitials,
    setProfile: updateProfile,
    updateProfile,
    clearProfile: () => {},
    profileComplete: !!currentUser,
    // Syllabus (server-persisted)
    syllabusData, setSyllabusData,
    // Theme
    theme, toggleTheme,
    // Activity
    streakDays, recordActivity, activityLog,
    sessionElapsedSeconds, formattedSessionTime, studySessions, isUserActive,
    // Institution
    institutionMode, setInstitutionMode,
    // Teacher classes (UI layout cache, isolated to teachers)
    teacherClasses: filteredTeacherClasses,
    allTeacherClasses: role === 'teacher' ? teacherClasses : [],
    activeClassId: role === 'teacher' ? activeClassId : '',
    activeClass,
    setActiveClassId,
    addClass, deleteClass, uploadStudentRoster,
    addOrUpdateStudentMarks, deleteStudentFromClass,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
