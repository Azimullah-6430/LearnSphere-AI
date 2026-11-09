import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import mermaid from 'mermaid'
import {
  Compass,
  Sprout,
  Sun,
  Droplets,
  Layers,
  Wrench,
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  HelpCircle,
  ShieldAlert,
  BookOpen,
  Eye,
  Lightbulb,
  TreePine,
  Home,
  Camera,
  Image as ImageIcon,
  X,
  RefreshCw,
  Check,
  ShieldCheck,
  Target,
  ArrowRight,
  ArrowLeft,
  Info,
  Wifi,
  WifiOff,
  History,
  Trash2,
  Edit3,
  Save,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  FileText,
  Code,
  Copy,
  Terminal,
  Play,
  BookOpenCheck,
  GraduationCap,
  User,
  Calculator,
  CheckSquare,
  Award,
  Circle,
  SlidersHorizontal,
  RotateCcw,
  Zap,
  Send,
  MessageSquare,
  Bot
} from 'lucide-react'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: 'inherit'
})

// ── 7 Guided Journey Steps ──────────────────────────────────────────────────
const JOURNEY_STEPS = [
  { id: 1, label: 'Subject', fullTitle: 'Select Subject', icon: BookOpen, desc: 'Choose validated subject' },
  { id: 2, label: 'Topic & Setup', fullTitle: 'Choose Topic & Setup', icon: Layers, desc: 'Select topic & surroundings' },
  { id: 3, label: 'Concept', fullTitle: 'Understand the Concept', icon: Lightbulb, desc: 'Clear conceptual explanation' },
  { id: 4, label: 'Applications', fullTitle: 'Real-World Applications', icon: Sun, desc: 'Everyday life & industry' },
  { id: 5, label: 'Activity', fullTitle: 'Practical Activities', icon: Wrench, desc: 'Hands-on steps & experiment' },
  { id: 6, label: 'Check', fullTitle: 'Check Understanding', icon: HelpCircle, desc: 'Answer checkpoint questions' },
  { id: 7, label: 'Complete', fullTitle: 'Complete & Continue', icon: Award, desc: 'Summary & progress tracking' }
]

const RESOURCE_ENVIRONMENTS = [
  { id: 'All Local Resources', label: 'Everyday Surroundings', icon: Compass },
  { id: 'Household & Crafts', label: 'Paper & Household Objects', icon: Home },
  { id: 'Sunlight & Shadows', label: 'Sunlight & Outdoors', icon: Sun },
  { id: 'Plants & Bio Resources', label: 'Leaves & Natural Materials', icon: TreePine },
  { id: 'Village Water & Wells', label: 'Water & Common Cups', icon: Droplets },
  { id: 'Farmland & Soil', label: 'Soil, Sand & Rocks', icon: Sprout },
  { id: 'Bicycle & Simple Tools', label: 'Rulers & Common Tools', icon: Wrench },
]

const QUICK_MATERIAL_TAGS = [
  'Notebook Paper & Pencil',
  'Ruler & Eraser',
  'Clean Water & Cup',
  'Coins or Bottle Caps',
  'Cotton Thread or String',
  'Cardboard or Carton',
  'Fallen Leaves or Petals',
  'Common Salt or Sugar',
  'Small Pebbles or Sand',
  'Sunlight & Shadows',
  'Kitchen Bowl or Spoon',
  'Free Software or Calculator'
]

const EXPLANATION_LANGUAGES = [
  { id: 'English', label: 'English' },
  { id: 'Hindi', label: 'Hindi (हिन्दी)' },
  { id: 'Tamil', label: 'Tamil (தமிழ்)' },
  { id: 'Telugu', label: 'Telugu (తెలుగు)' },
  { id: 'Bengali', label: 'Bengali (বাংলা)' },
  { id: 'Marathi', label: 'Marathi (मराठी)' },
  { id: 'Gujarati', label: 'Gujarati (ગુજરાતી)' },
  { id: 'Kannada', label: 'Kannada (ಕನ್ನಡ)' },
  { id: 'Malayalam', label: 'Malayalam (മലയാളം)' },
  { id: 'Urdu', label: 'Urdu (اردو)' },
  { id: 'Punjabi', label: 'Punjabi (ਪੰਜਾਬੀ)' },
  { id: 'Odia', label: 'Odia (ଓଡ଼ିଆ)' }
]

const LEARNING_METHODS = [
  { id: 'auto', label: 'Auto (Optimal Strategy)', icon: Sparkles, desc: 'AI dynamically picks best approach' },
  { id: 'practical', label: 'Hands-on Activity', icon: Wrench, desc: 'Experiment with low/zero-cost items' },
  { id: 'real_world', label: 'Real-World Example', icon: Sun, desc: 'Relatable everyday applications' },
  { id: 'worked_example', label: 'Worked Problem', icon: Target, desc: 'Step-by-step math or logic solution' },
  { id: 'coding', label: 'Code & Logic Task', icon: Code, desc: 'Algorithms & executable code' },
  { id: 'simulation', label: 'Thought Simulation', icon: Eye, desc: 'Visual intuition & thought experiment' },
  { id: 'theory', label: 'Reading & Analysis', icon: BookOpen, desc: 'Structured conceptual reading' }
]

// ── KaTeX & Mermaid Rendering Helpers ───────────────────────────────────────
function renderKatexMath(mathStr, isBlock = false) {
  try {
    return katex.renderToString(mathStr, {
      displayMode: isBlock,
      throwOnError: false
    })
  } catch {
    return mathStr
  }
}

