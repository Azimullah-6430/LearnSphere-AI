import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { GraduationCap, Users, Eye, EyeOff } from 'lucide-react'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { BOARDS, CLASSES, STREAMS, COLLEGE_SEMESTERS, COLLEGE_STREAMS, COLLEGE_DOMAINS } from '../data/syllabusData.js'

const PORTALS = [
  { id: 'teacher', title: 'Teacher', sub: 'Evaluate. Understand. Guide.', icon: GraduationCap },
  { id: 'student', title: 'Student', sub: 'Learn. Improve. Grow.', icon: Users },
]

export default function Login() {
  const [portal, setPortal] = useState('teacher')
  const [isLogin, setIsLogin] = useState(true)
  
  // Clean inputs with zero pre-filled demo credentials
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)

  // Teacher Registration State
  const [teacherLevel, setTeacherLevel] = useState('school') // 'school' or 'college'
  const [institutionName, setInstitutionName] = useState('')
  const [department, setDepartment] = useState('Computer Science')
  const [classesTaught, setClassesTaught] = useState(12)

  // Student Registration State
  const [level, setLevel] = useState('school') // 'school' or 'college'
  const [board, setBoard] = useState('CBSE')
  const [classLevel, setClassLevel] = useState(12)
  const [schoolStream, setSchoolStream] = useState('Science')
  const [collegeStream, setCollegeStream] = useState('Engineering & Technology')
  const [collegeDomain, setCollegeDomain] = useState('Computer Science & AI')
  const [semester, setSemester] = useState(1)
  
  const [loading, setLoading] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

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
          board: level === 'school' ? board : null, // ABSOLUTELY NO BOARD FOR COLLEGE
          classLevel: level === 'school' ? classLevel : null,
          stream: level === 'school' ? schoolStream : collegeStream,
          domain: level === 'college' ? collegeDomain : null,
          semester: level === 'college' ? semester : null,
          institutionName
        }

        const res = await api.register(payload)
        if (res && res.success && res.user) {
          await login(portal, res.user)
          navigate(portal === 'teacher' ? '/create-class' : '/app/dashboard')
        } else {
          setErrorMsg(res?.error || 'Account registration failed. Please try again.')
        }
      } else {
        // Sign In Flow - STRICT CREDENTIAL CHECK
        const res = await api.login({ email, password, role: portal })
        if (res && res.success && res.user) {
          await login(portal, res.user)
          navigate(portal === 'teacher' ? '/create-class' : '/app/dashboard')
        } else {
          setErrorMsg(res?.error || 'Invalid email or password. Please check your credentials or create an account.')
        }
      }
    } catch (err) {
      setErrorMsg('Authentication error. Please verify your login credentials.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen grid md:grid-cols-[1.1fr_1fr] bg-[var(--bg)]">
      <div className="hidden md:flex flex-col justify-between p-14 bg-[var(--accent-soft)]">
        <div className="flex items-center gap-2.5">
          <svg width="30" height="30" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="16" r="10.5" stroke="#28503F" strokeWidth="2" />
            <circle cx="24" cy="9" r="4" fill="#28503F" />
          </svg>
          <div className="text-base font-extrabold tracking-tight text-[#1B1C18]">
            LearnSphere<small className="font-semibold text-[#28503F] text-xs ml-0.5">AI</small>
          </div>
        </div>

        <div className="max-w-[420px] mt-16">
          <h1 className="font-serif text-[38px] leading-[1.15] tracking-tight text-[#1B1C18] mb-4">
            A clearer way to
            <br />
            understand learning.
          </h1>
          <p className="text-[15px] text-[#5D5C54] max-w-[380px]">
            Strict paper-based AI evaluation, persistent data storage, and personalized academic context.
          </p>
        </div>

        <div className="text-xs text-[#9B998E]">© 2026 LearnSphere AI — Connected to MongoDB Cloud.</div>
      </div>

      <div className="flex items-center justify-center p-8 md:p-14">
        <div className="w-full max-w-[400px]">
          <h2 className="text-xl font-bold mb-1.5">{isLogin ? 'Sign in' : 'Create account'}</h2>
          <p className="text-[var(--text-soft)] mb-6 text-sm">Choose your portal to continue.</p>

          <div className="grid grid-cols-2 gap-3 mb-6">
            {PORTALS.map((p) => {
              const Icon = p.icon
              const active = portal === p.id
              return (
                <button
                  type="button"
                  key={p.id}
                  onClick={() => handlePortalSwitch(p.id)}
                  className={`text-left border-[1.5px] rounded-xl p-4 transition-all ${
                    active
                      ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-[0_0_0_3px_var(--accent-soft)]'
                      : 'border-[var(--border-strong)] bg-[var(--surface)] hover:border-[var(--accent-dim)]'
                  }`}
                >
                  <Icon size={26} strokeWidth={1.6} className="text-[var(--accent)] mb-2.5" />
                  <div className="text-sm font-bold mb-0.5">{p.title}</div>
                  <div className="text-xs text-[var(--text-faint)]">{p.sub}</div>
                </button>
              )
            })}
          </div>

          {errorMsg && (
            <div className="p-3 bg-[var(--warning-soft)] border border-[var(--warning)] text-xs font-semibold rounded-lg mb-4 text-[var(--warning)]">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit}>


            {!isLogin && (
              <div className="mb-3.5">
                <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Full Name</label>
                <input
                  type="text"
                  placeholder="Enter your full name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  className="w-full px-3.5 py-[10px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--accent)]"
                />
              </div>
            )}

            {/* REGISTER FIELDS FOR TEACHER PORTAL */}
            {!isLogin && portal === 'teacher' && (
              <div className="bg-[var(--accent-soft)] p-4 rounded-xl mb-4 border border-[var(--border-strong)]">
                <div className="text-xs font-bold text-[var(--accent)] mb-3 uppercase tracking-wide">Teacher Institutional Profile</div>
                
                <div className="mb-3">
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Teaching Level</label>
                  <select value={teacherLevel} onChange={(e) => setTeacherLevel(e.target.value)} className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                    <option value="school">School Educator</option>
                    <option value="college">College Professor / Lecturer</option>
                  </select>
                </div>

                <div className="mb-3">
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">School / University / Institution Name</label>
                  <input
                    type="text"
                    placeholder="e.g. St. Xavier's School or IIT Bombay"
                    value={institutionName}
                    onChange={(e) => setInstitutionName(e.target.value)}
                    required
                    className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]"
                  />
                </div>

                {teacherLevel === 'school' ? (
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Board</label>
                      <select value={board} onChange={(e) => setBoard(e.target.value)} className="w-full px-2 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                        {BOARDS.map(b => <option key={b} value={b}>{b}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Grade Taught</label>
                      <select value={classesTaught} onChange={(e) => setClassesTaught(Number(e.target.value))} className="w-full px-2 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                        {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
                      </select>
                    </div>
                  </div>
                ) : (
                  <div>
                    <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Department / Subject Handled</label>
                    <input
                      type="text"
                      placeholder="e.g. Computer Science & AI, Economics"
                      value={department}
                      onChange={(e) => setDepartment(e.target.value)}
                      required
                      className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]"
                    />
                  </div>
                )}
              </div>
            )}

            {/* REGISTER FIELDS FOR STUDENT PORTAL */}
            {!isLogin && portal === 'student' && (
              <div className="bg-[var(--accent-soft)] p-4 rounded-xl mb-4 border border-[var(--border-strong)]">
                <div className="text-xs font-bold text-[var(--accent)] mb-3 uppercase tracking-wide">Student Academic Profile</div>
                
                <div className="mb-3">
                  <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Student Type</label>
                  <select value={level} onChange={(e) => setLevel(e.target.value)} className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                    <option value="school">School Student (Class 1 to 12)</option>
                    <option value="college">College / University Student</option>
                  </select>
                </div>

                {level === 'school' && (
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Board</label>
                        <select value={board} onChange={(e) => setBoard(e.target.value)} className="w-full px-2 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                          {BOARDS.map(b => <option key={b} value={b}>{b}</option>)}
                        </select>
                      </div>
                      <div>
                        <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Class (1 to 12)</label>
                        <select value={classLevel} onChange={(e) => setClassLevel(Number(e.target.value))} className="w-full px-2 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                          {CLASSES.map(c => <option key={c} value={c}>Class {c}</option>)}
                        </select>
                      </div>
                    </div>
                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Stream</label>
                      <select value={schoolStream} onChange={(e) => setSchoolStream(e.target.value)} className="w-full px-2 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                        {Object.keys(STREAMS).map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                  </div>
                )}

                {level === 'college' && (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">College Discipline / Stream</label>
                      <select value={collegeStream} onChange={(e) => handleCollegeStreamChange(e.target.value)} className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                        {COLLEGE_STREAMS.map(cs => <option key={cs} value={cs}>{cs}</option>)}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Domain / Branch Specialization</label>
                      <select value={collegeDomain} onChange={(e) => setCollegeDomain(e.target.value)} className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                        {(COLLEGE_DOMAINS[collegeStream] || []).map(cd => <option key={cd} value={cd}>{cd}</option>)}
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1">Current Semester</label>
                      <select value={semester} onChange={(e) => setSemester(Number(e.target.value))} className="w-full px-3 py-2 rounded-md border border-[var(--border-strong)] text-[13px] outline-none bg-[var(--surface)]">
                        {COLLEGE_SEMESTERS.map(s => <option key={s} value={s}>Semester {s}</option>)}
                      </select>
                    </div>
                  </div>
                )}
              </div>
            )}
            
            <div className="mb-3.5">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Email address</label>
              <input
                type="email"
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-3.5 py-[10px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--accent)]"
              />
            </div>
            
            <div className="mb-4">
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Password</label>
              <div className="relative flex items-center">
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full pl-3.5 pr-10 py-[10px] rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] text-sm focus:outline-none focus:border-[var(--accent)]"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 text-[var(--text-soft)] hover:text-[var(--text)] focus:outline-none"
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className={`w-full py-[11px] rounded-lg bg-[var(--accent)] text-[#F7F8F4] font-semibold text-sm hover:bg-[var(--accent-dim)] transition-colors ${!isLogin ? 'mb-4 mt-2' : ''}`}
            >
              {loading ? 'Processing...' : isLogin ? 'Sign in' : 'Create account'}
            </button>
            
            <div className="mt-5 text-center text-xs text-[var(--text-soft)]">
              {isLogin ? "Don't have an account? " : "Already registered? "}
              <button 
                type="button" 
                onClick={() => { setIsLogin(!isLogin); setErrorMsg('') }} 
                className="text-[var(--accent)] font-bold hover:underline ml-1"
              >
                {isLogin ? 'Create one' : 'Sign in instead'}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  )
}

