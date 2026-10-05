/**
 * LearnSphere AI - Application Context
 *
 * Auth & Profile Architecture:
 * - Single source of truth: MongoDB server session (/api/auth/me, /api/auth/login, /api/auth/register, /api/user/profile)
 * - Zero hardcoded student profiles, classes (no "12B", "Class 12", "CBSE" defaults)
 * - User state strictly belongs ONLY to the currently authenticated account
 * - User-scoped caching using `learnsphere_profile_<userId>` only as a secondary cache
 * - Full race-condition protection: sequence IDs ensure stale async responses never overwrite a newer user's state
 * - Strict role and data isolation: Teacher classes/rosters are empty for student accounts
 * - Comprehensive state cleanup on logout or account switch
 */

import { createContext, useContext, useEffect, useRef, useState, useCallback, useMemo } from 'react'
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

function getUserIdentifier(user) {
  if (!user) return null
  return user.id || user._id || (user.email ? user.email.toLowerCase().replace(/[^a-z0-9]/g, '_') : null)
}

function getUserStorageKey(prefix, user) {
  const uid = getUserIdentifier(user)
  return uid ? `learnsphere_${prefix}_${uid}` : null
}

function safeSet(key, value) {
  if (!key) return
  try { localStorage.setItem(key, typeof value === 'string' ? value : JSON.stringify(value)) } catch {}
}

