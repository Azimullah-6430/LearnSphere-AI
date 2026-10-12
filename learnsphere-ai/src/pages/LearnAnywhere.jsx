import { useState, useEffect, useMemo, useCallback, useRef } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
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
  Info,
  Wifi,
  WifiOff,
  History,
  Trash2,
  Edit3,
  Save,
  Calendar,
  Clock,
  ChevronLeft,
  ChevronRight,
  FileText,
  Code,
  Copy,
  ChevronDown,
  ChevronUp,
  Terminal,
  Play,
  Bug,
  BookOpenCheck
} from 'lucide-react'

const RESOURCE_ENVIRONMENTS = [
  { id: 'All Local Resources', label: 'All Village Resources', icon: Compass },
  { id: 'Farmland & Soil', label: 'Farmland & Soil', icon: Sprout },
  { id: 'Sunlight & Shadows', label: 'Sunlight & Shadows', icon: Sun },
  { id: 'Village Water & Wells', label: 'Water & Irrigation', icon: Droplets },
  { id: 'Plants & Bio Resources', label: 'Plants & Natural Bio', icon: TreePine },
  { id: 'Household & Crafts', label: 'Household & Clay Pots', icon: Home },
  { id: 'Bicycle & Simple Tools', label: 'Bicycle & Simple Tools', icon: Wrench },
]