function formatInlineText(text) {
  if (!text) return null
  const parts = []
  let remaining = String(text)

  while (remaining.length > 0) {
    const mathMatch = remaining.match(/^([\s\S]*?)\$(.+?)\$([\s\S]*)$/)
    const boldMatch = remaining.match(/^([\s\S]*?)\*\*(.+?)\*\*([\s\S]*)$/)
    const codeMatch = remaining.match(/^([\s\S]*?)`([^`]+)`([\s\S]*)$/)
    const italicMatch = remaining.match(/^([\s\S]*?)\*([^*]+)\*([\s\S]*)$/)

    const matches = [
      mathMatch && !mathMatch[1].endsWith('\\') ? { type: 'math', index: mathMatch[1].length, match: mathMatch } : null,
      boldMatch ? { type: 'bold', index: boldMatch[1].length, match: boldMatch } : null,
      codeMatch ? { type: 'code', index: codeMatch[1].length, match: codeMatch } : null,
      italicMatch ? { type: 'italic', index: italicMatch[1].length, match: italicMatch } : null
    ].filter(Boolean).sort((a, b) => a.index - b.index)

    if (matches.length === 0) {
      parts.push(remaining)
      break
    }

    const first = matches[0]
    const pre = first.match[1]
    const content = first.match[2]
    const post = first.match[3]

    if (pre) parts.push(pre)

    if (first.type === 'math') {
      const html = renderKatexMath(content, false)
      parts.push(
        <span
          key={parts.length}
          className="inline-math px-0.5 font-serif text-[var(--accent)] font-medium"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )
    } else if (first.type === 'bold') {
      parts.push(<strong key={parts.length} className="font-bold text-[var(--text)]">{formatInlineText(content)}</strong>)
    } else if (first.type === 'code') {
      parts.push(
        <code key={parts.length} className="px-1.5 py-0.5 rounded bg-[var(--surface-alt)] border border-[var(--border)] font-mono text-xs text-[var(--accent)]">
          {content}
        </code>
      )
    } else if (first.type === 'italic') {
      parts.push(<em key={parts.length} className="italic text-[var(--text-soft)]">{content}</em>)
    }

    remaining = post
  }

  return parts
}

function MermaidRenderer({ code }) {
  const [svgHtml, setSvgHtml] = useState('')
  const [hasError, setHasError] = useState(false)
  const chartId = useMemo(() => `lfa-mermaid-${Math.random().toString(36).substring(2, 9)}`, [])

  useEffect(() => {
    let active = true
    const renderChart = async () => {
      try {
        setHasError(false)
        let chartCode = (code || '').trim()
        if (!chartCode) return

        const validTypes = ['flowchart', 'graph', 'sequencediagram', 'classdiagram', 'statediagram', 'erdiagram', 'pie', 'gantt', 'mindmap', 'timeline']
        const firstLine = chartCode.split('\n')[0].trim().toLowerCase()
        if (!validTypes.some(t => firstLine.startsWith(t))) {
          chartCode = `flowchart TD\n${chartCode}`
        }

        const { svg } = await mermaid.render(chartId, chartCode)
        if (active) setSvgHtml(svg)
      } catch (err) {
        console.warn('Mermaid rendering issue:', err)
        if (active) setHasError(true)
      }
    }

    renderChart()
    return () => { active = false }
  }, [code, chartId])

  if (hasError || !svgHtml) {
    return (
      <div className="my-3 rounded-xl border border-[var(--border)] overflow-hidden bg-[var(--surface-alt)] p-4 text-xs font-mono whitespace-pre text-[var(--text-soft)]">
        {code}
      </div>
    )
  }

  return (
    <div className="my-4 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 sm:p-6 shadow-xs overflow-x-auto flex justify-center items-center">
      <div
        className="mermaid-wrapper max-w-full [&>svg]:max-w-full [&>svg]:h-auto"
        dangerouslySetInnerHTML={{ __html: svgHtml }}
      />
    </div>
  )
}

export default function LearnAnywhere() {
  const { user, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, units: allUnits } = useAuthoritativeCurriculum()
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)
  const requestIdRef = useRef(0)
  const abortControllerRef = useRef(null)

  // Guided Stepper State (Steps 1 to 7)
  const [currentStep, setCurrentStep] = useState(1)
  const [completedJourneySteps, setCompletedJourneySteps] = useState({})

  // Subject and Topic Selections
  const [selectedSubject, setSelectedSubject] = useState(subjects[0] || '')
  const [selectedTopic, setSelectedTopic] = useState('')
  const [learningMethod, setLearningMethod] = useState('auto')
  const [customMaterials, setCustomMaterials] = useState('')
  const [constraintMode, setConstraintMode] = useState('strict_only')
  const [selectedEnv, setSelectedEnv] = useState('All Local Resources')
  const [difficulty, setDifficulty] = useState('Medium')
  const [preferredLanguage, setPreferredLanguage] = useState('English')
  const [imagePreview, setImagePreview] = useState(null)
  const [imageData, setImageData] = useState('')
  const [showSetupPanel, setShowSetupPanel] = useState(false)

  // Activity Execution State
  const [loading, setLoading] = useState(false)
  const [activity, setActivity] = useState(null)
  const [completedSteps, setCompletedSteps] = useState({})
  const [checkedMaterials, setCheckedMaterials] = useState({})
  const [revealedQuestions, setRevealedQuestions] = useState({})
  const [showMaterialAlternatives, setShowMaterialAlternatives] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [profileIncomplete, setProfileIncomplete] = useState(false)

  // On-Demand Student Action State
  const [actionLoading, setActionLoading] = useState(false)
  const [actionResult, setActionResult] = useState(null)
  const [copyCodeSuccess, setCopyCodeSuccess] = useState(false)
  const [adaptiveLevel, setAdaptiveLevel] = useState('medium') // 'simple' | 'detailed' | 'quick' | 'medium'
  const [conversationHistory, setConversationHistory] = useState([])
  const [studentDoubt, setStudentDoubt] = useState('')
  const [missingMaterialInput, setMissingMaterialInput] = useState('')

  // Interactive Understanding Evaluation State
  const [userAnswers, setUserAnswers] = useState({})
  const [evaluations, setEvaluations] = useState({})
  const [evaluatingQ, setEvaluatingQ] = useState({})
  const [attemptsCount, setAttemptsCount] = useState({})
  const [additionalPractice, setAdditionalPractice] = useState([])
  const [loadingPractice, setLoadingPractice] = useState(false)
  const [saveStatus, setSaveStatus] = useState('idle')

  // Reflection in Step 7
  const [studentNotes, setStudentNotes] = useState('')
  const [savingNotes, setSavingNotes] = useState(false)
  const [notesSavedSuccess, setNotesSavedSuccess] = useState(false)

  // Activity History State
  const [showHistoryModal, setShowHistoryModal] = useState(false)
  const [historyList, setHistoryList] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyPage, setHistoryPage] = useState(1)
  const [historyTotal, setHistoryTotal] = useState(0)
  const [historyHasMore, setHistoryHasMore] = useState(false)
  const [editingReflectionId, setEditingReflectionId] = useState(null)
  const [reflectionText, setReflectionText] = useState('')
  const [savingReflection, setSavingReflection] = useState(false)

  // Connectivity Status
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)

  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    if (!showHistoryModal) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setShowHistoryModal(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [showHistoryModal])

  const loadHistory = useCallback(async (page = 1) => {
    setHistoryLoading(true)
    try {
      const res = await api.getLearnAnywhereHistory({ page, limit: 10 })
      if (res && res.success && Array.isArray(res.history)) {
        setHistoryList(res.history)
        setHistoryPage(res.page || page)
        setHistoryTotal(res.total || 0)
        setHistoryHasMore(!!res.has_more)
      }
    } catch (err) {
      console.warn('Could not load activity history:', err)
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  const handleSaveReflection = async (activityId, text) => {
    setSavingReflection(true)
    try {
      const res = await api.updateLearnAnywhereHistory(activityId, { reflections: text })
      if (res && res.success) {
        setHistoryList(prev => prev.map(item => item.activity_id === activityId ? { ...item, reflections: text } : item))
        setEditingReflectionId(null)
      }
    } catch (err) {
      console.warn('Could not update reflection:', err)
    } finally {
      setSavingReflection(false)
    }
  }

  const handleDeleteHistoryItem = async (activityId) => {
    if (typeof window !== 'undefined' && !window.confirm('Are you sure you want to delete this activity record from your history?')) return
    try {
      const res = await api.deleteLearnAnywhereHistory(activityId)
      if (res && res.success) {
        setHistoryList(prev => prev.filter(item => item.activity_id !== activityId))
        setHistoryTotal(prev => Math.max(0, prev - 1))
      }
    } catch (err) {
      console.warn('Could not delete history item:', err)
    }
  }

  const handleRevisitActivity = (item) => {
    if (item.activity) {
      setActivity(item.activity)
      if (item.subject) setSelectedSubject(item.subject)
      if (item.topic) setSelectedTopic(item.topic)
      setShowHistoryModal(false)
      setCurrentStep(3) // Jump to Step 3 (Concept)
    }
  }

  // Clear transient activity content
  const clearActivityState = useCallback(() => {
    setActivity(null)
    setCompletedSteps({})
    setCheckedMaterials({})
    setRevealedQuestions({})
    setUserAnswers({})
    setEvaluations({})
    setAttemptsCount({})
    setAdditionalPractice([])
    setActionResult(null)
    setErrorMsg('')
    setStudentNotes('')
    setConversationHistory([])
    setStudentDoubt('')
    setMissingMaterialInput('')
    setAdaptiveLevel('medium')
  }, [])

  // User-scoped cache loader & restore
  useEffect(() => {
    setActivity(null)
    setCompletedSteps({})
    setCheckedMaterials({})
    setRevealedQuestions({})
    setUserAnswers({})
    setEvaluations({})
    setAttemptsCount({})
    setAdditionalPractice([])
    setHistoryList([])
    setActionResult(null)

    if (!user?.id && !user?._id && !user?.email) return
    const currentUid = String(user?.id || user?._id || user?.email)
    const cacheKey = `learn_anywhere_activity_${currentUid}`
    let restoredFromCache = false

    const isSchool = user?.student_type === 'SCHOOL' || user?.level === 'school' || !!user?.grade_level || !!user?.grade
    const expectedLevel = isSchool ? 'SCHOOL' : 'COLLEGE'

    try {
      const rawCache = sessionStorage.getItem(cacheKey)
      if (rawCache) {
        const parsed = JSON.parse(rawCache)
        if (parsed && parsed.user_id === currentUid && parsed.activity) {
          const actSub = parsed.activity?.academic_grounding?.subject || parsed.activity?.subject
          const actLevel = (parsed.activity?.student_type || parsed.activity?.academic_level || '').toUpperCase()
          const isLevelMismatch = actLevel && actLevel !== expectedLevel
          const isSubMismatch = subjects.length > 0 && actSub && !subjects.includes(actSub)
          if (isSubMismatch || isLevelMismatch) {
            sessionStorage.removeItem(cacheKey)
          } else {
            setActivity(parsed.activity)
            if (actSub) setSelectedSubject(actSub)
            if (parsed.activity?.academic_grounding?.topic || parsed.activity?.topic) {
              setSelectedTopic(parsed.activity?.academic_grounding?.topic || parsed.activity?.topic)
            }
            if (parsed.completedSteps) setCompletedSteps(parsed.completedSteps)
            restoredFromCache = true
            // If user has active activity, advance to Step 3
            setCurrentStep(3)
          }
        }
      }
    } catch (e) {
      console.warn('Could not read user activity cache', e)
    }

    if (!restoredFromCache && navigator.onLine) {
      const activeQuerySub = selectedSubject || (subjects.length > 0 ? subjects[0] : '')
      api.getLearnAnywhereSession(activeQuerySub ? { subject: activeQuerySub } : {}).then(res => {
        if (res && res.success && res.activity) {
          const actSub = res.activity?.academic_grounding?.subject || res.activity?.subject || res.subject
          const actLevel = (res.activity?.student_type || res.activity?.academic_level || '').toUpperCase()
          const isLevelMismatch = actLevel && actLevel !== expectedLevel
          const isSubMismatch = subjects.length > 0 && actSub && !subjects.includes(actSub)
          if (!isSubMismatch && !isLevelMismatch) {
            setActivity(res.activity)
            if (actSub && (!subjects.length || subjects.includes(actSub))) setSelectedSubject(actSub)
            if (res.topic || res.activity?.topic) setSelectedTopic(res.topic || res.activity?.topic)
            setCurrentStep(3)
          }
        }
      }).catch(err => {
        console.warn('Session restoration check skipped:', err)
      })
    }
  }, [user, subjects])

  // Sync selectedSubject with authoritative subjects
  useEffect(() => {
    if (subjects.length > 0 && (!selectedSubject || !subjects.includes(selectedSubject))) {
      setSelectedSubject(subjects[0])
      clearActivityState()
    }
  }, [subjects, selectedSubject, clearActivityState])

  // Extract syllabus topics grouped by unit/chapter
  const groupedUnits = useMemo(() => {
    if (!selectedSubject) return []
    const groups = []
    const chaptersDict = curriculum?.chapters || curriculum?.units || allUnits || {}
    if (chaptersDict[selectedSubject] && Array.isArray(chaptersDict[selectedSubject])) {
      chaptersDict[selectedSubject].forEach((u, uIdx) => {
        if (typeof u === 'object' && u !== null) {
          const uTitle = u.name || `Unit ${uIdx + 1}`
          const tops = []
          if (u.name) tops.push(u.name)
          if (Array.isArray(u.concepts)) tops.push(...u.concepts)
          groups.push({ unitName: uTitle, topics: Array.from(new Set(tops.filter(Boolean))) })
        } else if (typeof u === 'string') {
          groups.push({ unitName: `Unit ${uIdx + 1}`, topics: [u] })
        }
      })
    }

    if (groups.length === 0 && Array.isArray(curriculum?.subjects)) {
      const subObj = curriculum.subjects.find(s =>
        (typeof s === 'object' && s.name === selectedSubject) || s === selectedSubject
      )
      if (subObj && typeof subObj === 'object') {
        if (Array.isArray(subObj.units)) {
          subObj.units.forEach((u, uIdx) => {
            if (typeof u === 'object' && u !== null) {
              const uTitle = u.name || `Unit ${uIdx + 1}`
              const tops = []
              if (u.name) tops.push(u.name)
              if (Array.isArray(u.concepts)) tops.push(...u.concepts)
              groups.push({ unitName: uTitle, topics: Array.from(new Set(tops.filter(Boolean))) })
            } else if (typeof u === 'string') {
              groups.push({ unitName: `Unit ${uIdx + 1}`, topics: [u] })
            }
          })
        } else if (Array.isArray(subObj.topics) && subObj.topics.length > 0) {
          groups.push({ unitName: 'Core Topics', topics: subObj.topics })
        }
      }
    }

    return groups
  }, [selectedSubject, curriculum, allUnits])

  // Validated flat topics
  const validatedSubjectTopics = useMemo(() => {
    if (!selectedSubject) return []
    const all = []
    groupedUnits.forEach(g => all.push(...g.topics))
    if (all.length > 0) return Array.from(new Set(all.filter(Boolean)))

    const chaptersDict = curriculum?.chapters || curriculum?.units || allUnits || {}
    if (chaptersDict[selectedSubject] && Array.isArray(chaptersDict[selectedSubject])) {
      chaptersDict[selectedSubject].forEach(u => {
        if (typeof u === 'object' && u !== null) {
          if (u.name) all.push(u.name)
          if (Array.isArray(u.concepts)) all.push(...u.concepts)
        } else if (typeof u === 'string') {
          all.push(u)
        }
      })
    }
    return Array.from(new Set(all.filter(Boolean)))
  }, [selectedSubject, groupedUnits, curriculum, allUnits])

  // Active Subject metadata
  const activeSubjectObj = useMemo(() => {
    if (!curriculum?.subjects) return null
    return (curriculum.subjects || []).find(s =>
      (typeof s === 'object' && s.name === selectedSubject) || s === selectedSubject
    )
  }, [curriculum, selectedSubject])

  const activeSubjectId = useMemo(() => {
    if (typeof activeSubjectObj === 'object' && activeSubjectObj) {
      return activeSubjectObj.subject_id || activeSubjectObj.subjectId || activeSubjectObj.id || activeSubjectObj.code || ''
    }
    return ''
  }, [activeSubjectObj])

  const activeSyllabusId = curriculum?.syllabus_id || curriculum?.syllabusId || ''

  // Subject selection handler
  const handleSubjectSelect = useCallback((newSub) => {
    if (newSub === selectedSubject) {
      setCurrentStep(2)
      return
    }
    setSelectedSubject(newSub)
    clearActivityState()
    setCurrentStep(2)
  }, [selectedSubject, clearActivityState])

  // Topic selection handler
  const handleTopicSelect = useCallback((newTopic) => {
    if (newTopic === selectedTopic) return
    setSelectedTopic(newTopic)
    clearActivityState()
  }, [selectedTopic, clearActivityState])

  // Set default topic if not set
  useEffect(() => {
    if (validatedSubjectTopics.length > 0 && (!selectedTopic || !validatedSubjectTopics.includes(selectedTopic))) {
      setSelectedTopic(validatedSubjectTopics[0])
    }
  }, [validatedSubjectTopics, selectedTopic])

  // Handle Image Upload
  const handleImageChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/bmp']
    if (file.type && !allowedTypes.includes(file.type.toLowerCase())) {
      setErrorMsg('Unsupported image format. Please upload JPEG, PNG, WEBP, GIF, or BMP format.')
      return
    }

    if (file.size > 5 * 1024 * 1024) {
      setErrorMsg('Image size exceeds 5MB limit. Please upload a photo smaller than 5MB.')
      return
    }

    setErrorMsg('')
    const reader = new FileReader()
    reader.onload = () => {
      setImagePreview(reader.result)
      setImageData(reader.result)
    }
    reader.readAsDataURL(file)
  }

  const handleRemoveImage = () => {
    setImagePreview(null)
    setImageData('')
  }

  const handleAddMaterialTag = (tag) => {
    if (customMaterials.toLowerCase().includes(tag.toLowerCase())) return
    setCustomMaterials(prev => prev.trim() ? `${prev.trim()}, ${tag}` : tag)
  }

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

  // Generate Activity
  const handleGenerateActivity = useCallback(async () => {
    if (!selectedSubject || loading) return
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setErrorMsg('Internet connection is required to generate new AI activities. Your previously loaded activity remains readable below.')
      return
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    const controller = new AbortController()
    abortControllerRef.current = controller

    requestIdRef.current += 1
    const currentRequestId = requestIdRef.current

    setActivity(null)
    setLoading(true)
    setErrorMsg('')
    setProfileIncomplete(false)
    setCompletedSteps({})
    setCheckedMaterials({})
    setRevealedQuestions({})
    setUserAnswers({})
    setEvaluations({})
    setEvaluatingQ({})
    setAttemptsCount({})
    setAdditionalPractice([])
    setSaveStatus('idle')

    const currentUid = String(user?.id || user?._id || user?.email || 'anon')
    const activeTopicTarget = selectedTopic || validatedSubjectTopics[0] || 'Core Practical Concept'
    const idempotencyKey = `lfa_req_${currentUid}_${selectedSubject.replace(/\s+/g, '_')}_${activeTopicTarget.replace(/\s+/g, '_')}_${Date.now()}`

    try {
      const res = await api.generateLearnAnywhere({
        subject: selectedSubject,
        subject_id: activeSubjectId || undefined,
        topic: activeTopicTarget,
        learning_method: learningMethod,
        resource_category: selectedEnv,
        difficulty,
        preferred_language: preferredLanguage,
        custom_materials: customMaterials.trim() || undefined,
        constraint_mode: constraintMode,
        image_data: imageData || undefined,
        syllabus_id: activeSyllabusId || undefined,
        idempotency_key: idempotencyKey
      }, { signal: controller.signal })

      if (currentRequestId !== requestIdRef.current || controller.signal.aborted) {
        return
      }

      if (res && res.success && res.activity) {
        const returnedSub = String(res.activity?.academic_grounding?.subject || res.activity?.subject || res.subject || '').trim().toLowerCase()
        if (returnedSub && returnedSub !== selectedSubject.trim().toLowerCase()) {
          setActivity(null)
          setErrorMsg(`Returned activity did not match requested subject '${selectedSubject}'. Please click Retry.`)
          return
        }

        setActivity(res.activity)
        setCompletedJourneySteps(prev => ({ ...prev, 1: true, 2: true, 3: true }))
        setCurrentStep(3) // Advance to Step 3: Understand Concept

        if (currentUid && currentUid !== 'anon') {
          try {
            sessionStorage.setItem(`learn_anywhere_activity_${currentUid}`, JSON.stringify({
              user_id: currentUid,
              activity: res.activity,
              completedSteps: {},
              timestamp: new Date().toISOString()
            }))
          } catch (e) {
            console.warn('Could not save user activity cache', e)
          }
        }

        if (recordActivity) {
          recordActivity('activity', `Generated Learn from Anywhere experiment: ${res.activity.title || selectedSubject}`, {
            subject: selectedSubject,
            topic: activeTopicTarget,
            syllabus_id: activeSyllabusId
          })
        }
      } else {
        setActivity(null)
        if (res?.profile_incomplete || res?.action_required === 'complete_profile' || /profile.*incomplete|complete.*profile/i.test(res?.error || '')) {
          setProfileIncomplete(true)
          setErrorMsg(res?.error || res?.message || 'Your student profile is incomplete. Please update your academic classification in Settings.')
        } else {
          setErrorMsg(res?.error || 'Failed to design practical activity. Please check your connection and retry.')
        }
      }
    } catch (err) {
      if (err?.name === 'AbortError' || controller.signal.aborted) return
      if (currentRequestId !== requestIdRef.current) return
      setActivity(null)
      if (err?.response?.data?.profile_incomplete || /profile.*incomplete|complete.*profile/i.test(err?.message || '')) {
        setProfileIncomplete(true)
      }
      setErrorMsg(err?.message || 'Generation timed out or connection was interrupted. Please click Retry.')
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [selectedSubject, activeSubjectId, selectedTopic, validatedSubjectTopics, selectedEnv, difficulty, preferredLanguage, customMaterials, constraintMode, imageData, activeSyllabusId, recordActivity, user, loading, learningMethod])

  // Save Progress
  const handleSaveProgress = useCallback(async (currentCompletedSteps = completedSteps, currentEvals = evaluations) => {
    if (!activity) return
    setSaveStatus('saving')
    try {
      const attemptsList = Object.keys(currentEvals).map(k => ({
        question_index: parseInt(k, 10),
        is_correct: currentEvals[k].is_correct,
        score: currentEvals[k].score,
        error_type: currentEvals[k].error_type,
        attempt_number: attemptsCount[k] || 1,
        timestamp: new Date().toISOString()
      }))
      const completedList = Object.keys(currentCompletedSteps).filter(k => currentCompletedSteps[k]).map(Number)

      const res = await api.saveLearnAnywhereProgress({
        activity_id: activity.activity_id || activity.id || `act_${selectedSubject}`,
        syllabus_id: activeSyllabusId,
        subject: selectedSubject,
        topic: selectedTopic || 'Syllabus Topic',
        attempts: attemptsList,
        completed_steps: completedList,
        total_steps: activity.steps?.length || 0,
        reflections: studentNotes || undefined
      })
      if (res && res.success) {
        setSaveStatus('saved')
      } else {
        setSaveStatus('idle')
      }
    } catch {
      setSaveStatus('idle')
    }
  }, [activity, selectedSubject, selectedTopic, activeSyllabusId, completedSteps, evaluations, attemptsCount, studentNotes])

  // Save Student Notes in Step 7
  const handleSaveNotes = async () => {
    if (!activity || !studentNotes.trim()) return
    setSavingNotes(true)
    setNotesSavedSuccess(false)
    try {
      await handleSaveProgress(completedSteps, evaluations)
      setNotesSavedSuccess(true)
      setTimeout(() => setNotesSavedSuccess(false), 3000)
    } finally {
      setSavingNotes(false)
    }
  }

  // Toggle step completion
  const toggleStep = (index) => {
    const updated = {
      ...completedSteps,
      [index]: !completedSteps[index]
    }
    setCompletedSteps(updated)
    handleSaveProgress(updated, evaluations)
  }

  // Toggle material item
  const toggleMaterial = (index) => {
    setCheckedMaterials(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  // Submit Answer for Step 6 Checkpoint
  const handleSubmitAnswer = async (qIdx, qObj) => {
    const studentAns = (userAnswers[qIdx] || '').trim()
    if (!studentAns) return

    setEvaluatingQ(prev => ({ ...prev, [qIdx]: true }))
    const nextAttempt = (attemptsCount[qIdx] || 0) + 1
    setAttemptsCount(prev => ({ ...prev, [qIdx]: nextAttempt }))

    try {
      const res = await api.evaluateLearnAnywhereAnswer({
        subject: selectedSubject,
        topic: selectedTopic || 'Syllabus Topic',
        question: qObj.question,
        expected_answer: qObj.answer,
        student_answer: studentAns,
        attempt_number: nextAttempt,
        preferred_language: preferredLanguage
      })

      if (res && res.success && res.evaluation) {
        const newEval = res.evaluation
        const updatedEvals = { ...evaluations, [qIdx]: newEval }
        setEvaluations(updatedEvals)
        handleSaveProgress(completedSteps, updatedEvals)
      }
    } catch (err) {
      setErrorMsg(err?.message || 'Failed to evaluate answer. Please try submitting again.')
    } finally {
      setEvaluatingQ(prev => ({ ...prev, [qIdx]: false }))
    }
  }

  // Load Additional Practice in Step 6
  const handleLoadAdditionalPractice = async () => {
    setLoadingPractice(true)
    try {
      const res = await api.getLearnAnywhereAdditionalPractice({
        subject: selectedSubject,
        topic: selectedTopic || 'Syllabus Topic',
        preferred_language: preferredLanguage
      })
      if (res && res.success && Array.isArray(res.questions)) {
        setAdditionalPractice(res.questions)
      }
    } catch (err) {
      setErrorMsg(err?.message || 'Could not load additional practice questions.')
    } finally {
      setLoadingPractice(false)
    }
  }

  // On-demand student action in Step 3 and Step 5
  const handleStudentAction = async (actionType, options = {}) => {
    if (!selectedSubject) return
    setActionLoading(true)
    setErrorMsg('')
    try {
      const activeTopicTarget = selectedTopic || validatedSubjectTopics[0] || 'Core Concept'
      const firstQ = activity?.understanding_questions?.[0]?.question || ''
      const questionToSend = options.question || studentDoubt || firstQ
      const activeLevel = options.adaptive_level || adaptiveLevel
      const res = await api.generateLearnAnywhereAction({
        action_type: actionType,
        subject: selectedSubject,
        topic: activeTopicTarget,
        question: questionToSend,
        current_explanation: activity?.simple_explanation || activity?.scientific_principle || '',
        current_example: activity?.expected_observations || activity?.expected_observation || '',
        preferred_language: preferredLanguage,
        conversation_history: options.conversation_history || conversationHistory,
        missing_material: options.missing_material || missingMaterialInput,
        adaptive_level: activeLevel,
        activity_title: activity?.title || activity?.activity_title || '',
        activity_steps: stepsList
      })

      if (res && res.success && res.result) {
        setActionResult(res.result)
        if (actionType === 'ask_question' && questionToSend) {
          setConversationHistory(prev => [
            ...prev,
            { role: 'student', content: questionToSend },
            {
              role: 'assistant',
              title: res.result.title,
              content: res.result.content,
              diagram: res.result.mermaid_diagram,
              points: res.result.key_points
            }
          ])
          setStudentDoubt('')
        }
      } else {
        setErrorMsg(res?.error || 'Could not process assistance request. Please try again.')
      }
    } catch (err) {
      setErrorMsg(err?.message || 'Error communicating with assistant. Please try again.')
    } finally {
      setActionLoading(false)
    }
  }

  const handleCopyCode = (codeText) => {
    if (!codeText || typeof navigator === 'undefined') return
    navigator.clipboard.writeText(codeText).then(() => {
      setCopyCodeSuccess(true)
      setTimeout(() => setCopyCodeSuccess(false), 2000)
    }).catch(err => {
      console.warn('Failed to copy code:', err)
    })
  }

  const cleanStepPrefix = useCallback((text) => {
    if (!text || typeof text !== 'string') return ''
    let s = text.trim()
    for (let i = 0; i < 5; i++) {
      const prev = s
      s = s.replace(/^(?:[-*•]\s*|#{1,6}\s*)+/, '').trim()
      s = s.replace(/^(?:\*{1,2}|_{1,2})?(?:step|task|phase|instruction)\s*#?\d+\s*[:.)\-–—]?(?:\*{1,2}|_{1,2})?\s*[:.\-–—]?\s*/i, '').trim()
      s = s.replace(/^(?:\*{1,2}|_{1,2})?\d+\s*[.)](?:\*{1,2}|_{1,2})?\s*[:.\-–—]?\s*/, '').trim()
      s = s.replace(/^(?:\*{1,2}|_{1,2})?\d+\s*[-–—:]\s*(?=[A-Za-z])(?:\*{1,2}|_{1,2})?\s*/, '').trim()
      s = s.replace(/^[\[\(]\s*\d+\s*[\]\)]\s*[:.\-–—]?\s*/, '').trim()
      if (s === prev) break
    }
    return s || text.trim()
  }, [])

  const structuredExperiments = useMemo(() => {
    if (!activity) return []
    let parsedExps = []

    const rawExps = activity.experiments || activity.tasks
    if (Array.isArray(rawExps) && rawExps.length > 0) {
      parsedExps = rawExps
        .filter(exp => exp && (Array.isArray(exp.steps) ? exp.steps.length > 0 : Boolean(exp.steps)))
        .map((exp, expIdx) => {
          const rawSteps = Array.isArray(exp.steps) ? exp.steps : String(exp.steps).split('\n')
          const cleanSteps = rawSteps
            .map(s => cleanStepPrefix(String(s)))
            .filter(Boolean)
          return {
            title: exp.title || exp.name || exp.experiment_title || `Part ${expIdx + 1}`,
            steps: cleanSteps
          }
        })
        .filter(exp => exp.steps.length > 0)
    }

    if (parsedExps.length === 0) {
      const rawSteps = activity.steps || activity.procedure || activity.instructions || []
      const lines = (Array.isArray(rawSteps) ? rawSteps : [rawSteps])
        .flatMap(item => typeof item === 'string' && item.includes('\n') ? item.split('\n') : [item])
        .map(item => String(item).trim())
        .filter(Boolean)

      let currentExp = { title: '', steps: [] }
      const detectedExps = []
      let foundExpHeader = false

      for (const line of lines) {
        const headerClean = line.replace(/^(?:#{1,6}\s*|[-*•]\s*|\*{1,2}|_{1,2})/, '').trim()
        const isExpHeader = /^(?:experiment|activity|task|part)\s*(\d+|[A-Z])\s*[:.\-–—]\s*(.*)$/i.test(headerClean) ||
                            (line.startsWith('#') && /experiment|activity|task|part/i.test(line))

        if (isExpHeader) {
          foundExpHeader = true
          if (currentExp.steps.length > 0) detectedExps.push(currentExp)
          currentExp = { title: headerClean, steps: [] }
          continue
        }

        if (/^(?:materials?|safety|expected observations?|observations?|notes?)\s*[:.]/i.test(headerClean) ||
            /^#{1,6}\s*(?:materials?|safety|observations?)/i.test(line)) {
          continue
        }

        const cleaned = cleanStepPrefix(line)
        if (cleaned) currentExp.steps.push(cleaned)
      }

      if (currentExp.steps.length > 0) detectedExps.push(currentExp)

      if (foundExpHeader && detectedExps.length > 1) {
        parsedExps = detectedExps
      } else if (detectedExps.length > 0) {
        const allSteps = detectedExps.flatMap(e => e.steps)
        parsedExps = [{ title: '', steps: allSteps }]
      }
    }

    let currentStartIndex = 0
    return parsedExps.map(exp => {
      const expWithIndex = { ...exp, startIndex: currentStartIndex }
      currentStartIndex += exp.steps.length
      return expWithIndex
    })
  }, [activity, cleanStepPrefix])

  const stepsList = useMemo(() => structuredExperiments.flatMap(exp => exp.steps), [structuredExperiments])
  const totalSteps = stepsList.length || activity?.steps?.length || 0
  const completedCount = Object.values(completedSteps).filter(Boolean).length

  const isCodingTask = useMemo(() => {
    if (!activity) return false
    return Boolean(
      activity.coding_task?.is_coding_topic ||
      activity.code_snippet ||
      activity.coding_task?.code ||
      activity.coding_task?.code_snippet ||
      activity.demonstration_type === 'code_and_logic_simulation' ||
      activity.demonstration_type === 'coding_task' ||
      /coding|software|algorithm|python|program|data structure/i.test(`${activity.subject || ''} ${activity.topic || ''}`)
    )
  }, [activity])

  const cleanMaterialsList = useMemo(() => {
    if (!activity) return []
    if (isCodingTask) {
      const raw = activity.materials_student_has || activity.local_materials || []
      const list = (Array.isArray(raw) ? raw : [raw]).filter(Boolean)
      const filtered = list.filter(m => !/soil|sand|matka|leaf|bicycle|clay|water & glass|charcoal|pebbles/i.test(m))
      if (filtered.length > 0) return filtered
      return ['Python 3 or browser IDE', 'Text editor or terminal', 'Paper & pen for trace table']
    }
    const raw = activity.materials_student_has || activity.local_materials || []
    return (Array.isArray(raw) ? raw : [raw]).filter(Boolean)
  }, [activity, isCodingTask])

  const learningObjective = useMemo(() => {
    if (!activity) return ''
    if (activity.learning_objective) return activity.learning_objective
    if (Array.isArray(activity.learning_objectives) && activity.learning_objectives[0]) {
      return activity.learning_objectives[0]
    }
    return `Understand the core principles and practical behavior of ${selectedTopic || activity.topic || selectedSubject}.`
  }, [activity, selectedTopic, selectedSubject])

  const resultOrExampleText = useMemo(() => {
    if (!activity) return ''
    if (activity.expected_observations || activity.expected_observation) {
      return activity.expected_observations || activity.expected_observation
    }
    if (activity.worked_example || activity.worked_solution) {
      return activity.worked_example || activity.worked_solution
    }
    if (activity.coding_task?.expected_output) {
      return `Expected Output:\n${activity.coding_task.expected_output}`
    }
    return activity.simple_explanation || 'Observe the expected change or completed solution output.'
  }, [activity])

  const questionsToShow = useMemo(() => {
    if (!activity) return []
    const qList = activity.understanding_questions
    if (Array.isArray(qList) && qList.length > 0) return qList.slice(0, 3)
    if (activity.reflection_task || activity.reflection_question) {
      return [{
        question: activity.reflection_task || activity.reflection_question,
        answer: activity.simple_explanation || 'Consider how parameters change the final observation.',
        explanation: activity.simple_explanation || ''
      }]
    }
    return []
  }, [activity])

  const safetyText = useMemo(() => {
    const raw = (activity?.safety_precautions || activity?.safety_notes || '').trim()
    if (!raw || /^(none|n\/a|not applicable|no special precautions|safe|no precautions needed)$/i.test(raw)) return ''
    return raw
  }, [activity])

  const limitationText = useMemo(() => {
    const raw = (activity?.limitations_and_misconceptions || activity?.practical_limitation || '').trim()
    if (!raw || /^(none|n\/a|not applicable|no limitations)$/i.test(raw)) return ''
    return raw
  }, [activity])

  // Count remaining topics for this subject
  const currentTopicIndex = validatedSubjectTopics.indexOf(selectedTopic)
  const remainingTopicsCount = Math.max(0, validatedSubjectTopics.length - (currentTopicIndex >= 0 ? currentTopicIndex + 1 : 0))

  // Move to next topic handler
  const handleLearnNextTopic = () => {
    if (currentTopicIndex >= 0 && currentTopicIndex + 1 < validatedSubjectTopics.length) {
      const nextTop = validatedSubjectTopics[currentTopicIndex + 1]
      setSelectedTopic(nextTop)
      clearActivityState()
      setCurrentStep(2)
    } else {
      setCurrentStep(1)
    }
  }

  // Teacher Guard
  if (user?.role === 'teacher') {
    return (
      <div className="p-8 max-w-lg mx-auto text-center space-y-4 my-12 bg-[var(--surface)] border border-[var(--border)] rounded-2xl shadow-sm">
        <ShieldAlert size={48} className="mx-auto text-red-500" />
        <h2 className="text-lg font-black text-[var(--text)]">Access Denied</h2>
        <p className="text-xs text-[var(--text-soft)] leading-relaxed">
          Learn from Anywhere is an offline-capable student practical discovery tool reserved exclusively for Student Portal accounts. Teacher accounts cannot access student learning activities.
        </p>
      </div>
    )
  }

  // Curriculum Gate
  if (!hasValidCurriculum || subjects.length === 0) {
    return (
      <div className="space-y-6">
        <PageHead
          title="Learn from Anywhere"
          action={
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
              <Sprout size={13} className="text-emerald-500" /> Rural & Village Learning
            </span>
          }
        />
        <CurriculumReviewNotice
          curriculum={curriculum}
          featureName="Learn from Anywhere"
          onOpenSyllabusModal={() => setIsSyllabusModalOpen(true)}
        />
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Page Header */}
      <PageHead
        title="Learn from Anywhere"
        subtitle="Turn your everyday surroundings into hands-on science, engineering, and logic discoveries aligned with your syllabus."
        action={
          <div className="flex items-center gap-2 flex-wrap">
            <button
              type="button"
              onClick={() => {
                setShowHistoryModal(true)
                loadHistory(1)
              }}
              className="px-3 py-1.5 bg-[var(--surface-alt)] hover:bg-[var(--surface)] text-[var(--text)] border border-[var(--border)] rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
            >
              <History size={14} className="text-[var(--accent)]" />
              <span>Activity History</span>
            </button>
            {isOnline ? (
              <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                <Wifi size={12} className="text-emerald-500" /> Data-Saver Ready
              </span>
            ) : (
              <span className="px-3 py-1 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                <WifiOff size={12} className="text-amber-500" /> Offline Mode
              </span>
            )}
          </div>
        }
      />

      {/* Offline Alert Banner */}
      {!isOnline && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-300 text-xs font-semibold flex items-center gap-2.5 animate-fadeIn">
          <WifiOff size={16} className="text-amber-500 shrink-0" />
          <div className="flex-1 leading-relaxed">
            <strong>Offline Reading Mode: </strong>
            Your connection is currently unavailable. Your previously loaded activities and steps remain fully interactive. Reconnect to generate new topics.
          </div>
        </div>
      )}

      {/* ── 7-Step Guided Stepper ── */}
      <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-3 md:p-4 shadow-xs">
        {/* Desktop Stepper */}
        <div className="hidden lg:grid grid-cols-7 gap-2">
          {JOURNEY_STEPS.map((step) => {
            const isCurrent = currentStep === step.id
            const isPast = currentStep > step.id
            const hasAccess = Boolean(activity) || step.id <= 2
            const StepIcon = step.icon

            return (
              <button
                key={step.id}
                type="button"
                disabled={!hasAccess && !isPast}
                onClick={() => {
                  if (hasAccess || isPast) setCurrentStep(step.id)
                }}
                className={`p-2.5 rounded-xl text-left border transition-all cursor-pointer flex flex-col gap-1.5 relative ${
                  isCurrent
                    ? 'border-[var(--accent)] bg-[var(--surface-alt)] shadow-xs ring-1 ring-[var(--accent)]/30'
                    : isPast
                    ? 'border-emerald-500/30 bg-emerald-500/5 hover:border-emerald-500/50'
                    : hasAccess
                    ? 'border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-alt)]'
                    : 'border-[var(--border)]/60 bg-[var(--surface)]/40 opacity-40 cursor-not-allowed'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                    isPast
                      ? 'bg-emerald-500 text-white'
                      : isCurrent
                      ? 'bg-[var(--accent)] text-white'
                      : 'bg-[var(--surface-alt)] text-[var(--text-soft)] border border-[var(--border)]'
                  }`}>
                    {isPast ? <Check size={12} strokeWidth={3} /> : step.id}
                  </span>
                  <StepIcon size={14} className={isCurrent ? 'text-[var(--accent)]' : isPast ? 'text-emerald-500' : 'text-[var(--text-faint)]'} />
                </div>
                <div className="leading-tight">
                  <div className={`text-xs font-bold truncate ${isCurrent ? 'text-[var(--text)]' : isPast ? 'text-emerald-700 dark:text-emerald-300' : 'text-[var(--text-soft)]'}`}>
                    {step.label}
                  </div>
                  <div className="text-[10px] text-[var(--text-faint)] truncate mt-0.5">
                    {step.desc}
                  </div>
                </div>
              </button>
            )
          })}
        </div>

        {/* Mobile / Tablet Compact Stepper */}
        <div className="lg:hidden space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="w-6 h-6 rounded-full bg-[var(--accent)] text-white flex items-center justify-center text-xs font-bold">
                {currentStep}
              </span>
              <span className="text-xs font-bold text-[var(--text)]">
                Step {currentStep} of 7: {JOURNEY_STEPS[currentStep - 1]?.fullTitle}
              </span>
            </div>
            <div className="flex items-center gap-1.5">
              <button
                type="button"
                disabled={currentStep <= 1}
                onClick={() => setCurrentStep(prev => Math.max(1, prev - 1))}
                className="p-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] disabled:opacity-30 cursor-pointer text-xs"
                title="Previous step"
              >
                <ChevronLeft size={14} />
              </button>
              <button
                type="button"
                disabled={currentStep >= 7 || (!activity && currentStep >= 2)}
                onClick={() => setCurrentStep(prev => Math.min(7, prev + 1))}
                className="p-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] disabled:opacity-30 cursor-pointer text-xs"
                title="Next step"
              >
                <ChevronRight size={14} />
              </button>
            </div>
          </div>
          {/* Progress bar */}
          <div className="w-full h-1.5 bg-[var(--surface-alt)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[var(--accent)] transition-all duration-300"
              style={{ width: `${(currentStep / 7) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {/* Profile Incomplete Guidance Banner */}
      {profileIncomplete && (
        <div className="p-4 md:p-5 rounded-2xl bg-amber-500/10 border border-amber-500/30 text-amber-900 dark:text-amber-200 text-sm font-medium flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 animate-fadeIn shadow-sm">
          <div className="flex items-start sm:items-center gap-3">
            <AlertTriangle size={20} className="shrink-0 text-amber-600 dark:text-amber-400 mt-0.5 sm:mt-0" />
            <div className="space-y-0.5">
              <div className="font-bold text-amber-950 dark:text-amber-100 text-sm sm:text-base">
                Profile Incomplete: Academic Level Required
              </div>
              <div className="text-xs sm:text-sm text-amber-800 dark:text-amber-300">
                Learn from Anywhere adapts explanations specifically to your School Grade or College Semester. Please complete your academic profile in Settings.
              </div>
            </div>
          </div>
          <Button
            onClick={() => {
              if (typeof window !== 'undefined') window.location.href = '/settings'
            }}
            variant="primary"
            size="sm"
            className="shrink-0 flex items-center gap-2 bg-amber-600 hover:bg-amber-700 text-white border-0 shadow-sm"
          >
            <User size={14} />
            <span>Go to Settings</span>
          </Button>
        </div>
      )}

      {/* Error & Retry Banner */}
      {errorMsg && !profileIncomplete && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-semibold flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertTriangle size={17} className="shrink-0 text-red-500" />
            <span>{errorMsg}</span>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {/syllabus|curriculum/i.test(errorMsg) && (
              <Button
                onClick={() => setIsSyllabusModalOpen(true)}
                variant="outline"
                size="sm"
                className="flex items-center gap-1.5 border-emerald-500/30 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-500/10 text-xs"
              >
                <BookOpen size={12} />
                <span>Upload / Validate Syllabus</span>
              </Button>
            )}
            <Button
              onClick={handleGenerateActivity}
              variant="outline"
              size="sm"
              className="flex items-center gap-1.5 border-red-500/30 text-red-600 dark:text-red-400 hover:bg-red-500/10 text-xs"
            >
              <RefreshCw size={12} />
              <span>Retry</span>
            </Button>
          </div>
        </div>
      )}

      {/* Loading Overlay State */}
      {loading && (
        <Card className="p-10 md:p-14 text-center my-6 space-y-4 border-[var(--border)] animate-fadeIn">
          <Loader2 size={40} className="animate-spin text-[var(--accent)] mx-auto" />
          <div className="space-y-1">
            <h3 className="text-base font-bold text-[var(--text)]">
              Designing Grounded Learning Journey...
            </h3>
            <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
              Grounding <strong>{selectedSubject}</strong> ({selectedTopic || 'Core Syllabus Principle'}) into zero-cost practical experiments using your local surroundings.
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-[11px] text-[var(--text-faint)] font-medium">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Authentic Syllabus AI • {preferredLanguage}</span>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 1: SELECT YOUR SUBJECT
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 1 && !loading && (
        <Card className="p-4 sm:p-6 md:p-7 space-y-6 animate-fadeIn border-[var(--border)]">
          <div className="border-b border-[var(--border)] pb-4 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
              <BookOpen size={14} />
              <span>Step 1: Choose Your Validated Syllabus Subject</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight">
              Select Your Subject
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-soft)]">
              Choose an active course from your syllabus. Only verified subjects from your uploaded syllabus are shown.
            </p>
          </div>

          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {subjects.map((sub) => {
              const isSelected = selectedSubject === sub
              const topicList = curriculum?.chapters?.[sub] || curriculum?.units?.[sub] || []
              const topicCount = Array.isArray(topicList) ? topicList.length : 0

              return (
                <div
                  key={sub}
                  onClick={() => handleSubjectSelect(sub)}
                  className={`p-5 rounded-2xl border text-left transition-all cursor-pointer flex flex-col justify-between gap-4 group ${
                    isSelected
                      ? 'border-[var(--accent)] bg-[var(--surface-alt)] shadow-sm ring-1 ring-[var(--accent)]/30'
                      : 'border-[var(--border)] bg-[var(--surface)] hover:border-[var(--border-strong)] hover:bg-[var(--surface-alt)]/50'
                  }`}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === ' ' || e.key === 'Enter') handleSubjectSelect(sub)
                  }}
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className={`p-2.5 rounded-xl ${isSelected ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface-alt)] text-[var(--text-soft)] border border-[var(--border)]'}`}>
                        <BookOpen size={18} />
                      </div>
                      {isSelected && (
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                          <Check size={12} strokeWidth={3} /> Selected
                        </span>
                      )}
                    </div>
                    <div>
                      <h3 className="font-bold text-base text-[var(--text)] group-hover:text-[var(--accent)] transition-colors leading-snug">
                        {sub}
                      </h3>
                      {topicCount > 0 && (
                        <p className="text-xs text-[var(--text-soft)] mt-1">
                          {topicCount} units / modules in syllabus
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-[var(--border)]/60 flex items-center justify-between text-xs font-semibold">
                    <span className="text-[var(--text-faint)]">Validated Course</span>
                    <span className={`flex items-center gap-1 transition-transform group-hover:translate-x-0.5 ${isSelected ? 'text-[var(--accent)]' : 'text-[var(--text-soft)]'}`}>
                      Select <ArrowRight size={13} />
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          <div className="pt-4 border-t border-[var(--border)] flex justify-end">
            <Button
              onClick={() => setCurrentStep(2)}
              disabled={!selectedSubject}
              className="px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold text-sm cursor-pointer shadow-sm"
            >
              <span>Continue to Choose Topic</span>
              <ArrowRight size={15} />
            </Button>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 2: CHOOSE TOPIC & SETUP
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 2 && !loading && (
        <Card className="p-4 sm:p-6 md:p-7 space-y-6 animate-fadeIn border-[var(--border)]">
          <div className="border-b border-[var(--border)] pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
                <Layers size={14} />
                <span>Step 2: Choose Topic & Setup</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight">
                Topics in {selectedSubject}
              </h2>
              <p className="text-xs sm:text-sm text-[var(--text-soft)]">
                Select the topic you want to understand practically. All topics are aligned with your validated curriculum.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowSetupPanel(prev => !prev)}
              className="px-3.5 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] hover:bg-[var(--surface)] text-[var(--text)] text-xs font-bold flex items-center gap-2 cursor-pointer self-start sm:self-auto transition-all shadow-xs"
            >
              <SlidersHorizontal size={14} className="text-[var(--accent)]" />
              <span>{showSetupPanel ? 'Hide Materials Setup' : 'Custom Surroundings & Materials'}</span>
              <ChevronDown size={13} className={`transition-transform duration-200 ${showSetupPanel ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {/* Optional Collapsible Surroundings & Materials Customizer */}
          {showSetupPanel && (
            <div className="p-4 md:p-5 rounded-2xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-5 animate-fadeIn">
              <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
                <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)] uppercase tracking-wider">
                  <Wrench size={14} className="text-[var(--accent)]" />
                  <span>Customize Your Surroundings & Available Materials</span>
                </div>
                <span className="text-[11px] text-[var(--text-faint)]">Optional — Never required</span>
              </div>

              {/* Local Environments */}
              <div>
                <label className="text-xs font-bold text-[var(--text-soft)] mb-2 block uppercase tracking-wider">
                  Available Natural / Local Environment
                </label>
                <div className="flex gap-2 flex-wrap">
                  {RESOURCE_ENVIRONMENTS.map(({ id, label, icon: Icon }) => {
                    const isSelected = selectedEnv === id
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => setSelectedEnv(id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all flex items-center gap-1.5 cursor-pointer ${
                          isSelected
                            ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-2xs'
                            : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                        }`}
                      >
                        <Icon size={13} />
                        <span>{label}</span>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Custom Materials description & quick add tags */}
              <div className="space-y-2">
                <label className="text-xs font-bold text-[var(--text-soft)] block uppercase tracking-wider">
                  Objects & Materials You Have Nearby
                </label>
                <input
                  type="text"
                  value={customMaterials}
                  onChange={(e) => setCustomMaterials(e.target.value)}
                  placeholder="e.g. Red clay, plastic bottle, turmeric, clean water, bicycle gears, sunlight, dry leaves, string..."
                  className="w-full px-3.5 py-2 text-xs sm:text-sm rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                />
                <div className="flex items-center gap-1.5 flex-wrap pt-1">
                  <span className="text-[11px] font-semibold text-[var(--text-faint)]">Quick add:</span>
                  {QUICK_MATERIAL_TAGS.slice(0, 8).map(tag => (
                    <button
                      key={tag}
                      type="button"
                      onClick={() => handleAddMaterialTag(tag)}
                      className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--surface)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-[var(--text-soft)] font-medium cursor-pointer transition-colors"
                    >
                      + {tag}
                    </button>
                  ))}
                </div>
              </div>

              {/* Preferences Row */}
              <div className="grid sm:grid-cols-3 gap-3 pt-2 border-t border-[var(--border)] text-xs">
                <div>
                  <span className="font-semibold text-[var(--text-soft)] block mb-1">Learning Method:</span>
                  <select
                    value={learningMethod}
                    onChange={(e) => setLearningMethod(e.target.value)}
                    className="w-full p-2 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)]"
                  >
                    {LEARNING_METHODS.map(m => (
                      <option key={m.id} value={m.id}>{m.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <span className="font-semibold text-[var(--text-soft)] block mb-1">Difficulty:</span>
                  <select
                    value={difficulty}
                    onChange={(e) => setDifficulty(e.target.value)}
                    className="w-full p-2 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)]"
                  >
                    <option value="Easy">Easy (Everyday Observations)</option>
                    <option value="Medium">Medium (Guided Hands-on)</option>
                    <option value="Hard">Advanced (Quantitative & Analytical)</option>
                  </select>
                </div>
                <div>
                  <span className="font-semibold text-[var(--text-soft)] block mb-1">Language:</span>
                  <select
                    value={preferredLanguage}
                    onChange={(e) => setPreferredLanguage(e.target.value)}
                    className="w-full p-2 rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)]"
                  >
                    {EXPLANATION_LANGUAGES.map(l => (
                      <option key={l.id} value={l.id}>{l.label}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Topic Sections */}
          <div className="space-y-5">
            {groupedUnits.length > 0 ? (
              groupedUnits.map((group, gIdx) => (
                <div key={gIdx} className="space-y-2.5">
                  <div className="text-xs font-bold text-[var(--accent)] uppercase tracking-wider flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                    <span>{group.unitName}</span>
                  </div>
                  <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                    {group.topics.map((top) => {
                      const isSelected = selectedTopic === top
                      return (
                        <button
                          key={top}
                          type="button"
                          onClick={() => handleTopicSelect(top)}
                          className={`p-3.5 rounded-xl text-left border transition-all cursor-pointer flex items-center justify-between gap-2.5 ${
                            isSelected
                              ? 'bg-[var(--accent-soft)]/50 border-[var(--accent)] text-[var(--accent)] font-bold shadow-xs'
                              : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)] hover:border-[var(--border-strong)]'
                          }`}
                        >
                          <span className="text-xs sm:text-sm truncate">{top}</span>
                          {isSelected && <CheckCircle2 size={16} className="text-[var(--accent)] shrink-0" />}
                        </button>
                      )
                    })}
                  </div>
                </div>
              ))
            ) : (
              <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2.5">
                {validatedSubjectTopics.map((top) => {
                  const isSelected = selectedTopic === top
                  return (
                    <button
                      key={top}
                      type="button"
                      onClick={() => handleTopicSelect(top)}
                      className={`p-3.5 rounded-xl text-left border transition-all cursor-pointer flex items-center justify-between gap-2.5 ${
                        isSelected
                          ? 'bg-[var(--accent-soft)]/50 border-[var(--accent)] text-[var(--accent)] font-bold shadow-xs'
                          : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)] hover:border-[var(--border-strong)]'
                      }`}
                    >
                      <span className="text-xs sm:text-sm truncate">{top}</span>
                      {isSelected && <CheckCircle2 size={16} className="text-[var(--accent)] shrink-0" />}
                    </button>
                  )
                })}
              </div>
            )}
          </div>

          {/* Navigation Footer */}
          <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between gap-3 flex-wrap">
            <Button
              onClick={() => setCurrentStep(1)}
              variant="outline"
              className="px-4 py-2 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Subjects</span>
            </Button>

            <Button
              onClick={handleGenerateActivity}
              disabled={!selectedTopic || loading}
              className="px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold text-sm cursor-pointer shadow-sm"
            >
              <Sparkles size={16} />
              <span>{activity ? 'Continue / Regenerate Learning →' : 'Start Guided Learning →'}</span>
            </Button>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 3: UNDERSTAND THE CONCEPT
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 3 && !loading && activity && (
        <Card className="p-6 md:p-8 space-y-6 animate-fadeIn border-[var(--border)]">
          {/* Header & Badges */}
          <div className="border-b border-[var(--border)] pb-4 space-y-2">
            <div className="flex items-center gap-2 flex-wrap text-xs">
              <Badge tone="accent">{activity.subject || selectedSubject}</Badge>
              <span className="px-2.5 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                <Target size={12} />
                <span>{selectedTopic || activity.topic}</span>
              </span>
              {(activity.student_type === 'SCHOOL' || activity.academic_level === 'SCHOOL') ? (
                <span className="px-2.5 py-0.5 rounded-full font-semibold bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-500/20 flex items-center gap-1">
                  <GraduationCap size={12} />
                  <span>School • {activity.academic_grounding?.grade_or_semester || user?.grade_level || 'Curriculum'}</span>
                </span>
              ) : (
                <span className="px-2.5 py-0.5 rounded-full font-semibold bg-indigo-500/10 text-indigo-800 dark:text-indigo-300 border border-indigo-500/20 flex items-center gap-1">
                  <GraduationCap size={12} />
                  <span>College • {activity.academic_grounding?.grade_or_semester ? `Sem ${activity.academic_grounding?.grade_or_semester}` : (user?.semester ? `Sem ${user.semester}` : 'Higher Ed')}</span>
                </span>
              )}
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight leading-snug">
              {activity.title || activity.activity_title || `${selectedSubject}: ${selectedTopic}`}
            </h2>
          </div>

          {/* Adaptive Explanation Level Switcher */}
          <div className="flex items-center justify-between p-3 rounded-xl bg-[var(--surface-alt)]/60 border border-[var(--border)] flex-wrap gap-2.5">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--text-soft)] uppercase tracking-wider">
              <SlidersHorizontal size={14} className="text-[var(--accent)]" />
              <span>Explanation Depth:</span>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              <button
                type="button"
                onClick={() => {
                  setAdaptiveLevel('simple')
                  handleStudentAction('adaptive_level', { adaptive_level: 'simple' })
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5 ${
                  adaptiveLevel === 'simple'
                    ? 'bg-emerald-500 text-white border-emerald-500 shadow-xs'
                    : 'bg-[var(--surface)] text-[var(--text-soft)] border-[var(--border)] hover:text-[var(--text)]'
                }`}
              >
                <span>🟢 Simple Mode</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdaptiveLevel('detailed')
                  handleStudentAction('adaptive_level', { adaptive_level: 'detailed' })
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5 ${
                  adaptiveLevel === 'detailed'
                    ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                    : 'bg-[var(--surface)] text-[var(--text-soft)] border-[var(--border)] hover:text-[var(--text)]'
                }`}
              >
                <span>🔵 Detailed Mode</span>
              </button>
              <button
                type="button"
                onClick={() => {
                  setAdaptiveLevel('quick')
                  handleStudentAction('adaptive_level', { adaptive_level: 'quick' })
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5 ${
                  adaptiveLevel === 'quick'
                    ? 'bg-amber-500 text-white border-amber-500 shadow-xs'
                    : 'bg-[var(--surface)] text-[var(--text-soft)] border-[var(--border)] hover:text-[var(--text)]'
                }`}
              >
                <span>🟡 Quick Learning</span>
              </button>
            </div>
          </div>

          {/* Learning Objective Box */}
          <div className="p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-sm text-[var(--text)] space-y-2">
            <div className="flex items-start gap-3">
              <Lightbulb size={18} className="text-amber-500 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <strong className="text-[var(--text)] font-semibold">What You Will Learn: </strong>
                <span className="text-[var(--text-soft)]">{learningObjective}</span>
              </div>
            </div>
            {activity.why_it_matters && (
              <div className="text-xs sm:text-sm text-[var(--text-soft)] pl-7.5 leading-relaxed border-t border-amber-500/15 pt-2">
                <strong className="text-[var(--text)] font-semibold">Why this matters: </strong>
                <span>{activity.why_it_matters}</span>
              </div>
            )}
          </div>

          {/* Word Bank / Unfamiliar Words (School & General) */}
          {Array.isArray(activity.unfamiliar_words) && activity.unfamiliar_words.length > 0 && (
            <div className="p-3.5 rounded-xl bg-emerald-500/5 border border-emerald-500/20 text-xs space-y-2">
              <div className="font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-1.5 uppercase tracking-wider">
                <BookOpen size={13} />
                <span>Word Bank & Essential Terminology</span>
              </div>
              <div className="flex flex-wrap gap-2">
                {activity.unfamiliar_words.map((item, idx) => (
                  <span key={idx} className="px-2.5 py-1 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text)]">
                    <strong className="text-[var(--accent)]">{typeof item === 'object' ? item.word : item}</strong>
                    {typeof item === 'object' && item.simple_meaning ? `: ${item.simple_meaning}` : ''}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Core Concept Explanation */}
          <div className="space-y-4">
            <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
              <Lightbulb size={16} className="text-[var(--accent)]" />
              <span>Core Concept & Scientific Principle</span>
            </div>
            <div className="p-5 rounded-2xl bg-[var(--surface-alt)]/50 border border-[var(--border)] space-y-3.5 leading-relaxed text-sm sm:text-base text-[var(--text)]">
              <div className="whitespace-pre-wrap leading-relaxed">
                {formatInlineText(activity.simple_explanation || activity.scientific_principle)}
              </div>

              {activity.academic_theory && (
                <div className="mt-4 pt-3 border-t border-[var(--border)] text-xs sm:text-sm text-[var(--text-soft)] space-y-1">
                  <div className="font-bold text-[var(--text)] uppercase tracking-wider text-[11px]">
                    Academic Grounding:
                  </div>
                  <div className="whitespace-pre-wrap leading-relaxed">
                    {formatInlineText(activity.academic_theory)}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Dynamic Diagram / Mermaid if present */}
          {(activity.flowchart || activity.ascii_schematic || activity.diagram) && (
            <div className="space-y-2">
              <div className="text-xs font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles size={14} className="text-[var(--accent)]" />
                <span>Visual Intuition Diagram</span>
              </div>
              <MermaidRenderer code={activity.flowchart || activity.ascii_schematic || activity.diagram} />
            </div>
          )}

          {/* Quick Action Bar (Step 7) */}
          <div className="p-4 sm:p-5 rounded-2xl bg-[var(--surface)] border border-[var(--border)] space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                <Zap size={14} className="text-amber-500" />
                <span>Instant Learning Actions</span>
              </div>
              <span className="text-[11px] text-[var(--text-faint)]">Click to tailor explanation</span>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('simpler_words')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>💡 Explain simply</span>
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('another_example')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>🏢 Another practical example</span>
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('show_diagram')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>📊 Show diagram / flowchart</span>
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('step_by_step')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>🔢 Step-by-step breakdown</span>
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('no_equipment_activity')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>🚫 No-equipment activity</span>
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('summarize')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>📝 Summarize topic</span>
              </button>
              <button
                type="button"
                disabled={actionLoading}
                onClick={() => handleStudentAction('test_understanding')}
                className="px-3 py-1.5 rounded-xl bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-xs font-semibold text-[var(--text-soft)] transition-colors cursor-pointer flex items-center gap-1.5"
              >
                <span>🎯 Test my understanding</span>
              </button>
            </div>

            {/* Assistance Response Card */}
            {actionLoading && (
              <div className="p-4 rounded-xl bg-[var(--surface-alt)] text-center text-xs text-[var(--text-soft)] flex items-center justify-center gap-2">
                <Loader2 size={15} className="animate-spin text-[var(--accent)]" />
                <span>Generating tailored explanation with real AI service...</span>
              </div>
            )}
            {actionResult && !actionLoading && (
              <div className="p-4 sm:p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--accent)]/30 space-y-3 animate-fadeIn text-xs sm:text-sm">
                <div className="font-bold text-[var(--accent)] flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Sparkles size={14} />
                    <span>{actionResult.title || 'Assistant Explanation'}</span>
                  </span>
                  <button
                    type="button"
                    onClick={() => setActionResult(null)}
                    className="p-1 rounded text-[var(--text-faint)] hover:text-[var(--text)] cursor-pointer"
                  >
                    <X size={14} />
                  </button>
                </div>
                <div className="leading-relaxed text-[var(--text)] whitespace-pre-wrap">
                  {formatInlineText(actionResult.content)}
                </div>
                {actionResult.mermaid_diagram && (
                  <div className="mt-2">
                    <MermaidRenderer code={actionResult.mermaid_diagram} />
                  </div>
                )}
                {Array.isArray(actionResult.steps) && actionResult.steps.length > 0 && (
                  <div className="space-y-1.5 pt-2 border-t border-[var(--border)]">
                    <div className="font-bold text-[var(--text)] text-xs uppercase tracking-wider">Key Steps:</div>
                    <div className="space-y-1 text-xs text-[var(--text-soft)] pl-2 border-l-2 border-[var(--accent)]">
                      {actionResult.steps.map((st, sIdx) => (
                        <div key={sIdx}>{st}</div>
                      ))}
                    </div>
                  </div>
                )}
                {Array.isArray(actionResult.key_points) && actionResult.key_points.length > 0 && (
                  <div className="space-y-1 pt-2 border-t border-[var(--border)]">
                    <div className="font-bold text-[var(--text)] text-xs uppercase tracking-wider">Important Highlights:</div>
                    <ul className="list-disc pl-4 space-y-0.5 text-xs text-[var(--text-soft)]">
                      {actionResult.key_points.map((pt, pIdx) => (
                        <li key={pIdx}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                )}
                {actionResult.follow_up_question && (
                  <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-1 text-xs">
                    <span className="font-bold text-[var(--accent)]">Quick Check: </span>
                    <span className="text-[var(--text)] font-medium">{actionResult.follow_up_question}</span>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Interactive Follow-Up Doubt & AI Tutor Chat (Step 8) */}
          <div className="p-4 sm:p-5 rounded-2xl bg-[var(--surface-alt)]/40 border border-[var(--border)] space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)] uppercase tracking-wider">
                <MessageSquare size={15} className="text-[var(--accent)]" />
                <span>Ask a Doubt or Follow-Up Question</span>
              </div>
              <span className="text-[11px] text-[var(--text-faint)]">Preserves conversation context</span>
            </div>

            {/* Chat Conversation History */}
            {conversationHistory.length > 0 && (
              <div className="space-y-3 max-h-96 overflow-y-auto pr-1">
                {conversationHistory.map((msg, mIdx) => (
                  <div
                    key={mIdx}
                    className={`p-3.5 rounded-2xl text-xs sm:text-sm leading-relaxed space-y-2 ${
                      msg.role === 'student'
                        ? 'bg-[var(--surface-elevated)] border border-[var(--border-strong)] ml-4 sm:ml-8 text-[var(--text)]'
                        : 'bg-[var(--surface)] border border-[var(--accent)]/30 mr-4 sm:mr-8 text-[var(--text)]'
                    }`}
                  >
                    <div className="flex items-center gap-2 font-bold text-[11px] text-[var(--text-soft)] uppercase tracking-wider">
                      {msg.role === 'student' ? <User size={13} className="text-emerald-500" /> : <Bot size={13} className="text-[var(--accent)]" />}
                      <span>{msg.role === 'student' ? 'Your Question' : (msg.title || 'AI Learning Tutor')}</span>
                    </div>
                    <div className="whitespace-pre-wrap leading-relaxed">
                      {formatInlineText(msg.content)}
                    </div>
                    {msg.diagram && (
                      <div className="mt-2">
                        <MermaidRenderer code={msg.diagram} />
                      </div>
                    )}
                    {Array.isArray(msg.points) && msg.points.length > 0 && (
                      <ul className="list-disc pl-4 space-y-1 text-xs text-[var(--text-soft)] pt-1 border-t border-[var(--border)]/40">
                        {msg.points.map((pt, pIdx) => (
                          <li key={pIdx}>{pt}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Doubt Input & Send Button */}
            <div className="space-y-2">
              <div className="flex gap-2">
                <input
                  type="text"
                  value={studentDoubt}
                  onChange={(e) => setStudentDoubt(e.target.value)}
                  placeholder="Ask a specific doubt (e.g. 'Can I demonstrate this with water?', 'Why does this happen?')..."
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !actionLoading && studentDoubt.trim()) {
                      e.preventDefault()
                      handleStudentAction('ask_question', { question: studentDoubt.trim() })
                    }
                  }}
                  className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] min-h-[42px]"
                />
                <Button
                  onClick={() => handleStudentAction('ask_question', { question: studentDoubt.trim() })}
                  disabled={actionLoading || !studentDoubt.trim()}
                  size="sm"
                  className="px-4 text-xs font-bold shrink-0 min-h-[42px] flex items-center gap-1.5 cursor-pointer"
                >
                  {actionLoading ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  <span>Ask</span>
                </Button>
              </div>

              {/* Suggested Question Chips for Instant Clicking */}
              <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                <span className="text-[11px] font-semibold text-[var(--text-faint)]">Suggested:</span>
                {[
                  "Can I demonstrate this using household materials?",
                  "Why does this step happen first?",
                  "What happens if one variable changes?",
                  "Give me another everyday example"
                ].map((promptText, pIdx) => (
                  <button
                    key={pIdx}
                    type="button"
                    onClick={() => {
                      setStudentDoubt(promptText)
                      handleStudentAction('ask_question', { question: promptText })
                    }}
                    className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--surface)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-[var(--text-soft)] transition-colors cursor-pointer"
                  >
                    {promptText}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Navigation Footer */}
          <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between gap-3 flex-wrap">
            <Button
              onClick={() => setCurrentStep(2)}
              variant="outline"
              className="px-4 py-2 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Topics</span>
            </Button>

            <Button
              onClick={() => {
                setCompletedJourneySteps(prev => ({ ...prev, 3: true }))
                setCurrentStep(4)
              }}
              className="px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold text-sm cursor-pointer shadow-sm"
            >
              <span>Explore Real-World Applications</span>
              <ArrowRight size={15} />
            </Button>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 4: EXPLORE REAL-WORLD APPLICATIONS
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 4 && !loading && activity && (
        <Card className="p-6 md:p-8 space-y-6 animate-fadeIn border-[var(--border)]">
          <div className="border-b border-[var(--border)] pb-4 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
              <Sun size={14} />
              <span>Step 4: Explore Real-World Applications</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight">
              Where Is This Used in Real Life?
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-soft)]">
              Discover how {selectedTopic || activity.topic} powers daily life, machinery, local surroundings, and modern industries.
            </p>
          </div>

          <div className="grid md:grid-cols-2 gap-4">
            {/* Card 1: The Practical Phenomenon */}
            <div className="p-5 rounded-2xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-3">
              <div className="flex items-center gap-2 font-bold text-sm text-[var(--text)]">
                <div className="p-2 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400">
                  <Sun size={18} />
                </div>
                <span>Practical Phenomenon</span>
              </div>
              <p className="text-xs sm:text-sm text-[var(--text-soft)] leading-relaxed whitespace-pre-wrap">
                {activity.real_world_concept || activity.simple_explanation}
              </p>
            </div>

            {/* Card 2: Everyday & Industry Applications */}
            <div className="p-5 rounded-2xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-3">
              <div className="flex items-center gap-2 font-bold text-sm text-[var(--text)]">
                <div className="p-2 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400">
                  <Compass size={18} />
                </div>
                <span>Everyday & Village Applications</span>
              </div>
              <p className="text-xs sm:text-sm text-[var(--text-soft)] leading-relaxed whitespace-pre-wrap">
                {activity.everyday_applications || activity.why_it_matters || 'See how this governing principle applies directly to machinery, water systems, natural phenomena, and household tools.'}
              </p>
            </div>

            {/* Card 3: Expected Observations in Real Situations */}
            <div className="p-5 rounded-2xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-3 md:col-span-2">
              <div className="flex items-center gap-2 font-bold text-sm text-[var(--text)]">
                <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                  <Eye size={18} />
                </div>
                <span>Expected Observations & Practical Behavior</span>
              </div>
              <p className="text-xs sm:text-sm text-[var(--text-soft)] leading-relaxed whitespace-pre-wrap">
                {resultOrExampleText}
              </p>
            </div>

            {/* Card 4: Technical Assumptions & Reasoning (If available) */}
            {Array.isArray(activity.assumptions_and_reasoning) && activity.assumptions_and_reasoning.length > 0 && (
              <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-2 md:col-span-2 text-xs">
                <span className="font-bold text-[var(--text)] uppercase tracking-wider block">
                  Assumptions & Environmental Boundaries:
                </span>
                <ul className="space-y-1 text-[var(--text-soft)] list-disc pl-4">
                  {activity.assumptions_and_reasoning.map((item, iIdx) => (
                    <li key={iIdx} className="leading-relaxed">{item}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Navigation Footer */}
          <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between gap-3 flex-wrap">
            <Button
              onClick={() => setCurrentStep(3)}
              variant="outline"
              className="px-4 py-2 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Concept</span>
            </Button>

            <Button
              onClick={() => {
                setCompletedJourneySteps(prev => ({ ...prev, 4: true }))
                setCurrentStep(5)
              }}
              className="px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold text-sm cursor-pointer shadow-sm"
            >
              <span>Continue to Practical Activity</span>
              <ArrowRight size={15} />
            </Button>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 5: LEARN THROUGH PRACTICAL ACTIVITIES
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 5 && !loading && activity && (
        <Card className="p-6 md:p-8 space-y-6 animate-fadeIn border-[var(--border)]">
          <div className="border-b border-[var(--border)] pb-4 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
              <Wrench size={14} />
              <span>Step 5: Learn Through Practical Activities</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight">
              Hands-On Activity & Instructions
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-soft)]">
              Follow these sequential steps using zero-cost materials from your surroundings. Check off each step as you complete it.
            </p>
          </div>

          {/* Materials Checklist */}
          {cleanMaterialsList.length > 0 && (
            <div className="space-y-3">
              <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center justify-between">
                <span className="flex items-center gap-2">
                  {isCodingTask ? <Code size={15} className="text-emerald-500" /> : <Wrench size={15} className="text-emerald-500" />}
                  <span>{isCodingTask ? 'Required Software & Tools' : 'Materials Needed (Check off what you have)'}</span>
                </span>
                <span className="text-xs text-[var(--text-soft)] font-normal">
                  {Object.values(checkedMaterials).filter(Boolean).length} / {cleanMaterialsList.length} ready
                </span>
              </div>

              <div className="flex flex-wrap gap-2">
                {cleanMaterialsList.map((mat, idx) => {
                  const isChecked = Boolean(checkedMaterials[idx])
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleMaterial(idx)}
                      className={`px-3 py-1.5 rounded-xl border text-xs sm:text-sm font-medium transition-all cursor-pointer flex items-center gap-2 ${
                        isChecked
                          ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-900 dark:text-emerald-100 line-through opacity-80'
                          : 'bg-[var(--surface-alt)] border-[var(--border)] text-[var(--text)] hover:border-emerald-500/40'
                      }`}
                    >
                      <span className={`w-4 h-4 rounded flex items-center justify-center text-[10px] font-bold ${
                        isChecked ? 'bg-emerald-500 text-white' : 'border border-[var(--border-strong)]'
                      }`}>
                        {isChecked ? '✓' : ''}
                      </span>
                      <span>{mat}</span>
                    </button>
                  )
                })}
              </div>

              {/* Zero-Cost Substitutions Helper */}
              {(activity.safe_substitutions?.length > 0 || activity.no_purchase_alternative || activity.offline_alternative) && (
                <div className="pt-1">
                  <button
                    type="button"
                    onClick={() => setShowMaterialAlternatives(prev => !prev)}
                    className="text-xs font-semibold text-[var(--accent)] hover:underline flex items-center gap-1.5 cursor-pointer"
                  >
                    <span>{showMaterialAlternatives ? 'Hide free substitutions & offline option' : 'Missing items or limited internet? View free substitutions & offline alternative'}</span>
                    <ChevronDown size={13} className={`transition-transform duration-200 ${showMaterialAlternatives ? 'rotate-180' : ''}`} />
                  </button>

                  {showMaterialAlternatives && (
                    <div className="mt-2 p-3.5 rounded-xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-2 text-xs">
                      <div className="flex items-start gap-2 text-emerald-700 dark:text-emerald-400 font-medium">
                        <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
                        <span><strong>Zero Purchase Guarantee: </strong>{activity.no_purchase_alternative || "All concepts can be explored using paper, pencil, water, or household objects."}</span>
                      </div>

                      {Array.isArray(activity.safe_substitutions) && activity.safe_substitutions.length > 0 && (
                        <div className="space-y-1">
                          <strong className="text-[var(--text)] block font-semibold">Free Substitutions:</strong>
                          <div className="space-y-1 text-[var(--text-soft)] pl-2 border-l-2 border-[var(--border)]">
                            {activity.safe_substitutions.map((sub, sIdx) => (
                              <div key={sIdx} className="flex items-start gap-1.5">
                                <span>•</span>
                                <span>{sub}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {activity.offline_alternative && (
                        <div className="pt-2 border-t border-[var(--border)] text-[var(--text-soft)]">
                          <strong className="text-[var(--text)] block font-semibold text-[var(--accent)] mb-0.5">Offline / Paper Alternative:</strong>
                          <p className="leading-relaxed">{activity.offline_alternative}</p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* Intelligent Resource Alternative Finder (Step 5) */}
              <div className="p-3.5 sm:p-4 rounded-2xl bg-[var(--surface-alt)]/50 border border-[var(--border)] space-y-3 mt-2">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)] uppercase tracking-wider">
                    <Compass size={14} className="text-emerald-500" />
                    <span>Intelligent Material Substitute Finder</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => handleStudentAction('no_equipment_activity')}
                    className="text-xs font-bold text-[var(--accent)] hover:underline flex items-center gap-1 cursor-pointer"
                  >
                    <Zap size={13} />
                    <span>Switch to Zero-Equipment Activity</span>
                  </button>
                </div>

                <div className="flex gap-2">
                  <input
                    type="text"
                    value={missingMaterialInput}
                    onChange={(e) => setMissingMaterialInput(e.target.value)}
                    placeholder="Missing an item? Type it here (e.g. resistor, glass beaker, magnet, wire)..."
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !actionLoading && missingMaterialInput.trim()) {
                        e.preventDefault()
                        handleStudentAction('material_substitute', { missing_material: missingMaterialInput.trim() })
                      }
                    }}
                    className="flex-1 px-3.5 py-2 text-xs sm:text-sm rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                  />
                  <Button
                    onClick={() => handleStudentAction('material_substitute', { missing_material: missingMaterialInput.trim() })}
                    disabled={actionLoading || !missingMaterialInput.trim()}
                    size="sm"
                    className="px-4 text-xs font-bold shrink-0 min-h-[38px] cursor-pointer"
                  >
                    {actionLoading ? <Loader2 size={13} className="animate-spin" /> : <Wrench size={13} />}
                    <span>Find Alternative</span>
                  </Button>
                </div>

                {/* Quick Material Missing Chips */}
                {cleanMaterialsList.length > 0 && (
                  <div className="flex items-center gap-1.5 flex-wrap pt-0.5">
                    <span className="text-[11px] font-semibold text-[var(--text-faint)]">I don't have:</span>
                    {cleanMaterialsList.slice(0, 5).map((mat, mIdx) => (
                      <button
                        key={mIdx}
                        type="button"
                        onClick={() => {
                          setMissingMaterialInput(mat)
                          handleStudentAction('material_substitute', { missing_material: mat })
                        }}
                        className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--surface)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-[var(--text-soft)] transition-colors cursor-pointer"
                      >
                        {mat}
                      </button>
                    ))}
                  </div>
                )}

                {/* Material Substitute Recommendation Display */}
                {actionResult && actionResult.action_type === 'material_substitute' && (
                  <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-xs sm:text-sm space-y-2 animate-fadeIn">
                    <div className="font-bold text-emerald-800 dark:text-emerald-300 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <ShieldCheck size={15} />
                        <span>{actionResult.title || 'Safe Substitute Recommendation'}</span>
                      </span>
                      <button
                        type="button"
                        onClick={() => setActionResult(null)}
                        className="p-1 rounded text-emerald-700 hover:text-emerald-900 cursor-pointer"
                      >
                        <X size={13} />
                      </button>
                    </div>
                    <p className="leading-relaxed text-[var(--text)] whitespace-pre-wrap">{actionResult.content}</p>
                    {actionResult.substitute_recommendation && (
                      <div className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-soft)] space-y-1">
                        <div>
                          <strong className="text-[var(--text)]">Safe Household Alternative: </strong>
                          <span className="text-emerald-600 dark:text-emerald-400 font-semibold">{actionResult.substitute_recommendation.substitute}</span>
                        </div>
                        <div>
                          <strong className="text-[var(--text)]">Scientific Difference / Limitation: </strong>
                          <span>{actionResult.substitute_recommendation.scientific_difference}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Zero-Equipment Activity Result Display */}
                {actionResult && actionResult.action_type === 'no_equipment_activity' && (
                  <div className="p-3.5 rounded-xl bg-blue-500/10 border border-blue-500/30 text-xs sm:text-sm space-y-2 animate-fadeIn">
                    <div className="font-bold text-blue-800 dark:text-blue-300 flex items-center justify-between">
                      <span className="flex items-center gap-1.5">
                        <Zap size={14} />
                        <span>{actionResult.title || 'Zero-Equipment Thought Experiment'}</span>
                      </span>
                      <button
                        type="button"
                        onClick={() => setActionResult(null)}
                        className="p-1 rounded text-blue-700 hover:text-blue-900 cursor-pointer"
                      >
                        <X size={13} />
                      </button>
                    </div>
                    <p className="leading-relaxed text-[var(--text)] whitespace-pre-wrap">{actionResult.content}</p>
                    {Array.isArray(actionResult.steps) && actionResult.steps.length > 0 && (
                      <div className="space-y-1 pl-2 border-l-2 border-blue-500/50 text-xs text-[var(--text-soft)]">
                        {actionResult.steps.map((st, sIdx) => (
                          <div key={sIdx}>{st}</div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Sequential Step-by-Step Instructions */}
          {stepsList.length > 0 && (
            <div className="space-y-4 pt-2">
              <div className="flex items-center justify-between">
                <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                  <Layers size={15} className="text-[var(--accent)]" />
                  <span>Sequential Activity Steps</span>
                </div>
                <span className="text-xs font-semibold text-[var(--accent)]">
                  {completedCount} / {stepsList.length} completed
                </span>
              </div>

              <div className="space-y-3">
                {structuredExperiments.map((exp, expIdx) => {
                  const expStartIndex = exp.startIndex || 0
                  return (
                    <div key={expIdx} className="space-y-2.5">
                      {exp.title && (
                        <div className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] pt-1 flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]" />
                          <span>{exp.title}</span>
                        </div>
                      )}
                      <div className="space-y-2">
                        {exp.steps.map((stepText, localIdx) => {
                          const globalIdx = expStartIndex + localIdx
                          const isDone = Boolean(completedSteps[globalIdx])
                          return (
                            <div
                              key={globalIdx}
                              onClick={() => toggleStep(globalIdx)}
                              className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                                isDone
                                  ? 'bg-[var(--accent-soft)]/40 border-[var(--accent)] text-[var(--text)]'
                                  : 'bg-[var(--surface-alt)]/50 border-[var(--border)] hover:border-[var(--border-strong)] text-[var(--text)]'
                              }`}
                              role="checkbox"
                              aria-checked={isDone}
                              tabIndex={0}
                              onKeyDown={(e) => {
                                if (e.key === ' ' || e.key === 'Enter') {
                                  e.preventDefault()
                                  toggleStep(globalIdx)
                                }
                              }}
                            >
                              <div className={`w-6 h-6 rounded-md flex items-center justify-center shrink-0 mt-0.5 border text-xs font-bold ${
                                isDone ? 'bg-[var(--accent)] text-white border-[var(--accent)]' : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)]'
                              }`}>
                                {isDone ? '✓' : localIdx + 1}
                              </div>
                              <div className={`text-sm leading-relaxed flex-1 whitespace-pre-wrap ${isDone ? 'line-through opacity-75' : ''}`}>
                                {stepText}
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Coding Block if coding topic */}
          {(activity.coding_task?.code || activity.code_snippet || activity.coding_task?.code_snippet) && (() => {
            const codeSnippet = activity.coding_task?.code || activity.code_snippet || activity.coding_task?.code_snippet
            const lang = activity.coding_task?.target_language || activity.coding_task?.language || 'Python'
            const out = activity.coding_task?.expected_output
            const runInst = activity.coding_task?.run_instructions
            const modTask = activity.coding_task?.modification_task
            return (
              <div className="rounded-2xl bg-gray-900 border border-gray-800 text-gray-100 overflow-hidden shadow-xs mt-3">
                <div className="px-4 py-2.5 bg-gray-950 border-b border-gray-800 flex items-center justify-between text-xs font-mono">
                  <span className="text-emerald-400 font-semibold">{lang}</span>
                  <button
                    type="button"
                    onClick={() => handleCopyCode(codeSnippet)}
                    className="px-2.5 py-1 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs flex items-center gap-1 cursor-pointer"
                  >
                    {copyCodeSuccess ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                    <span>{copyCodeSuccess ? 'Copied' : 'Copy'}</span>
                  </button>
                </div>
                {runInst && runInst !== 'N/A' && (
                  <div className="px-4 py-2 bg-gray-950/70 border-b border-gray-800 text-xs font-mono text-gray-300 flex items-center gap-1.5">
                    <Play size={12} className="text-emerald-400" />
                    <span className="text-gray-400">Run: </span>
                    <span>{runInst}</span>
                  </div>
                )}
                <pre className="p-4 text-xs sm:text-sm font-mono text-emerald-300 overflow-x-auto leading-relaxed">
                  <code>{codeSnippet}</code>
                </pre>
                {out && out !== 'N/A' && (
                  <div className="px-4 py-2.5 bg-gray-950/90 border-t border-gray-800 text-xs font-mono text-sky-300">
                    <span className="text-gray-400">Expected Output: </span>{out}
                  </div>
                )}
                {modTask && modTask !== 'N/A' && (
                  <div className="px-4 py-3 bg-gray-950 border-t border-gray-800 text-xs text-amber-300 flex items-start gap-2">
                    <Terminal size={14} className="text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <strong className="text-amber-200">Coding Exercise: </strong>
                      <span>{modTask}</span>
                    </div>
                  </div>
                )}
              </div>
            )
          })()}

          {/* Progressive Maths Practice */}
          {activity.math_progressive_practice && (
            <div className="space-y-3 pt-2">
              <div className="text-xs font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-1.5">
                <Calculator size={14} className="text-[var(--accent)]" />
                <span>Progressive Calculation Practice (Easy, Medium, Hard)</span>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {['easy', 'medium', 'hard'].map((level) => {
                  const tier = activity.math_progressive_practice[level]
                  if (!tier) return null
                  const badgeColor = level === 'easy'
                    ? 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/20'
                    : level === 'medium'
                    ? 'bg-sky-500/10 text-sky-800 dark:text-sky-300 border-sky-500/20'
                    : 'bg-purple-500/10 text-purple-800 dark:text-purple-300 border-purple-500/20'
                  return (
                    <div key={level} className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2 text-xs">
                      <span className={`px-2 py-0.5 rounded-full font-bold uppercase tracking-wider text-[10px] border ${badgeColor}`}>
                        {level}
                      </span>
                      <p className="font-semibold text-[var(--text)] leading-snug">{tier.question}</p>
                      {tier.method_and_calculations && (
                        <div className="p-2 rounded bg-[var(--surface)] border border-[var(--border)] text-[11px] text-[var(--text-soft)] font-mono whitespace-pre-wrap leading-relaxed">
                          <div className="font-sans font-semibold text-[var(--text)] mb-1 text-[10px] uppercase">Method:</div>
                          {tier.method_and_calculations}
                        </div>
                      )}
                      {tier.answer && (
                        <div className="font-semibold text-emerald-600 dark:text-emerald-400 text-xs">
                          Answer: {tier.answer}
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}

          {/* Safety Warning if relevant */}
          {safetyText && (
            <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs sm:text-sm text-red-900 dark:text-red-300 flex items-start gap-2.5">
              <ShieldAlert size={16} className="text-red-500 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <strong className="font-bold text-red-700 dark:text-red-400">Safety guidance: </strong>
                <span>{safetyText}</span>
              </div>
            </div>
          )}

          {/* Practical Limitations / Misconceptions */}
          {limitationText && (
            <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs sm:text-sm text-amber-900 dark:text-amber-300 flex items-start gap-2.5">
              <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
              <div className="leading-relaxed">
                <strong className="font-bold text-amber-700 dark:text-amber-400">Practical limitation: </strong>
                <span>{limitationText}</span>
              </div>
            </div>
          )}

          {/* Navigation Footer */}
          <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between gap-3 flex-wrap">
            <Button
              onClick={() => setCurrentStep(4)}
              variant="outline"
              className="px-4 py-2 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Applications</span>
            </Button>

            <Button
              onClick={() => {
                setCompletedJourneySteps(prev => ({ ...prev, 5: true }))
                setCurrentStep(6)
              }}
              className="px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold text-sm cursor-pointer shadow-sm"
            >
              <span>Check Your Understanding</span>
              <ArrowRight size={15} />
            </Button>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 6: CHECK YOUR UNDERSTANDING
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 6 && !loading && activity && (
        <Card className="p-6 md:p-8 space-y-6 animate-fadeIn border-[var(--border)]">
          <div className="border-b border-[var(--border)] pb-4 space-y-1">
            <div className="flex items-center gap-2 text-xs font-bold text-[var(--accent)] uppercase tracking-wider">
              <HelpCircle size={14} />
              <span>Step 6: Check Your Understanding</span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight">
              Test Your Practical Knowledge
            </h2>
            <p className="text-xs sm:text-sm text-[var(--text-soft)]">
              Answer these checkpoint questions based on the activity. You will receive genuine educational feedback.
            </p>
          </div>

          <div className="space-y-4">
            {questionsToShow.map((qObj, qIdx) => {
              const isRevealed = Boolean(revealedQuestions[qIdx])
              const evalResult = evaluations[qIdx]
              const isEvaluating = Boolean(evaluatingQ[qIdx])
              const attemptNum = attemptsCount[qIdx] || 0

              return (
                <div
                  key={qIdx}
                  className={`p-4 sm:p-5 rounded-2xl border space-y-3 transition-all ${
                    evalResult
                      ? evalResult.is_correct
                        ? 'bg-emerald-500/5 border-emerald-500/30'
                        : 'bg-amber-500/5 border-amber-500/30'
                      : 'bg-[var(--surface-alt)]/50 border-[var(--border)]'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="text-sm sm:text-base font-bold text-[var(--text)] flex items-start gap-2.5">
                      <span className="text-xs font-bold text-[var(--accent)] px-2 py-0.5 rounded-md bg-[var(--surface)] border border-[var(--border)] shrink-0 mt-0.5">
                        Q{qIdx + 1}
                      </span>
                      <span className="leading-snug">{qObj.question}</span>
                    </div>
                    {attemptNum > 0 && (
                      <span className="text-[11px] font-semibold text-[var(--text-faint)] shrink-0">
                        Attempt #{attemptNum}
                      </span>
                    )}
                  </div>

                  {/* Student Answer Input */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={userAnswers[qIdx] || ''}
                      onChange={(e) => setUserAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                      placeholder="Type your explanation or observation..."
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !isEvaluating) {
                          e.preventDefault()
                          handleSubmitAnswer(qIdx, qObj)
                        }
                      }}
                      className="flex-1 px-4 py-2.5 text-xs sm:text-sm rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] min-h-[42px]"
                    />
                    <Button
                      onClick={() => handleSubmitAnswer(qIdx, qObj)}
                      disabled={isEvaluating || !(userAnswers[qIdx] || '').trim()}
                      size="sm"
                      className="px-4 text-xs font-bold shrink-0 min-h-[42px] cursor-pointer"
                    >
                      {isEvaluating ? <Loader2 size={14} className="animate-spin" /> : <ArrowRight size={14} />}
                      <span>{evalResult ? 'Retry' : 'Submit'}</span>
                    </Button>
                  </div>

                  {/* Genuine Evaluation Feedback */}
                  {evalResult && (
                    <div className={`p-3 rounded-xl text-xs sm:text-sm leading-relaxed ${
                      evalResult.is_correct
                        ? 'bg-emerald-500/10 text-emerald-900 dark:text-emerald-200 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-900 dark:text-amber-200 border border-amber-500/20'
                    }`}>
                      <div className="font-bold mb-0.5 flex items-center gap-1.5">
                        {evalResult.is_correct ? <CheckCircle2 size={14} className="text-emerald-600" /> : <AlertTriangle size={14} className="text-amber-600" />}
                        <span>{evalResult.is_correct ? 'Correct understanding!' : 'Needs review:'}</span>
                      </div>
                      <p>{evalResult.feedback}</p>
                    </div>
                  )}

                  {/* Reference Answer Toggle */}
                  <div className="pt-1 flex justify-end">
                    <button
                      type="button"
                      onClick={() => setRevealedQuestions(prev => ({ ...prev, [qIdx]: !prev[qIdx] }))}
                      className="text-xs font-semibold text-[var(--accent)] hover:underline cursor-pointer flex items-center gap-1"
                    >
                      <Info size={12} />
                      <span>{isRevealed ? 'Hide model answer' : 'Show model answer'}</span>
                    </button>
                  </div>

                  {isRevealed && (
                    <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-soft)] space-y-1.5 animate-fadeIn">
                      <div className="font-bold text-emerald-600 dark:text-emerald-400">
                        Answer: {qObj.answer}
                      </div>
                      {qObj.explanation && (
                        <div className="leading-relaxed">
                          {qObj.explanation}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Additional Practice Button */}
          <div className="pt-2 flex justify-center">
            <button
              type="button"
              disabled={loadingPractice}
              onClick={handleLoadAdditionalPractice}
              className="text-xs font-bold text-[var(--accent)] hover:underline flex items-center gap-1.5 cursor-pointer"
            >
              {loadingPractice ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
              <span>Need more practice? Load extra questions</span>
            </button>
          </div>

          {/* Navigation Footer */}
          <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between gap-3 flex-wrap">
            <Button
              onClick={() => setCurrentStep(5)}
              variant="outline"
              className="px-4 py-2 text-xs font-semibold flex items-center gap-1.5 cursor-pointer"
            >
              <ArrowLeft size={14} />
              <span>Back to Practical Activity</span>
            </Button>

            <Button
              onClick={() => {
                setCompletedJourneySteps(prev => ({ ...prev, 6: true, 7: true }))
                handleSaveProgress(completedSteps, evaluations)
                setCurrentStep(7)
              }}
              className="px-6 py-2.5 min-h-[44px] flex items-center gap-2 font-bold text-sm cursor-pointer shadow-sm"
            >
              <span>Complete & Review Summary</span>
              <ArrowRight size={15} />
            </Button>
          </div>
        </Card>
      )}

      {/* ──────────────────────────────────────────────────────────────────────────
          STEP 7: COMPLETE AND CONTINUE LEARNING
      ────────────────────────────────────────────────────────────────────────── */}
      {currentStep === 7 && !loading && activity && (
        <Card className="p-6 md:p-8 space-y-6 animate-fadeIn border-[var(--border)]">
          {/* Completion Celebration Hero */}
          <div className="text-center py-6 space-y-3">
            <div className="w-16 h-16 rounded-3xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/20 shadow-sm">
              <Award size={36} />
            </div>
            <div className="space-y-1">
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight">
                Activity Completed!
              </h2>
              <p className="text-xs sm:text-sm text-[var(--text-soft)] max-w-md mx-auto">
                You have successfully completed the practical learning journey for <strong>{selectedTopic || activity.topic}</strong> in <strong>{selectedSubject}</strong>.
              </p>
            </div>
          </div>

          {/* Summary Stats Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-4 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] text-center space-y-1">
              <div className="text-xl sm:text-2xl font-extrabold text-[var(--accent)]">
                {completedCount} / {stepsList.length}
              </div>
              <div className="text-xs text-[var(--text-soft)] font-medium">
                Steps Finished
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] text-center space-y-1">
              <div className="text-xl sm:text-2xl font-extrabold text-emerald-600 dark:text-emerald-400">
                {Object.values(evaluations).filter(e => e?.is_correct).length} / {questionsToShow.length}
              </div>
              <div className="text-xs text-[var(--text-soft)] font-medium">
                Checks Passed
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] text-center space-y-1">
              <div className="text-xl sm:text-2xl font-extrabold text-blue-600 dark:text-blue-400">
                {remainingTopicsCount}
              </div>
              <div className="text-xs text-[var(--text-soft)] font-medium">
                Topics Remaining
              </div>
            </div>

            <div className="p-4 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] text-center space-y-1">
              <div className="text-xl sm:text-2xl font-extrabold text-purple-600 dark:text-purple-400">
                100%
              </div>
              <div className="text-xs text-[var(--text-soft)] font-medium">
                Syllabus Grounded
              </div>
            </div>
          </div>

          {/* Student Reflections & Personal Notes */}
          <div className="p-5 rounded-2xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-3">
            <div className="flex items-center justify-between">
              <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                <FileText size={15} className="text-[var(--accent)]" />
                <span>My Observations & Notes (Saved to History)</span>
              </div>
              {notesSavedSuccess && (
                <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                  <Check size={12} strokeWidth={3} /> Saved!
                </span>
              )}
            </div>

            <textarea
              value={studentNotes}
              onChange={(e) => setStudentNotes(e.target.value)}
              placeholder="What surprised you during the experiment? Write down your observations, real measurements, or takeaways..."
              rows={3}
              className="w-full p-3.5 text-xs sm:text-sm rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] leading-relaxed resize-none"
            />

            <div className="flex justify-end">
              <Button
                onClick={handleSaveNotes}
                disabled={savingNotes || !studentNotes.trim()}
                size="sm"
                className="px-4 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
              >
                {savingNotes ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                <span>Save Notes to Activity Record</span>
              </Button>
            </div>
          </div>

          {/* Action Navigation: Next Topic / Revise / Select Subject */}
          <div className="pt-4 border-t border-[var(--border)] flex flex-col sm:flex-row items-center justify-between gap-3">
            <Button
              onClick={() => setCurrentStep(1)}
              variant="outline"
              className="w-full sm:w-auto px-4 py-2.5 text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
            >
              <RotateCcw size={14} />
              <span>Choose Another Subject</span>
            </Button>

            <div className="flex items-center gap-2 w-full sm:w-auto">
              <Button
                onClick={() => setCurrentStep(3)}
                variant="outline"
                className="flex-1 sm:flex-initial px-4 py-2.5 text-xs font-semibold flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <BookOpen size={14} />
                <span>Revise Concept</span>
              </Button>

              <Button
                onClick={handleLearnNextTopic}
                className="flex-1 sm:flex-initial px-6 py-2.5 min-h-[44px] flex items-center justify-center gap-2 font-bold text-xs sm:text-sm cursor-pointer shadow-sm"
              >
                <span>Learn Next Topic</span>
                <ArrowRight size={15} />
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* ── Activity History Modal ── */}
      {showHistoryModal && (
        <div 
          className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-fadeIn"
          onClick={(e) => { if (e.target === e.currentTarget) setShowHistoryModal(false); }}
        >
          <div 
            role="dialog"
            aria-modal="true"
            aria-labelledby="activity-history-title"
            aria-describedby="activity-history-desc"
            className="bg-[var(--surface-elevated)] border border-[var(--border)] rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden"
          >
            {/* Header */}
            <div className="p-5 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-muted)]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-[var(--accent-dim)] text-[var(--accent)]">
                  <History size={18} />
                </div>
                <div>
                  <h2 id="activity-history-title" className="text-base font-bold text-[var(--text)]">Activity History</h2>
                  <p id="activity-history-desc" className="text-xs text-[var(--text-soft)]">
                    Revisit your past Learn from Anywhere activities, check understanding scores, and add reflections.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
                aria-label="Close activity history dialog"
                className="p-1.5 rounded-lg text-[var(--text-faint)] hover:text-[var(--text)] hover:bg-[var(--surface)] transition-all cursor-pointer"
              >
                <X size={18} />
              </button>
            </div>

            {/* Sub-header info & count */}
            <div className="px-5 py-3 border-b border-[var(--border)] bg-[var(--surface)] flex items-center justify-between text-xs">
              <span className="font-semibold text-[var(--text-soft)]">
                Total Saved Activities: <strong className="text-[var(--text)]">{historyTotal}</strong>
              </span>
              <button
                type="button"
                onClick={() => loadHistory(historyPage)}
                disabled={historyLoading}
                className="flex items-center gap-1 text-[var(--accent)] font-semibold hover:underline cursor-pointer"
              >
                <RefreshCw size={12} className={historyLoading ? 'animate-spin' : ''} />
                <span>Refresh</span>
              </button>
            </div>

            {/* List */}
            <div className="p-5 overflow-y-auto flex-1 space-y-4">
              {historyLoading && historyList.length === 0 ? (
                <div className="py-12 flex flex-col items-center justify-center text-[var(--text-soft)] space-y-2">
                  <Loader2 size={24} className="animate-spin text-[var(--accent)]" />
                  <p className="text-xs">Loading activity history...</p>
                </div>
              ) : historyList.length === 0 ? (
                <div className="py-12 text-center space-y-2">
                  <Clock size={32} className="mx-auto text-[var(--text-faint)]" />
                  <p className="text-sm font-semibold text-[var(--text)]">No Activity History Found</p>
                  <p className="text-xs text-[var(--text-soft)] max-w-sm mx-auto">
                    When you complete Learn from Anywhere activities, they will automatically be saved here for you to revisit anytime.
                  </p>
                </div>
              ) : (
                historyList.map((item) => {
                  const createdDate = item.created_at ? new Date(item.created_at).toLocaleDateString(undefined, {
                    year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
                  }) : 'Unknown date'
                  const isEditing = editingReflectionId === item.activity_id

                  return (
                    <Card key={item.activity_id || item._id} className="p-5 space-y-4 border-[var(--border)] hover:border-[var(--accent-dim)] transition-all">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                        <div className="space-y-1.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="px-2.5 py-1 rounded-md bg-[var(--accent-dim)] text-[var(--accent)] text-xs font-bold">
                              {item.subject} • {item.topic}
                            </span>
                            {item.is_current_curriculum ? (
                              <span className="px-3 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-xs font-semibold flex items-center gap-1.5">
                                <ShieldCheck size={12} /> Current Curriculum
                              </span>
                            ) : (
                              <span className="px-3 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-xs font-semibold flex items-center gap-1.5">
                                <AlertTriangle size={12} /> Previous Curriculum
                              </span>
                            )}
                            <span className={`px-2.5 py-0.5 rounded-full text-xs font-semibold ${
                              item.completion_status === 'completed'
                                ? 'bg-emerald-500/10 text-emerald-600'
                                : item.completion_status === 'in_progress'
                                ? 'bg-blue-500/10 text-blue-600'
                                : 'bg-gray-500/10 text-gray-600'
                            }`}>
                              {item.completion_status === 'completed' ? 'Completed' : item.completion_status === 'in_progress' ? 'In Progress' : 'Not Started'}
                            </span>
                          </div>
                          <h3 className="text-base font-bold text-[var(--text)]">{item.title}</h3>
                          <div className="text-xs sm:text-sm text-[var(--text-soft)] flex items-center gap-3 flex-wrap">
                            <span>Syllabus: <strong>{item.curriculum_reference || 'Validated Syllabus'}</strong></span>
                            <span>Date: {createdDate}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleRevisitActivity(item)}
                            className="px-3.5 py-2 rounded-xl bg-[var(--accent)] text-white text-xs sm:text-sm font-bold flex items-center gap-2 hover:opacity-90 transition-all cursor-pointer shadow-xs min-h-[40px]"
                          >
                            <Eye size={15} /> Revisit Activity
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteHistoryItem(item.activity_id)}
                            className="p-2 rounded-xl text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 border border-red-200 dark:border-red-900/40 transition-all cursor-pointer min-h-[40px] min-w-[40px] flex items-center justify-center"
                            title="Delete Activity Record"
                            aria-label="Delete activity record"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>

                      {/* Concept Checks / Attempts summary */}
                      {Array.isArray(item.attempts) && item.attempts.length > 0 && (
                        <div className="p-3 rounded-xl bg-[var(--surface-muted)] text-xs sm:text-sm text-[var(--text-soft)] space-y-1">
                          <div className="font-bold text-[var(--text)] flex items-center gap-1.5">
                            <Target size={14} className="text-[var(--accent)]" />
                            <span>Understanding Checks:</span>
                            <span className="ml-1 text-[var(--accent)]">{item.attempts.filter(a => a.is_correct).length} / {item.attempts.length} Passed</span>
                          </div>
                        </div>
                      )}

                      {/* Reflections section */}
                      <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-sm space-y-2.5">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[var(--text)] flex items-center gap-1.5 text-xs sm:text-sm">
                            <FileText size={14} className="text-[var(--accent)]" /> Student Reflections & Notes
                          </span>
                          {!isEditing && (
                            <button
                              type="button"
                              onClick={() => {
                                setEditingReflectionId(item.activity_id)
                                setReflectionText(item.reflections || '')
                              }}
                              className="text-xs sm:text-sm font-bold text-[var(--accent)] hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              <Edit3 size={13} /> {item.reflections ? 'Edit Notes' : 'Add Note'}
                            </button>
                          )}
                        </div>

                        {isEditing ? (
                          <div className="space-y-2.5">
                            <textarea
                              value={reflectionText}
                              onChange={(e) => setReflectionText(e.target.value)}
                              placeholder="Write your reflections, observations, or key takeaways for this activity..."
                              className="w-full p-3 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-elevated)] text-[var(--text)] text-sm focus:ring-2 focus:ring-[var(--accent)]"
                              rows={3}
                            />
                            <div className="flex justify-end gap-2.5">
                              <button
                                type="button"
                                onClick={() => setEditingReflectionId(null)}
                                className="px-3 py-1.5 text-xs sm:text-sm font-semibold text-[var(--text-soft)] hover:underline cursor-pointer"
                              >
                                Cancel
                              </button>
                              <button
                                type="button"
                                onClick={() => handleSaveReflection(item.activity_id, reflectionText)}
                                disabled={savingReflection}
                                className="px-3.5 py-1.5 rounded-lg bg-[var(--accent)] text-white text-xs sm:text-sm font-bold flex items-center gap-1.5 cursor-pointer min-h-[38px]"
                              >
                                {savingReflection ? <Loader2 size={13} className="animate-spin" /> : <Save size={13} />}
                                <span>Save Reflection</span>
                              </button>
                            </div>
                          </div>
                        ) : item.reflections ? (
                          <p className="text-xs sm:text-sm text-[var(--text-soft)] leading-relaxed italic">
                            "{item.reflections}"
                          </p>
                        ) : (
                          <p className="text-xs sm:text-sm text-[var(--text-faint)] italic">
                            No reflections saved yet. Click "Add Note" to write your personal observations.
                          </p>
                        )}
                      </div>
                    </Card>
                  )
                })
              )}
            </div>

            {/* Footer Pagination */}
            {historyTotal > 10 && (
              <div className="p-4 border-t border-[var(--border)] bg-[var(--surface-muted)] flex items-center justify-between text-xs">
                <span className="text-[var(--text-soft)]">
                  Page {historyPage} of {Math.ceil(historyTotal / 10)}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    disabled={historyPage <= 1 || historyLoading}
                    onClick={() => loadHistory(historyPage - 1)}
                    className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-[var(--text)] disabled:opacity-40 cursor-pointer flex items-center gap-1 font-semibold"
                  >
                    <ChevronLeft size={14} /> Prev
                  </button>
                  <button
                    type="button"
                    disabled={!historyHasMore || historyLoading}
                    onClick={() => loadHistory(historyPage + 1)}
                    className="px-3 py-1.5 rounded-lg border border-[var(--border)] text-[var(--text)] disabled:opacity-40 cursor-pointer flex items-center gap-1 font-semibold"
                  >
                    Next <ChevronRight size={14} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </div>
  )
}
