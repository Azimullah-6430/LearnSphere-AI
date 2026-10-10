import { useState, useEffect, useMemo, useCallback } from 'react'
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
  ChevronRight
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

export default function LearnAnywhere() {
  const { user, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, units: allUnits } = useAuthoritativeCurriculum()
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)

  const [selectedSubject, setSelectedSubject] = useState(subjects[0] || '')
  const [selectedTopic, setSelectedTopic] = useState('')
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
  const [errorMsg, setErrorMsg] = useState('')

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

    if (!user?.id && !user?._id && !user?.email) return
    const currentUid = String(user?.id || user?._id || user?.email)
    const cacheKey = `learn_anywhere_activity_${currentUid}`
    try {
      const rawCache = sessionStorage.getItem(cacheKey)
      if (rawCache) {
        const parsed = JSON.parse(rawCache)
        if (parsed && parsed.user_id === currentUid && parsed.activity) {
          setActivity(parsed.activity)
          if (parsed.completedSteps) setCompletedSteps(parsed.completedSteps)
        }
      }
    } catch (e) {
      console.warn('Could not read user activity cache', e)
    }
  }, [user])

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
    setErrorMsg('')
  }, [activeSyllabusId])

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
    const idempotencyKey = `lfa_req_${currentUid}_${selectedSubject.replace(/\s+/g, '_')}_${(selectedTopic || 'concept').replace(/\s+/g, '_')}_${Date.now()}`

    try {
      const res = await api.generateLearnAnywhere({
        subject: selectedSubject,
        subject_id: activeSubjectId || undefined,
        topic: selectedTopic || validatedSubjectTopics[0] || 'Core Practical Concept',
        resource_category: selectedEnv,
        difficulty,
        preferred_language: preferredLanguage,
        custom_materials: customMaterials.trim() || undefined,
        constraint_mode: constraintMode,
        image_data: imageData || undefined,
        syllabus_id: activeSyllabusId || undefined,
        idempotency_key: idempotencyKey
      })

      if (res && res.success && res.activity) {
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
            topic: selectedTopic,
            syllabus_id: activeSyllabusId
          })
        }
      } else {
        setErrorMsg(res?.error || 'Failed to design practical activity. Please check your connection and retry.')
      }
    } catch (err) {
      setErrorMsg(err?.message || 'Connection error while contacting the activity generator. Please try again.')
    } finally {
      setLoading(false)
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
        action={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => {
                setShowHistoryModal(true)
                loadHistory(1)
              }}
              className="px-3 py-1.5 bg-[var(--surface-elevated)] hover:bg-[var(--surface-muted)] text-[var(--text)] border border-[var(--border)] rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer shadow-xs"
            >
              <History size={14} className="text-[var(--accent)]" />
              <span>Activity History</span>
            </button>
            {isOnline ? (
              <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                <Wifi size={12} className="text-emerald-500" /> Rural Data-Saver Mode
              </span>
            ) : (
              <span className="px-3 py-1 bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
                <WifiOff size={12} className="text-amber-500" /> Offline Reading Mode
              </span>
            )}
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold hidden md:flex items-center gap-1.5">
              <Sprout size={13} className="text-emerald-500" /> Rural & Village Learning
            </span>
          </div>
        }
      />

      {/* Offline Status Alert Banner */}
      {!isOnline && (
        <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-300 text-xs font-semibold flex items-center gap-2.5 animate-fadeIn">
          <WifiOff size={16} className="text-amber-500 shrink-0" />
          <div className="flex-1 leading-relaxed">
            <strong>Offline Reading Mode: </strong>
            Your connection is currently unavailable. Your previously loaded activity instructions remain readable below. Reconnect to generate new AI experiments.
          </div>
        </div>
      )}

      {/* Educational Landing Intro Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-linear-to-r from-emerald-600 via-teal-600 to-emerald-700 text-white p-5 md:p-6 shadow-md">
        <div className="relative z-10 max-w-3xl space-y-2">
          <div className="inline-flex items-center gap-2 px-2.5 py-0.5 rounded-full bg-white/20 text-white text-[11px] font-bold uppercase tracking-wider backdrop-blur-xs">
            <Sparkles size={12} /> Real-World Academic Discovery
          </div>
          <h1 className="text-xl md:text-2xl font-black tracking-tight leading-snug">
            Turn Your Natural Surroundings into a Science & Math Laboratory
          </h1>
          <p className="text-xs md:text-sm text-emerald-50 font-normal leading-relaxed">
            You do not need expensive lab equipment or store-bought kits to master your syllabus. Use soil, sunlight, water, plants, bicycle gears, clay pots, and everyday household objects to perform real academic experiments right in your village or home.
          </p>
        </div>
      </div>

      {/* Setup & Resource Filter Card */}
      <Card className="p-5 md:p-6 shadow-sm space-y-5 border-[var(--border)]">
        {/* 1. Validated Syllabus Subject Selector */}
        <div>
          <label className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <BookOpen size={13} className="text-[var(--accent)]" />
            <span>1. Choose Validated Syllabus Subject</span>
          </label>
          <div className="flex gap-2 flex-wrap" role="radiogroup" aria-label="Select Subject">
            {subjects.map((sub) => {
              const isSelected = selectedSubject === sub
              return (
                <button
                  key={sub}
                  type="button"
                  onClick={() => setSelectedSubject(sub)}
                  className={`min-h-[40px] px-4 py-2 rounded-xl text-xs font-bold border transition-all cursor-pointer ${
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
            <label className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Target size={13} className="text-[var(--accent)]" />
              <span>2. Select Syllabus Topic / Unit</span>
            </label>
            <div className="grid sm:grid-cols-2 md:grid-cols-3 gap-2">
              {validatedSubjectTopics.slice(0, 9).map((top) => {
                const isSelected = selectedTopic === top
                return (
                  <button
                    key={top}
                    type="button"
                    onClick={() => setSelectedTopic(top)}
                    className={`min-h-[42px] px-3.5 py-2 rounded-xl text-left text-xs font-medium border transition-all truncate flex items-center justify-between gap-2 cursor-pointer ${
                      isSelected
                        ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] font-bold shadow-2xs'
                        : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
                    }`}
                    title={top}
                  >
                    <span className="truncate">{top}</span>
                    {isSelected && <Check size={14} className="text-[var(--accent)] shrink-0" />}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* 3. Local Surroundings & Material Environment Mode */}
        <div>
          <label className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Compass size={13} className="text-[var(--accent)]" />
            <span>3. Available Natural / Village Environment</span>
          </label>
          <div className="flex gap-2 flex-wrap">
            {RESOURCE_ENVIRONMENTS.map(({ id, label, icon: Icon }) => {
              const isSelected = selectedEnv === id
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => setSelectedEnv(id)}
                  className={`min-h-[40px] px-3.5 py-2 rounded-xl text-xs font-semibold border transition-all flex items-center gap-2 cursor-pointer ${
                    isSelected
                      ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] font-bold shadow-2xs'
                      : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  <Icon size={14} className={isSelected ? 'text-[var(--accent)]' : 'opacity-70'} />
                  <span>{label}</span>
                </button>
              )
            })}
          </div>
        </div>

        {/* 4. Text Description of Available Objects + Quick Add Tags */}
        <div className="space-y-2">
          <label className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider flex items-center gap-1.5">
            <Wrench size={13} className="text-[var(--accent)]" />
            <span>4. Objects, Plants, Tools & Materials You Have (Optional Description)</span>
          </label>
          <textarea
            value={customMaterials}
            onChange={(e) => setCustomMaterials(e.target.value)}
            placeholder="e.g. Red clay, plastic bottle, turmeric, clean water, bicycle gears, sunlight, dry leaves, string..."
            rows={2}
            className="w-full px-3.5 py-2.5 text-xs rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)] leading-relaxed resize-none"
          />
          {/* Quick-add tags for budget mobile 1-tap entry */}
          <div className="flex items-center gap-1.5 flex-wrap pt-1">
            <span className="text-[11px] font-semibold text-[var(--text-faint)]">Quick add:</span>
            {QUICK_MATERIAL_TAGS.map((tag) => (
              <button
                key={tag}
                type="button"
                onClick={() => handleAddMaterialTag(tag)}
                className="px-2.5 py-1 text-[11px] rounded-lg bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-[var(--text-soft)] font-medium transition-colors cursor-pointer"
              >
                + {tag}
              </button>
            ))}
          </div>
        </div>

        {/* 5. Image Upload & Constraint Mode Selection */}
        <div className="grid sm:grid-cols-2 gap-4 pt-2 border-t border-[var(--border)]">
          {/* Photo / Camera Option */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider flex items-center gap-1.5">
              <Camera size={13} className="text-[var(--accent)]" />
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
                  <X size={13} />
                </button>
              </div>
            ) : (
              <label className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-dashed border-[var(--border-strong)] bg-[var(--surface-alt)]/50 hover:bg-[var(--surface-alt)] text-[var(--text-soft)] text-xs font-medium cursor-pointer transition-colors w-fit">
                <ImageIcon size={15} className="text-[var(--text-faint)]" />
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
          <div className="space-y-2">
            <label className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider flex items-center gap-1.5">
              <ShieldCheck size={13} className="text-[var(--accent)]" />
              <span>Material Requirement Preference</span>
            </label>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setConstraintMode('strict_only')}
                className={`min-h-[42px] p-2 rounded-xl text-left text-[11px] font-semibold border transition-all cursor-pointer ${
                  constraintMode === 'strict_only'
                    ? 'bg-emerald-500/10 border-emerald-500 text-emerald-700 dark:text-emerald-400 font-bold'
                    : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                <div className="flex items-center gap-1">
                  <CheckCircle2 size={12} className={constraintMode === 'strict_only' ? 'text-emerald-500' : 'opacity-40'} />
                  <span>Strictly Mine</span>
                </div>
                <div className="text-[10px] text-[var(--text-faint)] font-normal mt-0.5 leading-tight">
                  Only use materials listed
                </div>
              </button>

              <button
                type="button"
                onClick={() => setConstraintMode('allow_minimal_common')}
                className={`min-h-[42px] p-2 rounded-xl text-left text-[11px] font-semibold border transition-all cursor-pointer ${
                  constraintMode === 'allow_minimal_common'
                    ? 'bg-[var(--surface-alt)] border-[var(--accent)] text-[var(--accent)] font-bold'
                    : 'border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                <div className="flex items-center gap-1">
                  <Sparkles size={12} className={constraintMode === 'allow_minimal_common' ? 'text-[var(--accent)]' : 'opacity-40'} />
                  <span>Allow Common Items</span>
                </div>
                <div className="text-[10px] text-[var(--text-faint)] font-normal mt-0.5 leading-tight">
                  Allow water, thread, spoon
                </div>
              </button>
            </div>
          </div>
        </div>

        {/* Generate Trigger Footer */}
        <div className="pt-3 border-t border-[var(--border)] flex flex-col sm:flex-row gap-3 items-center justify-between">
          <div className="flex items-center gap-3 w-full sm:w-auto flex-wrap">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-[var(--text-faint)]">Difficulty:</span>
              <select
                value={difficulty}
                onChange={(e) => setDifficulty(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg border border-[var(--border-strong)] text-xs font-semibold bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
              >
                <option value="Easy">Easy (Everyday Observations)</option>
                <option value="Medium">Medium (Guided Hands-on)</option>
                <option value="Hard">Advanced (Analytical & Quantitative)</option>
              </select>
            </div>

            <div className="flex items-center gap-1.5">
              <span className="text-xs font-semibold text-[var(--text-faint)]">Language:</span>
              <select
                value={preferredLanguage}
                onChange={(e) => setPreferredLanguage(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg border border-[var(--border-strong)] text-xs font-semibold bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
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
            className="w-full sm:w-auto min-h-[44px] px-6 flex items-center justify-center gap-2 cursor-pointer shadow-sm text-xs font-bold"
          >
            {loading ? <Loader2 size={15} className="animate-spin" /> : <Sparkles size={15} />}
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
          <div className="rounded-2xl bg-[var(--surface)] border border-[var(--border)] p-5 md:p-7 shadow-sm space-y-6">
            {/* Header / Badges */}
            <div className="flex flex-col md:flex-row md:items-start justify-between gap-4 border-b border-[var(--border)] pb-5">
              <div className="space-y-2">
                <div className="flex items-center gap-2 flex-wrap">
                  <Badge tone="accent">{activity.subject || selectedSubject}</Badge>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700 dark:text-amber-400 border border-amber-500/20 flex items-center gap-1">
                    <Compass size={11} /> {activity.resource_category || selectedEnv}
                  </span>
                  {activity.demonstration_type === 'thought_experiment_and_analog' ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/20 flex items-center gap-1">
                      <Lightbulb size={11} /> Thought Experiment & Physical Analog
                    </span>
                  ) : activity.demonstration_type === 'outdoor_observation' ? (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                      <TreePine size={11} /> Outdoor & Nature Observation
                    </span>
                  ) : (
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-bold bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-500/20 flex items-center gap-1">
                      <Home size={11} /> Household Hands-on Activity
                    </span>
                  )}
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-[var(--surface-alt)] text-[var(--text-soft)] border border-[var(--border)]">
                    Topic: {activity.syllabus_topic || selectedTopic || 'Syllabus Grounding'}
                  </span>
                  {(activity.syllabus_id || activeSyllabusId) && (
                    <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-500/20 flex items-center gap-1">
                      <ShieldCheck size={11} /> Validated Syllabus Traceable
                    </span>
                  )}
                </div>
                <h2 className="text-xl md:text-2xl font-black text-[var(--text)] tracking-tight leading-snug">
                  {activity.title || activity.activity_title}
                </h2>
                <div className="text-xs text-[var(--text-soft)] flex items-start gap-2 pt-0.5">
                  <Lightbulb size={15} className="text-amber-500 shrink-0 mt-0.5" />
                  <span className="leading-relaxed">
                    <strong className="text-[var(--text)]">Learning Objective: </strong>
                    {activity.learning_objective || (activity.learning_objectives && activity.learning_objectives[0])}
                  </span>
                </div>
              </div>

              {/* Progress Indicator Card */}
              <div className="shrink-0 bg-[var(--surface-alt)] p-3.5 rounded-2xl border border-[var(--border)] text-center min-w-[150px]">
                <div className="text-[11px] font-bold text-[var(--text-faint)] uppercase tracking-wider mb-1">
                  Practical Steps
                </div>
                <div className="text-xl font-black text-[var(--accent)]">
                  {completedCount} / {totalSteps} Done
                </div>
                <div className="w-full bg-[var(--border)] h-2 rounded-full overflow-hidden mt-2">
                  <div
                    className="bg-[var(--accent)] h-full transition-all duration-300 rounded-full"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
                <div className="text-[10px] font-semibold text-[var(--text-faint)] mt-1.5">
                  {progressPercent === 100 ? '🎉 Activity Complete!' : `${progressPercent}% Completed`}
                </div>
              </div>
            </div>

            {/* Non-Physical / Thought Experiment Feasibility Notice */}
            {activity.demonstration_type === 'thought_experiment_and_analog' && (
              <div className="p-3.5 md:p-4 rounded-xl bg-purple-500/10 border border-purple-500/20 text-xs text-purple-900 dark:text-purple-300 flex items-start gap-3">
                <Info size={17} className="text-purple-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong>Concept Feasibility Notice: </strong>
                  This syllabus topic involves microscopic, relativistic, or theoretical concepts that cannot be physically isolated in a household setting without specialized laboratory equipment. This activity uses rigorous thought experiments and macroscopic everyday analogs to build concrete scientific intuition.
                </div>
              </div>
            )}

            {/* Multimodal Image Observation & Analysis Block */}
            {activity.image_analysis && (
              <div className={`p-4 md:p-5 rounded-2xl border space-y-3 ${
                activity.image_analysis.image_processed
                  ? 'bg-sky-500/5 border-sky-500/20'
                  : 'bg-[var(--surface-alt)] border-[var(--border)]'
              }`}>
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--text)]">
                    <Camera size={16} className={activity.image_analysis.image_processed ? 'text-sky-500' : 'text-[var(--text-faint)]'} />
                    <span>Image Observation & Visual Identification</span>
                  </div>
                  <span className={`px-2.5 py-0.5 rounded-full text-[11px] font-bold border ${
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
                  <div className="space-y-2 text-xs text-[var(--text-soft)]">
                    <div className="font-semibold text-[var(--text)] flex items-center gap-1.5">
                      <Target size={14} className="text-sky-500" />
                      <span>Identified Object / Structure: </span>
                      <span className="font-bold text-sky-700 dark:text-sky-300">
                        {activity.image_analysis.identified_object_or_structure}
                      </span>
                    </div>

                    {activity.image_analysis.visible_features?.length > 0 && (
                      <div className="space-y-1">
                        <div className="text-[11px] font-bold text-[var(--text-faint)] uppercase">
                          Observed Visual Features:
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {activity.image_analysis.visible_features.map((feat, fIdx) => (
                            <span key={fIdx} className="px-2 py-0.5 rounded-md bg-[var(--surface)] border border-[var(--border)] text-[11px] font-medium text-[var(--text)]">
                              • {feat}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {activity.image_analysis.syllabus_connection && (
                      <p className="text-[11px] leading-relaxed pt-1 text-[var(--text)]">
                        <strong>Syllabus Connection: </strong>
                        {activity.image_analysis.syllabus_connection}
                      </p>
                    )}

                    {activity.image_analysis.clarification_needed && (
                      <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-300 text-[11px] flex items-start gap-2 mt-2">
                        <HelpCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                        <div>
                          <strong>Clarification Needed: </strong>
                          {activity.image_analysis.clarification_needed}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs text-[var(--text-soft)] leading-relaxed">
                    {activity.image_analysis.image_note || 'Generated a structured text-based practical activity based on your syllabus topic.'}
                  </p>
                )}
              </div>
            )}

            {/* Required Zero-Cost Materials Checklist */}
            <div className="p-4 md:p-5 rounded-2xl bg-emerald-500/5 border border-emerald-500/20 space-y-3">
              <div className="flex items-center justify-between gap-2 flex-wrap">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">
                  <Sprout size={16} />
                  <span>Required Zero-Cost & Locally Sourced Materials</span>
                </div>
                <span className="text-[11px] text-emerald-700 dark:text-emerald-400 font-medium">
                  Tap item to check off
                </span>
              </div>
              <div className="grid sm:grid-cols-2 gap-2.5">
                {(activity.local_materials || activity.materials_student_has || []).map((mat, idx) => {
                  const isChecked = Boolean(checkedMaterials[idx])
                  return (
                    <button
                      key={idx}
                      type="button"
                      onClick={() => toggleMaterial(idx)}
                      className={`p-2.5 rounded-xl border text-left text-xs flex items-start gap-2.5 transition-all cursor-pointer ${
                        isChecked
                          ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-900 dark:text-emerald-100 line-through opacity-80'
                          : 'bg-[var(--surface)] border-[var(--border)] text-[var(--text)] hover:border-emerald-500/40'
                      }`}
                    >
                      <div className={`w-4 h-4 rounded-md flex items-center justify-center shrink-0 mt-0.5 border text-[10px] font-bold ${
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
                <div className="pt-2 border-t border-emerald-500/20 text-xs text-emerald-900 dark:text-emerald-300 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <ShieldCheck size={13} className="text-emerald-600 dark:text-emerald-400" />
                    <span>No-Purchase Zero-Cost Substitutions:</span>
                  </div>
                  <p className="text-[11px] opacity-90 leading-relaxed">
                    {activity.no_purchase_alternative || activity.safe_substitutions?.join(' • ')}
                  </p>
                </div>
              )}
            </div>

            {/* Step-by-Step Practical Instructions */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider flex items-center gap-1.5">
                  <Layers size={14} className="text-[var(--accent)]" />
                  <span>Step-by-Step Procedure</span>
                </div>
                <span className="text-[11px] text-[var(--text-faint)]">
                  Tap step to mark complete
                </span>
              </div>
              <div className="space-y-2.5">
                {(activity.steps || []).map((step, idx) => {
                  const isDone = Boolean(completedSteps[idx])
                  return (
                    <div
                      key={idx}
                      onClick={() => toggleStep(idx)}
                      className={`min-h-[48px] p-3.5 md:p-4 rounded-xl border transition-all cursor-pointer flex items-start gap-3.5 ${
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
                      <div className={`w-6 h-6 rounded-lg flex items-center justify-center shrink-0 mt-0.5 border text-xs font-bold transition-colors ${
                        isDone ? 'bg-[var(--accent)] text-white border-[var(--accent)]' : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-faint)]'
                      }`}>
                        {isDone ? '✓' : idx + 1}
                      </div>
                      <div className="text-xs md:text-sm font-medium leading-relaxed flex-1">
                        {step}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Observation & Simple Explanation Grid */}
            <div className="grid md:grid-cols-2 gap-4 pt-2 border-t border-[var(--border)]">
              <div className="p-4 md:p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)]">
                  <Eye size={16} className="text-blue-500" />
                  <span>What You Will Observe</span>
                </div>
                <p className="text-xs text-[var(--text-soft)] leading-relaxed">
                  {activity.expected_observation || activity.expected_observations}
                </p>
              </div>

              <div className="p-4 md:p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)]">
                  <Lightbulb size={16} className="text-amber-500" />
                  <span>Simple Explanation (Why It Works)</span>
                </div>
                <p className="text-xs text-[var(--text-soft)] leading-relaxed font-normal">
                  {activity.simple_explanation || activity.scientific_principle}
                </p>
              </div>
            </div>

            {/* Academic Theory & Governing Formulas */}
            {(activity.academic_theory || activity.scientific_principle) && (
              <div className="p-4 md:p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)]">
                  <Sparkles size={16} className="text-[var(--accent)]" />
                  <span>Rigorous Academic Theory & Textbook Formulation</span>
                </div>
                <p className="text-xs text-[var(--text-soft)] leading-relaxed font-mono text-[11px] bg-[var(--surface)] p-3 rounded-xl border border-[var(--border)]">
                  {activity.academic_theory || activity.scientific_principle}
                </p>
              </div>
            )}

            {/* Village & Everyday Application Connection */}
            {(activity.everyday_applications || activity.village_application) && (
              <div className="p-4 md:p-5 rounded-2xl bg-amber-500/5 border border-amber-500/20 space-y-2">
                <div className="flex items-center gap-2 text-xs font-bold text-amber-800 dark:text-amber-300 uppercase tracking-wider">
                  <Home size={15} />
                  <span>Everyday, Farming & Sustainability Applications</span>
                </div>
                <p className="text-xs text-[var(--text)] leading-relaxed">
                  {activity.everyday_applications || activity.village_application}
                </p>
              </div>
            )}

            {/* Interactive Syllabus Understanding & Concept Checks */}
            {activity.understanding_questions && activity.understanding_questions.length > 0 && (
              <div className="space-y-4 pt-2 border-t border-[var(--border)]">
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--text-faint)] uppercase tracking-wider">
                    <HelpCircle size={14} className="text-[var(--accent)]" />
                    <span>Interactive Syllabus Concept Checks & Submissions</span>
                  </div>
                  {saveStatus === 'saving' && (
                    <span className="text-[11px] font-medium text-amber-600 dark:text-amber-400 flex items-center gap-1">
                      <Loader2 size={11} className="animate-spin" /> Syncing progress...
                    </span>
                  )}
                  {saveStatus === 'saved' && (
                    <span className="text-[11px] font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                      <Check size={11} /> Saved to Database
                    </span>
                  )}
                </div>

                <div className="space-y-3">
                  {activity.understanding_questions.map((qObj, qIdx) => {
                    const isRevealed = Boolean(revealedQuestions[qIdx])
                    const evalResult = evaluations[qIdx]
                    const isEvaluating = Boolean(evaluatingQ[qIdx])
                    const attemptNum = attemptsCount[qIdx] || 0

                    return (
                      <div
                        key={qIdx}
                        className={`p-4 rounded-xl border transition-all space-y-3 ${
                          evalResult
                            ? evalResult.is_correct
                              ? 'bg-emerald-500/5 border-emerald-500/30'
                              : 'bg-amber-500/5 border-amber-500/30'
                            : 'bg-[var(--surface-alt)]/60 border-[var(--border)]'
                        }`}
                      >
                        <div className="flex items-start justify-between gap-3">
                          <div className="text-xs font-bold text-[var(--text)] flex items-start gap-2">
                            <span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] shrink-0 mt-0.5 font-bold">
                              {qIdx + 1}
                            </span>
                            <span className="leading-snug">{qObj.question}</span>
                          </div>
                          {attemptNum > 0 && (
                            <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-[var(--surface)] text-[var(--text-faint)] border border-[var(--border)] shrink-0">
                              Attempt #{attemptNum}
                            </span>
                          )}
                        </div>

                        {/* Interactive Answer Input & Submit */}
                        <div className="space-y-2 pt-1">
                          <div className="flex gap-2">
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
                              className="flex-1 px-3 py-2 text-xs rounded-xl border border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] placeholder:text-[var(--text-faint)]"
                            />
                            <Button
                              onClick={() => handleSubmitAnswer(qIdx, qObj)}
                              disabled={isEvaluating || !(userAnswers[qIdx] || '').trim()}
                              size="sm"
                              className="px-4 text-xs font-bold shrink-0 flex items-center gap-1.5 cursor-pointer"
                            >
                              {isEvaluating ? <Loader2 size={13} className="animate-spin" /> : <ArrowRight size={13} />}
                              <span>{evalResult ? 'Retry Answer' : 'Submit'}</span>
                            </Button>
                          </div>
                        </div>

                        {/* AI Evaluation Feedback Card */}
                        {evalResult && (
                          <div className={`p-3.5 rounded-xl border text-xs space-y-2 animate-fadeIn ${
                            evalResult.is_correct
                              ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-900 dark:text-emerald-200'
                              : 'bg-amber-500/10 border-amber-500/30 text-amber-900 dark:text-amber-200'
                          }`}>
                            <div className="flex items-center justify-between gap-2 flex-wrap font-bold">
                              <div className="flex items-center gap-1.5">
                                {evalResult.is_correct ? (
                                  <CheckCircle2 size={15} className="text-emerald-500 shrink-0" />
                                ) : (
                                  <AlertTriangle size={15} className="text-amber-500 shrink-0" />
                                )}
                                <span>{evalResult.is_correct ? 'Conceptually Correct!' : 'Review Concept'}</span>
                              </div>
                              <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-md bg-[var(--surface)] border border-[var(--border)] uppercase">
                                {evalResult.error_type === 'spelling_grammar_only'
                                  ? 'Minor Typo (Accepted)'
                                  : evalResult.error_type === 'conceptual_misunderstanding'
                                  ? 'Conceptual Misunderstanding'
                                  : 'Accurate'}
                              </span>
                            </div>

                            <p className="text-[11px] leading-relaxed opacity-95">
                              {evalResult.feedback}
                            </p>

                            {evalResult.additional_hint && (
                              <div className="p-2.5 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[11px] text-[var(--text)] flex items-start gap-1.5">
                                <Lightbulb size={13} className="text-amber-500 shrink-0 mt-0.5" />
                                <div>
                                  <strong>Hint for Next Attempt: </strong>
                                  {evalResult.additional_hint}
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {/* Reference Explanation Toggle */}
                        <div className="pt-1 flex items-center justify-between text-[11px]">
                          <button
                            type="button"
                            onClick={() => setRevealedQuestions(prev => ({ ...prev, [qIdx]: !prev[qIdx] }))}
                            className="font-semibold text-[var(--accent)] hover:underline flex items-center gap-1 cursor-pointer"
                          >
                            <Info size={12} />
                            <span>{isRevealed ? 'Hide Explanation' : 'Review Explanation'}</span>
                          </button>
                        </div>

                        {isRevealed && (
                          <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs space-y-1.5 animate-fadeIn">
                            <div className="font-bold text-emerald-600 dark:text-emerald-400">
                              Reference Answer: {qObj.answer}
                            </div>
                            {qObj.explanation && (
                              <div className="text-[11px] text-[var(--text-soft)] leading-relaxed">
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
                <div className="pt-3 border-t border-[var(--border)]">
                  {additionalPractice.length > 0 ? (
                    <div className="p-4 rounded-2xl bg-purple-500/5 border border-purple-500/20 space-y-3 animate-fadeIn">
                      <div className="flex items-center gap-2 text-xs font-bold text-purple-900 dark:text-purple-300 uppercase tracking-wider">
                        <Sparkles size={15} className="text-purple-500" />
                        <span>Additional Targeted Practice Questions</span>
                      </div>
                      <div className="space-y-2">
                        {additionalPractice.map((apObj, apIdx) => (
                          <div key={apIdx} className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs space-y-1">
                            <div className="font-bold text-[var(--text)]">P{apIdx + 1}. {apObj.question}</div>
                            <div className="text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold">Answer: {apObj.answer}</div>
                            <div className="text-[10px] text-[var(--text-soft)]">{apObj.explanation}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex flex-col sm:flex-row items-center justify-between gap-3">
                      <div className="text-xs text-[var(--text-soft)] leading-snug">
                        <strong className="text-[var(--text)]">Need Extra Practice on {selectedTopic || 'this topic'}? </strong>
                        Generate additional practice questions tailored to your performance.
                      </div>
                      <Button
                        onClick={handleLoadAdditionalPractice}
                        disabled={loadingPractice}
                        variant="outline"
                        size="sm"
                        className="shrink-0 text-xs font-bold flex items-center gap-1.5 cursor-pointer"
                      >
                        {loadingPractice ? <Loader2 size={13} className="animate-spin" /> : <Sparkles size={13} />}
                        <span>Load Additional Practice</span>
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Limitations, Boundary Conditions & Misconceptions */}
            {activity.limitations_and_misconceptions && (
              <div className="p-3.5 md:p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-start gap-3 text-xs text-[var(--text-soft)]">
                <AlertTriangle size={17} className="text-amber-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-[var(--text)]">Limitations & Common Misconceptions: </strong>
                  {activity.limitations_and_misconceptions}
                </div>
              </div>
            )}

            {/* Safety Guidance */}
            {(activity.safety_precautions || activity.safety_notes) && (
              <div className="p-3.5 md:p-4 rounded-xl bg-red-500/5 border border-red-500/20 flex items-start gap-3 text-xs text-red-900 dark:text-red-300">
                <ShieldAlert size={17} className="text-red-500 shrink-0 mt-0.5" />
                <div className="leading-relaxed">
                  <strong className="text-red-700 dark:text-red-400">Safety Precautions: </strong>
                  {activity.safety_precautions || activity.safety_notes}
                </div>
              </div>
            )}

            {/* Follow-up Syllabus Practice */}
            {activity.follow_up_practice && (
              <div className="p-4 rounded-xl bg-blue-500/5 border border-blue-500/20 text-xs text-blue-900 dark:text-blue-300 space-y-1">
                <div className="font-bold flex items-center gap-1.5 text-blue-700 dark:text-blue-400">
                  <Target size={13} />
                  <span>Suggested Follow-up Syllabus Practice:</span>
                </div>
                <p className="leading-relaxed text-[11px]">
                  {activity.follow_up_practice}
                </p>
              </div>
            )}

            {/* Understanding Reflection Challenge */}
            {(activity.reflection_task || activity.reflection_question) && (
              <div className="p-4 md:p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] space-y-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 text-xs font-bold text-[var(--text)]">
                    <HelpCircle size={16} className="text-[var(--accent)]" />
                    <span>Reflection & Village Observation Challenge</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowReflectionAnswer(!showReflectionAnswer)}
                    className="text-xs font-bold text-[var(--accent)] hover:underline cursor-pointer"
                  >
                    {showReflectionAnswer ? 'Hide Conceptual Answer' : 'Think & Reveal Concept'}
                  </button>
                </div>
                <p className="text-xs md:text-sm font-medium text-[var(--text)] leading-relaxed">
                  {activity.reflection_task || activity.reflection_question}
                </p>
                {showReflectionAnswer && (
                  <div className="p-3.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs text-[var(--text-soft)] leading-relaxed animate-fadeIn space-y-1">
                    <div className="text-xs font-bold text-[var(--text)] flex items-center gap-1.5">
                      <CheckCircle2 size={13} className="text-emerald-500" />
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
        <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-50 flex items-center justify-center p-4 animate-fadeIn">
          <div className="bg-[var(--surface-elevated)] border border-[var(--border)] rounded-2xl max-w-4xl w-full max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
            {/* Header */}
            <div className="p-5 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-muted)]">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-xl bg-[var(--accent-dim)] text-[var(--accent)]">
                  <History size={18} />
                </div>
                <div>
                  <h2 className="text-base font-bold text-[var(--text)]">Activity History</h2>
                  <p className="text-xs text-[var(--text-soft)]">
                    Revisit your past Learn from Anywhere activities, check understanding scores, and add reflections.
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setShowHistoryModal(false)}
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
                    <Card key={item.activity_id || item._id} className="p-4 space-y-3.5 border-[var(--border)] hover:border-[var(--accent-dim)] transition-all">
                      <div className="flex flex-col md:flex-row md:items-center justify-between gap-2">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="px-2 py-0.5 rounded-md bg-[var(--accent-dim)] text-[var(--accent)] text-[11px] font-bold">
                              {item.subject} • {item.topic}
                            </span>
                            {/* Curriculum Versioning Flag */}
                            {item.is_current_curriculum ? (
                              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 text-[11px] font-bold flex items-center gap-1">
                                <ShieldCheck size={11} /> Current Curriculum
                              </span>
                            ) : (
                              <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20 text-[11px] font-bold flex items-center gap-1">
                                <AlertTriangle size={11} /> Previous Curriculum
                              </span>
                            )}
                            {/* Completion Status */}
                            <span className={`px-2 py-0.5 rounded-full text-[11px] font-bold ${
                              item.completion_status === 'completed'
                                ? 'bg-emerald-500/10 text-emerald-600'
                                : item.completion_status === 'in_progress'
                                ? 'bg-blue-500/10 text-blue-600'
                                : 'bg-gray-500/10 text-gray-600'
                            }`}>
                              {item.completion_status === 'completed' ? 'Completed' : item.completion_status === 'in_progress' ? 'In Progress' : 'Not Started'}
                            </span>
                          </div>
                          <h3 className="text-sm font-black text-[var(--text)]">{item.title}</h3>
                          <div className="text-[11px] text-[var(--text-soft)] flex items-center gap-3 flex-wrap">
                            <span>Syllabus: <strong>{item.curriculum_reference || 'Validated Syllabus'}</strong></span>
                            <span>Date: {createdDate}</span>
                          </div>
                        </div>
                        <div className="flex items-center gap-2 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleRevisitActivity(item)}
                            className="px-3 py-1.5 rounded-xl bg-[var(--accent)] text-white text-xs font-bold flex items-center gap-1.5 hover:opacity-90 transition-all cursor-pointer shadow-xs"
                          >
                            <Eye size={13} /> Revisit Activity
                          </button>
                          <button
                            type="button"
                            onClick={() => handleDeleteHistoryItem(item.activity_id)}
                            className="p-1.5 rounded-xl text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 border border-red-200 dark:border-red-900/40 transition-all cursor-pointer"
                            title="Delete Activity Record"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>

                      {/* Concept Checks / Attempts summary */}
                      {Array.isArray(item.attempts) && item.attempts.length > 0 && (
                        <div className="p-2.5 rounded-xl bg-[var(--surface-muted)] text-[11px] text-[var(--text-soft)] space-y-1">
                          <div className="font-bold text-[var(--text)] flex items-center gap-1">
                            <Target size={12} className="text-[var(--accent)]" />
                            <span>Understanding Checks:</span>
                            <span className="ml-1 text-[var(--accent)]">{item.attempts.filter(a => a.is_correct).length} / {item.attempts.length} Passed</span>
                          </div>
                        </div>
                      )}

                      {/* Reflections section */}
                      <div className="p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-xs space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-[var(--text)] flex items-center gap-1 text-[11px]">
                            <FileText size={12} className="text-[var(--accent)]" /> Student Reflections & Notes
                          </span>
                          {!isEditing && (
                            <button
                              type="button"
                              onClick={() => {
                                setEditingReflectionId(item.activity_id)
                                setReflectionText(item.reflections || '')
                              }}
                              className="text-[11px] font-bold text-[var(--accent)] hover:underline flex items-center gap-1 cursor-pointer"
                            >
                              <Edit3 size={11} /> {item.reflections ? 'Edit Notes' : 'Add Note'}
                            </button>
                          )}
                        </div>

                        {isEditing ? (
                          <div className="space-y-2">
                            <textarea
                              value={reflectionText}
                              onChange={(e) => setReflectionText(e.target.value)}
                              placeholder="Write your reflections, observations, or key takeaways for this activity..."
                              className="w-full p-2.5 rounded-xl border border-[var(--border-strong)] bg-[var(--surface-elevated)] text-[var(--text)] text-xs focus:ring-2 focus:ring-[var(--accent)]"
                              rows={3}
                            />
                            <div className="flex justify-end gap-2">
                              <button
                                type="button"
                                onClick={() => setEditingReflectionId(null)}
                                className="px-2.5 py-1 text-[11px] font-bold text-[var(--text-soft)] hover:underline cursor-pointer"
                              >
                                Cancel
                              </button>
                              <button
                                type="button"
                                onClick={() => handleSaveReflection(item.activity_id, reflectionText)}
                                disabled={savingReflection}
                                className="px-3 py-1 rounded-lg bg-[var(--accent)] text-white text-[11px] font-bold flex items-center gap-1 cursor-pointer"
                              >
                                {savingReflection ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
                                <span>Save Reflection</span>
                              </button>
                            </div>
                          </div>
                        ) : item.reflections ? (
                          <p className="text-[11px] text-[var(--text-soft)] leading-relaxed italic">
                            "{item.reflections}"
                          </p>
                        ) : (
                          <p className="text-[11px] text-[var(--text-faint)] italic">
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