function safeRemove(key) {
  if (!key) return
  try { localStorage.removeItem(key) } catch {}
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function AppProvider({ children }) {
  // ── Auth & Identity State (Authoritative source: MongoDB session) ─────────
  const [authenticated, setAuthenticated] = useState(false)
  const [authLoading,   setAuthLoading]   = useState(true)
  const [role,          setRole]          = useState(null)
  const [currentUser,   setCurrentUser]   = useState(null)

  // Request sequence tracker to prevent async race conditions across logins/logouts
  const authSequenceRef = useRef(0)

  // ── UI preferences ────────────────────────────────────────────────────────
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('ls-theme') || 'light' } catch { return 'light' }
  })

  // ── Syllabus (Server-persisted per account) ────────────────────────────────
  const [syllabusData, setSyllabusDataState] = useState(null)

  // ── Study session timer & activity (Account-scoped) ───────────────────────
  const [studySessions,        setStudySessions]        = useState([])
  const [currentSessionId,     setCurrentSessionId]     = useState(null)
  const [sessionElapsedSeconds,setSessionElapsedSeconds]= useState(0)
  const [activityLog,          setActivityLog]          = useState([])
  const [isUserActive,         setIsUserActive]         = useState(true)
  const lastActivityRef = useRef(Date.now())

  // ── Streak (Account-scoped) ───────────────────────────────────────────────
  const [streakDays,    setStreakDays]    = useState(1)
  const [lastActiveDate,setLastActiveDate]= useState(getTodayStr())

  // ── Teacher class layout cache (Teacher-scoped only) ──────────────────────
  const [institutionMode, setInstitutionModeState] = useState('school')
  const [teacherClasses,  setTeacherClasses]       = useState([])
  const [activeClassId,   setActiveClassIdState]   = useState('')

  // ═══════════════════════════════════════════════════════════════════════════
  // STATE CLEANUP & RESET
  // ═══════════════════════════════════════════════════════════════════════════

  const _clearAuthState = useCallback(() => {
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
  }, [])

  // ═══════════════════════════════════════════════════════════════════════════
  // INTERNAL HELPERS
  // ═══════════════════════════════════════════════════════════════════════════

  const _applyInstitutionMode = useCallback((user) => {
    if (!user) return
    const mode = user.teacher_level || user.teacherLevel || user.level || 'school'
    setInstitutionModeState(mode)
    const key = getUserStorageKey('institution_mode', user)
    if (key) safeSet(key, mode)
  }, [])

  const _fetchSyllabus = useCallback(async (expectedSeq) => {
    try {
      const res = await api.getMySyllabus()
      if (authSequenceRef.current !== expectedSeq) return
      if (res && res.success && res.syllabus) {
        setSyllabusDataState(res.syllabus.analysis || res.syllabus)
      }
    } catch {
      // Non-fatal: user simply hasn't uploaded a syllabus yet
    }
  }, [])

  const _restoreStreak = useCallback((user) => {
    if (!user) return
    const keyStreak   = getUserStorageKey('streak', user)
    const keyLastDate = getUserStorageKey('last_active_date', user)
    if (!keyStreak || !keyLastDate) return

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
  }, [])

  const _startSession = useCallback(() => {
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
  }, [])

  // ═══════════════════════════════════════════════════════════════════════════
  // INITIAL APP MOUNT: SESSION VALIDATION (/api/auth/me)
  // ═══════════════════════════════════════════════════════════════════════════

  useEffect(() => {
    // Purge any deprecated legacy global un-namespaced keys
    safeRemove('learnsphere_teacher_classes')
    safeRemove('learnsphere_active_class_id')
    safeRemove('learnsphere_institution_mode')
    safeRemove('learnsphere_user_profile')
    safeRemove('learnsphere_student_profile')

    async function validateSession() {
      const currentSeq = ++authSequenceRef.current
      setAuthLoading(true)

      try {
        const res = await api.authMe()
        // If an account action occurred while request was in-flight, discard
        if (authSequenceRef.current !== currentSeq) return

        if (res && res.success && res.authenticated && res.user) {
          const user = res.user
          setCurrentUser(user)
          setRole(user.role || null)
          setAuthenticated(true)

          // Cache profile under user-specific key
          const profileKey = getUserStorageKey('profile', user)
          if (profileKey) safeSet(profileKey, user)

          _applyInstitutionMode(user)
          _restoreStreak(user)
          _startSession()
          _fetchSyllabus(currentSeq)
        } else {
          _clearAuthState()
        }
      } catch {
        if (authSequenceRef.current === currentSeq) {
          _clearAuthState()
        }
      } finally {
        if (authSequenceRef.current === currentSeq) {
          setAuthLoading(false)
        }
      }
    }

    validateSession()
  }, [_applyInstitutionMode, _clearAuthState, _fetchSyllabus, _restoreStreak, _startSession])

  // ═══════════════════════════════════════════════════════════════════════════
  // TEACHER CLASSES STORAGE (ISOLATED TO TEACHER ROLE & USER ID)
  // ═══════════════════════════════════════════════════════════════════════════

  useEffect(() => {
    if (role === 'teacher' && currentUser) {
      const keyClasses     = getUserStorageKey('teacher_classes', currentUser)
      const keyActiveClass = getUserStorageKey('active_class_id', currentUser)
      const keyMode        = getUserStorageKey('institution_mode', currentUser)

      const mode = (keyMode && localStorage.getItem(keyMode)) || currentUser?.teacher_level || currentUser?.teacherLevel || 'school'
      setInstitutionModeState(mode)

      if (keyClasses) {
        const savedClasses = localStorage.getItem(keyClasses)
        if (savedClasses) {
          try { setTeacherClasses(JSON.parse(savedClasses)) } catch { setTeacherClasses([]) }
        } else {
          setTeacherClasses([])
        }
      }

      if (keyActiveClass) {
        const savedClassId = localStorage.getItem(keyActiveClass) || ''
        setActiveClassIdState(savedClassId)
      }
    } else {
      // Students have zero teacher classes
      setTeacherClasses([])
      setActiveClassIdState('')
    }
  }, [role, currentUser])

  useEffect(() => {
    if (role === 'teacher' && currentUser) {
      const keyClasses = getUserStorageKey('teacher_classes', currentUser)
      if (keyClasses) safeSet(keyClasses, teacherClasses)
    }
  }, [teacherClasses, role, currentUser])

  // ── Theme sync ────────────────────────────────────────────────────────────
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    safeSet('ls-theme', theme)
  }, [theme])

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
  // PUBLIC ACTIONS (AUTH, PROFILE, SESSIONS)
  // ═══════════════════════════════════════════════════════════════════════════

  const toggleTheme = () => setTheme(t => t === 'dark' ? 'light' : 'dark')

  /**
   * updateProfile() — Authoritative MongoDB update via backend API.
   * Caches the updated profile into user-specific localStorage key.
   */
  const updateProfile = useCallback(async (profileData) => {
    const res = await api.updateProfile(profileData)
    if (res && res.success && res.user) {
      const updated = res.user
      setCurrentUser(updated)
      if (updated.role) setRole(updated.role)
      const profileKey = getUserStorageKey('profile', updated)
      if (profileKey) safeSet(profileKey, updated)
      return updated
    }
    throw new Error(res?.error || 'Failed to update profile')
  }, [])

  /**
   * login() — Called after successful /api/auth/login or /api/auth/register.
   * MongoDB server response is the single source of truth.
   */
  const login = useCallback(async (serverRole, userData) => {
    if (!userData) throw new Error('No user data returned from server.')

    const currentSeq = ++authSequenceRef.current
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

    // Cache under user-specific storage key
    const profileKey = getUserStorageKey('profile', user)
    if (profileKey) safeSet(profileKey, user)

    _applyInstitutionMode(user)
    _restoreStreak(user)
    _startSession()

    await _fetchSyllabus(currentSeq)

    if (authSequenceRef.current === currentSeq) {
      setAuthLoading(false)
    }
  }, [_applyInstitutionMode, _clearAuthState, _fetchSyllabus, _restoreStreak, _startSession])

  /**
   * logout() — Invalidates server session, immediately wipes state and caches.
   */
  const logout = useCallback(async () => {
    const userToClean = currentUser
    ++authSequenceRef.current

    if (studySessions.length > 0) {
      const finalTime = formatClockTime()
      setStudySessions(prev => prev.map((s, i) => i === 0 ? { ...s, endTime: finalTime } : s))
    }

    try { await api.logout() } catch { /* best effort */ }

    _clearAuthState()

    if (userToClean) {
      safeRemove(getUserStorageKey('profile', userToClean))
      safeRemove(getUserStorageKey('teacher_classes', userToClean))
      safeRemove(getUserStorageKey('active_class_id', userToClean))
      safeRemove(getUserStorageKey('institution_mode', userToClean))
      safeRemove(getUserStorageKey('streak', userToClean))
      safeRemove(getUserStorageKey('last_active_date', userToClean))
    }
  }, [_clearAuthState, currentUser, studySessions])

  const recordActivity = useCallback((type, title, details = {}) => {
    if (currentUser) _restoreStreak(currentUser)
    const nowTime  = formatClockTime()
    const todayStr = getTodayStr()
    setStudySessions(prev => prev.map((s, i) => i === 0
      ? { ...s, endTime: nowTime, activities: [title, ...(s.activities || [])].slice(0, 10) }
      : s
    ))
    const newItem = { id: Date.now().toString(), type, text: title, when: nowTime, date: todayStr, ...details }
    setActivityLog(prev => [newItem, ...prev].slice(0, 50))
  }, [_restoreStreak, currentUser])

  // ── Syllabus ──────────────────────────────────────────────────────────────
  const setSyllabusData = useCallback((data) => {
    setSyllabusDataState(data)
  }, [])

  // ── Institution mode ──────────────────────────────────────────────────────
  const setInstitutionMode = (mode) => {
    setInstitutionModeState(mode)
    const key = getUserStorageKey('institution_mode', currentUser)
    if (key) safeSet(key, mode)
  }

  // ── Teacher class management (User-scoped layout cache) ───────────────────
  const setActiveClassId = (id) => {
    setActiveClassIdState(id)
    const key = getUserStorageKey('active_class_id', currentUser)
    if (key) safeSet(key, id)
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

  // ── Derived values (Strictly account-scoped) ──────────────────────────────
  const filteredTeacherClasses = role === 'teacher' ? teacherClasses.filter(c => c.level === institutionMode) : []
  const activeClass = role === 'teacher'
    ? (filteredTeacherClasses.find(c => c.id === activeClassId) || (filteredTeacherClasses.length > 0 ? filteredTeacherClasses[0] : null))
    : null

  const userWithInitials = useMemo(() => {
    if (!currentUser) return null
    return {
      ...currentUser,
      initials: currentUser.initials
        || (currentUser.name
          ? currentUser.name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()
          : 'US'),
    }
  }, [currentUser])

  // Explicit structured studentProfile for student role (null for teachers or unauthenticated)
  const studentProfile = useMemo(() => {
    if (!userWithInitials || role !== 'student') return null
    return {
      ...userWithInitials,
      class: userWithInitials.grade_level || userWithInitials.classLevel || null,
      section: userWithInitials.section || null,
      school: userWithInitials.institution_name || userWithInitials.school || null,
      department: userWithInitials.department || userWithInitials.domain || null,
      semester: userWithInitials.semester || null,
    }
  }, [userWithInitials, role])

  const formattedSessionTime = formatDuration(sessionElapsedSeconds)

  // ── Context value ─────────────────────────────────────────────────────────
  const value = {
    // Auth
    authenticated,
    authLoading,
    role,
    setRole,
    user: userWithInitials,
    login,
    logout,

    // Profile (MongoDB authenticated user object is single source of truth)
    profile: userWithInitials,
    studentProfile,
    setProfile: updateProfile,
    updateProfile,
    clearProfile: _clearAuthState,
    profileComplete: !!currentUser,

    // Syllabus (server-persisted)
    syllabusData,
    setSyllabusData,

    // Theme
    theme,
    toggleTheme,

    // Activity & Session
    streakDays,
    recordActivity,
    activityLog,
    sessionElapsedSeconds,
    formattedSessionTime,
    studySessions,
    isUserActive,

    // Institution
    institutionMode,
    setInstitutionMode,

    // Teacher classes (isolated to teachers)
    teacherClasses: filteredTeacherClasses,
    allTeacherClasses: role === 'teacher' ? teacherClasses : [],
    activeClassId: role === 'teacher' ? activeClassId : '',
    activeClass,
    setActiveClassId,
    addClass,
    deleteClass,
    uploadStudentRoster,
    addOrUpdateStudentMarks,
    deleteStudentFromClass,
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