const QUICK_MATERIAL_TAGS = [
  'Red Clay / Farm Soil',
  'River Sand',
  'Sunlight & Cardboard',
  'Turmeric Powder',
  'Hibiscus Petals',
  'Charcoal / Wood Ash',
  'Clay Pot (Matka)',
  'Bicycle Wheel / Chain',
  'Clean Water & Glass',
  'Cotton Thread & Ruler',
  'Mustard / Gram Seeds',
  'Banana Leaf'
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

export default function LearnAnywhere() {
  const { user, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, units: allUnits } = useAuthoritativeCurriculum()
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)
  const requestIdRef = useRef(0)

  const [selectedSubject, setSelectedSubject] = useState(subjects[0] || '')
  const [selectedTopic, setSelectedTopic] = useState('')
  const [learningMethod, setLearningMethod] = useState('auto')
  const [customMaterials, setCustomMaterials] = useState('')
  const [constraintMode, setConstraintMode] = useState('strict_only') // 'strict_only' | 'allow_minimal_common'
  const [selectedEnv, setSelectedEnv] = useState('All Local Resources')
  const [difficulty, setDifficulty] = useState('Medium')
  const [preferredLanguage, setPreferredLanguage] = useState('English')
  const [imagePreview, setImagePreview] = useState(null)
  const [imageData, setImageData] = useState('')

  const [loading, setLoading] = useState(false)
  const [activity, setActivity] = useState(null)
  const [completedSteps, setCompletedSteps] = useState({})
  const [checkedMaterials, setCheckedMaterials] = useState({})
  const [revealedQuestions, setRevealedQuestions] = useState({})
  const [showReflectionAnswer, setShowReflectionAnswer] = useState(false)
  const [showAcademicTheory, setShowAcademicTheory] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  // Student On-Demand Assistance Action State
  const [actionLoading, setActionLoading] = useState(false)
  const [actionResult, setActionResult] = useState(null)
  const [copyCodeSuccess, setCopyCodeSuccess] = useState(false)

  // Interactive Learning & Attempt Tracking State
  const [userAnswers, setUserAnswers] = useState({})
  const [evaluations, setEvaluations] = useState({})
  const [evaluatingQ, setEvaluatingQ] = useState({})
  const [attemptsCount, setAttemptsCount] = useState({})
  const [additionalPractice, setAdditionalPractice] = useState([])
  const [loadingPractice, setLoadingPractice] = useState(false)
  const [saveStatus, setSaveStatus] = useState('idle') // 'idle' | 'saving' | 'saved'

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

  // Rural Network Connectivity Status Tracking
  const [isOnline, setIsOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true)

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
    }
  }

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

  // User-scoped cache loader: ensure Student A's cached activity is NEVER presented to Student B
  useEffect(() => {
    // Reset transient state on user change to prevent cross-account stale cache leakage
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
    try {
      const rawCache = sessionStorage.getItem(cacheKey)
      if (rawCache) {
        const parsed = JSON.parse(rawCache)
        if (parsed && parsed.user_id === currentUid && parsed.activity) {
          setActivity(parsed.activity)
          if (parsed.completedSteps) setCompletedSteps(parsed.completedSteps)
          restoredFromCache = true
        }
      }
    } catch (e) {
      console.warn('Could not read user activity cache', e)
    }

    // If no session cached locally, check server session endpoint to restore active activity
    if (!restoredFromCache && navigator.onLine) {
      api.getLearnAnywhereSession().then(res => {
        if (res && res.success && res.activity) {
          setActivity(res.activity)
          if (res.subject) setSelectedSubject(res.subject)
          if (res.topic) setSelectedTopic(res.topic)
        }
      }).catch(err => {
        console.warn('Session restoration check skipped:', err)
      })
    }
  }, [user])

  // Handle On-Demand Student Assistance Actions (Simpler Explanation, Another Example, Worked Solution, Challenge Task)
  const handleStudentAction = async (actionType) => {
    if (!selectedSubject) return
    setActionLoading(true)
    setErrorMsg('')
    try {
      const activeTopicTarget = selectedTopic || validatedSubjectTopics[0] || 'Core Concept'
      const firstQ = activity?.understanding_questions?.[0]?.question || ''
      const res = await api.generateLearnAnywhereAction({
        action_type: actionType,
        subject: selectedSubject,
        topic: activeTopicTarget,
        question: firstQ,
        current_explanation: activity?.simple_explanation || activity?.scientific_principle || '',
        current_example: activity?.expected_observation || '',
        preferred_language: preferredLanguage
      })

      if (res && res.success && res.result) {
        setActionResult(res.result)
      } else {
        setErrorMsg(res?.error || 'Could not process request. Please try again.')
      }
    } catch (err) {
      setErrorMsg(err?.message || 'Error communicating with assistant.')
    } finally {
      setActionLoading(false)
    }
  }

  // Copy Code Helper for Coding Block
  const handleCopyCode = (codeText) => {
    if (!codeText || typeof navigator === 'undefined') return
    navigator.clipboard.writeText(codeText).then(() => {
      setCopyCodeSuccess(true)
      setTimeout(() => setCopyCodeSuccess(false), 2000)
    }).catch(err => {
      console.warn('Failed to copy code:', err)
    })
  }

  // Sync selectedSubject with authoritative subjects
  useEffect(() => {
    if (subjects.length > 0 && (!selectedSubject || !subjects.includes(selectedSubject))) {
      setSelectedSubject(subjects[0])
    }
  }, [subjects, selectedSubject])

  // Extract validated topics specifically for the active subject from authoritative syllabus
  const validatedSubjectTopics = useMemo(() => {
    if (!selectedSubject) return []
    const topics = []
    const chaptersDict = curriculum?.chapters || curriculum?.units || allUnits || {}
    if (chaptersDict[selectedSubject]) {
      const uList = chaptersDict[selectedSubject]
      if (Array.isArray(uList)) {
        uList.forEach(u => {
          if (typeof u === 'object' && u !== null) {
            if (u.name) topics.push(u.name)
            if (Array.isArray(u.concepts)) topics.push(...u.concepts)
          } else if (typeof u === 'string') {
            topics.push(u)
          }
        })
      }
    }
    // Also inspect subjects array in curriculum
    if (Array.isArray(curriculum?.subjects)) {
      const subObj = curriculum.subjects.find(s =>
        (typeof s === 'object' && s.name === selectedSubject) || s === selectedSubject
      )
      if (subObj && typeof subObj === 'object') {
        if (Array.isArray(subObj.topics)) topics.push(...subObj.topics)
        if (Array.isArray(subObj.units)) {
          subObj.units.forEach(u => {
            if (typeof u === 'object' && u !== null) {
              if (u.name) topics.push(u.name)
              if (Array.isArray(u.concepts)) topics.push(...u.concepts)
            } else if (typeof u === 'string') {
              topics.push(u)
            }
          })
        }
      }
    }
    return Array.from(new Set(topics.filter(Boolean)))
  }, [selectedSubject, curriculum, allUnits])

  // Match active subject metadata from authoritative curriculum
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

  // Reset activity and error states when active syllabus changes or is replaced
  const activeSyllabusId = curriculum?.syllabus_id || curriculum?.syllabusId || ''
  useEffect(() => {
    setActivity(null)
    setCompletedSteps({})
    setCheckedMaterials({})
    setUserAnswers({})
    setEvaluations({})
    setAttemptsCount({})
    setAdditionalPractice([])
    setActionResult(null)
    setErrorMsg('')
  }, [activeSyllabusId])

  // Clear incompatible previous activity content when selection changes
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
  }, [])

  // Handle Subject selection and synchronously reset topic and transient activity state
  const handleSubjectSelect = useCallback((newSub) => {
    if (newSub === selectedSubject) return
    setSelectedSubject(newSub)
    clearActivityState()
    const topics = []
    const chaptersDict = curriculum?.chapters || curriculum?.units || allUnits || {}
    if (chaptersDict[newSub]) {
      const uList = chaptersDict[newSub]
      if (Array.isArray(uList)) {
        uList.forEach(u => {
          if (typeof u === 'object' && u !== null) {
            if (u.name) topics.push(u.name)
            if (Array.isArray(u.concepts)) topics.push(...u.concepts)
          } else if (typeof u === 'string') {
            topics.push(u)
          }
        })
      }
    }
    if (Array.isArray(curriculum?.subjects)) {
      const subObj = curriculum.subjects.find(s =>
        (typeof s === 'object' && s.name === newSub) || s === newSub
      )
      if (subObj && typeof subObj === 'object') {
        if (Array.isArray(subObj.topics)) topics.push(...subObj.topics)
        if (Array.isArray(subObj.units)) {
          subObj.units.forEach(u => {
            if (typeof u === 'object' && u !== null) {
              if (u.name) topics.push(u.name)
              if (Array.isArray(u.concepts)) topics.push(...u.concepts)
            } else if (typeof u === 'string') {
              topics.push(u)
            }
          })
        }
      }
    }
    const cleanTopics = Array.from(new Set(topics.filter(Boolean)))
    setSelectedTopic(cleanTopics[0] || '')
  }, [selectedSubject, clearActivityState, curriculum, allUnits])

  // Handle Topic selection and clear incompatible activity content
  const handleTopicSelect = useCallback((newTopic) => {
    if (newTopic === selectedTopic) return
    setSelectedTopic(newTopic)
    clearActivityState()
  }, [selectedTopic, clearActivityState])

  // Set default topic when subject topics change
  useEffect(() => {
    if (validatedSubjectTopics.length > 0 && (!selectedTopic || !validatedSubjectTopics.includes(selectedTopic))) {
      setSelectedTopic(validatedSubjectTopics[0])
    }
  }, [validatedSubjectTopics, selectedTopic])

  // Handle Image Upload with MIME and Size Validation
  const handleImageChange = (e) => {
    const file = e.target.files?.[0]
    if (!file) return

    const allowedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp', 'image/gif', 'image/bmp']
    if (file.type && !allowedTypes.includes(file.type.toLowerCase())) {
      setErrorMsg('Unsupported image format. Please upload JPEG, PNG, WEBP, GIF, or BMP format images.')
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

  const handleGenerateActivity = useCallback(async () => {
    if (!selectedSubject) return
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setErrorMsg('Internet connection is required to generate new AI activities. Your previously loaded activity remains readable below.')
      return
    }

    requestIdRef.current += 1
    const currentRequestId = requestIdRef.current

    setLoading(true)
    setErrorMsg('')
    setShowReflectionAnswer(false)
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
      })

      if (currentRequestId !== requestIdRef.current) {
        console.warn('Superseded generation request completed; discarding out-of-order response.')
        return
      }

      if (res && res.success && res.activity) {
        const returnedSub = String(res.activity?.academic_grounding?.subject || res.activity?.subject || res.subject || '').trim().toLowerCase()
        if (returnedSub && returnedSub !== selectedSubject.trim().toLowerCase()) {
          console.warn(`Mismatched subject returned from API: expected '${selectedSubject}', got '${returnedSub}'`)
          setActivity(null)
          setErrorMsg(`Returned activity did not match requested subject '${selectedSubject}'. Please click Retry to generate a clean activity.`)
          return
        }

        setActivity(res.activity)
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
        setErrorMsg(res?.error || 'Failed to design practical activity. Please check your connection and retry.')
      }
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) return
      setActivity(null)
      setErrorMsg(err?.message || 'Connection error while contacting the activity generator. Please try again.')
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setLoading(false)
      }
    }
  }, [selectedSubject, activeSubjectId, selectedTopic, validatedSubjectTopics, selectedEnv, difficulty, preferredLanguage, customMaterials, constraintMode, imageData, activeSyllabusId, recordActivity, user])

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
        total_steps: activity.steps?.length || 0
      })
      if (res && res.success) {
        setSaveStatus('saved')
      } else {
        setSaveStatus('idle')
      }
    } catch {
      setSaveStatus('idle')
    }
  }, [activity, selectedSubject, selectedTopic, activeSyllabusId, completedSteps, evaluations, attemptsCount])

  const toggleStep = (index) => {
    const updated = {
      ...completedSteps,
      [index]: !completedSteps[index]
    }
    setCompletedSteps(updated)
    handleSaveProgress(updated, evaluations)
  }

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

  const toggleMaterial = (index) => {
    setCheckedMaterials(prev => ({
      ...prev,
      [index]: !prev[index]
    }))
  }

  // Teacher Guard: Learn from Anywhere is reserved exclusively for Student Portal
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

  // Curriculum Gate: If no valid syllabus, show CurriculumReviewNotice
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

  const totalSteps = activity?.steps?.length || 0
  const completedCount = Object.values(completedSteps).filter(Boolean).length
  const progressPercent = totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0

  return (
    <div className="space-y-6">
      <PageHead
        title="Learn from Anywhere"
        subtitle="Turn everyday surroundings and local materials into hands-on science and engineering experiments aligned with your syllabus."
        action={
          <div className="flex items-center gap-2">
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
                <Wifi size={12} className="text-emerald-500" /> Data-Saver Mode
              </span>
            ) : (
              <span className="px-3 py-1 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                <WifiOff size={12} className="text-amber-500" /> Offline Mode
              </span>
            )}
          </div>
        }
      />

      {/* Offline Status Alert Banner */}
      {!isOnline && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-300 text-xs font-semibold flex items-center gap-2.5 animate-fadeIn">
          <WifiOff size={16} className="text-amber-500 shrink-0" />
          <div className="flex-1 leading-relaxed">
            <strong>Offline Reading Mode: </strong>
            Your connection is currently unavailable. Your previously loaded activity instructions remain readable below. Reconnect to generate new activities.
          </div>
        </div>
      )}

      {/* Setup & Resource Filter Card */}
      <Card className="p-5 md:p-7 shadow-sm space-y-6 border-[var(--border)]">
        {/* 1. Validated Syllabus Subject Selector */}
        <div>
          <label className="text-sm sm:text-base font-semibold text-[var(--text)] mb-2.5 flex items-center gap-2">
            <BookOpen size={16} className="text-[var(--accent)]" />
            <span>1. Choose Validated Syllabus Subject</span>
          </label>
          <div className="flex gap-2.5 flex-wrap" role="radiogroup" aria-label="Select Subject">
            {subjects.map((sub) => {
              const isSelected = selectedSubject === sub
              return (
                <button
                  key={sub}
                  type="button"
                  onClick={() => handleSubjectSelect(sub)}
                  className={`min-h-[44px] px-4 py-2 rounded-xl text-sm font-semibold border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                      : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:border-[var(--accent-dim)] hover:text-[var(--text)]'
                  }`}
                  aria-checked={isSelected}
                >
                  {sub}
                </button>
              )
            })}
          </div>
        </div>

        {/* 2. Syllabus Topic Selector (Populated exclusively from active syllabus) */}
        {validatedSubjectTopics.length > 0 && (
          <div>
            <label className="text-sm sm:text-base font-semibold text-[var(--text)] mb-2.5 flex items-center gap-2">
              <Target size={16} className="text-[var(--accent)]" />
              <span>2. Select Syllabus Topic / Unit</span>
            </label>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2.5">
              {validatedSubjectTopics.slice(0, 9).map((top) => {
                const isSelected = selectedTopic === top
                return (
                  <button
                    key={top}
                    type="button"
                    onClick={() => handleTopicSelect(top)}
                    className={`min-h-[46px] px-4 py-2.5 rounded-xl text-left text-sm font-medium border transition-all truncate flex items-center justify-between gap-2 cursor-pointer ${
                      isSelected
                        ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] font-semibold shadow-2xs'
                        : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
                    }`}
                    title={top}
                  >
                    <span className="truncate">{top}</span>
                    {isSelected && <Check size={16} className="text-[var(--accent)] shrink-0" />}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* 3. Learning Strategy & Method Selector */}
        <div>
          <label className="text-sm sm:text-base font-semibold text-[var(--text)] mb-2.5 flex items-center gap-2">
            <BookOpenCheck size={16} className="text-[var(--accent)]" />
            <span>3. Choose Learning Method (Optional)</span>
          </label>
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2.5">
            {LEARNING_METHODS.map(({ id, label, icon: Icon, desc }) => {
              const isSelected = learningMethod === id
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setLearningMethod(id)
                    clearActivityState()
                  }}
                  className={`min-h-[58px] p-3 rounded-xl text-left border transition-all cursor-pointer flex flex-col justify-between ${
                    isSelected
                      ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] shadow-2xs'
                      : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
                  }`}
                >
                  <div className="flex items-center gap-1.5 font-semibold text-xs sm:text-sm">
                    <Icon size={15} className={isSelected ? 'text-[var(--accent)]' : 'opacity-70'} />
                    <span className="truncate">{label}</span>
                  </div>
                  <span className="text-xs text-[var(--text-soft)] font-normal line-clamp-1 mt-1">
                    {desc}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* 4. Local Surroundings & Material Environment Mode */}
        <div>
          <label className="text-sm sm:text-base font-semibold text-[var(--text)] mb-2.5 flex items-center gap-2">
            <Compass size={16} className="text-[var(--accent)]" />
            <span>4. Available Natural / Village Environment</span>
          </label>
          <div className="flex gap-2.5 flex-wrap">
            {RESOURCE_ENVIRONMENTS.map(({ id, label, icon: Icon }) => {
              const isSelected = selectedEnv === id
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSelectedEnv(id)}
                  className={`min-h-[44px] px-4 py-2.5 rounded-xl text-sm font-semibold border transition-all flex items-center gap-2 cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] font-semibold shadow-2xs'
                      : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <Icon size={16} className={isSelected ? 'text-[var(--accent)]' : 'opacity-70'} />
                  <span>{label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* 4. Text Description of Available Objects + Quick Add Tags */}
        <div className="space-y-2.5">
          <label className="text-sm sm:text-base font-semibold text-[var(--text)] flex items-center gap-2">
            <Wrench size={16} className="text-[var(--accent)]" />
            <span>4. Objects, Plants, Tools & Materials You Have (Optional Description)</span>
          </label>
          <textarea
            value={customMaterials}
            onChange={(e) => setCustomMaterials(e.target.value)}
            placeholder="e.g. Red clay, plastic bottle, turmeric, clean water, bicycle gears, sunlight, dry leaves, string..."
            rows={2}
            className="w-full px-4 py-3 text-sm sm:text-base rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)] leading-relaxed resize-none"
          />
          {/* Quick-add tags for budget mobile 1-tap entry */}
          <div className="flex items-center gap-2 flex-wrap pt-1">
            <span className="text-xs sm:text-sm font-semibold text-[var(--text-soft)]">Quick add:</span>
            {QUICK_MATERIAL_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => handleAddMaterialTag(tag)}
                className="px-3 py-1.5 text-xs sm:text-[13px] rounded-lg bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-[var(--text-soft)] font-medium transition-colors cursor-pointer"
              >
                + {tag}
              </button>
            ))}
          </div>
        </div>

        {/* 5. Image Upload & Constraint Mode Selection */}
        <div className="grid sm:grid-cols-2 gap-4 pt-3 border-t border-[var(--border)]">
          {/* Photo / Camera Option */}
          <div className="space-y-2.5">
            <label className="text-sm sm:text-base font-semibold text-[var(--text)] flex items-center gap-2">
              <Camera size={16} className="text-[var(--accent)]" />
              <span>Photograph Materials (Optional)</span>
            </label>
            {imagePreview ? (
              <div className="relative inline-block rounded-xl overflow-hidden border border-[var(--border-strong)] bg-[var(--surface-alt)] p-1">
                <img
                  src={imagePreview}
                  alt="Available materials"
                  className="h-20 w-32 object-cover rounded-lg"
                />
                <button
                  type="button"
                  onClick={handleRemoveImage}
                  className="absolute top-2 right-2 p-1 rounded-full bg-black/70 text-white hover:bg-black transition-colors cursor-pointer"
                  title="Remove photo"
                  aria-label="Remove photo"
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <label className="flex items-center gap-2 px-4 py-2.5 rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface-alt)]/50 hover:bg-[var(--surface-alt)] text-[var(--text-soft)] text-sm font-medium cursor-pointer transition-colors w-fit">
                <ImageIcon size={17} className="text-[var(--text-faint)]" />
                <span>Upload or take a photo of materials</span>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleImageChange}
                  className="hidden"
                />
              </label>
            )}
          </div>

          {/* Material Constraint Mode Selector */}
          <div className="space-y-2.5">
            <label className="text-sm sm:text-base font-semibold text-[var(--text)] flex items-center gap-2">
              <ShieldCheck size={16} className="text-[var(--accent)]" />
              <span>Material Requirement Preference</span>
            </label>
            <div className="grid grid-cols-2 gap-2.5">
              <button
                type="button"
                onClick={() => setConstraintMode('strict_only')}
                className={`min-h-[50px] p-2.5 rounded-xl text-left text-xs sm:text-sm font-semibold border transition-all cursor-pointer ${
                  constraintMode === 'strict_only'
                    ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 font-bold'
                    : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <CheckCircle2 size={14} className={constraintMode === 'strict_only' ? 'text-emerald-500' : 'opacity-40'} />
                  <span>Strictly Mine</span>
                </div>
                <div className="text-xs text-[var(--text-soft)] font-normal mt-0.5 leading-tight">
                  Only use materials listed
                </div>
              </button>

              <button
                type="button"
                onClick={() => setConstraintMode('allow_minimal_common')}
                className={`min-h-[50px] p-2.5 rounded-xl text-left text-xs sm:text-sm font-semibold border transition-all cursor-pointer ${
                  constraintMode === 'allow_minimal_common'
                    ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] font-bold'
                    : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  <Sparkles size={14} className={constraintMode === 'allow_minimal_common' ? 'text-[var(--accent)]' : 'opacity-40'} />
                  <span>Allow Common Items</span>
                </div>
                <div className="text-xs text-[var(--text-soft)] font-normal mt-0.5 leading-tight">
                  Allow water, thread, spoon
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Generate Trigger Footer */}
        <div className="pt-4 border-t border-[var(--border)] flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="flex items-center gap-3 w-full sm:w-auto flex-wrap">
            <div className="flex items-center gap-2">
              <span className="text-xs sm:text-sm font-semibold text-[var(--text-soft)]">Difficulty:</span>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="px-3 py-2 rounded-xl border border-[var(--border-strong)] text-sm font-medium bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] min-h-[42px]"
              >
                <option value="Easy">Easy (Everyday Observations)</option>
                <option value="Medium">Medium (Guided Hands-on)</option>
                <option value="Hard">Advanced (Analytical & Quantitative)</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-xs sm:text-sm font-semibold text-[var(--text-soft)]">Language:</span>
              <select
                value={preferredLanguage}
                onChange={(e) => setPreferredLanguage(e.target.value)}
                className="px-3 py-2 rounded-xl border border-[var(--border-strong)] text-sm font-medium bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] min-h-[42px]"
              >
                {EXPLANATION_LANGUAGES.map(lang => (
                  <option key={lang.id} value={lang.id}>{lang.label}</option>
                ))}
              </select>
            </div>
          </div>

          <Button
            onClick={handleGenerateActivity}
            disabled={loading}
            className="w-full sm:w-auto min-h-[46px] px-6 flex items-center justify-center gap-2 cursor-pointer shadow-sm text-sm sm:text-base font-bold"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Sparkles size={16} />}
            <span>{activity ? 'Generate Another Activity' : 'Design Practical Activity'}</span>
          </Button>
        </div>
      </Card>

      {/* Error & Retry State */}
      {errorMsg && (
        <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 text-xs font-semibold flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 animate-fadeIn">
          <div className="flex items-center gap-2">
            <AlertTriangle size={17} className="shrink-0 text-red-500" />
            <span>{errorMsg}</span>
          </div>
          <Button
            onClick={handleGenerateActivity}
            variant="outline"
            size="sm"
            className="shrink-0 flex items-center gap-1.5 border-red-500/30 text-red-600 dark:text-red-400 hover:bg-red-500/10 text-xs"
          >
            <RefreshCw size={12} />
            <span>Retry</span>
          </Button>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <Card className="p-10 md:p-14 text-center my-6 space-y-4 border-[var(--border)] animate-fadeIn">
          <Loader2 size={40} className="animate-spin text-[var(--accent)] mx-auto" />
          <div className="space-y-1">
            <h3 className="text-base font-bold text-[var(--text)]">
              Designing Grounded Village Activity...
            </h3>
            <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
              Grounding <strong>{selectedSubject}</strong> concepts ({selectedTopic || 'Core Syllabus Principle'}) into zero-cost practical experiments using locally available materials.
            </p>
          </div>
          <div className="flex items-center justify-center gap-2 text-[11px] text-[var(--text-faint)] font-medium">
            <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
            <span>Zero-Cost Local Resources Mode ({preferredLanguage})</span>
          </div>
        </Card>
      )}

      {/* Empty State (Before first generation) */}
      {!loading && !activity && !errorMsg && (
        <Card className="p-10 text-center space-y-3 border-dashed border-[var(--border-strong)] bg-[var(--surface)]/50">
          <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto">
            <Compass size={24} />
          </div>
          <h3 className="text-sm font-bold text-[var(--text)]">
            Ready to Explore Academic Concepts in Your Surroundings
          </h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
            Select your syllabus topic above, mention whatever materials you have around you, and click <strong>Design Practical Activity</strong> to start.
          </p>
          <Button
            onClick={handleGenerateActivity}
            size="sm"
            className="mt-2 text-xs font-bold inline-flex items-center gap-1.5"
          >
            <Sparkles size={13} />
            <span>Start Activity</span>
          </Button>
        </Card>
      )}

      {/* Generated Activity Presentation */}
      {!loading && activity && (
        <div className="space-y-6 animate-fadeIn">
          <div className="rounded-2xl bg-[var(--surface)] border border-[var(--border)] p-5 md:p-8 shadow-sm space-y-7">
            {/* Header / Badges */}
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-[var(--border)] pb-6">
              <div className="space-y-2.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge tone="accent">{activity.subject || selectedSubject}</Badge>
                  <span className="px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1.5">
                    <Compass size={13} /> {activity.resource_category || selectedEnv}
                  </span>
                  {activity.demonstration_type === 'thought_experiment_and_analog' ? (
                    <span className="px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/20 flex items-center gap-1.5">
                      <Lightbulb size={13} /> Thought Experiment & Physical Analog
                    </span>
                  ) : activity.demonstration_type === 'outdoor_observation' ? (
                    <span className="px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                      <TreePine size={13} /> Outdoor & Nature Observation
                    </span>
                  ) : (
                    <span className="px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-500/20 flex items-center gap-1.5">
                      <Home size={13} /> Household Hands-on Activity
                    </span>
                  )}
                  <span className="px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold bg-[var(--surface-alt)] text-[var(--text-soft)] border border-[var(--border)]">
                    Topic: {activity.syllabus_topic || selectedTopic || 'Syllabus Grounding'}
                  </span>
                  {(activity.syllabus_id || activeSyllabusId) && (
                    <span className="px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1.5">
                      <ShieldCheck size={13} /> Validated Syllabus Traceable
                    </span>
                  )}
                </div>
                <h2 className="heading-section text-2xl sm:text-3xl font-black text-[var(--text)] tracking-tight leading-snug">
                  {activity.title || activity.activity_title}
                </h2>
                <div className="text-sm sm:text-base text-[var(--text-soft)] flex items-start gap-2 pt-1">
                  <Lightbulb size={18} className="text-amber-500 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">
                    <strong className="text-[var(--text)]">Learning Objective: </strong>
                    {activity.learning_objective || (activity.learning_objectives && activity.learning_objectives[0])}
                  </span>
                </div>
              </div>

              {/* Progress Indicator Card */}
              <div className="shrink-0 bg-[var(--surface-alt)] p-4 rounded-2xl border border-[var(--border)] text-center min-w-[170px]">
                <div className="text-xs sm:text-sm font-semibold text-[var(--text-soft)] uppercase tracking-wider mb-1">
                  Practical Steps
                </div>
                <div className="text-2xl sm:text-3xl font-black text-[var(--accent)]">
                  {completedCount} / {totalSteps} Done
                </div>
                <div className="w-full bg-[var(--border)] h-2.5 rounded-full overflow-hidden mt-2.5">
                  <div
                    className="bg-[var(--accent)] h-full transition-all duration-300 rounded-full"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="text-xs font-semibold text-[var(--text-soft)] mt-2">
                  {progressPercent === 100 ? '🎉 Activity Complete!' : `${progressPercent}% Completed`}
                </div>
              </div>
            </div>

            {/* Non-Physical / Thought Experiment Feasibility Notice */}
            {activity.demonstration_type === 'thought_experiment_and_analog' && (
              <div className="p-4 md:p-5 rounded-xl bg-purple-500/10 border border-purple-500/20 text-sm sm:text-base text-purple-900 dark:text-purple-300 flex items-start gap-3">
                <Info size={20} className="text-purple-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong>Concept Feasibility Notice: </strong>
                  This syllabus topic involves microscopic, relativistic, or theoretical concepts that cannot be physically isolated in a household setting without specialized laboratory equipment. This activity uses rigorous thought experiments and macroscopic everyday analogs to build concrete scientific intuition.
                </div>
              </div>
            )}

            {/* Multimodal Image Observation & Analysis Block */}
            {activity.image_analysis && (
              <div className={`p-5 md:p-6 rounded-2xl border space-y-4 ${
                activity.image_analysis.image_processed
                  ? 'bg-sky-500/5 border-sky-500/20'
                  : 'bg-[var(--surface-alt)] border-[var(--border)]'
              }`}>
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-[var(--text)]">
                    <Camera size={18} className={activity.image_analysis.image_processed ? 'text-sky-500' : 'text-[var(--text-faint)]'} />
                    <span>Image Observation & Visual Identification</span>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold border ${
                    activity.image_analysis.image_processed
                      ? 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30'
                      : 'bg-gray-500/10 text-gray-600 dark:text-gray-400 border-gray-500/20'
                  }`}>
                    {activity.image_analysis.image_processed
                      ? `Confidence: ${activity.image_analysis.confidence_level || 'High'}`
                      : 'Text Fallback / No Image'}
                  </span>
                </div>

                {activity.image_analysis.image_processed ? (
                  <div className="space-y-3 text-sm sm:text-base text-[var(--text-soft)]">
                    <div className="font-semibold text-[var(--text)] flex items-center gap-2">
                      <Target size={16} className="text-sky-500" />
                      <span>Identified Object / Structure: </span>
                      <span className="font-bold text-sky-700 dark:text-sky-300">
                        {activity.image_analysis.identified_object_or_structure}
                      </span>
                    </div>

                    {activity.image_analysis.visible_features?.length > 0 && (
                      <div className="space-y-1.5">
                        <div className="text-xs sm:text-sm font-semibold text-[var(--text-soft)]">
                          Observed Visual Features:
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {activity.image_analysis.visible_features.map((feat, fIdx) => (
                            <span key={fIdx} className="px-2.5 py-1 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-xs sm:text-sm font-medium text-[var(--text)]">
                              • {feat}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {activity.image_analysis.syllabus_connection && (
                      <p className="text-sm sm:text-base leading-relaxed pt-1 text-[var(--text)]">
                        <strong>Syllabus Connection: </strong>
                        {activity.image_analysis.syllabus_connection}
                      </p>
                    )}

                    {activity.image_analysis.clarification_needed && (
                      <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-300 text-sm flex items-start gap-2.5 mt-2">
                        <HelpCircle size={16} className="text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <strong>Clarification Needed: </strong>
                          {activity.image_analysis.clarification_needed}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed">
                    {activity.image_analysis.image_note || 'Generated a structured text-based practical activity based on your syllabus topic.'}
                  </p>
                )}
              </div>
            )}

            {/* Required Zero-Cost Materials Checklist */}
            <div className="p-5 md:p-6 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 space-y-4">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-emerald-800 dark:text-emerald-300">
                  <Sprout size={18} />
                  <span>Required Zero-Cost & Locally Sourced Materials</span>
                </div>
                <span className="text-xs sm:text-sm text-emerald-700 dark:text-emerald-400 font-medium">
                  Tap item to check off
                </span>
              </div>
              <div className="grid sm:grid-cols-2 gap-3">
                {(activity.local_materials || activity.materials_student_has || []).map((mat, idx) => {
                  const isChecked = Boolean(checkedMaterials[idx])
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleMaterial(idx)}
                      className={`min-h-[46px] p-3 rounded-xl border text-left text-sm sm:text-base flex items-start gap-3 transition-all cursor-pointer ${
                        isChecked
                          ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-900 dark:text-emerald-100 line-through opacity-80'
                          : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)] hover:border-emerald-500/40'
                      }`}
                    >
                      <div className={`w-5 h-5 rounded-md flex items-center justify-center shrink-0 mt-0.5 border text-xs font-bold ${
                        isChecked ? 'bg-emerald-500 text-white border-emerald-500' : 'border-[var(--border-strong)] bg-[var(--surface)]'
                      }`}>
                        {isChecked ? '✓' : ''}
                      </div>
                      <span className="leading-snug">{mat}</span>
                    </button>
                  )
                })}
              </div>

              {/* No Purchase Alternative & Safe Substitutions */}
              {(activity.no_purchase_alternative || (activity.safe_substitutions && activity.safe_substitutions.length > 0)) && (
                <div className="pt-2.5 border-t border-emerald-500/20 text-sm sm:text-base text-emerald-900 dark:text-emerald-300 space-y-1">
                  <div className="font-bold flex items-center gap-2">
                    <ShieldCheck size={16} className="text-emerald-600 dark:text-emerald-400" />
                    <span>No-Purchase Zero-Cost Substitutions:</span>
                  </div>
                  <p className="opacity-95 leading-relaxed text-sm">
                    {activity.no_purchase_alternative || activity.safe_substitutions?.join(' • ')}
                  </p>
                </div>
              )}
            </div>

            {/* Step-by-Step Practical Instructions */}
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-sm sm:text-base font-bold text-[var(--text)] flex items-center gap-2">
                  <Layers size={17} className="text-[var(--accent)]" />
                  <span>Step-by-Step Procedure</span>
                </div>
                <span className="text-xs sm:text-sm text-[var(--text-soft)]">
                  Tap step to mark complete
                </span>
              </div>
              <div className="space-y-3">
                {(activity.steps || []).map((step, idx) => {
                  const isDone = Boolean(completedSteps[idx])
                  return (
                    <div
                      key={idx}
                      onClick={() => toggleStep(idx)}
                      className={`min-h-[54px] p-4 md:p-5 rounded-xl border transition-all cursor-pointer flex items-start gap-4 ${
                        isDone
                          ? 'bg-[var(--accent-soft)]/50 border-[var(--accent)] text-[var(--text)] shadow-2xs'
                          : 'bg-[var(--surface-alt)]/60 border-[var(--border)] hover:border-[var(--border-strong)] text-[var(--text-soft)]'
                      }`}
                      role="checkbox"
                      aria-checked={isDone}
                      tabIndex={0}
                      onKeyDown={(e) => {
                        if (e.key === ' ' || e.key === 'Enter') {
                          e.preventDefault()
                          toggleStep(idx)
                        }
                      }}
                    >
                      <div className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 border text-sm font-bold transition-colors ${
                        isDone ? 'bg-[var(--accent)] text-white border-[var(--accent)]' : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)]'
                      }`}>
                        {isDone ? '✓' : idx + 1}
                      </div>
                      <div className="text-sm sm:text-base font-medium leading-relaxed flex-1">
                        {step}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Observation & Simple Explanation Grid */}
            <div className="grid md:grid-cols-2 gap-5 pt-3 border-t border-[var(--border)]">
              <div className="p-5 md:p-6 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2.5">
                <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-[var(--text)]">
                  <Eye size={18} className="text-blue-500" />
                  <span>What You Will Observe</span>
                </div>
                <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed">
                  {activity.expected_observation || activity.expected_observations}
                </p>
              </div>

              <div className="p-5 md:p-6 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2.5">
                <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-[var(--text)]">
                  <Lightbulb size={18} className="text-amber-500" />
                  <span>Simple Explanation (Why It Works)</span>
                </div>
                <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed font-normal">
                  {activity.simple_explanation || activity.scientific_principle}
                </p>
              </div>
            </div>

            {/* Readable Dark Monospace Code Block Component (for Computer Science / Coding Tasks) */}
            {(activity.coding_task || activity.code_snippet) && (() => {
              const codeObj = activity.coding_task || { code: activity.code_snippet, language: 'python', task_objective: 'Algorithm Implementation' }
              return (
                <div className="rounded-2xl bg-gray-900 border border-gray-800 text-gray-100 overflow-hidden shadow-md space-y-0 my-5">
                  <div className="px-5 py-3.5 bg-gray-950 border-b border-gray-800 flex items-center justify-between flex-wrap gap-2.5">
                    <div className="flex items-center gap-2.5 text-sm font-mono font-bold text-emerald-400">
                      <Code size={17} />
                      <span className="uppercase">{codeObj.language || 'Python / Pseudocode'}</span>
                      <span className="text-xs text-gray-300 font-normal border border-gray-700 rounded-md px-2.5 py-0.5">
                        {codeObj.task_objective || 'Executable Code Task'}
                      </span>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleCopyCode(codeObj.code)}
                      className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs sm:text-sm font-mono font-semibold flex items-center gap-1.5 transition-colors cursor-pointer"
                    >
                      {copyCodeSuccess ? <Check size={15} className="text-emerald-400" /> : <Copy size={15} />}
                      <span>{copyCodeSuccess ? 'Copied!' : 'Copy Code'}</span>
                    </button>
                  </div>

                  {/* Code Editor Body */}
                  <pre className="p-5 md:p-6 text-sm sm:text-base font-mono text-emerald-300 overflow-x-auto leading-relaxed whitespace-pre font-normal bg-gray-900/90 selection:bg-emerald-900 selection:text-white">
                    <code>{codeObj.code}</code>
                  </pre>

                  {/* Logic Breakdown & Execution Box */}
                  <div className="p-5 bg-gray-950/80 border-t border-gray-800 text-sm text-gray-300 space-y-3.5">
                    {codeObj.logic_breakdown && codeObj.logic_breakdown.length > 0 && (
                      <div className="space-y-2">
                        <div className="text-xs sm:text-sm font-mono font-bold uppercase text-emerald-400 tracking-wider flex items-center gap-1.5">
                          <Terminal size={15} /> Logic Breakdown:
                        </div>
                        <ul className="space-y-1.5 pl-1">
                          {codeObj.logic_breakdown.map((lb, lbIdx) => (
                            <li key={lbIdx} className="text-xs sm:text-sm text-gray-300 flex items-start gap-2">
                              <span className="text-emerald-500 font-mono shrink-0">•</span>
                              <span className="leading-relaxed">{lb}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="grid sm:grid-cols-2 gap-3.5 pt-1">
                      {codeObj.run_command && (
                        <div className="p-3 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                          <div className="text-xs font-mono font-bold text-gray-400 uppercase flex items-center gap-1.5">
                            <Play size={13} className="text-emerald-400" /> How to Run:
                          </div>
                          <div className="text-xs sm:text-sm font-mono text-emerald-300 font-bold">
                            {codeObj.run_command}
                          </div>
                        </div>
                      )}

                      {codeObj.expected_output && (
                        <div className="p-3 rounded-xl bg-gray-900 border border-gray-800 space-y-1">
                          <div className="text-xs font-mono font-bold text-gray-400 uppercase flex items-center gap-1.5">
                            <CheckCircle2 size={13} className="text-sky-400" /> Expected Output:
                          </div>
                          <div className="text-xs sm:text-sm font-mono text-sky-300">
                            {codeObj.expected_output}
                          </div>
                        </div>
                      )}
                    </div>

                    {codeObj.debugging_tips && (
                      <div className="p-3 rounded-xl bg-amber-950/40 border border-amber-800/40 text-amber-300 text-xs sm:text-sm flex items-start gap-2.5">
                        <Bug size={16} className="text-amber-400 shrink-0 mt-0.5" />
                        <div className="leading-relaxed">
                          <strong>Debugging Guidance: </strong>
                          {codeObj.debugging_tips}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )
            })()}

            {/* Expandable Accordion for Academic Theory (Avoid Walls of Text) */}
            {(activity.academic_theory || activity.scientific_principle) && (
              <div className="rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] overflow-hidden transition-all">
                <button
                  type="button"
                  onClick={() => setShowAcademicTheory(!showAcademicTheory)}
                  className="w-full p-4 md:p-5 flex items-center justify-between text-left cursor-pointer hover:bg-[var(--surface)] transition-colors"
                >
                  <div className="flex items-center gap-2.5 text-sm sm:text-base font-bold text-[var(--text)]">
                    <Sparkles size={18} className="text-[var(--accent)]" />
                    <span>Academic Theory & Textbook Formulation</span>
                    <span className="text-xs px-2.5 py-0.5 rounded-full bg-[var(--accent-dim)] text-[var(--accent)] font-semibold">
                      {showAcademicTheory ? 'Click to collapse' : 'Click to expand'}
                    </span>
                  </div>
                  {showAcademicTheory ? <ChevronUp size={18} className="text-[var(--text-soft)]" /> : <ChevronDown size={18} className="text-[var(--text-soft)]" />}
                </button>

                {showAcademicTheory && (
                  <div className="p-5 pt-0 border-t border-[var(--border)] animate-fadeIn space-y-2 mt-2">
                    <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed bg-[var(--surface)] p-4 rounded-xl border border-[var(--border)]">
                      {activity.academic_theory || activity.scientific_principle}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Interactive Student On-Demand Assistance Actions */}
            <div className="p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-4">
              <div className="flex items-center justify-between">
                <div className="text-sm sm:text-base font-bold text-[var(--text)] flex items-center gap-2">
                  <Sparkles size={16} className="text-[var(--accent)]" />
                  <span>On-Demand Learning Assistance</span>
                </div>
                <span className="text-xs sm:text-sm text-[var(--text-soft)] font-medium">
                  Tap button for instant AI support
                </span>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                <button
                  type="button"
                  onClick={() => handleStudentAction('simpler_explanation')}
                  disabled={actionLoading}
                  className="min-h-[46px] p-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] text-[var(--text)] text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                >
                  <Lightbulb size={16} className="text-amber-500" />
                  <span>Simpler Explanation</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleStudentAction('another_example')}
                  disabled={actionLoading}
                  className="min-h-[46px] p-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] text-[var(--text)] text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                >
                  <FileText size={16} className="text-blue-500" />
                  <span>Another Example</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleStudentAction('worked_solution')}
                  disabled={actionLoading}
                  className="min-h-[46px] p-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] text-[var(--text)] text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                >
                  <Target size={16} className="text-emerald-500" />
                  <span>Worked Solution</span>
                </button>

                <button
                  type="button"
                  onClick={() => handleStudentAction('more_challenging_task')}
                  disabled={actionLoading}
                  className="min-h-[46px] p-3 rounded-xl border border-[var(--border)] bg-[var(--surface)] hover:bg-[var(--surface-muted)] text-[var(--text)] text-xs sm:text-sm font-semibold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                >
                  <Sparkles size={16} className="text-purple-500" />
                  <span>Challenge Task</span>
                </button>
              </div>

              {actionLoading && (
                <div className="py-4 text-center text-sm text-[var(--text-soft)] font-medium flex items-center justify-center gap-2">
                  <Loader2 size={18} className="animate-spin text-[var(--accent)]" />
                  <span>Generating tailored learning response...</span>
                </div>
              )}

              {actionResult && (
                <div className="p-5 rounded-xl bg-[var(--surface)] border border-[var(--accent-dim)] space-y-3 animate-fadeIn relative">
                  <button
                    type="button"
                    onClick={() => setActionResult(null)}
                    className="absolute top-3 right-3 text-[var(--text-faint)] hover:text-[var(--text)] p-1.5 cursor-pointer"
                    title="Close assistance card"
                  >
                    <X size={16} />
                  </button>
                  <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-[var(--accent)]">
                    <Sparkles size={16} />
                    <span>{actionResult.title || 'Learning Assistance'}</span>
                  </div>
                  <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed whitespace-pre-wrap font-medium">
                    {actionResult.content}
                  </p>
                  {actionResult.steps?.length > 0 && (
                    <ol className="list-decimal list-inside space-y-1.5 text-sm sm:text-base text-[var(--text)] pt-1">
                      {actionResult.steps.map((st, stIdx) => (
                        <li key={stIdx} className="leading-relaxed">{st}</li>
                      ))}
                    </ol>
                  )}
                </div>
              )}
            </div>

            {/* Village & Everyday Application Connection */}
            {(activity.everyday_applications || activity.village_application) && (
              <div className="p-5 md:p-6 rounded-2xl bg-amber-500/5 border border-amber-500/20 space-y-2.5">
                <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-amber-800 dark:text-amber-300">
                  <Home size={17} />
                  <span>Everyday, Farming & Sustainability Applications</span>
                </div>
                <p className="text-sm sm:text-base text-[var(--text)] leading-relaxed">
                  {activity.everyday_applications || activity.village_application}
                </p>
              </div>
            )}

            {/* Interactive Syllabus Understanding & Concept Checks */}
            {activity.understanding_questions && activity.understanding_questions.length > 0 && (
              <div className="space-y-5 pt-3 border-t border-[var(--border)]">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-[var(--text)]">
                    <HelpCircle size={16} className="text-[var(--accent)]" />
                    <span>Interactive Syllabus Concept Checks & Submissions</span>
                  </div>
                  {saveStatus === 'saving' && (
                    <span className="text-xs sm:text-sm font-medium text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
                      <Loader2 size={13} className="animate-spin" /> Syncing progress...
                    </span>
                  )}
                  {saveStatus === 'saved' && (
                    <span className="text-xs sm:text-sm font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
                      <Check size={13} /> Saved to Database
                    </span>
                  )}
                </div>

                <div className="space-y-4">
                  {activity.understanding_questions.map((qObj, qIdx) => {
                    const isRevealed = Boolean(revealedQuestions[qIdx])
                    const evalResult = evaluations[qIdx]
                    const isEvaluating = Boolean(evaluatingQ[qIdx])
                    const attemptNum = attemptsCount[qIdx] || 0

                    return (
                      <div
                        key={qIdx}
                        className={`p-5 rounded-xl border transition-all space-y-3.5 ${
                          evalResult
                            ? evalResult.is_correct
                              ? 'bg-emerald-500/5 border-emerald-500/30'
                              : 'bg-amber-500/5 border-amber-500/30'
                            : 'bg-[var(--surface-alt)]/60 border-[var(--border)]'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="text-sm sm:text-base font-bold text-[var(--text)] flex items-start gap-2.5">
                            <span className="w-6 h-6 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-xs shrink-0 mt-0.5 font-bold">
                              {qIdx + 1}
                            </span>
                            <span className="leading-snug">{qObj.question}</span>
                          </div>
                          {attemptNum > 0 && (
                            <span className="text-xs font-semibold px-2.5 py-1 rounded-md bg-[var(--surface)] text-[var(--text-soft)] border border-[var(--border)] shrink-0">
                              Attempt #{attemptNum}
                            </span>
                          )}
                        </div>

                        {/* Interactive Answer Input & Submit */}
                        <div className="space-y-2 pt-1">
                          <div className="flex gap-2.5">
                            <input
                              type="text"
                              value={userAnswers[qIdx] || ''}
                              onChange={(e) => setUserAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                              placeholder="Type your answer here..."
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' && !isEvaluating) {
                                  e.preventDefault()
                                  handleSubmitAnswer(qIdx, qObj)
                                }
                              }}
                              className="flex-1 px-4 py-2.5 text-sm sm:text-base rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)] min-h-[44px]"
                            />
                            <Button
                              onClick={() => handleSubmitAnswer(qIdx, qObj)}
                              disabled={isEvaluating || !(userAnswers[qIdx] || '').trim()}
                              size="md"
                              className="px-5 text-sm font-bold shrink-0 flex items-center gap-2 cursor-pointer min-h-[44px]"
                            >
                              {isEvaluating ? <Loader2 size={15} className="animate-spin" /> : <ArrowRight size={15} />}
                              <span>{evalResult ? 'Retry Answer' : 'Submit'}</span>
                            </Button>
                          </div>
                        </div>

                        {/* AI Evaluation Feedback Card */}
                        {evalResult && (
                          <div className={`p-4 rounded-xl border text-sm space-y-2.5 animate-fadeIn ${
                            evalResult.is_correct
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200'
                              : 'bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200'
                          }`}>
                            <div className="flex items-center justify-between gap-2 flex-wrap font-bold">
                              <div className="flex items-center gap-2">
                                {evalResult.is_correct ? (
                                  <CheckCircle2 size={17} className="text-emerald-500 shrink-0" />
                                ) : (
                                  <AlertTriangle size={17} className="text-amber-500 shrink-0" />
                                )}
                                <span>{evalResult.is_correct ? 'Conceptually Correct!' : 'Review Concept'}</span>
                              </div>
                              <span className="text-xs font-bold px-2.5 py-0.5 rounded-md bg-[var(--surface)] border border-[var(--border)] uppercase">
                                {evalResult.error_type === 'spelling_grammar_only'
                                  ? 'Minor Typo (Accepted)'
                                  : evalResult.error_type === 'conceptual_misunderstanding'
                                  ? 'Conceptual Misunderstanding'
                                  : 'Accurate'}
                              </span>
                            </div>

                            <p className="text-sm sm:text-base leading-relaxed opacity-95">
                              {evalResult.feedback}
                            </p>

                            {evalResult.additional_hint && (
                              <div className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-sm text-[var(--text)] flex items-start gap-2">
                                <Lightbulb size={15} className="text-amber-500 shrink-0 mt-0.5" />
                                <div>
                                  <strong>Hint for Next Attempt: </strong>
                                  {evalResult.additional_hint}
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Reference Explanation Toggle */}
                        <div className="pt-1 flex items-center justify-between text-xs sm:text-sm">
                          <button
                            type="button"
                            onClick={() => setRevealedQuestions(prev => ({ ...prev, [qIdx]: !prev[qIdx] }))}
                            className="font-semibold text-[var(--accent)] hover:underline flex items-center gap-1.5 cursor-pointer"
                          >
                            <Info size={14} />
                            <span>{isRevealed ? 'Hide Explanation' : 'Review Explanation'}</span>
                          </button>
                        </div>

                        {isRevealed && (
                          <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-sm sm:text-base space-y-2 animate-fadeIn">
                            <div className="font-bold text-emerald-600 dark:text-emerald-400">
                              Reference Answer: {qObj.answer}
                            </div>
                            {qObj.explanation && (
                              <div className="text-sm text-[var(--text-soft)] leading-relaxed">
                                <em>Academic Explanation:</em> {qObj.explanation}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )
                  })}
                </div>

                {/* Additional Practice Generator Card for Difficulties */}
                <div className="pt-4 border-t border-[var(--border)]">
                  {additionalPractice.length > 0 ? (
                    <div className="p-5 rounded-2xl bg-purple-500/5 border border-purple-500/20 space-y-3.5 animate-fadeIn">
                      <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-purple-900 dark:text-purple-300">
                        <Sparkles size={16} className="text-purple-500" />
                        <span>Additional Targeted Practice Questions</span>
                      </div>
                      <div className="space-y-2.5">
                        {additionalPractice.map((apObj, apIdx) => (
                          <div key={apIdx} className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-sm space-y-1.5">
                            <div className="font-bold text-[var(--text)]">P{apIdx + 1}. {apObj.question}</div>
                            <div className="text-sm text-emerald-600 dark:text-emerald-400 font-semibold">Answer: {apObj.answer}</div>
                            <div className="text-xs sm:text-sm text-[var(--text-soft)] leading-relaxed">{apObj.explanation}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex flex-col sm:flex-row items-center justify-between gap-3">
                      <div className="text-sm text-[var(--text-soft)] leading-relaxed">
                        <strong className="text-[var(--text)]">Need Extra Practice on {selectedTopic || 'this topic'}? </strong>
                        Generate additional practice questions tailored to your performance.
                      </div>
                      <Button
                        onClick={handleLoadAdditionalPractice}
                        disabled={loadingPractice}
                        variant="outline"
                        size="md"
                        className="shrink-0 text-sm font-bold flex items-center gap-2 cursor-pointer min-h-[42px]"
                      >
                        {loadingPractice ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
                        <span>Load Additional Practice</span>
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Limitations, Boundary Conditions & Misconceptions */}
            {activity.limitations_and_misconceptions && (
              <div className="p-4 md:p-5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-start gap-3.5 text-sm sm:text-base text-[var(--text-soft)]">
                <AlertTriangle size={18} className="text-amber-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-[var(--text)]">Limitations & Common Misconceptions: </strong>
                  {activity.limitations_and_misconceptions}
                </div>
              </div>
            )}

            {/* Safety Guidance */}
            {(activity.safety_precautions || activity.safety_notes) && (
              <div className="p-4 md:p-5 rounded-xl bg-red-500/5 border border-red-500/20 flex items-start gap-3.5 text-sm sm:text-base text-red-900 dark:text-red-300">
                <ShieldAlert size={18} className="text-red-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-red-700 dark:text-red-400">Safety Precautions: </strong>
                  {activity.safety_precautions || activity.safety_notes}
                </div>
              </div>
            )}

            {/* Follow-up Syllabus Practice */}
            {activity.follow_up_practice && (
              <div className="p-4 md:p-5 rounded-xl bg-blue-500/5 border border-blue-500/20 text-sm sm:text-base text-blue-900 dark:text-blue-300 space-y-1.5">
                <div className="font-bold flex items-center gap-2 text-blue-700 dark:text-blue-400">
                  <Target size={16} />
                  <span>Suggested Follow-up Syllabus Practice:</span>
                </div>
                <p className="leading-relaxed text-sm">
                  {activity.follow_up_practice}
                </p>
              </div>
            )}

            {/* Understanding Reflection Challenge */}
            {(activity.reflection_task || activity.reflection_question) && (
              <div className="p-5 md:p-6 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-3.5">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 text-sm sm:text-base font-bold text-[var(--text)]">
                    <HelpCircle size={18} className="text-[var(--accent)]" />
                    <span>Reflection & Village Observation Challenge</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowReflectionAnswer(!showReflectionAnswer)}
                    className="text-sm font-bold text-[var(--accent)] hover:underline cursor-pointer"
                  >
                    {showReflectionAnswer ? 'Hide Conceptual Answer' : 'Think & Reveal Concept'}
                  </button>
                </div>
                <p className="text-sm sm:text-base font-medium text-[var(--text)] leading-relaxed">
                  {activity.reflection_task || activity.reflection_question}
                </p>
                {showReflectionAnswer && (
                  <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-sm sm:text-base text-[var(--text-soft)] leading-relaxed animate-fadeIn space-y-1.5">
                    <div className="font-bold text-[var(--text)] flex items-center gap-2">
                      <CheckCircle2 size={16} className="text-emerald-500" />
                      <span>Academic Concept Breakdown</span>
                    </div>
                    <p>
                      This physical phenomenon directly verifies the underlying curriculum law. When parameters such as density, particle surface area, light angle, or concentration change, the physical system responds according to established mathematical and scientific principles.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Activity History Modal */}
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
                    When you generate Learn from Anywhere activities, they will automatically be saved here for you to revisit anytime.
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
                            {/* Curriculum Versioning Flag */}
                            {item.is_current_curriculum ? (
                              <span className="px-3 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-xs font-semibold flex items-center gap-1.5">
                                <ShieldCheck size={12} /> Current Curriculum
                              </span>
                            ) : (
                              <span className="px-3 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-xs font-semibold flex items-center gap-1.5">
                                <AlertTriangle size={12} /> Previous Curriculum
                              </span>
                            )}
                            {/* Completion Status */}
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
