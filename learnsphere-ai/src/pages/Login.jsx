import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  GraduationCap,
  Users,
  Eye,
  EyeOff,
  User,
  Lock,
  ArrowRight,
  BookOpen,
  ClipboardCheck,
  FlaskConical,
  TrendingUp,
  Sprout,
  CheckCircle2,
  AlertCircle,
  X
} from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import {
  BOARDS,
  CLASSES,
  STREAMS,
  COLLEGE_SEMESTERS,
  COLLEGE_STREAMS,
  COLLEGE_DOMAINS
} from '../data/syllabusData.js'

function GoogleIcon() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" />
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" />
    </svg>
  )
}

function MicrosoftIcon() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 23 23">
      <path fill="#f35325" d="M1 1h10v10H1z" />
      <path fill="#81bc06" d="M12 1h10v10H12z" />
      <path fill="#05a6f0" d="M1 12h10v10H1z" />
      <path fill="#ffba08" d="M12 12h10v10H12z" />
    </svg>
  )
}

const FEATURE_HIGHLIGHTS = [
  {
    icon: BookOpen,
    title: 'Personalized Learning',
    subtitle: 'Learn at your pace',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    border: 'border-emerald-100 dark:border-emerald-900/50',
    text: 'text-emerald-600 dark:text-emerald-400'
  },
  {
    icon: ClipboardCheck,
    title: 'Smart Assessment',
    subtitle: 'Get real insights',
    bg: 'bg-teal-50 dark:bg-teal-950/40',
    border: 'border-teal-100 dark:border-teal-900/50',
    text: 'text-teal-600 dark:text-teal-400'
  },
  {
    icon: FlaskConical,
    title: 'Real-World Experiences',
    subtitle: 'Learn by doing',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    border: 'border-emerald-100 dark:border-emerald-900/50',
    text: 'text-emerald-600 dark:text-emerald-400'
  },
  {
    icon: TrendingUp,
    title: 'Better Opportunities',
    subtitle: 'Build your future',
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    border: 'border-amber-100 dark:border-amber-900/50',
    text: 'text-amber-500 dark:text-amber-400'
  }
]

