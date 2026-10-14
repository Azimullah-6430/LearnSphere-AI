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
  BookOpenCheck,
  GraduationCap,
  User,
  Calculator,
  CheckSquare
} from 'lucide-react'

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

export default function LearnAnywhere() {
  const { user, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, units: allUnits } = useAuthoritativeCurriculum()
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)
  const requestIdRef = useRef(0)
  const abortControllerRef = useRef(null)

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
  const [showMaterialAlternatives, setShowMaterialAlternatives] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [profileIncomplete, setProfileIncomplete] = useState(false)

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

    // User-scoped cache loader: ensure Student A's cached activity is NEVER presented to Student B
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
          }
        }
      }
    } catch (e) {
      console.warn('Could not read user activity cache', e)
    }

    // If no session cached locally, check server session endpoint to restore active activity
    if (!restoredFromCache && navigator.onLine) {
      const activeQuerySub = selectedSubject || (subjects.length > 0 ? subjects[0] : '')
      api.getLearnAnywhereSession(activeQuerySub ? { subject: activeQuerySub } : {}).then(res => {
        if (res && res.success && res.activity) {
          const actSub = res.activity?.academic_grounding?.subject || res.activity?.subject || res.subject
          const actLevel = (res.activity?.student_type || res.activity?.academic_level || '').toUpperCase()
          const isLevelMismatch = actLevel && actLevel !== expectedLevel
          const isSubMismatch = subjects.length > 0 && actSub && !subjects.includes(actSub)
          if (isSubMismatch || isLevelMismatch) {
            // Activity does not belong to active validated syllabus or educational level
          } else {
            setActivity(res.activity)
            if (actSub && (!subjects.length || subjects.includes(actSub))) setSelectedSubject(actSub)
            if (res.topic || res.activity?.topic) setSelectedTopic(res.topic || res.activity?.topic)
          }
        }
      }).catch(err => {
        console.warn('Session restoration check skipped:', err)
      })
    }
  }, [user, subjects])

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

  // Sync selectedSubject with authoritative subjects
  useEffect(() => {
    if (subjects.length > 0 && (!selectedSubject || !subjects.includes(selectedSubject))) {
      setSelectedSubject(subjects[0])
      clearActivityState()
    }
  }, [subjects, selectedSubject, clearActivityState])

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

  useEffect(() => {
    return () => {
      if (abortControllerRef.current) {
        abortControllerRef.current.abort()
      }
    }
  }, [])

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
      }, { signal: controller.signal })

      if (currentRequestId !== requestIdRef.current || controller.signal.aborted) {
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
        if (res?.profile_incomplete || res?.action_required === 'complete_profile' || /profile.*incomplete|complete.*profile/i.test(res?.error || '')) {
          setProfileIncomplete(true)
          setErrorMsg(res?.error || res?.message || 'Your student profile is incomplete. Please update your academic classification in Settings.')
        } else {
          setErrorMsg(res?.error || 'Failed to design practical activity. Please check your connection and retry.')
        }
      }
    } catch (err) {
      if (err?.name === 'AbortError' || controller.signal.aborted) {
        return
      }
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

    // 1. Check if structured experiments or tasks array is present
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
            title: exp.title || exp.name || exp.experiment_title || `Experiment ${expIdx + 1}`,
            steps: cleanSteps
          }
        })
        .filter(exp => exp.steps.length > 0)
    }

    // 2. If no valid experiments array, parse activity.steps / procedure / instructions
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
          if (currentExp.steps.length > 0) {
            detectedExps.push(currentExp)
          }
          currentExp = { title: headerClean, steps: [] }
          continue
        }

        // Filter out headings or metadata sections like Materials/Safety/Observations
        if (/^(?:materials?|safety|expected observations?|observations?|notes?)\s*[:.]/i.test(headerClean) ||
            /^#{1,6}\s*(?:materials?|safety|observations?)/i.test(line)) {
          continue
        }

        const cleaned = cleanStepPrefix(line)
        if (cleaned) {
          currentExp.steps.push(cleaned)
        }
      }

      if (currentExp.steps.length > 0) {
        detectedExps.push(currentExp)
      }

      if (foundExpHeader && detectedExps.length > 1) {
        parsedExps = detectedExps
      } else if (detectedExps.length > 0) {
        const allSteps = detectedExps.flatMap(e => e.steps)
        parsedExps = [{ title: '', steps: allSteps }]
      }
    }

    // Assign startIndex to each experiment for contiguous global indexing
    let currentStartIndex = 0
    return parsedExps.map(exp => {
      const expWithIndex = {
        ...exp,
        startIndex: currentStartIndex
      }
      currentStartIndex += exp.steps.length
      return expWithIndex
    })
  }, [activity, cleanStepPrefix])

  const stepsList = useMemo(() => {
    return structuredExperiments.flatMap(exp => exp.steps)
  }, [structuredExperiments])

  const totalSteps = stepsList.length || activity?.steps?.length || 0
  const completedCount = Object.values(completedSteps).filter(Boolean).length
  const progressPercent = totalSteps > 0 ? Math.round((completedCount / totalSteps) * 100) : 0

  const isSubjectMismatched = useMemo(() => {
    if (!activity || !selectedSubject) return false
    const actSub = String(activity.academic_grounding?.subject || activity.subject || '').trim().toLowerCase()
    return actSub && actSub !== selectedSubject.trim().toLowerCase()
  }, [activity, selectedSubject])

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
    if (activity.expected_observation || activity.expected_observations) {
      return activity.expected_observation || activity.expected_observations
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
    if (Array.isArray(qList) && qList.length > 0) {
      return qList.slice(0, 2)
    }
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

  const hasRealSafety = Boolean(safetyText)
  const hasRealLimitation = Boolean(limitationText)

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
              <span>Photograph Materials (Optional — Never Required)</span>
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
            <p className="text-[11px] text-[var(--text-faint)] leading-normal flex items-start gap-1.5 pt-0.5">
              <span className="font-semibold text-[var(--accent)]">Privacy note:</span>
              <span>Never photograph faces, private documents, home interiors, or sensitive locations. Impersonal everyday objects only.</span>
            </p>
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
                Learn from Anywhere adapts explanations and activities specifically to School or College students. Please complete your academic profile (School Grade or College Semester) in Settings.
              </div>
            </div>
          </div>
          <Button
            onClick={() => {
              if (typeof window !== 'undefined') {
                window.location.href = '/settings'
              }
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

      {/* Error & Retry State */}
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

      {/* Subject Mismatch Guard */}
      {!loading && activity && isSubjectMismatched && (
        <Card className="p-8 text-center space-y-3 border-amber-500/30 bg-amber-500/5 my-4">
          <AlertTriangle size={32} className="mx-auto text-amber-500" />
          <h3 className="text-sm font-bold text-[var(--text)]">
            Subject Switched to {selectedSubject}
          </h3>
          <p className="text-xs text-[var(--text-soft)] max-w-md mx-auto leading-relaxed">
            The previously loaded activity belonged to another subject. Generate a fresh practical activity specifically designed for <strong>{selectedSubject}</strong>.
          </p>
          <Button
            onClick={handleGenerateActivity}
            size="sm"
            className="mt-2 text-xs font-bold inline-flex items-center gap-1.5"
          >
            <Sparkles size={13} />
            <span>Generate Activity for {selectedSubject}</span>
          </Button>
        </Card>
      )}

      {/* Generated Activity Presentation (Compact Simplified Structure) */}
      {!loading && activity && !isSubjectMismatched && (
        <div className="space-y-6 animate-fadeIn">
          <div className="rounded-2xl bg-[var(--surface)] border border-[var(--border)] p-4 sm:p-6 md:p-7 shadow-sm space-y-6">

            {/* 1. Activity Title */}
            <div className="border-b border-[var(--border)] pb-4 space-y-2">
              <div className="flex items-center gap-2 flex-wrap">
                <Badge tone="accent">{activity.subject || selectedSubject}</Badge>
                {(activity.student_type === 'SCHOOL' || activity.academic_level === 'SCHOOL') ? (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border border-emerald-500/20 flex items-center gap-1.5">
                    <GraduationCap size={12} className="text-emerald-600 dark:text-emerald-400" />
                    <span>School • {activity.academic_grounding?.grade_or_semester || user?.grade_level || 'Curriculum'}</span>
                  </span>
                ) : (
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-500/10 text-indigo-800 dark:text-indigo-300 border border-indigo-500/20 flex items-center gap-1.5">
                    <GraduationCap size={12} className="text-indigo-600 dark:text-indigo-400" />
                    <span>College • {activity.academic_grounding?.grade_or_semester ? `Sem ${activity.academic_grounding?.grade_or_semester}` : (user?.semester ? `Sem ${user.semester}` : 'Higher Ed')}</span>
                  </span>
                )}
              </div>
              <h2 className="text-xl sm:text-2xl font-bold text-[var(--text)] tracking-tight leading-snug">
                {activity.title || activity.activity_title || `${selectedSubject}: ${selectedTopic}`}
              </h2>
            </div>

            {/* 2. What you will learn */}
            <div className="p-3.5 sm:p-4 rounded-xl bg-amber-500/5 border border-amber-500/20 text-sm text-[var(--text)] space-y-2.5">
              <div className="flex items-start gap-3">
                <Lightbulb size={18} className="text-amber-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-[var(--text)] font-semibold">What you will learn: </strong>
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

            {/* Word Bank / Glossary (School Students) */}
            {activity.unfamiliar_words?.length > 0 && (
              <div className="p-3 rounded-xl bg-amber-500/5 border border-amber-500/20 text-xs space-y-1.5">
                <div className="font-semibold text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                  <BookOpen size={13} />
                  <span>Word Bank:</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {activity.unfamiliar_words.map((item, idx) => (
                    <span key={idx} className="px-2 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)] text-[var(--text)]">
                      <strong className="text-[var(--accent)]">{typeof item === 'object' ? item.word : item}</strong>
                      {typeof item === 'object' && item.simple_meaning ? `: ${item.simple_meaning}` : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* 3. What you need */}
            {cleanMaterialsList.length > 0 && (
              <div className="space-y-2">
                <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                  {isCodingTask ? <Code size={15} className="text-emerald-500" /> : <Wrench size={15} className="text-emerald-500" />}
                  <span>{isCodingTask ? 'What you need (Software & Tools)' : 'What you need'}</span>
                </div>
                <div className="flex flex-wrap gap-2">
                  {cleanMaterialsList.map((mat, idx) => {
                    const isChecked = Boolean(checkedMaterials[idx])
                    return (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => toggleMaterial(idx)}
                        className={`px-3 py-1.5 rounded-lg border text-xs sm:text-sm font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                          isChecked
                            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-900 dark:text-emerald-100 line-through opacity-75'
                            : 'bg-[var(--surface-alt)] border-[var(--border)] text-[var(--text)] hover:border-emerald-500/40'
                        }`}
                      >
                        <span className={`w-3.5 h-3.5 rounded flex items-center justify-center text-[10px] font-bold ${
                          isChecked ? 'bg-emerald-500 text-white' : 'border border-[var(--border-strong)]'
                        }`}>
                          {isChecked ? '✓' : ''}
                        </span>
                        <span>{mat}</span>
                      </button>
                    )
                  })}
                </div>

                {/* Free Substitutes & Offline Alternative Helper */}
                {(activity.safe_substitutions?.length > 0 || activity.no_purchase_alternative || activity.offline_alternative) && (
                  <div className="pt-1.5">
                    <button
                      type="button"
                      onClick={() => setShowMaterialAlternatives((prev) => !prev)}
                      className="text-xs font-semibold text-[var(--accent)] hover:underline flex items-center gap-1.5 cursor-pointer"
                    >
                      <span>{showMaterialAlternatives ? 'Hide zero-cost substitutions & offline alternative' : 'Missing items or limited internet? View free substitutions & offline option'}</span>
                      <ChevronDown size={13} className={`transition-transform duration-200 ${showMaterialAlternatives ? 'rotate-180' : ''}`} />
                    </button>

                    {showMaterialAlternatives && (
                      <div className="mt-2 p-3.5 rounded-xl bg-[var(--surface-alt)]/60 border border-[var(--border)] space-y-2 text-xs">
                        {/* No purchase guarantee */}
                        <div className="flex items-start gap-2 text-emerald-700 dark:text-emerald-400 font-medium">
                          <CheckCircle2 size={14} className="shrink-0 mt-0.5" />
                          <span><strong>Zero Purchase Required:</strong> {activity.no_purchase_alternative || "No purchases needed. All concepts can be explored using notebook paper, pencil, ruler, water, or ordinary household items."}</span>
                        </div>

                        {/* Safe substitutions */}
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

                        {/* Offline alternative */}
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
              </div>
            )}

            {/* 4. Steps */}
            {stepsList.length > 0 && (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                    <Layers size={15} className="text-[var(--accent)]" />
                    <span>{structuredExperiments.length > 1 ? 'Activities & Steps' : 'Steps'}</span>
                  </div>
                  <span className="text-xs text-[var(--text-soft)]">
                    {completedCount} / {stepsList.length} completed
                  </span>
                </div>
                <div className="space-y-4">
                  {structuredExperiments.map((exp, expIdx) => {
                    const expStartIndex = exp.startIndex || 0
                    return (
                      <div key={expIdx} className="space-y-2.5">
                        {exp.title && (
                          <div className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] pt-1 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]"></span>
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
                                className={`p-3 sm:p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
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

            {/* 5. Result or example */}
            <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-3">
              <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                <Eye size={15} className="text-blue-500" />
                <span>Result or Example</span>
              </div>
              <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed whitespace-pre-wrap">
                {resultOrExampleText}
              </p>

              {/* Progressive Maths Practice (Easy, Medium, Hard with worked method and calculations) */}
              {activity.math_progressive_practice && (
                <div className="space-y-2.5 pt-3 border-t border-[var(--border)]">
                  <div className="text-xs font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-1.5">
                    <Calculator size={14} className="text-[var(--accent)]" />
                    <span>Progressive Practice & Method (Easy, Medium, Hard)</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2.5">
                    {['easy', 'medium', 'hard'].map((level) => {
                      const tier = activity.math_progressive_practice[level]
                      if (!tier) return null
                      const badgeColor = level === 'easy'
                        ? 'bg-emerald-500/10 text-emerald-800 dark:text-emerald-300 border-emerald-500/20'
                        : level === 'medium'
                        ? 'bg-sky-500/10 text-sky-800 dark:text-sky-300 border-sky-500/20'
                        : 'bg-purple-500/10 text-purple-800 dark:text-purple-300 border-purple-500/20'
                      return (
                        <div key={level} className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-2 text-xs">
                          <div className="flex items-center justify-between">
                            <span className={`px-2 py-0.5 rounded-full font-bold uppercase tracking-wider text-[10px] border ${badgeColor}`}>
                              {level}
                            </span>
                          </div>
                          <p className="font-semibold text-[var(--text)] leading-snug">{tier.question}</p>
                          {tier.method_and_calculations && (
                            <div className="p-2 rounded bg-[var(--surface-alt)] border border-[var(--border)] text-[11px] text-[var(--text-soft)] font-mono whitespace-pre-wrap leading-relaxed">
                              <div className="font-sans font-semibold text-[var(--text)] mb-1 text-[10px] uppercase">Method & Calculations:</div>
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

              {/* Coding block if coding task present */}
              {(activity.coding_task?.code || activity.code_snippet || activity.coding_task?.code_snippet) && (() => {
                const codeSnippet = activity.coding_task?.code || activity.code_snippet || activity.coding_task?.code_snippet
                const lang = activity.coding_task?.target_language || activity.coding_task?.language || 'Python'
                const out = activity.coding_task?.expected_output
                const runInst = activity.coding_task?.run_instructions
                const modTask = activity.coding_task?.modification_task
                return (
                  <div className="rounded-xl bg-gray-900 border border-gray-800 text-gray-100 overflow-hidden shadow-xs mt-2">
                    <div className="px-3.5 py-2 bg-gray-950 border-b border-gray-800 flex items-center justify-between text-xs font-mono">
                      <span className="text-emerald-400 font-semibold">{lang}</span>
                      <button
                        type="button"
                        onClick={() => handleCopyCode(codeSnippet)}
                        className="px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 text-xs flex items-center gap-1 cursor-pointer"
                      >
                        {copyCodeSuccess ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
                        <span>{copyCodeSuccess ? 'Copied' : 'Copy'}</span>
                      </button>
                    </div>
                    {runInst && runInst !== 'N/A' && (
                      <div className="px-3.5 py-1.5 bg-gray-950/70 border-b border-gray-800 text-xs font-mono text-gray-300 flex items-center gap-1.5">
                        <Play size={11} className="text-emerald-400" />
                        <span className="text-gray-400">Run: </span>
                        <span>{runInst}</span>
                      </div>
                    )}
                    <pre className="p-3.5 text-xs sm:text-sm font-mono text-emerald-300 overflow-x-auto leading-relaxed">
                      <code>{codeSnippet}</code>
                    </pre>
                    {out && out !== 'N/A' && (
                      <div className="px-3.5 py-2 bg-gray-950/90 border-t border-gray-800 text-xs font-mono text-sky-300">
                        <span className="text-gray-400">Expected Output: </span>{out}
                      </div>
                    )}
                    {modTask && modTask !== 'N/A' && (
                      <div className="px-3.5 py-2.5 bg-gray-950 border-t border-gray-800 text-xs text-amber-300 flex items-start gap-2">
                        <Terminal size={14} className="text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <strong className="text-amber-200">Modification Task: </strong>
                          <span>{modTask}</span>
                        </div>
                      </div>
                    )}
                  </div>
                )
              })()}

              {/* Model Answer (English & Social Science) */}
              {activity.model_answer && activity.model_answer !== 'N/A' && (
                <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-1.5 text-xs">
                  <div className="font-semibold text-[var(--text)] flex items-center gap-1.5">
                    <CheckCircle2 size={13} className="text-emerald-500" />
                    <span>Model Answer:</span>
                  </div>
                  <p className="text-[var(--text-soft)] leading-relaxed italic whitespace-pre-wrap">
                    {activity.model_answer}
                  </p>
                </div>
              )}

              {/* Assessment Checklist (English & Social Science) */}
              {Array.isArray(activity.assessment_checklist) && activity.assessment_checklist.length > 0 && (
                <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] space-y-2 text-xs">
                  <div className="font-semibold text-[var(--text)] flex items-center gap-1.5">
                    <CheckSquare size={13} className="text-blue-500" />
                    <span>Assessment Checklist:</span>
                  </div>
                  <div className="space-y-1 text-[var(--text-soft)]">
                    {activity.assessment_checklist.map((item, cIdx) => (
                      <div key={cIdx} className="flex items-start gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 shrink-0 mt-1.5" />
                        <span className="leading-relaxed">{item}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Assumptions & Reasoning (College Students) */}
              {activity.assumptions_and_reasoning?.length > 0 && (
                <div className="text-xs text-[var(--text-soft)] pt-2 border-t border-[var(--border)]">
                  <strong className="text-[var(--text)]">Assumptions & Reasoning: </strong>
                  <span>{activity.assumptions_and_reasoning.join(' • ')}</span>
                </div>
              )}
            </div>

            {/* 6. Check your understanding */}
            {questionsToShow.length > 0 && (
              <div className="space-y-3.5 pt-2 border-t border-[var(--border)]">
                <div className="text-xs sm:text-sm font-bold text-[var(--text)] uppercase tracking-wider flex items-center gap-2">
                  <HelpCircle size={15} className="text-[var(--accent)]" />
                  <span>Check Your Understanding</span>
                </div>

                <div className="space-y-3">
                  {questionsToShow.map((qObj, qIdx) => {
                    const isRevealed = Boolean(revealedQuestions[qIdx])
                    const evalResult = evaluations[qIdx]
                    const isEvaluating = Boolean(evaluatingQ[qIdx])

                    return (
                      <div
                        key={qIdx}
                        className={`p-3.5 sm:p-4 rounded-xl border space-y-2.5 transition-all ${
                          evalResult
                            ? evalResult.is_correct
                              ? 'bg-emerald-500/5 border-emerald-500/30'
                              : 'bg-amber-500/5 border-amber-500/30'
                            : 'bg-[var(--surface-alt)]/50 border-[var(--border)]'
                        }`}
                      >
                        <div className="text-sm font-semibold text-[var(--text)] flex items-start gap-2">
                          <span className="text-xs font-bold text-[var(--accent)] px-1.5 py-0.5 rounded bg-[var(--surface)] border border-[var(--border)] shrink-0 mt-0.5">
                            Q{qIdx + 1}
                          </span>
                          <span className="leading-snug">{qObj.question}</span>
                        </div>

                        {/* Answer Input */}
                        <div className="flex gap-2">
                          <input
                            type="text"
                            value={userAnswers[qIdx] || ''}
                            onChange={(e) => setUserAnswers(prev => ({ ...prev, [qIdx]: e.target.value }))}
                            placeholder="Your answer..."
                            onKeyDown={(e) => {
                              if (e.key === 'Enter' && !isEvaluating) {
                                e.preventDefault()
                                handleSubmitAnswer(qIdx, qObj)
                              }
                            }}
                            className="flex-1 px-3 py-1.5 text-xs sm:text-sm rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] min-h-[38px]"
                          />
                          <Button
                            onClick={() => handleSubmitAnswer(qIdx, qObj)}
                            disabled={isEvaluating || !(userAnswers[qIdx] || '').trim()}
                            size="sm"
                            className="px-3 text-xs font-bold shrink-0 min-h-[38px]"
                          >
                            {isEvaluating ? <Loader2 size={13} className="animate-spin" /> : <ArrowRight size={13} />}
                            <span>{evalResult ? 'Retry' : 'Submit'}</span>
                          </Button>
                        </div>

                        {/* Evaluation Feedback */}
                        {evalResult && (
                          <div className={`p-2.5 rounded-lg text-xs leading-relaxed ${
                            evalResult.is_correct
                              ? 'bg-emerald-500/10 text-emerald-900 dark:text-emerald-200'
                              : 'bg-amber-500/10 text-amber-900 dark:text-amber-200'
                          }`}>
                            <strong>{evalResult.is_correct ? 'Correct! ' : 'Review: '}</strong>
                            {evalResult.feedback}
                          </div>
                        )}

                        {/* Reference Answer Toggle */}
                        <div className="pt-0.5 flex justify-end">
                          <button
                            type="button"
                            onClick={() => setRevealedQuestions(prev => ({ ...prev, [qIdx]: !prev[qIdx] }))}
                            className="text-xs font-semibold text-[var(--accent)] hover:underline cursor-pointer flex items-center gap-1"
                          >
                            <Info size={12} />
                            <span>{isRevealed ? 'Hide answer' : 'Show answer'}</span>
                          </button>
                        </div>

                        {isRevealed && (
                          <div className="p-3 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-soft)] space-y-1 animate-fadeIn">
                            <div className="font-semibold text-emerald-600 dark:text-emerald-400">
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
              </div>
            )}

            {/* Optional Safety Guidance (Appears only when relevant) */}
            {hasRealSafety && (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-xs sm:text-sm text-red-900 dark:text-red-300 flex items-start gap-2.5">
                <ShieldAlert size={16} className="text-red-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="font-bold text-red-700 dark:text-red-400">Safety guidance: </strong>
                  <span>{safetyText}</span>
                </div>
              </div>
            )}

            {/* Optional Practical Limitation (Appears only when there is a real limitation to explain) */}
            {hasRealLimitation && (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs sm:text-sm text-amber-900 dark:text-amber-300 flex items-start gap-2.5">
                <AlertTriangle size={16} className="text-amber-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="font-bold text-amber-700 dark:text-amber-400">Practical limitation: </strong>
                  <span>{limitationText}</span>
                </div>
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
