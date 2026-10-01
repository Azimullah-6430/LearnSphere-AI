import { createContext, useContext, useEffect, useState, useRef } from 'react'
import { api } from '../services/api.js'

const AppContext = createContext(null)

const DEFAULT_TEACHER_CLASSES = []

function formatDuration(totalSeconds) {
  if (!totalSeconds || totalSeconds <= 0) return '0s'
  const hrs = Math.floor(totalSeconds / 3600)
  const mins = Math.floor((totalSeconds % 3600) / 60)
  const secs = totalSeconds % 60
  if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`
  if (mins > 0) return `${mins}m ${secs}s`
  return `${secs}s`
}

function formatClockTime(date = new Date()) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function getTodayStr() {
  return new Date().toISOString().split('T')[0]
}

function getYesterdayStr() {
  const d = new Date()
  d.setDate(d.getDate() - 1)
  return d.toISOString().split('T')[0]
}

export function AppProvider({ children }) {
  const [authenticated, setAuthenticated] = useState(() => {
    try { return localStorage.getItem('ls-auth') === 'true' } catch { return false }
  })
  
  const [role, setRole] = useState(() => {
    try { return localStorage.getItem('ls-role') || 'teacher' } catch { return 'teacher' }
  })

  const [currentUser, setCurrentUser] = useState(() => {
    try {
      const saved = localStorage.getItem('ls-user')
      return saved ? JSON.parse(saved) : DEFAULT_USERS['teacher']
    } catch { return DEFAULT_USERS['teacher'] }
  })

  const [profile, setProfileState] = useState(() => {
    try {
      const saved = localStorage.getItem('ls-profile')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })

  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('ls-theme') || 'light' } catch { return 'light' }
  })

  // Student streak state
  const [streakDays, setStreakDays] = useState(() => {
    try {
      const saved = localStorage.getItem('ls-streak')
      return saved ? parseInt(saved, 10) : 1
    } catch { return 1 }
  })

  const [lastActiveDate, setLastActiveDate] = useState(() => {
    try {
      return localStorage.getItem('ls-last-active-date') || getTodayStr()
    } catch { return getTodayStr() }
  })

  // Live Login Study Session Timer & Log for Parent Agent
  const [studySessions, setStudySessions] = useState(() => {
    try {
      const saved = localStorage.getItem('ls-study-sessions')
      return saved ? JSON.parse(saved) : []
    } catch { return [] }
  })

  const [currentSessionId, setCurrentSessionId] = useState(() => {
    try { return localStorage.getItem('ls-current-session-id') || null } catch { return null }
  })

  const [sessionElapsedSeconds, setSessionElapsedSeconds] = useState(0)

  // Student activity feed for Parent Agent & Analytics
  const [activityLog, setActivityLog] = useState(() => {
    try {
      const saved = localStorage.getItem('ls-activity-log')
      return saved ? JSON.parse(saved) : []
    } catch { return [] }
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem('ls-theme', theme) } catch {}
  }, [theme])

  useEffect(() => {
    try {
      localStorage.setItem('ls-auth', authenticated ? 'true' : 'false')
      localStorage.setItem('ls-role', role)
      if (currentUser) localStorage.setItem('ls-user', JSON.stringify(currentUser))
    } catch {}
  }, [authenticated, role, currentUser])

  useEffect(() => {
    if (profile) {
      try { localStorage.setItem('ls-profile', JSON.stringify(profile)) } catch {}
    }
  }, [profile])

  useEffect(() => {
    try {
      localStorage.setItem('ls-study-sessions', JSON.stringify(studySessions))
    } catch {}
  }, [studySessions])

  const [isUserActive, setIsUserActive] = useState(true)
  const lastActivityRef = useRef(Date.now())

  // Listen for cursor movement & user feature interactions
  useEffect(() => {
    if (!authenticated) return

    const handleUserActivity = () => {
      lastActivityRef.current = Date.now()
      setIsUserActive(true)
    }

    const events = ['mousemove', 'mousedown', 'keydown', 'scroll', 'touchstart', 'click']
    events.forEach((evt) => window.addEventListener(evt, handleUserActivity, { passive: true }))

    return () => {
      events.forEach((evt) => window.removeEventListener(evt, handleUserActivity))
    }
  }, [authenticated])

  // Active Timer Interval - Increments ONLY when cursor movement / user activity occurs on features
  useEffect(() => {
    if (!authenticated) return

    const INACTIVITY_THRESHOLD_MS = 15000 // 15 seconds of cursor inactivity threshold

    const timer = setInterval(() => {
      const now = Date.now()
      const timeSinceLastActivity = now - lastActivityRef.current
      const active = timeSinceLastActivity < INACTIVITY_THRESHOLD_MS

      setIsUserActive(active)

      if (!active) {
        // Cursor stationary / User idle on feature. Pause study time recording!
        return
      }

      setSessionElapsedSeconds((prevSecs) => {
        const nextSecs = prevSecs + 1
        const nowTime = formatClockTime()
        
        // Update live active session
        setStudySessions((prevSessions) => {
          if (!prevSessions || prevSessions.length === 0) {
            const todayStr = getTodayStr()
            const newSess = {
              id: `sess_${Date.now()}`,
              date: todayStr,
              startTime: nowTime,
              endTime: nowTime,
              durationSeconds: nextSecs,
              durationText: formatDuration(nextSecs),
              activities: [`Active cursor session on ${todayStr}`]
            }
            setCurrentSessionId(newSess.id)
            return [newSess]
          }

          return prevSessions.map((s, idx) => {
            if (idx === 0) {
              return {
                ...s,
                endTime: nowTime,
                durationSeconds: (s.durationSeconds || 0) + 1,
                durationText: formatDuration((s.durationSeconds || 0) + 1)
              }
            }
            return s
          })
        })

        return nextSecs
      })
    }, 1000)

    return () => clearInterval(timer)
  }, [authenticated])

  // Calculate & Update Daily Streak per User Account
  const checkAndUpdateStreak = (userEmail = null) => {
    const todayStr = getTodayStr()
    const yesterdayStr = getYesterdayStr()
    const targetEmail = userEmail || currentUser?.email || 'default'
    const keyStreak = `ls-streak-${targetEmail}`
    const keyLastDate = `ls-last-active-date-${targetEmail}`

    const savedLastDate = localStorage.getItem(keyLastDate) || ''
    const savedStreakRaw = localStorage.getItem(keyStreak)
    let currentStreak = savedStreakRaw ? parseInt(savedStreakRaw, 10) : 1

    if (!savedLastDate) {
      // First time logging in/creating account today
      currentStreak = 1
      localStorage.setItem(keyStreak, '1')
      localStorage.setItem(keyLastDate, todayStr)
    } else if (savedLastDate !== todayStr) {
      if (savedLastDate === yesterdayStr) {
        // Logged in on consecutive day -> Increment streak by 1
        currentStreak += 1
      } else {
        // Missed a whole day -> Streak breaks, reset to 1
        currentStreak = 1
      }
      localStorage.setItem(keyStreak, currentStreak.toString())
      localStorage.setItem(keyLastDate, todayStr)
    }

    setStreakDays(currentStreak)
    setLastActiveDate(todayStr)
    return currentStreak
  }

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  const recordActivity = (type, title, details = {}) => {
    const todayStr = getTodayStr()
    const nowTime = formatClockTime()
    
    checkAndUpdateStreak()

    // Append activity to active study session
    setStudySessions((prevSessions) => {
      if (!prevSessions || prevSessions.length === 0) return prevSessions
      return prevSessions.map((s, idx) => {
        if (idx === 0) {
          const acts = s.activities || []
          return {
            ...s,
            endTime: nowTime,
            activities: [title, ...acts].slice(0, 10)
          }
        }
        return s
      })
    })

    // Add item to activity log feed
    const newItem = {
      id: Date.now().toString(),
      type, // 'trainer' | 'challenge' | 'lab' | 'evaluation'
      text: title,
      when: nowTime,
      date: todayStr,
      ...details
    }

    setActivityLog((prev) => {
      const updated = [newItem, ...prev].slice(0, 50)
      try { localStorage.setItem('ls-activity-log', JSON.stringify(updated)) } catch {}
      return updated
    })
  }

  const login = async (chosenRole, customUserData = null) => {
    if (!customUserData) {
      throw new Error("Account does not exist. Please create an account first to log in.")
    }
    
    setRole(chosenRole)
    const loggedInUser = {
      ...customUserData,
      initials: customUserData.initials || (customUserData.name ? customUserData.name.split(' ').map(n=>n[0]).join('').slice(0, 2).toUpperCase() : 'US')
    }

    if (loggedInUser.teacherLevel || loggedInUser.level) {
      setInstitutionMode(loggedInUser.teacherLevel || loggedInUser.level)
    }

    setCurrentUser(loggedInUser)
    setAuthenticated(true)

    // Calculate user-specific daily streak
    checkAndUpdateStreak(loggedInUser.email)
    const nowStr = formatClockTime()
    const todayStr = getTodayStr()
    const newSessId = `sess_${Date.now()}`
    const newSession = {
      id: newSessId,
      date: todayStr,
      startTime: nowStr,
      endTime: nowStr,
      durationSeconds: 0,
      durationText: '0s',
      activities: [`Logged in at ${nowStr}`]
    }
    
    setCurrentSessionId(newSessId)
    setSessionElapsedSeconds(0)
    setStudySessions((prev) => [newSession, ...(prev || [])].slice(0, 30))
    try {
      localStorage.setItem('ls-current-session-id', newSessId)
    } catch {}
  }

  const logout = () => {
    // Finalize current session on logout
    if (studySessions && studySessions.length > 0) {
      const finalTime = formatClockTime()
      setStudySessions((prev) => prev.map((s, idx) => idx === 0 ? { ...s, endTime: finalTime } : s))
    }
    setAuthenticated(false)
    try { localStorage.removeItem('ls-auth') } catch {}
  }

  const setProfile = (p) => setProfileState(p)
  
  const clearProfile = () => {
    setProfileState(null)
    try { localStorage.removeItem('ls-profile') } catch {}
  }

  const profileComplete = role === 'teacher' || profile !== null

  const [syllabusData, setSyllabusDataState] = useState(() => {
    try {
      const saved = localStorage.getItem('ls-syllabus-data')
      return saved ? JSON.parse(saved) : null
    } catch { return null }
  })

  const setSyllabusData = (data) => {
    setSyllabusDataState(data)
    try { localStorage.setItem('ls-syllabus-data', JSON.stringify(data)) } catch {}
  }

  const userWithInitials = currentUser ? {
    ...currentUser,
    initials: currentUser.initials || (currentUser.name ? currentUser.name.split(' ').map(n=>n[0]).join('').slice(0, 2).toUpperCase() : 'US')
  } : DEFAULT_USERS[role]

  // Formatted live session timer e.g. "00:15:32"
  const formattedSessionTime = formatDuration(sessionElapsedSeconds)

  // Workplace / Institution Mode State ('school' | 'college')
  const [institutionMode, setInstitutionModeState] = useState(() => {
    try { return localStorage.getItem('learnsphere_institution_mode') || 'school' } catch { return 'school' }
  })

  const setInstitutionMode = (mode) => {
    setInstitutionModeState(mode)
    try { localStorage.setItem('learnsphere_institution_mode', mode) } catch {}
  }

  // Teacher Class & Department Management State
  const [teacherClasses, setTeacherClasses] = useState(() => {
    try {
      const saved = localStorage.getItem('learnsphere_teacher_classes')
      if (saved) {
        const parsed = JSON.parse(saved)
        // Clean out legacy demo classes (e.g. cls-1, cls-2, cls-3, cls-4) if present
        const realClasses = parsed.filter(c => !['cls-1', 'cls-2', 'cls-3', 'cls-4'].includes(c.id))
        return realClasses
      }
      return []
    } catch { return [] }
  })

  const [activeClassId, setActiveClassIdState] = useState(() => {
    try {
      return localStorage.getItem('learnsphere_active_class_id') || ''
    } catch { return '' }
  })

  useEffect(() => {
    try {
      localStorage.setItem('learnsphere_teacher_classes', JSON.stringify(teacherClasses))
    } catch {}
  }, [teacherClasses])

  const setActiveClassId = (id) => {
    setActiveClassIdState(id)
    try { localStorage.setItem('learnsphere_active_class_id', id) } catch {}
  }

  const addClass = (newCls) => {
    const created = {
      id: `cls_${Date.now()}`,
      created_at: new Date().toISOString().split('T')[0],
      ...newCls
    }
    setTeacherClasses((prev) => [created, ...prev])
    setActiveClassId(created.id)
    return created
  }

  const deleteClass = (classId) => {
    setTeacherClasses((prev) => prev.filter((c) => c.id !== classId))
    if (activeClassId === classId) {
      setActiveClassId('')
    }
  }

  const uploadStudentRoster = (classId, newStudentsList) => {
    setTeacherClasses((prev) =>
      prev.map((cls) => {
        if (cls.id === classId) {
          const updatedStudents = newStudentsList.map((st, idx) => ({
            id: st.id || `std_${Date.now()}_${idx}`,
            rollNo: st.rollNo || `ROLL-${idx + 1}`,
            name: st.name,
            order: idx + 1,
            marksHistory: st.marksHistory || []
          }))
          return {
            ...cls,
            students: updatedStudents,
            students_count: updatedStudents.length
          }
        }
        return cls
      })
    )
  }

  const addOrUpdateStudentMarks = (classId, studentId, markEntry) => {
    setTeacherClasses((prev) =>
      prev.map((cls) => {
        if (cls.id === classId) {
          const updatedStudents = (cls.students || []).map((std) => {
            if (std.id === studentId || std.rollNo === studentId || std.name === studentId) {
              const currentHistory = std.marksHistory || []
              const existingIdx = currentHistory.findIndex(
                (m) => m.subject === markEntry.subject && m.assessment === markEntry.assessment
              )
              let nextHistory = []
              if (existingIdx >= 0) {
                nextHistory = [...currentHistory]
                nextHistory[existingIdx] = markEntry
              } else {
                nextHistory = [markEntry, ...currentHistory]
              }
              return { ...std, marksHistory: nextHistory }
            }
            return std
          })
          return { ...cls, students: updatedStudents }
        }
        return cls
      })
    )
  }

  const deleteStudentFromClass = (classId, studentId) => {
    setTeacherClasses((prev) =>
      prev.map((cls) => {
        if (cls.id === classId) {
          const updatedStudents = (cls.students || []).filter((s) => s.id !== studentId)
          return {
            ...cls,
            students: updatedStudents,
            students_count: updatedStudents.length
          }
        }
        return cls
      })
    )
  }

  // Filter stored classes strictly according to teacher's institution mode ('school' vs 'college')
  const filteredTeacherClasses = teacherClasses.filter((c) => c.level === institutionMode)
  const activeClass = filteredTeacherClasses.find((c) => c.id === activeClassId) || (filteredTeacherClasses.length > 0 ? filteredTeacherClasses[0] : null)

  const value = {
    authenticated, role, setRole,
    user: userWithInitials,
    theme, toggleTheme,
    login, logout,
    profile, setProfile, clearProfile,
    profileComplete,
    syllabusData, setSyllabusData,
    streakDays, recordActivity, activityLog,
    sessionElapsedSeconds, formattedSessionTime, studySessions, isUserActive,
    institutionMode, setInstitutionMode,
    teacherClasses: filteredTeacherClasses,
    allTeacherClasses: teacherClasses,
    activeClassId, activeClass, setActiveClassId, addClass, deleteClass,
    uploadStudentRoster, addOrUpdateStudentMarks, deleteStudentFromClass
  }

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used within AppProvider')
  return ctx
}
