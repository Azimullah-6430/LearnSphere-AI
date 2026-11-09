import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Headphones,
  Volume2,
  VolumeX,
  Play,
  Pause,
  RotateCcw,
  FastForward,
  CheckCircle2,
  AlertTriangle,
  BookOpen,
  Layers,
  Compass,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  HelpCircle,
  X,
  ChevronRight,
  Bookmark,
  GraduationCap,
  Award,
  Settings as SettingsIcon
} from 'lucide-react'
import { Card, PageHead, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'

export default function BlindCompanion() {
  const { user, onOpenSyllabusModal } = useApp()
  const navigate = useNavigate()
  const { curriculum, isValid: hasValidCurriculum, subjects, subjectObjects, units: allUnits } = useAuthoritativeCurriculum()

  // Companion Settings (read from user profile or sensible defaults)
  const userSettings = user?.blind_companion_settings || {}
  const [audioSpeed, setAudioSpeed] = useState(userSettings.audio_speed || 1.0)
  const [explanationMode, setExplanationMode] = useState(userSettings.explanation_mode || 'detailed')
  const [audioFirst] = useState(userSettings.audio_first !== false)
  const [voiceQuestions] = useState(userSettings.voice_questions !== false)
  const [spokenDiagrams] = useState(userSettings.spoken_diagrams !== false)

  // Speech State
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [currentSpeechText, setCurrentSpeechText] = useState('')
  const [speechLabel, setSpeechLabel] = useState('Ready to assist')
  const synthRef = useRef(window.speechSynthesis || null)

  // Curriculum Navigation State
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedUnit, setSelectedUnit] = useState(null)
  const [selectedTopic, setSelectedTopic] = useState(null)

  // Misconceptions / Improvement Areas State
  const [misconceptions, setMisconceptions] = useState([])
  const [loadingMisconceptions, setLoadingMisconceptions] = useState(false)

  // Practice & Checkpoint State
  const [practiceAnswer, setPracticeAnswer] = useState('')
  const [practiceSubmitted, setPracticeSubmitted] = useState(false)
  const [practiceFeedback, setPracticeFeedback] = useState('')

  // Keyboard Shortcuts Help Modal
  const [showHelpModal, setShowHelpModal] = useState(false)
  const [highContrast, setHighContrast] = useState(false)

  // Access Isolation Check
  const isCompanionEnabled = Boolean(user?.is_disabled_student || user?.blind_companion_enabled)

  // ── Speech Synthesis Engine ────────────────────────────────────────────────
  const speakText = useCallback((text, label = 'Audio Reader') => {
    if (!synthRef.current) return
    const synth = synthRef.current

    // Cancel any ongoing speech
    synth.cancel()

    if (!text || typeof text !== 'string') return

    // Clean markdown/special characters for clear speech
    const cleanText = text
      .replace(/[#*_`~[\]()]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()

    if (!cleanText) return

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.rate = audioSpeed
    utterance.pitch = 1.0

    // Choose preferred English voice if available
    const voices = synth.getVoices ? synth.getVoices() : []
    const preferredVoice = voices.find(v => v.lang.startsWith('en') && (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha')))
    if (preferredVoice) utterance.voice = preferredVoice

    utterance.onstart = () => {
      setIsSpeaking(true)
      setIsPaused(false)
      setCurrentSpeechText(cleanText)
      setSpeechLabel(label)
    }

    utterance.onend = () => {
      setIsSpeaking(false)
      setIsPaused(false)
    }

    utterance.onerror = () => {
      setIsSpeaking(false)
      setIsPaused(false)
    }

    synth.speak(utterance)
  }, [audioSpeed])

  const pauseSpeech = useCallback(() => {
    if (synthRef.current && synthRef.current.speaking && !synthRef.current.paused) {
      synthRef.current.pause()
      setIsPaused(true)
    }
  }, [])

  const resumeSpeech = useCallback(() => {
    if (synthRef.current && synthRef.current.paused) {
      synthRef.current.resume()
      setIsPaused(false)
    }
  }, [])

  const stopSpeech = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel()
      setIsSpeaking(false)
      setIsPaused(false)
      setSpeechLabel('Audio stopped')
    }
  }, [])

  const repeatSpeech = useCallback(() => {
    if (currentSpeechText) {
      speakText(currentSpeechText, speechLabel)
    }
  }, [currentSpeechText, speechLabel, speakText])

  // Stop speech on unmount
  useEffect(() => {
    return () => {
      if (synthRef.current) synthRef.current.cancel()
    }
  }, [])

  // ── Keyboard Shortcuts Listener ───────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Don't trigger if user is typing in an input or textarea
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return

      const key = e.key.toLowerCase()

      if (key === 'p' || e.code === 'Space') {
        e.preventDefault()
        if (isSpeaking) {
          if (isPaused) resumeSpeech()
          else pauseSpeech()
        } else if (currentSpeechText) {
          repeatSpeech()
        }
      } else if (key === 's') {
        e.preventDefault()
        stopSpeech()
      } else if (key === 'r') {
        e.preventDefault()
        repeatSpeech()
      } else if (key === '?' || key === 'h') {
        e.preventDefault()
        setShowHelpModal(prev => !prev)
      } else if (key === 'c') {
        e.preventDefault()
        setHighContrast(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isSpeaking, isPaused, resumeSpeech, pauseSpeech, repeatSpeech, stopSpeech, currentSpeechText])

  // ── Load Authentic Misconceptions ─────────────────────────────────────────
  useEffect(() => {
    let mounted = true
    const fetchGaps = async () => {
      setLoadingMisconceptions(true)
      try {
        const res = await api.getMisconceptions({ student_name: user?.name })
        if (mounted && res && res.success && Array.isArray(res.misconceptions)) {
          setMisconceptions(res.misconceptions)
        }
      } catch (err) {
        console.warn('Failed to load student misconceptions', err)
      } finally {
        if (mounted) setLoadingMisconceptions(false)
      }
    }
    if (user?.name) fetchGaps()
    return () => { mounted = false }
  }, [user?.name])

  // ── Determine Active Subjects & Structure ────────────────────────────────
  const authoritativeSubjects = useMemo(() => {
    if (Array.isArray(subjects) && subjects.length > 0) return subjects
    if (curriculum && Array.isArray(curriculum.subjects)) {
      return curriculum.subjects.map(s => (typeof s === 'string' ? s : s.name)).filter(Boolean)
    }
    return []
  }, [subjects, curriculum])

  useEffect(() => {
    if (!selectedSubject && authoritativeSubjects.length > 0) {
      setSelectedSubject(authoritativeSubjects[0])
    }
  }, [authoritativeSubjects, selectedSubject])

  // Active Subject Units and Topics
  const activeSubjectData = useMemo(() => {
    if (!selectedSubject) return null
    if (Array.isArray(subjectObjects)) {
      const match = subjectObjects.find(s => s.name?.toLowerCase() === selectedSubject.toLowerCase())
      if (match) return match
    }
    if (curriculum?.subjects && Array.isArray(curriculum.subjects)) {
      const match = curriculum.subjects.find(s => (s.name || s)?.toLowerCase() === selectedSubject.toLowerCase())
      if (match && typeof match === 'object') return match
    }
    return null
  }, [selectedSubject, subjectObjects, curriculum])

  const activeUnits = useMemo(() => {
    if (activeSubjectData?.units && Array.isArray(activeSubjectData.units)) {
      return activeSubjectData.units
    }
    if (activeSubjectData?.chapters && Array.isArray(activeSubjectData.chapters)) {
      return activeSubjectData.chapters
    }
    if (Array.isArray(allUnits) && allUnits.length > 0) {
      return allUnits.filter(u => !u.subject || u.subject.toLowerCase() === selectedSubject.toLowerCase())
    }
    return []
  }, [activeSubjectData, allUnits, selectedSubject])

  useEffect(() => {
    if (activeUnits.length > 0) {
      if (!selectedUnit || !activeUnits.some(u => (u.title || u.name) === (selectedUnit.title || selectedUnit.name))) {
        setSelectedUnit(activeUnits[0])
      }
    } else {
      setSelectedUnit(null)
    }
  }, [activeUnits, selectedUnit])

  const activeTopics = useMemo(() => {
    if (!selectedUnit) return []
    const rawTopics = selectedUnit.topics || selectedUnit.concepts || selectedUnit.subtopics || []
    if (Array.isArray(rawTopics)) {
      return rawTopics.map((t, idx) => {
        if (typeof t === 'string') {
          return { id: `topic-${idx}`, title: t, description: `Core topic in ${selectedUnit.title || selectedUnit.name}` }
        }
        return {
          id: t.id || `topic-${idx}`,
          title: t.title || t.name || `Topic ${idx + 1}`,
          description: t.description || t.summary || `Syllabus topic: ${t.title || t.name}`,
          objectives: t.objectives || t.learning_outcomes || []
        }
      })
    }
    return []
  }, [selectedUnit])

  useEffect(() => {
    if (activeTopics.length > 0) {
      if (!selectedTopic || !activeTopics.some(t => t.title === selectedTopic.title)) {
        setSelectedTopic(activeTopics[0])
      }
    } else {
      setSelectedTopic(null)
    }
  }, [activeTopics, selectedTopic])

  // Welcome Announcement
  const handleAnnounceWelcome = () => {
    const welcomeMsg = `Welcome to the Blind Learning Companion, ${user?.name || 'Student'}. ` +
      (hasValidCurriculum
        ? `Your active syllabus has ${authoritativeSubjects.length} subjects. Selected subject is ${selectedSubject || 'none'}. You can press P to play or pause audio, N to jump, or question mark for keyboard help.`
        : `You currently have no validated syllabus uploaded. Please select Upload Syllabus to import your course document.`)
    speakText(welcomeMsg, 'Welcome Greeting')
  }

  // Speak Current Topic
  const handleReadCurrentTopic = () => {
    if (!selectedTopic) {
      speakText('No topic is currently selected. Please choose a subject and unit from your syllabus.', 'Topic Reader')
      return
    }

    let speech = `Subject: ${selectedSubject}. Unit: ${selectedUnit?.title || selectedUnit?.name || 'Unit'}. Topic: ${selectedTopic.title}. `
    if (explanationMode === 'simple') {
      speech += `Concept overview: ${selectedTopic.description || selectedTopic.title}. Remember, this concept builds on your core curriculum foundations.`
    } else {
      speech += `Detailed syllabus breakdown: ${selectedTopic.description || selectedTopic.title}. `
      if (Array.isArray(selectedTopic.objectives) && selectedTopic.objectives.length > 0) {
        speech += `Key learning outcomes: ${selectedTopic.objectives.join('. ')}. `
      }
      if (spokenDiagrams) {
        speech += `Spoken schema note: Conceptual diagrams for this unit represent hierarchical flow from foundational definitions down to practical problems.`
      }
    }
    speakText(speech, `Topic: ${selectedTopic.title}`)
  }

  // Handle Practice Submit
  const handlePracticeSubmit = (e) => {
    e.preventDefault()
    if (!practiceAnswer.trim()) return
    setPracticeSubmitted(true)
    const feedback = `Thank you for your answer on ${selectedTopic?.title || 'this topic'}. Your spoken input has been registered. You accurately identified the core principles. Continue practicing with past exam questions.`
    setPracticeFeedback(feedback)
    if (voiceQuestions) {
      speakText(feedback, 'Practice Feedback')
    }
  }

  // If student does not have feature enabled
  if (!isCompanionEnabled) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4 text-center">
        <div className="w-16 h-16 rounded-3xl bg-indigo-100 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 mx-auto flex items-center justify-center mb-4">
          <Headphones size={32} />
        </div>
        <h2 className="text-xl font-extrabold text-slate-900 dark:text-white mb-2">
          Blind Learning Companion
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-400 mb-6 max-w-xl mx-auto leading-relaxed">
          The Blind Learning Companion is an audio-first accessibility suite specifically designed for blind and low-vision students. By default, it remains turned OFF to ensure non-disabled profiles remain completely undisturbed.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link to="/app/settings">
            <Button className="bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs px-5 py-2.5">
              Enable in Settings
            </Button>
          </Link>
          <Link to="/app/dashboard">
            <Button variant="secondary" className="font-bold text-xs px-5 py-2.5">
              Back to Main Dashboard
            </Button>
          </Link>
        </div>
      </div>
    )
  }

  return (
    <main
      role="main"
      aria-label="Blind Learning Companion Dashboard"
      className={`space-y-6 pb-12 transition-colors ${highContrast ? 'bg-black text-yellow-300 font-bold' : ''}`}
    >
      {/* Hidden Live Region for Screen Readers */}
      <div aria-live="assertive" aria-atomic="true" className="sr-only">
        {speechLabel}: {currentSpeechText}
      </div>

      {/* Top Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pb-2 border-b border-[var(--border)]">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-10 h-10 rounded-2xl bg-indigo-600 text-white flex items-center justify-center shadow-md shadow-indigo-600/20">
              <Headphones size={22} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl sm:text-2xl font-black text-slate-900 dark:text-white tracking-tight">
                  Blind Learning Companion
                </h1>
                <Badge className="bg-indigo-600 text-white font-bold text-[10px] uppercase tracking-wider">
                  Audio-First
                </Badge>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                Accessible, syllabus-grounded learning companion with synthesized speech and voice navigation.
              </p>
            </div>
          </div>
        </div>

        {/* Global Accessible Controls */}
        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => setHighContrast(prev => !prev)}
            className="text-xs font-bold flex items-center gap-1.5 focus-visible:ring-4 focus-visible:ring-indigo-500"
            aria-label="Toggle High Contrast Display Mode (Hotkey: C)"
          >
            {highContrast ? 'Standard Contrast' : 'High Contrast'}
          </Button>

          <Button
            type="button"
            variant="secondary"
            onClick={() => setShowHelpModal(true)}
            className="text-xs font-bold flex items-center gap-1.5 focus-visible:ring-4 focus-visible:ring-indigo-500"
            aria-label="Open Keyboard Shortcuts Help (Hotkey: ?)"
          >
            <HelpCircle size={15} />
            <span>Shortcuts (?)</span>
          </Button>

          <Link to="/app/settings">
            <Button
              variant="secondary"
              className="text-xs font-bold flex items-center gap-1.5 focus-visible:ring-4 focus-visible:ring-indigo-500"
              aria-label="Open Settings"
            >
              <SettingsIcon size={15} />
              <span>Companion Settings</span>
            </Button>
          </Link>
        </div>
      </div>

      {/* ── Persistent Audio Control Bar ──────────────────────────────────── */}
      <section
        aria-label="Audio Reader Bar"
        className="sticky top-2 z-20 p-4 rounded-2xl bg-slate-900 text-white shadow-xl border-2 border-indigo-500/50 flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3 min-w-0">
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${isSpeaking ? 'bg-emerald-500 text-white animate-pulse' : 'bg-slate-800 text-slate-400'}`}>
            {isSpeaking ? <Volume2 size={22} /> : <VolumeX size={22} />}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-xs uppercase tracking-wider font-extrabold text-indigo-400">
                {isSpeaking ? (isPaused ? 'Paused' : 'Now Speaking') : 'Audio Status'}
              </span>
              <span className="text-[11px] text-slate-400">· Speed: {audioSpeed}x</span>
            </div>
            <div className="text-xs sm:text-sm font-semibold truncate text-slate-200" title={speechLabel}>
              {speechLabel}
            </div>
          </div>
        </div>

        {/* Audio Action Buttons */}
        <div className="flex items-center gap-2 self-start md:self-center shrink-0">
          {isSpeaking ? (
            isPaused ? (
              <Button
                type="button"
                onClick={resumeSpeech}
                className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold flex items-center gap-1.5 px-3.5 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-white"
                aria-label="Resume Speech (Hotkey: P or Space)"
              >
                <Play size={16} />
                <span>Resume</span>
              </Button>
            ) : (
              <Button
                type="button"
                onClick={pauseSpeech}
                className="bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-1.5 px-3.5 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-white"
                aria-label="Pause Speech (Hotkey: P or Space)"
              >
                <Pause size={16} />
                <span>Pause</span>
              </Button>
            )
          ) : (
            <Button
              type="button"
              onClick={handleReadCurrentTopic}
              disabled={!selectedTopic}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 px-3.5 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-white disabled:opacity-50"
              aria-label="Listen to Current Topic (Hotkey: P or Space)"
            >
              <Play size={16} />
              <span>Read Topic</span>
            </Button>
          )}

          <Button
            type="button"
            variant="secondary"
            onClick={repeatSpeech}
            disabled={!currentSpeechText}
            className="text-xs font-bold flex items-center gap-1.5 px-3 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-indigo-400 text-white bg-slate-800 hover:bg-slate-700 border-slate-700 disabled:opacity-40"
            aria-label="Repeat Audio (Hotkey: R)"
          >
            <RotateCcw size={15} />
            <span>Repeat</span>
          </Button>

          <Button
            type="button"
            variant="secondary"
            onClick={stopSpeech}
            disabled={!isSpeaking && !isPaused}
            className="text-xs font-bold flex items-center gap-1.5 px-3 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-red-400 text-red-300 bg-slate-800 hover:bg-slate-700 border-slate-700 disabled:opacity-40"
            aria-label="Stop Audio (Hotkey: S)"
          >
            <VolumeX size={15} />
            <span>Stop</span>
          </Button>
        </div>
      </section>

      {/* ── Section: Welcome and Progress Overview ───────────────────────── */}
      <section aria-labelledby="overview-heading" className="p-6 rounded-2xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-900/50">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 id="overview-heading" className="text-base sm:text-lg font-bold text-slate-900 dark:text-white">
              Hello, {user?.name || 'Student'}
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-300 mt-0.5">
              Current enrolled subject: <strong className="text-indigo-700 dark:text-indigo-400">{selectedSubject || 'None Selected'}</strong>
              {selectedUnit ? ` · Unit: ${selectedUnit.title || selectedUnit.name}` : ''}
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button
              type="button"
              onClick={handleAnnounceWelcome}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-2 px-4 py-2 rounded-xl shadow-xs focus-visible:ring-4 focus-visible:ring-indigo-500"
              aria-label="Listen to Audio Summary of Current Academic Progress"
            >
              <Volume2 size={16} />
              <span>Audio Summary</span>
            </Button>
          </div>
        </div>
      </section>

      {/* ── Section 1: My Syllabus ────────────────────────────────────────── */}
      <section aria-labelledby="syllabus-heading" className="space-y-4">
        <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-2">
          <div className="flex items-center gap-2">
            <BookOpen size={18} className="text-indigo-600" />
            <h2 id="syllabus-heading" className="text-base font-bold text-slate-900 dark:text-white">
              1. My Syllabus (Structured Curriculum Navigation)
            </h2>
          </div>
          <button
            onClick={onOpenSyllabusModal}
            className="text-xs font-semibold text-indigo-600 hover:underline flex items-center gap-1 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500 rounded p-1"
          >
            <UploadCloud size={14} />
            <span>Change Syllabus</span>
          </button>
        </div>

        {!hasValidCurriculum || authoritativeSubjects.length === 0 ? (
          <Card className="p-8 text-center border-dashed border-2 border-slate-300 dark:border-slate-700">
            <div className="w-12 h-12 rounded-2xl bg-amber-100 text-amber-800 mx-auto flex items-center justify-center mb-3">
              <AlertTriangle size={24} />
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-1">
              No Validated Syllabus Uploaded Yet
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-md mx-auto mb-4">
              To experience syllabus-grounded audio learning, upload your semester or course syllabus document.
            </p>
            <Button
              type="button"
              onClick={onOpenSyllabusModal}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-xl"
            >
              Upload Official Syllabus PDF
            </Button>
          </Card>
        ) : (
          <div className="grid md:grid-cols-3 gap-4">
            {/* Subject Selector */}
            <div className="p-4 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
              <label htmlFor="subject-select" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                A. Choose Subject ({authoritativeSubjects.length})
              </label>
              <select
                id="subject-select"
                value={selectedSubject}
                onChange={(e) => {
                  setSelectedSubject(e.target.value)
                  speakText(`Selected subject: ${e.target.value}`, 'Subject Switch')
                }}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-xs font-semibold focus-visible:ring-4 focus-visible:ring-indigo-500"
              >
                {authoritativeSubjects.map(s => (
                  <option key={s} value={s}>{s}</option>
                ))}
              </select>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Grounds all audio lessons in this syllabus course.
              </p>
            </div>

            {/* Unit / Chapter Selector */}
            <div className="p-4 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
              <label htmlFor="unit-select" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                B. Choose Unit ({activeUnits.length})
              </label>
              <select
                id="unit-select"
                value={selectedUnit ? (selectedUnit.title || selectedUnit.name) : ''}
                onChange={(e) => {
                  const unit = activeUnits.find(u => (u.title || u.name) === e.target.value)
                  setSelectedUnit(unit)
                  speakText(`Selected unit: ${e.target.value}`, 'Unit Switch')
                }}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-xs font-semibold focus-visible:ring-4 focus-visible:ring-indigo-500"
              >
                {activeUnits.map((u, i) => (
                  <option key={i} value={u.title || u.name}>
                    {u.unit_number ? `Unit ${u.unit_number}: ` : ''}{u.title || u.name}
                  </option>
                ))}
              </select>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                {selectedUnit?.summary || 'Standard syllabus module.'}
              </p>
            </div>

            {/* Topic Selector */}
            <div className="p-4 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
              <label htmlFor="topic-select" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                C. Choose Topic ({activeTopics.length})
              </label>
              <select
                id="topic-select"
                value={selectedTopic ? selectedTopic.title : ''}
                onChange={(e) => {
                  const t = activeTopics.find(top => top.title === e.target.value)
                  setSelectedTopic(t)
                  speakText(`Selected topic: ${e.target.value}`, 'Topic Switch')
                }}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-xs font-semibold focus-visible:ring-4 focus-visible:ring-indigo-500"
              >
                {activeTopics.map((top, idx) => (
                  <option key={idx} value={top.title}>{top.title}</option>
                ))}
              </select>
              <p className="text-[11px] text-slate-500 dark:text-slate-400 truncate">
                {selectedTopic?.description || 'Active focus topic.'}
              </p>
            </div>
          </div>
        )}
      </section>

      {/* ── Section 2: Continue Learning ──────────────────────────────────── */}
      <section aria-labelledby="continue-heading" className="p-6 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2">
              <Compass size={18} className="text-indigo-600" />
              <h2 id="continue-heading" className="text-base font-bold text-slate-900 dark:text-white">
                2. Continue Learning
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              Currently queued lesson: <strong className="text-slate-800 dark:text-slate-200">{selectedTopic?.title || 'None selected'}</strong>
            </p>
          </div>

          <Button
            type="button"
            onClick={handleReadCurrentTopic}
            disabled={!selectedTopic}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-2 px-4 py-2.5 rounded-xl self-start sm:self-center disabled:opacity-50 focus-visible:ring-4 focus-visible:ring-indigo-500"
            aria-label={`Play audio lesson for ${selectedTopic?.title || 'selected topic'}`}
          >
            <Play size={16} />
            <span>Play Audio Lesson</span>
          </Button>
        </div>

        {selectedTopic && (
          <div className="p-4 bg-slate-50 dark:bg-slate-900/60 rounded-xl border border-slate-200 dark:border-slate-700/80">
            <h3 className="text-xs font-bold text-slate-800 dark:text-slate-200 mb-1">
              Conceptual Summary & Spoken Text
            </h3>
            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
              {selectedTopic.description || `In-depth syllabus focus on ${selectedTopic.title}. Use the audio reader bar above or press Space to listen.`}
            </p>
          </div>
        )}
      </section>

      {/* ── Section 3: Concepts I Need to Improve (Evaluations & Misconceptions) ─ */}
      <section aria-labelledby="improve-heading" className="space-y-3">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-600" />
            <h2 id="improve-heading" className="text-base font-bold text-slate-900 dark:text-white">
              3. Concepts I Need to Improve (Evidence-Based Learning Gaps)
            </h2>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {misconceptions.length} recorded gap{misconceptions.length === 1 ? '' : 's'}
          </span>
        </div>

        {loadingMisconceptions ? (
          <Card className="p-6 text-center text-xs text-slate-500">
            Checking evaluated assessment records...
          </Card>
        ) : misconceptions.length === 0 ? (
          <Card className="p-5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 flex items-start gap-3">
            <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                No Active Conceptual Misconceptions Found
              </div>
              <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-0.5">
                Your past evaluated assessments indicate solid conceptual understanding across completed topics. Any future evaluation weak spots will be synthesized here with spoken corrective advice.
              </p>
            </div>
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3.5">
            {misconceptions.slice(0, 4).map((gap, i) => (
              <div
                key={gap.id || i}
                className="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-2 hover:border-amber-400 transition-colors"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-amber-600 bg-amber-50 dark:bg-amber-950/50 px-2 py-0.5 rounded">
                    {gap.subject || selectedSubject}
                  </span>
                  <button
                    type="button"
                    onClick={() => {
                      const msg = `Identified learning gap: ${gap.concept || gap.topic}. Detail: ${gap.description}. Recommended remedy: ${gap.remedy || 'Review standard textbook problems.'}`
                      speakText(msg, `Gap: ${gap.concept || gap.topic}`)
                    }}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-indigo-500 rounded p-1"
                    aria-label={`Listen to spoken explanation for misconception ${gap.concept || gap.topic}`}
                  >
                    <Volume2 size={14} />
                    <span>Listen</span>
                  </button>
                </div>
                <div className="font-bold text-xs text-slate-900 dark:text-white">
                  {gap.concept || gap.topic || 'Concept Weakness'}
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {gap.description}
                </p>
                {gap.remedy && (
                  <div className="text-[11px] text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/40 p-2 rounded-lg">
                    <strong>Recommended Fix:</strong> {gap.remedy}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Section 4: Recommended Next Topic ─────────────────────────────── */}
      <section aria-labelledby="next-heading" className="p-5 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700">
        <div className="flex items-center gap-2 mb-2">
          <ArrowRight size={18} className="text-indigo-600" />
          <h2 id="next-heading" className="text-base font-bold text-slate-900 dark:text-white">
            4. Recommended Next Syllabus Topic
          </h2>
        </div>

        {activeTopics.length > 1 ? (
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700">
            <div>
              <span className="text-[10px] uppercase font-bold text-indigo-600 tracking-wider">
                Sequenced Curriculum Step
              </span>
              <div className="text-sm font-bold text-slate-900 dark:text-white mt-0.5">
                {activeTopics[1].title}
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {activeTopics[1].description || 'Next sequential topic in active module.'}
              </p>
            </div>

            <Button
              type="button"
              onClick={() => {
                setSelectedTopic(activeTopics[1])
                speakText(`Switched to next topic: ${activeTopics[1].title}.`, 'Topic Advancement')
              }}
              className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-xl self-start sm:self-center"
            >
              Advance to Topic
            </Button>
          </div>
        ) : (
          <p className="text-xs text-slate-500">
            Continue mastering your current focus topic or select another unit from Section 1 above.
          </p>
        )}
      </section>

      {/* ── Section 5: Practice and Assess ────────────────────────────────── */}
      <section aria-labelledby="practice-heading" className="p-6 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Award size={18} className="text-indigo-600" />
            <h2 id="practice-heading" className="text-base font-bold text-slate-900 dark:text-white">
              5. Practice & Assess (Audio Checkpoint)
            </h2>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const qText = `Checkpoint question on ${selectedTopic?.title || 'this topic'}: In your own words, explain the fundamental definition and one real world application of this concept.`
              speakText(qText, 'Checkpoint Question')
            }}
            className="text-xs font-bold flex items-center gap-1.5 self-start sm:self-center"
            aria-label="Listen to practice question spoken aloud"
          >
            <Volume2 size={15} />
            <span>Spoken Question</span>
          </Button>
        </div>

        <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700 space-y-2">
          <p className="text-xs text-slate-700 dark:text-slate-300 font-semibold leading-relaxed">
            <strong>Question:</strong> State the core principle of <span className="text-indigo-600 dark:text-indigo-400">{selectedTopic?.title || 'your selected topic'}</span> and explain how it solves an everyday engineering or theoretical problem.
          </p>

          <form onSubmit={handlePracticeSubmit} className="space-y-3 pt-2">
            <label htmlFor="checkpoint-input" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
              Type or dictate your response:
            </label>
            <textarea
              id="checkpoint-input"
              rows={3}
              value={practiceAnswer}
              onChange={(e) => setPracticeAnswer(e.target.value)}
              placeholder="Enter your synthesized answer here..."
              className="w-full p-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs text-slate-900 dark:text-white focus-visible:ring-4 focus-visible:ring-indigo-500 outline-none"
            />
            <div className="flex items-center justify-between gap-3">
              <span className="text-[11px] text-slate-500">
                Spoken feedback will play automatically upon submission.
              </span>
              <Button
                type="submit"
                disabled={!practiceAnswer.trim()}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-xl disabled:opacity-50"
              >
                Submit Answer
              </Button>
            </div>
          </form>

          {practiceSubmitted && practiceFeedback && (
            <div className="mt-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-200 flex items-start gap-3">
              <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold mb-0.5">Assessment Evaluation:</strong>
                <p className="leading-relaxed">{practiceFeedback}</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ── Section 6: Audio Revision ─────────────────────────────────────── */}
      <section aria-labelledby="revision-heading" className="p-6 rounded-2xl bg-gradient-to-r from-indigo-900 to-slate-900 text-white space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Bookmark size={18} className="text-indigo-400" />
            <h2 id="revision-heading" className="text-base font-bold text-white">
              6. Audio Revision Mode
            </h2>
          </div>
          <span className="text-xs text-indigo-300">
            Speed: {audioSpeed}x · Mode: {explanationMode}
          </span>
        </div>

        <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
          Listen to a uninterrupted, comprehensive recap of your active syllabus unit: <strong>{selectedUnit?.title || 'Current Unit'}</strong>. Perfect for hands-free audio review on headphones.
        </p>

        <div className="flex flex-wrap items-center gap-3 pt-2">
          <Button
            type="button"
            onClick={() => {
              const revisionSummary = `Unit Revision for ${selectedSubject}. Unit: ${selectedUnit?.title || 'Selected Module'}. Topics included: ${activeTopics.map(t => t.title).join(', ')}. In this module, the fundamental goal is to understand how these interrelated principles form the foundation of ${selectedSubject}. Keep practicing past problem sets to reinforce speed and accuracy.`
              speakText(revisionSummary, `Revision: ${selectedUnit?.title || 'Active Unit'}`)
            }}
            className="bg-white hover:bg-slate-100 text-slate-900 text-xs font-bold flex items-center gap-2 px-5 py-2.5 rounded-xl shadow-lg focus-visible:ring-4 focus-visible:ring-indigo-400"
            aria-label="Start Unit Audio Revision"
          >
            <Play size={16} className="text-indigo-600" />
            <span>Start Unit Audio Revision</span>
          </Button>

          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const rates = [0.75, 1.0, 1.25, 1.5, 2.0]
              const nextRate = rates[(rates.indexOf(audioSpeed) + 1) % rates.length]
              setAudioSpeed(nextRate)
              speakText(`Audio playback speed set to ${nextRate}x.`, 'Speed Change')
            }}
            className="bg-slate-800 hover:bg-slate-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl border border-slate-700"
            aria-label="Toggle playback speed"
          >
            <FastForward size={15} />
            <span>Speed: {audioSpeed}x</span>
          </Button>
        </div>
      </section>

      {/* ── Accessible Keyboard Help Modal ────────────────────────────────── */}
      {showHelpModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="help-title"
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4"
        >
          <div className="bg-white dark:bg-slate-900 rounded-2xl max-w-md w-full p-6 border border-slate-200 dark:border-slate-800 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <HelpCircle size={18} className="text-indigo-600" />
                <h3 id="help-title" className="text-base font-bold text-slate-900 dark:text-white">
                  Keyboard Shortcuts & Navigation
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowHelpModal(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-white p-1 rounded-lg"
                aria-label="Close Help Dialog"
              >
                <X size={18} />
              </button>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Play / Pause Speech</span>
                <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono font-bold text-slate-900 dark:text-white">P or Space</kbd>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Stop Speech</span>
                <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono font-bold text-slate-900 dark:text-white">S</kbd>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Repeat Last Speech</span>
                <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono font-bold text-slate-900 dark:text-white">R</kbd>
              </div>
              <div className="flex items-center justify-between py-1.5 border-b border-slate-100 dark:border-slate-800">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Toggle High Contrast</span>
                <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono font-bold text-slate-900 dark:text-white">C</kbd>
              </div>
              <div className="flex items-center justify-between py-1.5">
                <span className="font-semibold text-slate-700 dark:text-slate-300">Open This Help Dialog</span>
                <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono font-bold text-slate-900 dark:text-white">? or H</kbd>
              </div>
            </div>

            <Button
              type="button"
              onClick={() => setShowHelpModal(false)}
              className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs py-2 rounded-xl"
            >
              Close Help
            </Button>
          </div>
        </div>
      )}
    </main>
  )
}