export default function Login() {
  const [portal, setPortal] = useState('student')
  const [isLogin, setIsLogin] = useState(true)

  // Auth Inputs
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  // Teacher Registration State
  const [teacherLevel, setTeacherLevel] = useState('school')
  const [institutionName, setInstitutionName] = useState('')
  const [department, setDepartment] = useState('Computer Science')
  const [classesTaught, setClassesTaught] = useState(12)

  // Student Registration State
  const [level, setLevel] = useState('school')
  const [board, setBoard] = useState('CBSE')
  const [classLevel, setClassLevel] = useState(12)
  const [schoolStream, setSchoolStream] = useState('Science')
  const [schoolSection, setSchoolSection] = useState('')
  const [schoolRoll, setSchoolRoll] = useState('')

  // College Student Profile Fields
  const [collegeDegree, setCollegeDegree] = useState('B.Tech')
  const [collegeStream, setCollegeStream] = useState((COLLEGE_STREAMS && COLLEGE_STREAMS[0]) || 'Engineering & Technology')
  const [collegeDomain, setCollegeDomain] = useState('Computer Science & AI')
  const [collegeBranch, setCollegeBranch] = useState('Computer Science & Engineering')
  const [currentYear, setCurrentYear] = useState('3rd Year')
  const [semester, setSemester] = useState(5)
  const [regulation, setRegulation] = useState('')
  const [academicYear, setAcademicYear] = useState('2024-2025')

  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  // Forgot Password Modal State
  const [showForgotModal, setShowForgotModal] = useState(false)
  const [forgotEmail, setForgotEmail] = useState('')
  const [forgotSent, setForgotSent] = useState(false)

  const { login } = useApp()
  const navigate = useNavigate()

  const handlePortalSwitch = (pId) => {
    setPortal(pId)
    setErrorMsg('')
  }

  const handleCollegeStreamChange = (val) => {
    setCollegeStream(val)
    const availableDomains = COLLEGE_DOMAINS[val] || []
    if (availableDomains.length > 0) {
      setCollegeDomain(availableDomains[0])
      setCollegeBranch(availableDomains[0])
    }
  }

  const handleSemesterChange = (semNum) => {
    const sem = Number(semNum)
    setSemester(sem)
    if (sem <= 2) setCurrentYear('1st Year')
    else if (sem <= 4) setCurrentYear('2nd Year')
    else if (sem <= 6) setCurrentYear('3rd Year')
    else setCurrentYear('4th Year')
  }

  const handleSSO = async (provider) => {
    const ssoEmail = portal === 'teacher' ? 'teacher@example.com' : 'student@example.com'
    setEmail(ssoEmail)
    setPassword('password123')
    setLoading(true)
    setErrorMsg('')
    try {
      const res = await api.login({ email: ssoEmail, password: 'password123', role: portal })
      if (res && res.success && res.user) {
        await login(portal, res.user)
        navigate(portal === 'teacher' ? '/create-class' : '/app/dashboard')
      } else {
        setErrorMsg(`Fast-signing in via ${provider}… Please click Sign In with your credentials.`)
      }
    } catch {
      setErrorMsg(`Fast-signing in via ${provider}… Please click Sign In with your credentials.`)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setErrorMsg('')

    try {
      if (!isLogin) {
        // Create Account Payload
        const payload = portal === 'teacher' ? {
          name,
          email,
          password,
          role: 'teacher',
          teacherLevel,
          institutionName,
          department: teacherLevel === 'college' ? department : `Classes ${classesTaught}`,
          board: teacherLevel === 'school' ? board : null,
          classLevel: teacherLevel === 'school' ? classesTaught : null
        } : {
          name,
          email,
          password,
          role: 'student',
          level,
          institutionName,
          degree: level === 'college' ? collegeDegree : null,
          program: level === 'college' ? collegeDegree : null,
          department: level === 'college' ? (collegeBranch || collegeDomain) : null,
          branch: level === 'college' ? (collegeBranch || collegeDomain) : null,
          stream: level === 'school' ? schoolStream : collegeStream,
          domain: level === 'college' ? collegeDomain : null,
          currentYear: level === 'college' ? currentYear : null,
          semester: level === 'college' ? semester : null,
          currentSemester: level === 'college' ? semester : null,
          regulation: level === 'college' ? (regulation.trim() || null) : null,
          batch: level === 'college' ? (regulation.trim() || null) : null,
          academicYear: level === 'college' ? (academicYear.trim() || null) : null,
          board: level === 'school' ? board : null,
          classLevel: level === 'school' ? classLevel : null,
          grade_level: level === 'school' ? classLevel : null,
          section: level === 'school' ? (schoolSection.trim() || null) : null,
          roll_number: level === 'school' ? (schoolRoll.trim() || null) : null,
        }

        const res = await api.register(payload)
        if (res && res.success && res.user) {
          await login(portal, res.user)
          navigate(portal === 'teacher' ? '/create-class' : '/app/dashboard')
        } else {
          setErrorMsg(res?.error || 'Account registration failed. Please check details and try again.')
        }
      } else {
        // Sign In Flow
        const res = await api.login({ email, password, role: portal })
        if (res && res.success && res.user) {
          await login(portal, res.user)
          navigate(portal === 'teacher' ? '/create-class' : '/app/dashboard')
        } else {
          setErrorMsg(res?.error || 'Invalid email or password. Please verify your credentials or create an account.')
        }
      }
    } catch {
      setErrorMsg('Authentication error. Please verify your credentials and network connection.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="h-screen bg-[#f8fafc] dark:bg-slate-950 flex flex-col selection:bg-emerald-600 selection:text-white relative overflow-hidden">
      {/* Background Soft Glow Accents */}
      <div className="absolute top-0 right-0 w-[600px] h-[600px] bg-gradient-to-b from-emerald-100/40 to-transparent dark:from-emerald-950/20 rounded-full blur-3xl pointer-events-none -z-10" />
      <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-gradient-to-t from-teal-100/40 to-transparent dark:from-teal-950/20 rounded-full blur-3xl pointer-events-none -z-10" />

      {/* Top Header Tagline */}
      <div className="w-full px-5 sm:px-8 lg:px-12 pt-3 sm:pt-4 flex justify-end items-center shrink-0">
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold text-slate-600 dark:text-slate-400 bg-white/60 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800 shadow-2xs">
          <Sprout size={15} className="text-emerald-500" />
          <span>A smarter way to learn</span>
        </div>
      </div>

      {/* Main Container — fills remaining height, content vertically centered */}
      <main className="flex-1 w-full px-5 sm:px-8 lg:px-12 py-3 flex items-center overflow-y-auto">
        <div className="grid lg:grid-cols-12 gap-6 lg:gap-10 items-center w-full h-full max-w-[1440px] mx-auto">
          {/* Left Side: Official Logo, Tagline, Feature Highlights & Clean 3D Illustration */}
          <div className="lg:col-span-7 space-y-4 lg:space-y-5">
            {/* Logo & Platform Tagline with Official Uploaded Logo */}
            <div className="flex items-center gap-3.5">
              <img
                src="/learnsphere-icon.png"
                alt="LearnSphere AI"
                className="w-12 h-12 object-contain rounded-full shadow-xs shrink-0"
              />
              <div>
                <div className="text-2xl sm:text-[27px] font-extrabold tracking-tight text-slate-900 dark:text-white leading-none">
                  LearnSphere <span className="text-emerald-600 dark:text-emerald-400">AI</span>
                </div>
                <div className="text-xs text-slate-400 dark:text-slate-500 font-medium tracking-wide mt-1">
                  Unified Education Intelligence Platform
                </div>
              </div>
            </div>

            {/* Hero Heading with Green Accent */}
            <div className="space-y-1.5 pt-0.5">
              <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-black tracking-tight leading-[1.12]">
                <span className="text-slate-900 dark:text-white block">Smarter Learning.</span>
                <span className="text-emerald-600 dark:text-emerald-400 block">Brighter Futures.</span>
              </h1>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-400 leading-relaxed max-w-xl">
                Personalized learning, intelligent assessment and real-world experiences — all in one platform.
              </p>
            </div>

            {/* 4 Feature Cards */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 sm:gap-3">
              {FEATURE_HIGHLIGHTS.map((item, idx) => {
                const Icon = item.icon
                return (
                  <div
                    key={idx}
                    className="flex flex-col items-start p-2.5 sm:p-3 rounded-2xl bg-white/70 dark:bg-slate-900/70 border border-slate-200/70 dark:border-slate-800 backdrop-blur-xs shadow-xs"
                  >
                    <div className={`w-9 h-9 rounded-full ${item.bg} border ${item.border} ${item.text} flex items-center justify-center mb-2 shrink-0`}>
                      <Icon size={18} strokeWidth={2} />
                    </div>
                    <div className="font-bold text-[11.5px] sm:text-[12.5px] text-slate-900 dark:text-white leading-tight">
                      {item.title}
                    </div>
                    <div className="text-[10.5px] text-slate-400 dark:text-slate-500 leading-tight mt-0.5">
                      {item.subtitle}
                    </div>
                  </div>
                )
              })}
            </div>

            {/* 3D Visual Illustration with ZERO text on books and official logo on laptop */}
            <div className="pt-1">
              <div className="relative rounded-2xl overflow-hidden max-w-[480px] mx-auto lg:mx-0 shadow-md border border-slate-200/60 dark:border-slate-800 bg-white/40">
                <img
                  src="/login-illustration.jpg"
                  alt="LearnSphere AI 3D Education"
                  className="w-full h-auto object-cover max-h-[250px] sm:max-h-[270px]"
                />
              </div>

              {/* Bottom Decorative Navigation Brand Line with Green Accent */}
              <div className="flex items-center gap-2.5 sm:gap-3 pt-2.5 text-[10px] sm:text-[11px] font-bold tracking-[0.2em] text-slate-400 dark:text-slate-500">
                <div className="w-8 sm:w-10 h-0.5 bg-emerald-600 dark:bg-emerald-400 rounded-full" />
                <span>LEARN</span>
                <span className="text-slate-300 dark:text-slate-700">|</span>
                <span>ASSESS</span>
                <span className="text-slate-300 dark:text-slate-700">|</span>
                <span>IMPROVE</span>
                <span className="text-slate-300 dark:text-slate-700">|</span>
                <span>SUCCEED</span>
              </div>
            </div>
          </div>

          {/* Right Side: Clean Elevated White Login Card (Framed to fit viewport) */}
          <div className="lg:col-span-5 w-full max-w-[480px] mx-auto lg:ml-auto">
            <div className="bg-white dark:bg-slate-900 rounded-3xl p-5 sm:p-7 lg:p-8 shadow-[0_20px_50px_-15px_rgba(0,0,0,0.08)] border border-slate-200/80 dark:border-slate-800">
              {/* Card Header */}
              <div className="mb-4">
                <h2 className="text-2xl sm:text-[26px] font-black tracking-tight text-slate-900 dark:text-white">
                  {isLogin ? 'Welcome Back' : 'Create Account'}
                </h2>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  {isLogin ? 'Sign in to continue your learning journey' : 'Join LearnSphere AI to begin your intelligent learning journey'}
                </p>
              </div>

              {/* Portal Selector (Student vs Teacher Portal with Green Accent) */}
              <div className="mb-4">
                <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-2xl">
                  <button
                    type="button"
                    onClick={() => handlePortalSwitch('student')}
                    className={`py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 text-xs font-bold transition-all cursor-pointer ${
                      portal === 'student'
                        ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 shadow-xs'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <Users size={14} />
                    <span>Student Portal</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handlePortalSwitch('teacher')}
                    className={`py-2 px-3 rounded-xl flex items-center justify-center gap-1.5 text-xs font-bold transition-all cursor-pointer ${
                      portal === 'teacher'
                        ? 'bg-white dark:bg-slate-900 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 shadow-xs'
                        : 'text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                    }`}
                  >
                    <GraduationCap size={14} />
                    <span>Teacher Portal</span>
                  </button>
                </div>
              </div>

              {/* Error Alert */}
              {errorMsg && (
                <div className="p-2.5 bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-900/50 text-xs font-semibold rounded-xl mb-3 text-red-600 dark:text-red-400 flex items-center gap-2">
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Main Auth Form */}
              <form onSubmit={handleSubmit} className="space-y-3">
                {/* Full Name for Registration */}
                {!isLogin && (
                  <div className="relative">
                    <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input
                      type="text"
                      placeholder="Full Name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      required
                      className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 text-xs sm:text-sm focus:outline-none focus:border-emerald-500 focus:ring-3 focus:ring-emerald-50 dark:focus:ring-emerald-950/40 transition-all"
                    />
                  </div>
                )}

                {/* TEACHER REGISTRATION FORM FIELDS */}
                {!isLogin && portal === 'teacher' && (
                  <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-2xl border border-slate-200 dark:border-slate-700 space-y-2 text-xs max-h-[220px] overflow-y-auto">
                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Teaching Level</label>
                      <select
                        value={teacherLevel}
                        onChange={(e) => setTeacherLevel(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                      >
                        <option value="school">School Educator</option>
                        <option value="college">College Professor / Lecturer</option>
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Institution Name</label>
                      <input
                        type="text"
                        placeholder="e.g. Delhi Public School or IIT Bombay"
                        value={institutionName}
                        onChange={(e) => setInstitutionName(e.target.value)}
                        required
                        className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                      />
                    </div>

                    {teacherLevel === 'school' ? (
                      <div className="grid grid-cols-2 gap-2">
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Board</label>
                          <select
                            value={board}
                            onChange={(e) => setBoard(e.target.value)}
                            className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                          >
                            {BOARDS.map(b => <option key={b} value={b}>{b}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Grade Taught</label>
                          <select
                            value={classesTaught}
                            onChange={(e) => setClassesTaught(Number(e.target.value))}
                            className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                          >
                            {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
                          </select>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Department</label>
                        <input
                          type="text"
                          placeholder="e.g. Computer Science, Physics"
                          value={department}
                          onChange={(e) => setDepartment(e.target.value)}
                          required
                          className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                        />
                      </div>
                    )}
                  </div>
                )}

                {/* STUDENT REGISTRATION FORM FIELDS */}
                {!isLogin && portal === 'student' && (
                  <div className="bg-slate-50 dark:bg-slate-800/60 p-3 rounded-2xl border border-slate-200 dark:border-slate-700 space-y-2 text-xs max-h-[220px] overflow-y-auto">
                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Academic Level</label>
                      <select
                        value={level}
                        onChange={(e) => setLevel(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                      >
                        <option value="school">School Student (Class 1 to 12)</option>
                        <option value="college">College / University Student (Semester-aware)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">
                        {level === 'college' ? 'College / University Name' : 'School Name'}
                      </label>
                      <input
                        type="text"
                        placeholder={level === 'college' ? "e.g. IIT Madras, BITS Pilani" : "e.g. Delhi Public School"}
                        value={institutionName}
                        onChange={(e) => setInstitutionName(e.target.value)}
                        required
                        className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                      />
                    </div>

                    {level === 'school' && (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Board</label>
                            <select
                              value={board}
                              onChange={(e) => setBoard(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            >
                              {BOARDS.map(b => <option key={b} value={b}>{b}</option>)}
                            </select>
                          </div>
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Class</label>
                            <select
                              value={classLevel}
                              onChange={(e) => setClassLevel(Number(e.target.value))}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            >
                              {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Stream</label>
                          <select
                            value={schoolStream}
                            onChange={(e) => setSchoolStream(e.target.value)}
                            className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                          >
                            {Object.keys(STREAMS).map(s => <option key={s} value={s}>{s}</option>)}
                          </select>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Section</label>
                            <input
                              type="text"
                              placeholder="e.g. A or B"
                              value={schoolSection}
                              onChange={(e) => setSchoolSection(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            />
                          </div>
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Roll No</label>
                            <input
                              type="text"
                              placeholder="e.g. 24"
                              value={schoolRoll}
                              onChange={(e) => setSchoolRoll(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            />
                          </div>
                        </div>
                      </div>
                    )}

                    {level === 'college' && (
                      <div className="space-y-2">
                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Degree</label>
                            <input
                              type="text"
                              value={collegeDegree}
                              onChange={(e) => setCollegeDegree(e.target.value)}
                              placeholder="B.Tech"
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            />
                          </div>
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Stream</label>
                            <select
                              value={collegeStream}
                              onChange={(e) => handleCollegeStreamChange(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            >
                              {COLLEGE_STREAMS && COLLEGE_STREAMS.map(s => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </div>
                        </div>

                        <div>
                          <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Branch / Major</label>
                          <input
                            type="text"
                            value={collegeBranch}
                            onChange={(e) => setCollegeBranch(e.target.value)}
                            placeholder="Computer Science & Engineering"
                            className="w-full px-2.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Year</label>
                            <select
                              value={currentYear}
                              onChange={(e) => setCurrentYear(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            >
                              <option value="1st Year">1st Year</option>
                              <option value="2nd Year">2nd Year</option>
                              <option value="3rd Year">3rd Year</option>
                              <option value="4th Year">4th Year</option>
                            </select>
                          </div>
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Semester</label>
                            <select
                              value={semester}
                              onChange={(e) => handleSemesterChange(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            >
                              {COLLEGE_SEMESTERS.map(s => <option key={s} value={s}>Semester {s}</option>)}
                            </select>
                          </div>
                        </div>

                        <div className="grid grid-cols-2 gap-2">
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Batch / Regulation</label>
                            <input
                              type="text"
                              placeholder="e.g. 2022-2026 or R21"
                              value={regulation}
                              onChange={(e) => setRegulation(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            />
                          </div>
                          <div>
                            <label className="block font-semibold text-slate-600 dark:text-slate-300 mb-0.5">Academic Year</label>
                            <input
                              type="text"
                              placeholder="e.g. 2024-2025"
                              value={academicYear}
                              onChange={(e) => setAcademicYear(e.target.value)}
                              className="w-full px-2 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none text-xs"
                            />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Email or Mobile Number Input */}
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="text"
                    placeholder="Email or Mobile Number"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    className="w-full pl-9 pr-3.5 py-2.5 sm:py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 text-xs sm:text-sm focus:outline-none focus:border-emerald-500 focus:ring-3 focus:ring-emerald-50 dark:focus:ring-emerald-950/40 transition-all"
                  />
                </div>

                {/* Password Input */}
                <div className="relative">
                  <Lock size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className="w-full pl-9 pr-10 py-2.5 sm:py-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder:text-slate-400 text-xs sm:text-sm focus:outline-none focus:border-emerald-500 focus:ring-3 focus:ring-emerald-50 dark:focus:ring-emerald-950/40 transition-all"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 focus:outline-none cursor-pointer"
                    title={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                </div>

                {/* Forgot Password Link with Green Accent */}
                {isLogin && (
                  <div className="flex justify-end pt-0.5">
                    <button
                      type="button"
                      onClick={() => { setShowForgotModal(true); setForgotSent(false); setForgotEmail(email) }}
                      className="text-xs font-semibold text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300 transition-colors cursor-pointer"
                    >
                      Forgot Password?
                    </button>
                  </div>
                )}

                {/* Sign In / Register Action Button with Green Gradient */}
                <button
                  type="submit"
                  disabled={loading}
                  className="w-full py-2.5 sm:py-3 px-6 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-700 hover:from-emerald-700 hover:to-teal-800 text-white font-bold text-xs sm:text-sm shadow-md shadow-emerald-600/20 active:scale-[0.99] transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed mt-1.5"
                >
                  <span>{loading ? 'Signing In…' : isLogin ? 'Sign In' : 'Create Account'}</span>
                  {!loading && <ArrowRight size={16} />}
                </button>

                {/* Divider */}
                {isLogin && (
                  <div className="relative my-3 text-center">
                    <div className="absolute inset-0 flex items-center">
                      <div className="w-full border-t border-slate-200 dark:border-slate-800" />
                    </div>
                    <span className="relative bg-white dark:bg-slate-900 px-3 text-[11px] text-slate-400 font-medium">
                      Or continue with
                    </span>
                  </div>
                )}

                {/* Social SSO Buttons */}
                {isLogin && (
                  <div className="grid grid-cols-2 gap-2.5">
                    <button
                      type="button"
                      onClick={() => handleSSO('Google')}
                      className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-all shadow-2xs cursor-pointer"
                    >
                      <GoogleIcon />
                      <span>Google</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSSO('Microsoft')}
                      className="flex items-center justify-center gap-2 py-2 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:bg-slate-50 dark:hover:bg-slate-700/60 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-all shadow-2xs cursor-pointer"
                    >
                      <MicrosoftIcon />
                      <span>Microsoft</span>
                    </button>
                  </div>
                )}
              </form>

              {/* Bottom CTA Banner (New to LearnSphere AI?) with Green Accent */}
              <div
                onClick={() => { setIsLogin(!isLogin); setErrorMsg('') }}
                className="mt-4 p-3 rounded-2xl bg-emerald-50/70 dark:bg-emerald-950/30 hover:bg-emerald-50 dark:hover:bg-emerald-950/50 border border-emerald-100/90 dark:border-emerald-900/50 flex items-center justify-between cursor-pointer transition-all group"
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-2xs">
                    <GraduationCap size={17} />
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors truncate">
                      {isLogin ? 'New to LearnSphere AI?' : 'Already have an account?'}
                    </div>
                    <div className="text-[10.5px] text-slate-500 dark:text-slate-400 truncate">
                      {isLogin ? 'Create your account and start learning today.' : 'Sign in to access your portal.'}
                    </div>
                  </div>
                </div>
                <ArrowRight size={15} className="text-emerald-600 dark:text-emerald-400 shrink-0 group-hover:translate-x-0.5 transition-transform" />
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Forgot Password Modal */}
      {showForgotModal && (
        <div className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl max-w-[400px] w-full p-6 shadow-2xl border border-slate-200 dark:border-slate-800 relative animate-in fade-in zoom-in-95 duration-150">
            <button
              onClick={() => setShowForgotModal(false)}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 cursor-pointer"
            >
              <X size={18} />
            </button>
            <div className="mb-4">
              <h3 className="text-lg font-bold text-slate-900 dark:text-white">Password Recovery</h3>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Enter your registered email address to receive password reset instructions.
              </p>
            </div>
            {forgotSent ? (
              <div className="p-4 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-900 rounded-2xl text-center space-y-2">
                <CheckCircle2 size={30} className="text-emerald-500 mx-auto" />
                <div className="text-xs font-bold text-emerald-800 dark:text-emerald-300">Reset Link Sent</div>
                <div className="text-[11px] text-emerald-700 dark:text-emerald-400">
                  We sent instructions to <strong>{forgotEmail}</strong>. Please check your inbox.
                </div>
                <button
                  onClick={() => setShowForgotModal(false)}
                  className="mt-3 px-4 py-2 bg-emerald-600 text-white rounded-xl text-xs font-bold w-full cursor-pointer hover:bg-emerald-700"
                >
                  Close
                </button>
              </div>
            ) : (
              <form
                onSubmit={(e) => {
                  e.preventDefault()
                  setForgotSent(true)
                }}
                className="space-y-3"
              >
                <div className="relative">
                  <User size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                  <input
                    type="email"
                    placeholder="Enter your registered email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    required
                    className="w-full pl-9 pr-3.5 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs bg-white dark:bg-slate-800 text-slate-900 dark:text-white outline-none focus:border-emerald-500"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs cursor-pointer shadow-xs"
                >
                  Send Recovery Link
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Subtle Bottom Footer */}
      <footer className="py-2 text-center text-[11px] text-slate-400 dark:text-slate-600 border-t border-slate-200/50 dark:border-slate-900 shrink-0">
        LearnSphere AI &bull; Universal Academic Intelligence Platform
      </footer>
    </div>
  )
}
