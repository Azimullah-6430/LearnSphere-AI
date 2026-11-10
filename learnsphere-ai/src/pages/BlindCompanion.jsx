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
  Award,
  Mic,
  MicOff,
  Send,
  RefreshCw,
  Sliders,
  Cpu,
  Zap,
  Activity,
  Settings as SettingsIcon,
  Check,
  Edit3,
  FileText,
  AlertCircle,
  Clock,
  ArrowUpRight
} from 'lucide-react'
import { Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { narrateMathClient } from '../utils/blindAudio.js'

// ── HOTKEY MAP ───────────────────────────────────────────────────────────────
// Alt+1: My Syllabus
// Alt+2: Listen & Learn
// Alt+3: Practice
// Alt+4: My Progress
// Alt+5: Learning Settings
// Space: Pause / Resume Speech
// R: Repeat Current Audio
// S: Stop Speech
// M: Toggle Microphone
// ─────────────────────────────────────────────────────────────────────────────

export default function BlindCompanion() {
  const navigate = useNavigate()
  const { user, onOpenSyllabusModal, updateUserProfile } = useApp()
  const {
    curriculum,
    isValid: hasValidCurriculum,
    subjects,
    subjectObjects,
    units: allUnits
  } = useAuthoritativeCurriculum()

  // Master Activation State
  const isCompanionEnabled = Boolean(user?.is_disabled_student || user?.blind_companion_enabled)

  // Section State: 'syllabus' | 'learn' | 'practice' | 'progress' | 'settings'
  const [activeSection, setActiveSection] = useState('syllabus')

  // Live Screen Reader Announcement
  const [liveAnnouncement, setLiveAnnouncement] = useState('')
  const announceTimerRef = useRef(null)

  const announce = useCallback((text) => {
    if (!text) return
    setLiveAnnouncement('')
    if (announceTimerRef.current) clearTimeout(announceTimerRef.current)
    announceTimerRef.current = setTimeout(() => {
      setLiveAnnouncement(text)
    }, 50)
  }, [])

  // User Preferences
  const userSettings = user?.blind_companion_settings || {}
  const [audioSpeed, setAudioSpeed] = useState(userSettings.audio_speed || 1.0)
  const [explanationMode, setExplanationMode] = useState(userSettings.explanation_mode || 'detailed')
  const [audioFirstNav, setAudioFirstNav] = useState(userSettings.audio_first !== false)
  const [voiceInputEnabled, setVoiceInputEnabled] = useState(userSettings.voice_questions !== false)
  const [spokenDiagrams, setSpokenDiagrams] = useState(userSettings.spoken_diagrams !== false)
  const [highContrast, setHighContrast] = useState(Boolean(userSettings.high_contrast))
  const [savingSettings, setSavingSettings] = useState(false)
  const [settingsSuccess, setSettingsSuccess] = useState('')

  // Speech Synthesis Controller
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [currentSpeechText, setCurrentSpeechText] = useState('')
  const [speechLabel, setSpeechLabel] = useState('Audio Assistant Ready')
  const synthRef = useRef(typeof window !== 'undefined' ? window.speechSynthesis : null)
  const currentUtteranceRef = useRef(null)

  // Speech Recognition (Voice Input) Controller
  const [isListening, setIsListening] = useState(false)
  const [pendingTranscript, setPendingTranscript] = useState('')
  const [transcriptTarget, setTranscriptTarget] = useState(null) // 'question' | 'practice'
  const [isReviewingTranscript, setIsReviewingTranscript] = useState(false)
  const [voiceSupported, setVoiceSupported] = useState(false)
  const recognitionRef = useRef(null)

  // Active Curriculum Selection
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedUnit, setSelectedUnit] = useState(null)
  const [selectedTopic, setSelectedTopic] = useState(null)

  // Listen & Learn State
  const [teachingMode, setTeachingMode] = useState('structured_10_step')
  const [activeLesson, setActiveLesson] = useState(null)
  const [activeLessonSections, setActiveLessonSections] = useState([])
  const [activeSectionIndex, setActiveSectionIndex] = useState(0)
  const [loadingLesson, setLoadingLesson] = useState(false)
  const [studentQuestion, setStudentQuestion] = useState('')
  const [conversationHistory, setConversationHistory] = useState([])
  const [askingQuestion, setAskingQuestion] = useState(false)

  // Practice State
  const [practiceQuestion, setPracticeQuestion] = useState(null)
  const [loadingQuestion, setLoadingQuestion] = useState(false)
  const [practiceAnswer, setPracticeAnswer] = useState('')
  const [submittingPractice, setSubmittingPractice] = useState(false)
  const [practiceFeedback, setPracticeFeedback] = useState(null)

  // Progress & Learning Gaps State
  const [learningGaps, setLearningGaps] = useState([])
  const [topicStatusMap, setTopicStatusMap] = useState({})
  const [progressSummaryText, setProgressSummaryText] = useState('')
  const [loadingProgress, setLoadingProgress] = useState(false)
  const [learningPath, setLearningPath] = useState(null)
  const [loadingPath, setLoadingPath] = useState(false)

  // ── 1. Speech Synthesis Engine ─────────────────────────────────────────────
  const stopSpeech = useCallback(() => {
    if (synthRef.current) {
      synthRef.current.cancel()
    }
    setIsSpeaking(false)
    setIsPaused(false)
    setSpeechLabel('Audio stopped')
  }, [])

  const speakText = useCallback(
    (text, label = 'Audio Reader', onComplete) => {
      if (!synthRef.current) return
      stopSpeech()

      if (!text || typeof text !== 'string') return

      // Translate math notation and strip markdown symbols
      let clean = text
        .replace(/\$([^\$]+)\$/g, (_, expr) => narrateMathClient(expr))
        .replace(/###/g, '')
        .replace(/##/g, '')
        .replace(/#/g, '')
        .replace(/\*\*/g, '')
        .replace(/\*/g, '')
        .replace(/```mermaid[\s\S]*?```/g, ' Diagram workflow is narrated below. ')
        .replace(/```[\s\S]*?```/g, ' Code snippet. ')
        .replace(/\s+/g, ' ')
        .trim()

      if (!clean) return

      const utterance = new SpeechSynthesisUtterance(clean)
      utterance.rate = audioSpeed
      utterance.pitch = 1.0

      const voices = synthRef.current.getVoices ? synthRef.current.getVoices() : []
      const preferred = voices.find(
        (v) =>
          v.lang.startsWith('en') &&
          (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('Samantha'))
      )
      if (preferred) utterance.voice = preferred

      utterance.onstart = () => {
        setIsSpeaking(true)
        setIsPaused(false)
        setCurrentSpeechText(clean)
        setSpeechLabel(label)
        announce(label)
      }

      utterance.onend = () => {
        setIsSpeaking(false)
        setIsPaused(false)
        if (onComplete) onComplete()
      }

      utterance.onerror = () => {
        setIsSpeaking(false)
        setIsPaused(false)
      }

      currentUtteranceRef.current = utterance
      synthRef.current.speak(utterance)
    },
    [audioSpeed, stopSpeech, announce]
  )

  const pauseSpeech = useCallback(() => {
    if (synthRef.current && synthRef.current.speaking && !synthRef.current.paused) {
      synthRef.current.pause()
      setIsPaused(true)
      setSpeechLabel('Audio paused')
      announce('Audio paused')
    }
  }, [announce])

  const resumeSpeech = useCallback(() => {
    if (synthRef.current && synthRef.current.paused) {
      synthRef.current.resume()
      setIsPaused(false)
      setSpeechLabel('Audio resumed')
      announce('Audio resumed')
    }
  }, [announce])

  const repeatSpeech = useCallback(() => {
    if (currentSpeechText) {
      speakText(currentSpeechText, speechLabel)
    } else {
      announce('Nothing to repeat')
    }
  }, [currentSpeechText, speechLabel, speakText, announce])

  // Stop speech on unmount
  useEffect(() => {
    return () => {
      if (synthRef.current) synthRef.current.cancel()
    }
  }, [])

  // ── 2. Speech Recognition (Voice Input) Engine ─────────────────────────────
  useEffect(() => {
    const SpeechRec = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null
    if (SpeechRec) {
      setVoiceSupported(true)
      const instance = new SpeechRec()
      instance.continuous = false
      instance.interimResults = false
      instance.lang = 'en-US'

      instance.onstart = () => {
        setIsListening(true)
        announce('Listening. Please speak your answer or question clearly.')
      }

      instance.onresult = (evt) => {
        const transcript = evt.results?.[0]?.[0]?.transcript || ''
        if (transcript.trim()) {
          setPendingTranscript(transcript.trim())
          setIsReviewingTranscript(true)
          const readout = `Recognized speech: "${transcript.trim()}". Please review and confirm before submission.`
          speakText(readout, 'Voice Transcript Review')
        }
      }

      instance.onerror = (err) => {
        console.warn('[BlindCompanion] Speech recognition error:', err)
        setIsListening(false)
        announce('Speech recognition error. You can type using your keyboard.')
      }

      instance.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = instance
    } else {
      setVoiceSupported(false)
    }
  }, [announce, speakText])

  const startVoiceDictation = useCallback(
    (target) => {
      if (!voiceSupported) {
        announce('Speech recognition is not supported in this browser. Please use the keyboard text input.')
        return
      }
      stopSpeech()
      setTranscriptTarget(target)
      setPendingTranscript('')
      setIsReviewingTranscript(false)
      try {
        recognitionRef.current?.start()
      } catch (err) {
        console.debug('Recognition restart:', err)
      }
    },
    [voiceSupported, announce, stopSpeech]
  )

  const cancelVoiceDictation = useCallback(() => {
    try {
      recognitionRef.current?.stop()
    } catch {
      // ignore
    }
    setIsListening(false)
    setIsReviewingTranscript(false)
    setPendingTranscript('')
    announce('Voice dictation cancelled.')
  }, [announce])

  const confirmPendingTranscript = useCallback(() => {
    if (transcriptTarget === 'question') {
      setStudentQuestion(pendingTranscript)
      setIsReviewingTranscript(false)
      announce(`Question confirmed: ${pendingTranscript}`)
    } else if (transcriptTarget === 'practice') {
      setPracticeAnswer(pendingTranscript)
      setIsReviewingTranscript(false)
      announce(`Practice answer confirmed: ${pendingTranscript}`)
    }
    setPendingTranscript('')
  }, [transcriptTarget, pendingTranscript, announce])

  // ── 3. Navigation Switcher ─────────────────────────────────────────────────
  const switchSection = useCallback(
    (sectionKey) => {
      setActiveSection(sectionKey)
      stopSpeech()

      const labels = {
        syllabus: 'Section 1: My Syllabus. Browse your uploaded curriculum subjects, units, and learning objectives.',
        learn: 'Section 2: Listen & Learn. Central audio teaching and concept exploration.',
        practice: 'Section 3: Practice. Accessible topic-based practice with voice and keyboard answers.',
        progress: 'Section 4: My Progress. Review evidence-based learning gaps and your personalized learning path.',
        settings: 'Section 5: Learning Settings. Customize your speech speed, voice input, and display preferences.'
      }

      const announcement = labels[sectionKey] || `Switched to ${sectionKey}`
      announce(announcement)
      if (audioFirstNav) {
        speakText(announcement, `Navigation: ${sectionKey}`)
      }
    },
    [stopSpeech, announce, audioFirstNav, speakText]
  )

  // ── 4. Global Keyboard Shortcuts ──────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Avoid hotkeys when user is typing inside an input or textarea
      const tag = e.target?.tagName?.toLowerCase()
      const isInput = tag === 'input' || tag === 'textarea' || e.target?.isContentEditable

      // Navigation Hotkeys: Alt+1 to Alt+5 (works even in inputs)
      if (e.altKey && e.key === '1') {
        e.preventDefault()
        switchSection('syllabus')
        return
      }
      if (e.altKey && e.key === '2') {
        e.preventDefault()
        switchSection('learn')
        return
      }
      if (e.altKey && e.key === '3') {
        e.preventDefault()
        switchSection('practice')
        return
      }
      if (e.altKey && e.key === '4') {
        e.preventDefault()
        switchSection('progress')
        return
      }
      if (e.altKey && e.key === '5') {
        e.preventDefault()
        switchSection('settings')
        return
      }

      // Audio Control Shortcuts (when not typing in an input)
      if (!isInput) {
        if (e.code === 'Space') {
          e.preventDefault()
          if (isSpeaking && !isPaused) pauseSpeech()
          else if (isPaused) resumeSpeech()
        } else if (e.key === 'r' || e.key === 'R') {
          e.preventDefault()
          repeatSpeech()
        } else if (e.key === 's' || e.key === 'S') {
          e.preventDefault()
          stopSpeech()
        } else if (e.key === 'm' || e.key === 'M') {
          e.preventDefault()
          if (isListening) cancelVoiceDictation()
          else startVoiceDictation(activeSection === 'practice' ? 'practice' : 'question')
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [
    switchSection,
    isSpeaking,
    isPaused,
    pauseSpeech,
    resumeSpeech,
    repeatSpeech,
    stopSpeech,
    isListening,
    cancelVoiceDictation,
    startVoiceDictation,
    activeSection
  ])

  // ── 5. Auto-Initialize Curriculum Selection ────────────────────────────────
  useEffect(() => {
    if (subjects && subjects.length > 0 && !selectedSubject) {
      setSelectedSubject(subjects[0])
    }
  }, [subjects, selectedSubject])

  // Derive current subject's units & topics
  const currentUnits = useMemo(() => {
    if (!selectedSubject) return []

    // 1. Try subjectObjects
    const matchObj = (subjectObjects || []).find((s) => s.name === selectedSubject || s.code === selectedSubject)
    if (matchObj && Array.isArray(matchObj.units) && matchObj.units.length > 0) {
      return matchObj.units.map((u, idx) => ({
        id: u.id || `unit_${idx + 1}`,
        title: u.name || `Unit ${idx + 1}`,
        concepts: u.concepts || u.topics || []
      }))
    }

    // 2. Try curriculum.chapters or curriculum.units
    const chaps = curriculum?.chapters?.[selectedSubject] || curriculum?.units?.[selectedSubject]
    if (Array.isArray(chaps) && chaps.length > 0) {
      return chaps.map((u, idx) => {
        if (typeof u === 'string') {
          return { id: `unit_${idx + 1}`, title: u, concepts: [u] }
        }
        return {
          id: u.id || `unit_${idx + 1}`,
          title: u.name || `Unit ${idx + 1}`,
          concepts: u.concepts || u.topics || []
        }
      })
    }

    // 3. Fallback to global topics
    if (matchObj && Array.isArray(matchObj.topics) && matchObj.topics.length > 0) {
      return [{ id: 'unit_1', title: 'Curriculum Core Units', concepts: matchObj.topics }]
    }

    return []
  }, [selectedSubject, subjectObjects, curriculum])

  // When units change, auto-select first unit & first topic
  useEffect(() => {
    if (currentUnits.length > 0) {
      const u = currentUnits[0]
      setSelectedUnit(u)
      if (u.concepts && u.concepts.length > 0) {
        setSelectedTopic({
          title: u.concepts[0],
          unit: u.title,
          subject: selectedSubject,
          objectives: [`Master foundational concepts of ${u.concepts[0]}`]
        })
      }
    }
  }, [currentUnits, selectedSubject])

  // ── 6. Load Progress, Learning Gaps & Adaptive Path ────────────────────────
  const fetchProgressAndGaps = useCallback(async () => {
    setLoadingProgress(true)
    try {
      const gapsRes = await api.getBlindLearningGaps()
      if (gapsRes && gapsRes.success) {
        setLearningGaps(gapsRes.learning_gaps || [])
        setTopicStatusMap(gapsRes.topic_status_map || {})
        setProgressSummaryText(gapsRes.audio_summary || '')
      }
    } catch (err) {
      console.warn('[BlindCompanion] Error fetching learning gaps:', err)
    } finally {
      setLoadingProgress(false)
    }

    setLoadingPath(true)
    try {
      const pathRes = await api.getBlindLearningPath()
      if (pathRes && pathRes.success && pathRes.learning_path) {
        setLearningPath(pathRes.learning_path)
      }
    } catch (err) {
      console.warn('[BlindCompanion] Error fetching learning path:', err)
    } finally {
      setLoadingPath(false)
    }
  }, [])

  useEffect(() => {
    if (isCompanionEnabled) {
      fetchProgressAndGaps()
    }
  }, [isCompanionEnabled, fetchProgressAndGaps])

  // ── 7. Generate & Play Audio Lesson ────────────────────────────────────────
  const generateLesson = useCallback(
    async (modeOverride) => {
      if (!selectedTopic) {
        announce('Please select a topic from My Syllabus first.')
        return
      }

      const mode = modeOverride || teachingMode
      setLoadingLesson(true)
      stopSpeech()

      const topicTitle = selectedTopic.title
      const unitTitle = selectedUnit?.title || 'Unit'
      const subjectTitle = selectedSubject || 'Curriculum Subject'

      let promptMsg = ''
      if (mode === 'structured_10_step') {
        promptMsg = `Teach me ${topicTitle} from ${unitTitle} in ${subjectTitle} following the complete 10-step structured teaching workflow.`
      } else if (mode === 'concept_to_sense') {
        promptMsg = `Explain the visual diagram, circuit architecture, mathematical equations, and component breakdown for ${topicTitle} using Concept-to-Sense audio intelligence.`
      } else if (mode === 'simple') {
        promptMsg = `Explain ${topicTitle} in simple everyday language with intuitive analogies.`
      } else if (mode === 'quick_revision') {
        promptMsg = `Provide a rapid-fire high-yield exam revision for ${topicTitle} in ${subjectTitle}.`
      } else {
        promptMsg = `Provide a detailed subject-specific explanation of ${topicTitle} grounded in our syllabus.`
      }

      const payload = {
        message: promptMsg,
        subject: subjectTitle,
        unit: unitTitle,
        topic: topicTitle,
        subtopic: topicTitle,
        learning_objectives: selectedTopic.objectives || [],
        teaching_mode: mode,
        diagram_type:
          subjectTitle.toLowerCase().includes('physic') ||
          subjectTitle.toLowerCase().includes('electr') ||
          subjectTitle.toLowerCase().includes('circuit')
            ? 'Circuit Diagram'
            : subjectTitle.toLowerCase().includes('math')
            ? 'Mathematical Graph / Expression'
            : 'Architectural Flowchart',
        audio_friendly: true,
        explanation_mode: explanationMode,
        history: conversationHistory.slice(-4)
      }

      try {
        const res = await api.trainerChat(payload)
        if (res && res.success && res.reply) {
          const lessonText = res.reply

          // Parse into manageable sections by headings or numbers
          const rawSections = lessonText
            .split(/(?=###?\s+\d+\.|\n\d+\.\s+)/)
            .map((s) => s.trim())
            .filter(Boolean)

          const sections = rawSections.length > 1 ? rawSections : [lessonText]

          setActiveLesson({
            title: topicTitle,
            subject: subjectTitle,
            unit: unitTitle,
            mode: mode,
            fullText: lessonText,
            sections: sections
          })
          setActiveLessonSections(sections)
          setActiveSectionIndex(0)

          const intro = `Lesson ready for ${topicTitle}. Playing section 1.`
          speakText(`${intro} ${sections[0]}`, `Lesson: ${topicTitle}`)
        } else {
          const msg = res?.error || 'Teaching engine could not generate lesson. Please retry.'
          announce(msg)
          speakText(msg, 'Lesson Generation Notice')
        }
      } catch (err) {
        console.error('[BlindCompanion] Lesson generation error:', err)
        announce('Network error generating lesson. Please check connection.')
      } finally {
        setLoadingLesson(false)
      }
    },
    [selectedTopic, selectedUnit, selectedSubject, teachingMode, explanationMode, conversationHistory, stopSpeech, announce, speakText]
  )

  const playLessonSection = useCallback(
    (index) => {
      if (!activeLessonSections || index < 0 || index >= activeLessonSections.length) return
      setActiveSectionIndex(index)
      const secText = activeLessonSections[index]
      speakText(`Section ${index + 1} of ${activeLessonSections.length}. ${secText}`, `Section ${index + 1}`)
    },
    [activeLessonSections, speakText]
  )

  const nextLessonSection = useCallback(() => {
    if (activeSectionIndex < activeLessonSections.length - 1) {
      playLessonSection(activeSectionIndex + 1)
    } else {
      speakText('You have reached the end of this audio lesson. You can replay sections or start topic practice.', 'Lesson Completed')
    }
  }, [activeSectionIndex, activeLessonSections, playLessonSection, speakText])

  const prevLessonSection = useCallback(() => {
    if (activeSectionIndex > 0) {
      playLessonSection(activeSectionIndex - 1)
    }
  }, [activeSectionIndex, playLessonSection])

  // ── 8. Conversational Q&A Inside Topic ─────────────────────────────────────
  const submitStudentQuestion = useCallback(
    async (qText) => {
      const questionToSend = qText || studentQuestion
      if (!questionToSend.trim()) return

      if (!selectedTopic) {
        announce('Please select a topic from My Syllabus first.')
        return
      }

      setAskingQuestion(true)
      stopSpeech()

      const payload = {
        message: questionToSend,
        subject: selectedSubject,
        unit: selectedUnit?.title || 'Unit',
        topic: selectedTopic.title,
        subtopic: selectedTopic.title,
        learning_objectives: selectedTopic.objectives || [],
        teaching_mode: teachingMode,
        audio_friendly: true,
        explanation_mode: explanationMode,
        history: conversationHistory.slice(-6)
      }

      try {
        const res = await api.trainerChat(payload)
        if (res && res.success && res.reply) {
          const reply = res.reply
          setConversationHistory((prev) => [
            ...prev,
            { role: 'user', content: questionToSend },
            { role: 'assistant', content: reply }
          ])
          setStudentQuestion('')
          speakText(`Answer: ${reply}`, 'Tutor Reply')
        } else {
          announce('Could not answer question. Please try asking again.')
        }
      } catch (err) {
        console.error('[BlindCompanion] Question error:', err)
        announce('Network error answering question.')
      } finally {
        setAskingQuestion(false)
      }
    },
    [studentQuestion, selectedTopic, selectedSubject, selectedUnit, teachingMode, explanationMode, conversationHistory, stopSpeech, speakText, announce]
  )

  // ── 9. Practice Engine ─────────────────────────────────────────────────────
  const loadPracticeQuestion = useCallback(async () => {
    if (!selectedTopic) {
      announce('Select a topic first to practice.')
      return
    }

    setLoadingQuestion(true)
    setPracticeAnswer('')
    setPracticeFeedback(null)
    stopSpeech()

    const subjectTitle = selectedSubject || 'Curriculum Subject'
    const topicTitle = selectedTopic.title

    try {
      // Use existing mastery question generator
      const res = await api.generateBlindMasteryQuestions({
        subject: subjectTitle,
        unit: selectedUnit?.title || 'Unit',
        topic: topicTitle,
        learning_objectives: selectedTopic.objectives || [],
        tier: 'adaptive'
      })

      if (res && res.success && Array.isArray(res.questions) && res.questions.length > 0) {
        const q = res.questions[0]
        setPracticeQuestion(q)
        const qSpeech = `Practice question for ${topicTitle}: ${q.question_text || q.question}. You can speak your answer by pressing M or type your response.`
        speakText(qSpeech, 'Practice Question')
      } else {
        // Fallback to targeted question from AI tutor
        const tutorRes = await api.trainerChat({
          message: `Give me 1 single diagnostic practice question to test my understanding of ${topicTitle}. Do not reveal the answer.`,
          subject: subjectTitle,
          unit: selectedUnit?.title || 'Unit',
          topic: topicTitle,
          teaching_mode: 'structured_10_step',
          audio_friendly: true
        })

        if (tutorRes && tutorRes.success && tutorRes.reply) {
          const q = {
            id: `q_${Date.now()}`,
            subject: subjectTitle,
            topic: topicTitle,
            question_text: tutorRes.reply,
            expected_answer: 'Thorough explanation of core principles'
          }
          setPracticeQuestion(q)
          speakText(`Diagnostic Practice Question: ${tutorRes.reply}`, 'Practice Question')
        } else {
          announce('Could not generate practice question. Please retry.')
        }
      }
    } catch (err) {
      console.error('[BlindCompanion] Practice question error:', err)
      announce('Error retrieving practice question.')
    } finally {
      setLoadingQuestion(false)
    }
  }, [selectedTopic, selectedSubject, selectedUnit, stopSpeech, speakText, announce])

  const submitPracticeAnswer = useCallback(async () => {
    if (!practiceAnswer.trim() || !practiceQuestion) {
      announce('Please enter or speak your answer before submitting.')
      return
    }

    setSubmittingPractice(true)
    stopSpeech()

    const payload = {
      subject: practiceQuestion.subject || selectedSubject,
      unit: selectedUnit?.title || 'Unit',
      topic: practiceQuestion.topic || selectedTopic?.title,
      subtopic: practiceQuestion.topic || selectedTopic?.title,
      question_text: practiceQuestion.question_text || practiceQuestion.question,
      expected_answer: practiceQuestion.expected_answer || 'Accurate syllabus response',
      student_answer: practiceAnswer.trim(),
      submission_mode: 'accessible_companion'
    }

    try {
      const res = await api.submitBlindPractice(payload)
      if (res && res.success) {
        const isCorr = res.is_correct
        const score = res.score ?? (isCorr ? 5 : 2)
        const maxScore = res.max_score ?? 5
        const advice = res.feedback || (isCorr ? 'Excellent concept understanding demonstrated.' : 'Review foundational definitions and retry.')

        const fb = {
          is_correct: isCorr,
          score: score,
          max_score: maxScore,
          feedback: advice,
          raw: res
        }
        setPracticeFeedback(fb)

        const fbSpeech = isCorr
          ? `Correct! Score: ${score} out of ${maxScore}. ${advice}`
          : `Needs practice. Score: ${score} out of ${maxScore}. ${advice}`

        speakText(fbSpeech, 'Evaluation Feedback')
        // Refresh gaps in background
        fetchProgressAndGaps()
      } else {
        announce('Could not evaluate answer. Please try again.')
      }
    } catch (err) {
      console.error('[BlindCompanion] Practice submission error:', err)
      announce('Network error during evaluation.')
    } finally {
      setSubmittingPractice(false)
    }
  }, [practiceAnswer, practiceQuestion, selectedSubject, selectedUnit, selectedTopic, stopSpeech, speakText, announce, fetchProgressAndGaps])

  // ── 10. Save Learning Settings ─────────────────────────────────────────────
  const handleSaveSettings = useCallback(async () => {
    setSavingSettings(true)
    setSettingsSuccess('')
    try {
      const payload = {
        blind_companion_enabled: true,
        settings: {
          audio_speed: audioSpeed,
          explanation_mode: explanationMode,
          audio_first: audioFirstNav,
          voice_questions: voiceInputEnabled,
          spoken_diagrams: spokenDiagrams,
          high_contrast: highContrast,
          keyboard_nav: true
        }
      }
      const res = await api.updateBlindCompanionSettings(payload)
      if (res && res.success) {
        setSettingsSuccess('Preferences saved successfully.')
        announce('Preferences saved successfully to your account.')
        speakText('Your learning settings have been saved.', 'Settings Updated')
        if (updateUserProfile) {
          updateUserProfile({
            blind_companion_settings: payload.settings,
            blind_companion_enabled: true
          })
        }
      } else {
        announce('Failed to save settings. Please try again.')
      }
    } catch (err) {
      console.error('[BlindCompanion] Settings save error:', err)
      announce('Network error saving settings.')
    } finally {
      setSavingSettings(false)
    }
  }, [audioSpeed, explanationMode, audioFirstNav, voiceInputEnabled, spokenDiagrams, highContrast, announce, speakText, updateUserProfile])

  // ── 11. Enable Blind Companion for Student ─────────────────────────────────
  const handleEnableCompanion = useCallback(async () => {
    try {
      const res = await api.updateBlindCompanionSettings({
        blind_companion_enabled: true,
        is_disabled_student: true
      })
      if (res && res.success) {
        if (updateUserProfile) {
          updateUserProfile({ blind_companion_enabled: true, is_disabled_student: true })
        }
        announce('Blind Learning Companion enabled. Welcome to your audio-first learning hub.')
      }
    } catch (err) {
      console.error('[BlindCompanion] Enable error:', err)
    }
  }, [updateUserProfile, announce])

  // ── RENDER: NOT ENABLED STATE ──────────────────────────────────────────────
  if (!isCompanionEnabled) {
    return (
      <div className="max-w-3xl mx-auto py-12 px-4 space-y-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-indigo-600 text-white mx-auto flex items-center justify-center shadow-md">
          <Headphones size={32} />
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white">
          Blind Learning Companion
        </h1>
        <p className="text-sm sm:text-base text-slate-600 dark:text-slate-300 max-w-xl mx-auto leading-relaxed">
          An independent, audio-first learning environment designed specifically for blind and low-vision students.
          Features syllabus-grounded audio teaching, Concept-to-Sense visual descriptions, and accessible voice practice.
        </p>

        <div className="pt-4 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            onClick={handleEnableCompanion}
            className="w-full sm:w-auto px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-extrabold text-sm sm:text-base rounded-xl shadow-md cursor-pointer"
          >
            Enable Blind Learning Companion
          </Button>
          <Button
            variant="outline"
            onClick={() => navigate('/app/dashboard')}
            className="w-full sm:w-auto px-6 py-3 font-bold text-sm sm:text-base rounded-xl cursor-pointer"
          >
            Return to Dashboard
          </Button>
        </div>
      </div>
    )
  }

  // ── RENDER: REDESIGNED COMPANION ───────────────────────────────────────────
  const themeClasses = highContrast
    ? 'bg-black text-yellow-300 min-h-screen selection:bg-yellow-400 selection:text-black'
    : 'min-h-screen space-y-6 pb-20'

  return (
    <div className={themeClasses} role="region" aria-label="Blind Learning Companion Workspace">
      {/* ── ARIA LIVE REGION FOR SCREEN READERS ────────────────────────────── */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {liveAnnouncement}
      </div>

      {/* ── TOP ACCESSIBLE CONTROLLER BAR ──────────────────────────────────── */}
      <header
        role="banner"
        className={`p-4 sm:p-5 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 shadow-xs ${
          highContrast
            ? 'bg-black border-yellow-400 text-yellow-300'
            : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800'
        }`}
      >
        <div className="flex items-center gap-3.5">
          <div
            className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
              highContrast ? 'bg-yellow-400 text-black' : 'bg-indigo-600 text-white shadow-xs'
            }`}
          >
            <Headphones size={24} />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg sm:text-xl font-extrabold tracking-tight">
                Blind Learning Companion
              </h1>
              <span
                className={`text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider ${
                  highContrast ? 'bg-yellow-400 text-black' : 'bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300'
                }`}
              >
                Audio-First
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {speechLabel}
            </p>
          </div>
        </div>

        {/* Global Audio Controls Bar */}
        <div className="flex items-center gap-2 flex-wrap">
          <button
            type="button"
            onClick={() => {
              if (isSpeaking && !isPaused) pauseSpeech()
              else if (isPaused) resumeSpeech()
              else if (currentSpeechText) repeatSpeech()
            }}
            className={`px-3.5 py-2 rounded-xl text-xs font-extrabold flex items-center gap-1.5 cursor-pointer transition-all focus-visible:ring-4 ${
              highContrast
                ? 'bg-yellow-400 text-black hover:bg-yellow-300 focus-visible:ring-white'
                : 'bg-indigo-600 hover:bg-indigo-700 text-white focus-visible:ring-indigo-300'
            }`}
            aria-label={isSpeaking && !isPaused ? 'Pause Audio (Space)' : 'Play / Resume Audio (Space)'}
          >
            {isSpeaking && !isPaused ? <Pause size={15} /> : <Play size={15} />}
            <span>{isSpeaking && !isPaused ? 'Pause' : isPaused ? 'Resume' : 'Play'}</span>
          </button>

          <button
            type="button"
            onClick={repeatSpeech}
            className={`px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-all border focus-visible:ring-4 ${
              highContrast
                ? 'border-yellow-400 text-yellow-300 hover:bg-yellow-950 focus-visible:ring-white'
                : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
            aria-label="Repeat Audio (Hotkey: R)"
          >
            <RotateCcw size={14} />
            <span>Repeat (R)</span>
          </button>

          <button
            type="button"
            onClick={stopSpeech}
            className={`px-3 py-2 rounded-xl text-xs font-bold flex items-center gap-1.5 cursor-pointer transition-all border focus-visible:ring-4 ${
              highContrast
                ? 'border-yellow-400 text-yellow-300 hover:bg-yellow-950 focus-visible:ring-white'
                : 'border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800'
            }`}
            aria-label="Stop Audio (Hotkey: S)"
          >
            <VolumeX size={14} />
            <span>Stop (S)</span>
          </button>

          {/* Speed Selector */}
          <div className="flex items-center gap-1 border rounded-xl px-2 py-1 text-xs font-bold">
            <span className="text-[11px] text-slate-400">Speed:</span>
            {[0.75, 1.0, 1.25, 1.5].map((rate) => (
              <button
                key={rate}
                type="button"
                onClick={() => {
                  setAudioSpeed(rate)
                  announce(`Speech speed set to ${rate}x`)
                }}
                className={`px-1.5 py-0.5 rounded text-[11px] font-bold cursor-pointer ${
                  audioSpeed === rate
                    ? highContrast
                      ? 'bg-yellow-400 text-black'
                      : 'bg-indigo-600 text-white'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-white'
                }`}
                aria-label={`Set speech speed to ${rate}x`}
              >
                {rate}x
              </button>
            ))}
          </div>

          {/* High Contrast Toggle */}
          <button
            type="button"
            onClick={() => {
              const next = !highContrast
              setHighContrast(next)
              announce(next ? 'High contrast enabled' : 'Normal contrast enabled')
            }}
            className={`px-3 py-2 rounded-xl text-xs font-bold border cursor-pointer ${
              highContrast ? 'border-yellow-400 bg-yellow-400 text-black' : 'border-slate-300 dark:border-slate-700'
            }`}
            aria-label="Toggle High Contrast Display Mode"
          >
            {highContrast ? 'Normal Contrast' : 'High Contrast'}
          </button>
        </div>
      </header>

      {/* ── 5 DEDICATED SECTIONS NAVIGATION BAR ───────────────────────────── */}
      <nav
        role="navigation"
        aria-label="Blind Learning Companion Main Navigation"
        className="grid grid-cols-2 sm:grid-cols-5 gap-2"
      >
        {[
          { key: 'syllabus', label: '1. My Syllabus', hotkey: 'Alt+1', desc: 'Browse courses & topics', icon: BookOpen },
          { key: 'learn', label: '2. Listen & Learn', hotkey: 'Alt+2', desc: 'Audio teaching & diagrams', icon: Headphones },
          { key: 'practice', label: '3. Practice', hotkey: 'Alt+3', desc: 'Q&A checkpoints', icon: Award },
          { key: 'progress', label: '4. My Progress', hotkey: 'Alt+4', desc: 'Gaps & learning path', icon: Compass },
          { key: 'settings', label: '5. Settings', hotkey: 'Alt+5', desc: 'Audio & preferences', icon: Sliders }
        ].map((item) => {
          const Icon = item.icon
          const isActive = activeSection === item.key
          return (
            <button
              key={item.key}
              type="button"
              onClick={() => switchSection(item.key)}
              aria-current={isActive ? 'page' : undefined}
              className={`p-3.5 sm:p-4 rounded-2xl border text-left transition-all cursor-pointer focus-visible:ring-4 ${
                isActive
                  ? highContrast
                    ? 'border-yellow-400 bg-yellow-400 text-black font-extrabold focus-visible:ring-white shadow-md'
                    : 'border-indigo-600 bg-indigo-50/90 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 font-extrabold focus-visible:ring-indigo-400 shadow-xs'
                  : highContrast
                  ? 'border-yellow-900 bg-black text-yellow-400 hover:border-yellow-400'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-700 dark:text-slate-300 hover:border-indigo-400'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <Icon size={18} className={isActive ? (highContrast ? 'text-black' : 'text-indigo-600 dark:text-indigo-400') : 'text-slate-400'} />
                <span className={`text-[10px] font-extrabold px-1.5 py-0.5 rounded ${highContrast ? 'bg-black text-yellow-400' : 'bg-slate-100 dark:bg-slate-800 text-slate-500'}`}>
                  {item.hotkey}
                </span>
              </div>
              <div className="text-sm font-extrabold leading-tight">{item.label}</div>
              <div className={`text-[11px] mt-0.5 truncate ${isActive ? (highContrast ? 'text-black font-semibold' : 'text-indigo-700 dark:text-indigo-300') : 'text-slate-500 dark:text-slate-400'}`}>
                {item.desc}
              </div>
            </button>
          )
        })}
      </nav>

      {/* ── MAIN CONTENT CONTAINER ────────────────────────────────────────── */}
      <main id="blind-main" tabIndex="-1" className="space-y-6 outline-none">
        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 1: MY SYLLABUS                                            */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeSection === 'syllabus' && (
          <div className="space-y-6">
            <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                    <BookOpen size={20} className="text-indigo-600" />
                    <span>My Uploaded Syllabus</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Your authenticated course curriculum is the source of truth for all lessons and practice.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      const msg = hasValidCurriculum
                        ? `Your uploaded syllabus contains ${subjects.length} subjects: ${subjects.join(', ')}.`
                        : 'No validated syllabus document found. Please upload your course syllabus PDF.'
                      speakText(msg, 'Syllabus Summary')
                    }}
                    className="text-xs font-bold flex items-center gap-1.5"
                    aria-label="Read syllabus overview aloud"
                  >
                    <Volume2 size={14} />
                    <span>Read Overview</span>
                  </Button>

                  <Button
                    size="sm"
                    onClick={onOpenSyllabusModal}
                    className="text-xs font-bold flex items-center gap-1.5 bg-indigo-600 text-white hover:bg-indigo-700"
                    aria-label="Upload or update syllabus document"
                  >
                    <UploadCloud size={14} />
                    <span>Upload Syllabus</span>
                  </Button>
                </div>
              </div>

              {!hasValidCurriculum ? (
                <div className="p-8 text-center border-2 border-dashed border-amber-300 dark:border-amber-800 rounded-2xl space-y-3 bg-amber-50/50 dark:bg-amber-950/20">
                  <AlertCircle size={36} className="text-amber-600 mx-auto" />
                  <h3 className="text-base font-extrabold text-slate-900 dark:text-white">
                    No Validated Syllabus Uploaded
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400 max-w-md mx-auto leading-relaxed">
                    Please upload your official course syllabus PDF to auto-extract your subjects, units, and learning
                    objectives. Your syllabus powers every audio lesson and practice checkpoint.
                  </p>
                  <Button
                    onClick={onOpenSyllabusModal}
                    className="bg-indigo-600 text-white hover:bg-indigo-700 font-bold text-xs px-5 py-2.5 rounded-xl shadow-xs"
                  >
                    Upload Syllabus Document Now
                  </Button>
                </div>
              ) : (
                <div className="grid lg:grid-cols-3 gap-5">
                  {/* Step 1: Subjects List */}
                  <div className="space-y-2">
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                      Step 1: Enrolled Subjects ({subjects.length})
                    </label>
                    <div className="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
                      {subjects.map((sName, sIdx) => {
                        const isSel = selectedSubject === sName
                        return (
                          <button
                            key={sIdx}
                            type="button"
                            onClick={() => {
                              setSelectedSubject(sName)
                              announce(`Subject selected: ${sName}`)
                              speakText(`Subject: ${sName}`, `Subject ${sIdx + 1}`)
                            }}
                            className={`w-full p-3 rounded-xl border text-left text-xs font-bold transition-all cursor-pointer flex items-center justify-between ${
                              isSel
                                ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                                : 'bg-slate-50 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:border-indigo-400'
                            }`}
                            aria-label={`Subject ${sIdx + 1}: ${sName}`}
                          >
                            <span className="truncate flex-1">{sName}</span>
                            <ChevronRight size={14} className={isSel ? 'text-white' : 'text-slate-400'} />
                          </button>
                        )
                      })}
                    </div>
                  </div>

                  {/* Step 2: Units List for Selected Subject */}
                  <div className="space-y-2">
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                      Step 2: Units for {selectedSubject || 'Subject'}
                    </label>
                    {currentUnits.length === 0 ? (
                      <p className="text-xs text-slate-500 py-3">No unit subdivisions detected for this subject.</p>
                    ) : (
                      <div className="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
                        {currentUnits.map((u, uIdx) => {
                          const isSel = selectedUnit?.title === u.title
                          return (
                            <button
                              key={uIdx}
                              type="button"
                              onClick={() => {
                                setSelectedUnit(u)
                                if (u.concepts && u.concepts.length > 0) {
                                  setSelectedTopic({
                                    title: u.concepts[0],
                                    unit: u.title,
                                    subject: selectedSubject,
                                    objectives: [`Master ${u.concepts[0]}`]
                                  })
                                }
                                announce(`Unit selected: ${u.title}`)
                                speakText(`Unit: ${u.title}. Contains ${u.concepts.length} syllabus topics.`, `Unit ${uIdx + 1}`)
                              }}
                              className={`w-full p-3 rounded-xl border text-left text-xs font-bold transition-all cursor-pointer flex items-center justify-between ${
                                isSel
                                ? 'bg-indigo-100 dark:bg-indigo-950/60 border-indigo-500 text-indigo-900 dark:text-indigo-200'
                                : 'bg-slate-50 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:border-indigo-400'
                              }`}
                              aria-label={`Unit ${uIdx + 1}: ${u.title}`}
                            >
                              <div className="truncate flex-1">
                                <div>{u.title}</div>
                                <div className="text-[10px] font-normal text-slate-500 mt-0.5">
                                  {u.concepts.length} concepts
                                </div>
                              </div>
                              <ChevronRight size={14} className="text-slate-400" />
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>

                  {/* Step 3: Topics List for Selected Unit */}
                  <div className="space-y-2">
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                      Step 3: Topics in {selectedUnit?.title || 'Unit'}
                    </label>
                    {!selectedUnit || (selectedUnit.concepts && selectedUnit.concepts.length === 0) ? (
                      <p className="text-xs text-slate-500 py-3">Select a unit to see topics.</p>
                    ) : (
                      <div className="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
                        {selectedUnit.concepts.map((conceptName, cIdx) => {
                          const isSel = selectedTopic?.title === conceptName
                          const statusKey = `${selectedSubject}::${conceptName}`
                          const topicStatus = topicStatusMap[statusKey] || 'Not started'
                          return (
                            <button
                              key={cIdx}
                              type="button"
                              onClick={() => {
                                const tObj = {
                                  title: conceptName,
                                  unit: selectedUnit.title,
                                  subject: selectedSubject,
                                  objectives: [`Master ${conceptName} in ${selectedSubject}`]
                                }
                                setSelectedTopic(tObj)
                                announce(`Topic selected: ${conceptName}. Status: ${topicStatus}`)
                                speakText(`Topic: ${conceptName}. Learning status: ${topicStatus}.`, `Topic: ${conceptName}`)
                              }}
                              className={`w-full p-3 rounded-xl border text-left text-xs font-bold transition-all cursor-pointer flex flex-col justify-between gap-1 ${
                                isSel
                                ? 'border-indigo-600 bg-indigo-600 text-white shadow-xs'
                                : 'bg-slate-50 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 hover:border-indigo-400'
                              }`}
                              aria-label={`Topic ${cIdx + 1}: ${conceptName}, Status: ${topicStatus}`}
                            >
                              <div className="truncate font-bold">{conceptName}</div>
                              <div className="flex items-center justify-between text-[10px] opacity-90">
                                <span>Status:</span>
                                <span className={`px-1.5 py-0.2 rounded font-extrabold ${isSel ? 'bg-white/20 text-white' : 'bg-slate-200 dark:bg-slate-700 text-slate-700 dark:text-slate-300'}`}>
                                  {topicStatus}
                                </span>
                              </div>
                            </button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Selected Topic Action Bar */}
              {selectedTopic && (
                <div className="p-4 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-800/80 flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-4">
                  <div className="min-w-0">
                    <span className="text-[10px] font-extrabold uppercase tracking-wider text-indigo-700 dark:text-indigo-300">
                      Active Syllabus Topic
                    </span>
                    <h3 className="text-base font-extrabold text-slate-900 dark:text-white truncate">
                      {selectedTopic.title}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-400 truncate mt-0.5">
                      {selectedSubject} · {selectedUnit?.title || 'Unit'}
                    </p>
                  </div>

                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      onClick={() => {
                        switchSection('learn')
                        generateLesson()
                      }}
                      className="text-xs font-extrabold bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-1.5 px-4 py-2 rounded-xl shadow-xs"
                      aria-label="Start Audio Lesson in Listen and Learn"
                    >
                      <Headphones size={15} />
                      <span>Start Audio Lesson</span>
                    </Button>

                    <Button
                      variant="outline"
                      onClick={() => {
                        switchSection('practice')
                        loadPracticeQuestion()
                      }}
                      className="text-xs font-extrabold flex items-center gap-1.5 px-4 py-2 rounded-xl"
                      aria-label="Practice This Topic Now"
                    >
                      <Award size={15} />
                      <span>Practice Topic</span>
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 2: LISTEN & LEARN                                         */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeSection === 'learn' && (
          <div className="space-y-6">
            {/* Active Topic Banner */}
            <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <span className="text-[11px] font-extrabold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                    Syllabus-Aware Audio Tutor
                  </span>
                  <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white mt-0.5">
                    {selectedTopic?.title || 'Please Select a Topic in My Syllabus'}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    {selectedSubject} · {selectedUnit?.title || 'Unit'}
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => switchSection('syllabus')}
                    className="text-xs font-bold"
                    aria-label="Change Topic from My Syllabus"
                  >
                    Change Topic
                  </Button>
                  <Button
                    size="sm"
                    onClick={() => generateLesson()}
                    disabled={loadingLesson || !selectedTopic}
                    className="text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-1.5 shadow-xs"
                    aria-label="Generate Audio Lesson for this topic"
                  >
                    <RefreshCw size={13} className={loadingLesson ? 'animate-spin' : ''} />
                    <span>{loadingLesson ? 'Generating…' : 'Generate Lesson'}</span>
                  </Button>
                </div>
              </div>

              {/* Teaching Mode Selector */}
              <div className="space-y-2">
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Select Teaching Mode
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
                  {[
                    { key: 'structured_10_step', label: '10-Step Master Lesson', desc: 'Full syllabus depth' },
                    { key: 'concept_to_sense', label: 'Concept-to-Sense', desc: 'Diagrams & equations' },
                    { key: 'simple', label: 'Simple Language', desc: 'Everyday analogies' },
                    { key: 'detailed', label: 'Detailed Rigor', desc: 'Governing laws' },
                    { key: 'quick_revision', label: 'Quick Revision', desc: 'High-yield points' }
                  ].map((m) => {
                    const isSel = teachingMode === m.key
                    return (
                      <button
                        key={m.key}
                        type="button"
                        onClick={() => {
                          setTeachingMode(m.key)
                          announce(`Teaching mode set to ${m.label}`)
                          generateLesson(m.key)
                        }}
                        className={`p-3 rounded-xl border text-left text-xs font-bold cursor-pointer transition-all ${
                          isSel
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                            : 'bg-slate-50 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-400'
                        }`}
                        aria-label={`Teaching mode: ${m.label}`}
                      >
                        <div className="truncate">{m.label}</div>
                        <div className={`text-[10px] mt-0.5 ${isSel ? 'text-indigo-100' : 'text-slate-400'}`}>
                          {m.desc}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Concept-to-Sense Verbalization Quick Actions */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700/80 space-y-2">
                <div className="text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <Sparkles size={14} className="text-indigo-600" />
                  <span>Concept-to-Sense Verbalization Shortcuts</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { label: 'Explain Diagram / Circuit', prompt: `Explain the visual structure, circuit components, polarity, and loops for ${selectedTopic?.title || 'this topic'} using Concept-to-Sense.` },
                    { label: 'Explain Equations & Math', prompt: `Verbalize every equation, symbol, and derivative step for ${selectedTopic?.title || 'this topic'} in plain spoken language.` },
                    { label: 'Explain Graphs & Trends', prompt: `Describe the graph axes, labels, units, and slope inflection points for ${selectedTopic?.title || 'this topic'}.` },
                    { label: 'Simpler Real-Life Analogy', prompt: `Explain ${selectedTopic?.title || 'this concept'} using an intuitive everyday real-world analogy (Feynman style).` }
                  ].map((act, aIdx) => (
                    <button
                      key={aIdx}
                      type="button"
                      onClick={() => submitStudentQuestion(act.prompt)}
                      className="p-2.5 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 text-left text-xs font-bold text-slate-800 dark:text-slate-200 hover:border-indigo-500 cursor-pointer shadow-2xs"
                      aria-label={act.label}
                    >
                      {act.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Audio Lesson Presentation & Section Navigation */}
              {loadingLesson ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-indigo-600 text-white mx-auto flex items-center justify-center animate-spin">
                    <RefreshCw size={20} />
                  </div>
                  <div className="text-sm font-extrabold text-slate-900 dark:text-white">
                    Generating Structured Audio Lesson for {selectedTopic?.title}…
                  </div>
                  <p className="text-xs text-slate-500 max-w-sm mx-auto">
                    Synthesizing syllabus learning objectives, formulas, and visual diagrams. Speech will begin automatically.
                  </p>
                </div>
              ) : activeLesson ? (
                <div className="space-y-4 pt-2">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-indigo-50/70 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/80">
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-extrabold text-indigo-900 dark:text-indigo-200">
                        Section {activeSectionIndex + 1} of {activeLessonSections.length}
                      </span>
                      <span className="text-slate-400">·</span>
                      <span className="text-xs text-slate-600 dark:text-slate-400 truncate max-w-xs sm:max-w-md">
                        {activeLesson.title}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={prevLessonSection}
                        disabled={activeSectionIndex === 0}
                        className="text-xs font-bold"
                        aria-label="Previous Lesson Section"
                      >
                        Previous
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => playLessonSection(activeSectionIndex)}
                        className="text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700 flex items-center gap-1"
                        aria-label="Replay Current Section"
                      >
                        <Volume2 size={13} />
                        <span>Replay</span>
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={nextLessonSection}
                        disabled={activeSectionIndex >= activeLessonSections.length - 1}
                        className="text-xs font-bold"
                        aria-label="Next Lesson Section"
                      >
                        Next
                      </Button>
                    </div>
                  </div>

                  {/* Section Jumper Bar */}
                  <div className="flex items-center gap-1.5 flex-wrap">
                    {activeLessonSections.map((sec, sIdx) => (
                      <button
                        key={sIdx}
                        type="button"
                        onClick={() => playLessonSection(sIdx)}
                        className={`px-3 py-1.5 rounded-lg text-xs font-bold border cursor-pointer ${
                          activeSectionIndex === sIdx
                            ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                            : 'border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-400'
                        }`}
                        aria-label={`Jump to Section ${sIdx + 1}`}
                      >
                        Sec {sIdx + 1}
                      </button>
                    ))}
                  </div>

                  {/* Section Text Reader Box */}
                  <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 text-sm leading-relaxed text-slate-800 dark:text-slate-200 whitespace-pre-wrap font-medium">
                    {activeLessonSections[activeSectionIndex]}
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-slate-500 text-xs">
                  Click &ldquo;Generate Lesson&rdquo; above to synthesize the 10-step audio lesson for this topic.
                </div>
              )}
            </div>

            {/* Explore Concepts: Conversational Tutor & Doubt Resolution */}
            <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
              <div>
                <h3 className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                  <Compass size={18} className="text-indigo-600" />
                  <span>Explore Concepts &amp; Ask Questions</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                  Ask doubts through speech or keyboard. Answers remain strictly locked to your validated syllabus topic.
                </p>
              </div>

              {/* Pending Speech Review & Confirmation Box */}
              {isReviewingTranscript && transcriptTarget === 'question' && (
                <div className="p-4 rounded-xl border-2 border-indigo-500 bg-indigo-50 dark:bg-indigo-950/60 space-y-3">
                  <div className="flex items-center gap-2 text-xs font-extrabold text-indigo-900 dark:text-indigo-200">
                    <CheckCircle2 size={16} className="text-indigo-600" />
                    <span>Voice Transcript Review</span>
                  </div>
                  <p className="text-sm font-bold text-slate-900 dark:text-white">
                    &ldquo;{pendingTranscript}&rdquo;
                  </p>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    Speech errors will not penalize your learning score. Confirm, edit, or cancel before submitting.
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    <Button
                      size="sm"
                      onClick={() => {
                        confirmPendingTranscript()
                        submitStudentQuestion(pendingTranscript)
                      }}
                      className="bg-indigo-600 text-white font-extrabold text-xs px-4 py-2"
                      aria-label="Confirm and Submit Question"
                    >
                      <Check size={14} /> Confirm &amp; Submit
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setStudentQuestion(pendingTranscript)
                        setIsReviewingTranscript(false)
                        announce('Transcript placed in question input field for keyboard editing.')
                      }}
                      className="text-xs font-bold"
                      aria-label="Edit Question using Keyboard"
                    >
                      <Edit3 size={14} /> Edit with Keyboard
                    </Button>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={cancelVoiceDictation}
                      className="text-xs font-bold text-rose-600"
                      aria-label="Cancel Voice Question"
                    >
                      Cancel
                    </Button>
                  </div>
                </div>
              )}

              {/* Question Input Controls */}
              <div className="flex flex-col sm:flex-row items-stretch gap-2">
                <input
                  type="text"
                  value={studentQuestion}
                  onChange={(e) => setStudentQuestion(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      submitStudentQuestion()
                    }
                  }}
                  placeholder={`Ask a question about ${selectedTopic?.title || 'this topic'}…`}
                  aria-label={`Ask a doubt or question about ${selectedTopic?.title || 'current topic'}`}
                  className="flex-1 px-4 py-3 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
                />

                <button
                  type="button"
                  onClick={() => {
                    if (isListening) cancelVoiceDictation()
                    else startVoiceDictation('question')
                  }}
                  className={`px-4 py-3 rounded-xl font-bold text-xs flex items-center justify-center gap-1.5 cursor-pointer transition-all ${
                    isListening
                      ? 'bg-rose-600 text-white animate-pulse'
                      : 'border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                  aria-label={isListening ? 'Stop Listening' : 'Speak Question (Hotkey: M)'}
                >
                  {isListening ? <MicOff size={16} /> : <Mic size={16} />}
                  <span>{isListening ? 'Listening…' : 'Speak (M)'}</span>
                </button>

                <Button
                  onClick={() => submitStudentQuestion()}
                  disabled={askingQuestion || !studentQuestion.trim()}
                  className="bg-indigo-600 text-white hover:bg-indigo-700 font-extrabold text-xs px-5 py-3 rounded-xl flex items-center justify-center gap-1.5 shadow-xs"
                  aria-label="Send question to tutor"
                >
                  <Send size={15} />
                  <span>{askingQuestion ? 'Thinking…' : 'Ask Question'}</span>
                </Button>
              </div>

              {/* Conversation History List */}
              {conversationHistory.length > 0 && (
                <div className="space-y-3 pt-2">
                  <div className="text-xs font-extrabold uppercase tracking-wider text-slate-500">
                    Topic Discussion History
                  </div>
                  <div className="space-y-2.5 max-h-[350px] overflow-y-auto pr-1">
                    {conversationHistory.map((item, idx) => {
                      const isUser = item.role === 'user'
                      return (
                        <div
                          key={idx}
                          className={`p-3.5 rounded-xl border text-xs sm:text-sm leading-relaxed space-y-1.5 ${
                            isUser
                              ? 'bg-slate-100 dark:bg-slate-800/80 border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white'
                              : 'bg-indigo-50/60 dark:bg-indigo-950/30 border-indigo-200 dark:border-indigo-800 text-slate-800 dark:text-slate-200'
                          }`}
                        >
                          <div className="flex items-center justify-between font-extrabold text-[11px]">
                            <span className={isUser ? 'text-slate-600 dark:text-slate-400' : 'text-indigo-600 dark:text-indigo-400'}>
                              {isUser ? 'My Question' : 'AI Tutor Explanation'}
                            </span>
                            {!isUser && (
                              <button
                                type="button"
                                onClick={() => speakText(item.content, 'Tutor Explanation')}
                                className="text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 cursor-pointer"
                                aria-label="Listen to this explanation aloud"
                              >
                                <Volume2 size={13} />
                                <span>Listen</span>
                              </button>
                            )}
                          </div>
                          <div className="whitespace-pre-wrap font-medium">{item.content}</div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 3: PRACTICE                                               */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeSection === 'practice' && (
          <div className="space-y-6">
            <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <span className="text-[11px] font-extrabold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">
                    Accessible Topic Practice
                  </span>
                  <h2 className="text-xl sm:text-2xl font-extrabold text-slate-900 dark:text-white mt-0.5">
                    Practice: {selectedTopic?.title || 'Selected Topic'}
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                    Grounded in your syllabus learning objectives. No handwriting or camera uploads required.
                  </p>
                </div>

                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => switchSection('syllabus')}
                    className="text-xs font-bold"
                  >
                    Change Topic
                  </Button>
                  <Button
                    size="sm"
                    onClick={loadPracticeQuestion}
                    disabled={loadingQuestion || !selectedTopic}
                    className="text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700 flex items-center gap-1.5 shadow-xs"
                    aria-label="Generate new practice question"
                  >
                    <RefreshCw size={13} className={loadingQuestion ? 'animate-spin' : ''} />
                    <span>{loadingQuestion ? 'Generating…' : 'New Question'}</span>
                  </Button>
                </div>
              </div>

              {/* Active Practice Question Card */}
              {loadingQuestion ? (
                <div className="py-12 text-center space-y-3">
                  <div className="w-10 h-10 rounded-xl bg-emerald-600 text-white mx-auto flex items-center justify-center animate-spin">
                    <RefreshCw size={20} />
                  </div>
                  <div className="text-sm font-extrabold text-slate-900 dark:text-white">
                    Generating diagnostic practice question for {selectedTopic?.title}…
                  </div>
                </div>
              ) : practiceQuestion ? (
                <div className="space-y-5">
                  <div className="p-5 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 space-y-3">
                    <div className="flex items-center justify-between text-xs font-extrabold text-emerald-900 dark:text-emerald-300">
                      <span>Question</span>
                      <button
                        type="button"
                        onClick={() =>
                          speakText(
                            `Question: ${practiceQuestion.question_text || practiceQuestion.question}`,
                            'Practice Question'
                          )
                        }
                        className="text-emerald-700 dark:text-emerald-300 hover:underline flex items-center gap-1 cursor-pointer font-bold"
                        aria-label="Repeat practice question aloud"
                      >
                        <Volume2 size={14} />
                        <span>Repeat Question</span>
                      </button>
                    </div>

                    <div className="text-base sm:text-lg font-extrabold text-slate-900 dark:text-white leading-relaxed">
                      {practiceQuestion.question_text || practiceQuestion.question}
                    </div>

                    {practiceQuestion.learning_objective && (
                      <p className="text-xs text-slate-600 dark:text-slate-400 font-semibold">
                        Objective: {practiceQuestion.learning_objective}
                      </p>
                    )}
                  </div>

                  {/* Pending Speech Review & Confirmation for Practice */}
                  {isReviewingTranscript && transcriptTarget === 'practice' && (
                    <div className="p-4 rounded-xl border-2 border-emerald-500 bg-emerald-50 dark:bg-emerald-950/60 space-y-3">
                      <div className="flex items-center gap-2 text-xs font-extrabold text-emerald-900 dark:text-emerald-200">
                        <CheckCircle2 size={16} className="text-emerald-600" />
                        <span>Review Recognized Voice Answer</span>
                      </div>
                      <p className="text-sm font-bold text-slate-900 dark:text-white">
                        &ldquo;{pendingTranscript}&rdquo;
                      </p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <Button
                          size="sm"
                          onClick={confirmPendingTranscript}
                          className="bg-emerald-600 text-white font-extrabold text-xs px-4 py-2"
                          aria-label="Confirm answer and place into answer box"
                        >
                          <Check size={14} /> Confirm Answer
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setPracticeAnswer(pendingTranscript)
                            setIsReviewingTranscript(false)
                            announce('Transcript placed in answer area for editing.')
                          }}
                          className="text-xs font-bold"
                          aria-label="Edit Answer with Keyboard"
                        >
                          <Edit3 size={14} /> Edit with Keyboard
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={cancelVoiceDictation}
                          className="text-xs font-bold text-rose-600"
                        >
                          Cancel
                        </Button>
                      </div>
                    </div>
                  )}

                  {/* Answer Input Area */}
                  <div className="space-y-2">
                    <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                      Your Answer (Speak or Type)
                    </label>
                    <textarea
                      rows={4}
                      value={practiceAnswer}
                      onChange={(e) => setPracticeAnswer(e.target.value)}
                      placeholder="Type or dictate your answer here. Explain your reasoning and steps clearly…"
                      aria-label="Type your practice answer"
                      className="w-full p-4 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-sm text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500 leading-relaxed font-medium"
                    />

                    <div className="flex flex-col sm:flex-row items-center justify-between gap-3 pt-1">
                      <div className="flex items-center gap-2 w-full sm:w-auto">
                        <button
                          type="button"
                          onClick={() => {
                            if (isListening) cancelVoiceDictation()
                            else startVoiceDictation('practice')
                          }}
                          className={`w-full sm:w-auto px-4 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 cursor-pointer transition-all ${
                            isListening
                              ? 'bg-rose-600 text-white animate-pulse'
                              : 'border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800'
                          }`}
                          aria-label={isListening ? 'Stop Listening' : 'Speak Answer with Microphone (Hotkey: M)'}
                        >
                          {isListening ? <MicOff size={15} /> : <Mic size={15} />}
                          <span>{isListening ? 'Listening…' : 'Dictate Answer (M)'}</span>
                        </button>
                      </div>

                      <Button
                        onClick={submitPracticeAnswer}
                        disabled={submittingPractice || !practiceAnswer.trim()}
                        className="w-full sm:w-auto bg-emerald-600 text-white hover:bg-emerald-700 font-extrabold text-xs px-6 py-2.5 rounded-xl shadow-xs"
                        aria-label="Submit practice answer for evaluation"
                      >
                        {submittingPractice ? 'Evaluating Answer…' : 'Submit for Evaluation'}
                      </Button>
                    </div>
                  </div>

                  {/* Feedback Box */}
                  {practiceFeedback && (
                    <div
                      className={`p-5 rounded-2xl border space-y-3 ${
                        practiceFeedback.is_correct
                          ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800'
                          : 'bg-amber-50 dark:bg-amber-950/40 border-amber-300 dark:border-amber-800'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <CheckCircle2
                            size={18}
                            className={practiceFeedback.is_correct ? 'text-emerald-600' : 'text-amber-600'}
                          />
                          <h4 className="text-sm font-extrabold text-slate-900 dark:text-white">
                            {practiceFeedback.is_correct ? 'Correct Understanding' : 'Needs Reinforcement'}
                          </h4>
                        </div>
                        <Badge
                          tone={practiceFeedback.is_correct ? 'success' : 'warning'}
                          className="font-bold text-xs"
                        >
                          Score: {practiceFeedback.score} / {practiceFeedback.max_score}
                        </Badge>
                      </div>

                      <p className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed font-medium">
                        {practiceFeedback.feedback}
                      </p>

                      <div className="pt-2 flex items-center gap-2">
                        <Button
                          size="sm"
                          onClick={loadPracticeQuestion}
                          className="text-xs font-bold bg-emerald-600 text-white hover:bg-emerald-700"
                        >
                          Attempt Next Question
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            switchSection('learn')
                            generateLesson('structured_10_step')
                          }}
                          className="text-xs font-bold"
                        >
                          Review Lesson in Listen &amp; Learn
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-12 text-center space-y-3">
                  <Award size={36} className="text-slate-400 mx-auto" />
                  <div className="text-sm font-extrabold text-slate-800 dark:text-slate-200">
                    Ready to practice {selectedTopic?.title || 'your syllabus topic'}
                  </div>
                  <Button
                    onClick={loadPracticeQuestion}
                    className="bg-emerald-600 text-white hover:bg-emerald-700 font-extrabold text-xs px-5 py-2.5 rounded-xl shadow-xs"
                  >
                    Start Practice Session
                  </Button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 4: MY PROGRESS                                            */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeSection === 'progress' && (
          <div className="space-y-6">
            <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
                <div>
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                    <Compass size={20} className="text-indigo-600" />
                    <span>My Learning Progress &amp; Gaps</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Grounded strictly in your genuine accessible practice attempts.
                  </p>
                </div>

                <Button
                  size="sm"
                  onClick={() => {
                    const speech =
                      progressSummaryText ||
                      `You have completed practice across your syllabus. Diagnosed learning points: ${learningGaps.length}.`
                    speakText(speech, 'Learning Progress Summary')
                  }}
                  className="bg-indigo-600 text-white hover:bg-indigo-700 font-extrabold text-xs flex items-center gap-1.5 shadow-xs"
                  aria-label="Listen to your progress summary aloud"
                >
                  <Volume2 size={14} />
                  <span>Listen Progress Summary</span>
                </Button>
              </div>

              {/* Personalized Adaptive Learning Path */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-extrabold uppercase tracking-wider text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5">
                    <Sparkles size={14} />
                    <span>Personalized Learning Path (What to Study Next)</span>
                  </div>
                  {learningPath?.recommended_path?.length > 0 && (
                    <span className="text-xs text-slate-500">
                      {learningPath.recommended_path.length} prioritized steps
                    </span>
                  )}
                </div>

                {loadingPath ? (
                  <div className="py-6 text-center text-xs text-slate-500 animate-pulse">
                    Computing adaptive learning path from your actual practice results…
                  </div>
                ) : !learningPath?.recommended_path || learningPath.recommended_path.length === 0 ? (
                  <div className="p-5 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-center space-y-1 bg-slate-50/50 dark:bg-slate-800/30">
                    <div className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      No Prioritized Learning Path Generated Yet
                    </div>
                    <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                      Complete topic checkpoints in Practice to discover targeted recommendations.
                    </p>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {learningPath.recommended_path.map((step, idx) => (
                      <div
                        key={idx}
                        className="p-4 rounded-xl border border-indigo-200 dark:border-indigo-800/60 bg-indigo-50/40 dark:bg-indigo-950/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="w-5 h-5 rounded-full bg-indigo-600 text-white font-extrabold text-[10px] flex items-center justify-center shrink-0">
                              {idx + 1}
                            </span>
                            <span className="text-xs font-extrabold text-slate-900 dark:text-white truncate">
                              {step.title || step.topic}
                            </span>
                            <span className="text-[10px] px-1.5 py-0.2 rounded bg-indigo-100 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-200 font-bold">
                              {step.subject}
                            </span>
                          </div>
                          <p className="text-xs text-slate-600 dark:text-slate-400 mt-1 pl-7">
                            {step.reason || 'Recommended topic to strengthen core mastery.'}
                          </p>
                        </div>

                        <div className="flex items-center gap-2 shrink-0 pl-7 sm:pl-0">
                          <button
                            type="button"
                            onClick={() => {
                              const sText = `Step ${idx + 1}: ${step.title} in ${step.subject}. Reason: ${step.reason}.`
                              speakText(sText, `Step ${idx + 1}`)
                            }}
                            className="text-xs font-bold text-indigo-600 hover:underline flex items-center gap-1 cursor-pointer"
                            aria-label={`Listen to step ${idx + 1}`}
                          >
                            <Volume2 size={13} />
                            <span>Listen</span>
                          </button>
                          <Button
                            size="sm"
                            onClick={() => {
                              setSelectedSubject(step.subject)
                              setSelectedTopic({
                                title: step.topic || step.title,
                                unit: step.unit || 'Unit',
                                subject: step.subject,
                                objectives: [`Master ${step.topic || step.title}`]
                              })
                              switchSection('learn')
                              generateLesson('structured_10_step')
                            }}
                            className="text-xs font-bold bg-indigo-600 text-white hover:bg-indigo-700"
                          >
                            Study Lesson <ArrowRight size={12} className="ml-1" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Diagnosed Learning Gaps List */}
              <div className="space-y-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                <div className="text-xs font-extrabold uppercase tracking-wider text-amber-700 dark:text-amber-400 flex items-center gap-1.5">
                  <AlertTriangle size={14} />
                  <span>Diagnosed Learning Difficulties ({learningGaps.length})</span>
                </div>

                {loadingProgress ? (
                  <div className="py-6 text-center text-xs text-slate-500 animate-pulse">
                    Loading genuine learning evidence…
                  </div>
                ) : learningGaps.length === 0 ? (
                  <div className="p-5 rounded-xl border border-dashed border-slate-300 dark:border-slate-700 text-center space-y-1 bg-slate-50/50 dark:bg-slate-800/30">
                    <CheckCircle2 size={24} className="text-emerald-500 mx-auto mb-1" />
                    <div className="text-xs font-bold text-slate-700 dark:text-slate-300">
                      No Learning Gaps Observed
                    </div>
                    <p className="text-[11px] text-slate-500 max-w-sm mx-auto">
                      All completed topic checkpoints demonstrate sound conceptual reasoning. Continue exploring new syllabus units.
                    </p>
                  </div>
                ) : (
                  <div className="grid sm:grid-cols-2 gap-3">
                    {learningGaps.map((gap, gIdx) => (
                      <div
                        key={gIdx}
                        className="p-4 rounded-xl border border-amber-200 dark:border-amber-800/60 bg-amber-50/50 dark:bg-amber-950/20 space-y-2 flex flex-col justify-between"
                      >
                        <div>
                          <div className="flex items-center justify-between text-xs font-extrabold text-amber-900 dark:text-amber-300">
                            <span className="truncate">{gap.subject}</span>
                            <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-200/60 dark:bg-amber-900/40">
                              {gap.evidence_strength || 'Identified Gap'}
                            </span>
                          </div>

                          <h4 className="text-sm font-extrabold text-slate-900 dark:text-white mt-1">
                            {gap.topic || gap.concept}
                          </h4>

                          <p className="text-xs text-slate-700 dark:text-slate-300 mt-1 leading-relaxed">
                            {gap.why_learning_gap || gap.observed_gap}
                          </p>

                          {gap.recommended_action && (
                            <p className="text-[11px] text-amber-800 dark:text-amber-400 font-semibold mt-1.5">
                              Next: {gap.recommended_action}
                            </p>
                          )}
                        </div>

                        <div className="pt-2 border-t border-amber-200/60 dark:border-amber-800/40 flex items-center justify-between">
                          <button
                            type="button"
                            onClick={() => {
                              const speech = `Subject: ${gap.subject}. Topic: ${gap.topic}. Observed difficulty: ${gap.why_learning_gap || gap.observed_gap}. Recommended action: ${gap.recommended_action || 'Review topic lesson'}.`
                              speakText(speech, `Gap in ${gap.topic}`)
                            }}
                            className="text-xs font-bold text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1 cursor-pointer"
                          >
                            <Volume2 size={13} />
                            <span>Listen</span>
                          </button>

                          <Button
                            size="sm"
                            onClick={() => {
                              setSelectedSubject(gap.subject)
                              setSelectedTopic({
                                title: gap.topic,
                                unit: gap.unit || 'Unit',
                                subject: gap.subject,
                                objectives: [`Master ${gap.topic}`]
                              })
                              switchSection('practice')
                              loadPracticeQuestion()
                            }}
                            className="text-xs font-bold bg-amber-600 text-white hover:bg-amber-700"
                          >
                            Practice Now
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════ */}
        {/* SECTION 5: LEARNING SETTINGS                                      */}
        {/* ══════════════════════════════════════════════════════════════════ */}
        {activeSection === 'settings' && (
          <div className="space-y-6">
            <div className="p-5 sm:p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-6">
              <div className="pb-3 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-extrabold text-slate-900 dark:text-white flex items-center gap-2">
                    <Sliders size={20} className="text-indigo-600" />
                    <span>Learning Settings &amp; Preferences</span>
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    Customize your audio speed, speech dictation, and contrast. Saved to your authenticated account.
                  </p>
                </div>

                <Button
                  onClick={handleSaveSettings}
                  disabled={savingSettings}
                  className="bg-indigo-600 text-white hover:bg-indigo-700 font-extrabold text-xs px-5 py-2.5 rounded-xl shadow-xs"
                >
                  {savingSettings ? 'Saving…' : 'Save Preferences'}
                </Button>
              </div>

              {settingsSuccess && (
                <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 text-xs font-bold text-emerald-800 dark:text-emerald-300 flex items-center gap-2">
                  <CheckCircle2 size={16} />
                  <span>{settingsSuccess}</span>
                </div>
              )}

              {/* Audio Speed Setting */}
              <div className="space-y-2">
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Text-to-Speech Speed ({audioSpeed}x)
                </label>
                <div className="grid grid-cols-5 gap-2">
                  {[0.75, 1.0, 1.25, 1.5, 2.0].map((rate) => (
                    <button
                      key={rate}
                      type="button"
                      onClick={() => setAudioSpeed(rate)}
                      className={`p-3 rounded-xl border text-center text-xs font-extrabold cursor-pointer transition-all ${
                        audioSpeed === rate
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-xs'
                          : 'bg-slate-50 dark:bg-slate-800 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300 hover:border-indigo-400'
                      }`}
                      aria-label={`Set speech speed to ${rate} times`}
                    >
                      {rate}x
                    </button>
                  ))}
                </div>
              </div>

              {/* Explanation Mode Setting */}
              <div className="space-y-2">
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Preferred Explanation Level
                </label>
                <div className="grid sm:grid-cols-2 gap-3">
                  {[
                    { key: 'simple', title: 'Simple Explanation Mode', desc: 'Focuses on intuitive language, relatable analogies, and core conceptual foundations.' },
                    { key: 'detailed', title: 'Detailed Subject-Specific Mode', desc: 'Comprehensive technical exposition with governing laws, formal equations, and precise terms.' }
                  ].map((lvl) => {
                    const isSel = explanationMode === lvl.key
                    return (
                      <button
                        key={lvl.key}
                        type="button"
                        onClick={() => setExplanationMode(lvl.key)}
                        className={`p-4 rounded-xl border text-left cursor-pointer transition-all ${
                          isSel
                            ? 'border-indigo-600 bg-indigo-50/80 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200'
                            : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 hover:border-indigo-400'
                        }`}
                        aria-label={lvl.title}
                      >
                        <div className="text-xs font-extrabold">{lvl.title}</div>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
                          {lvl.desc}
                        </div>
                      </button>
                    )
                  })}
                </div>
              </div>

              {/* Feature Toggles */}
              <div className="space-y-3 pt-2">
                <label className="block text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300">
                  Accessibility Preferences
                </label>

                {[
                  {
                    id: 'audio_nav',
                    label: 'Audio-First Navigation',
                    desc: 'Automatically reads page headers and section titles aloud when switching tabs.',
                    checked: audioFirstNav,
                    onChange: (v) => setAudioFirstNav(v)
                  },
                  {
                    id: 'voice_input',
                    label: 'Voice Dictation for Questions & Answers',
                    desc: 'Enables microphone dictation with pre-submission transcript review.',
                    checked: voiceInputEnabled,
                    onChange: (v) => setVoiceInputEnabled(v)
                  },
                  {
                    id: 'spoken_diag',
                    label: 'Spoken Visual & Equation Descriptions',
                    desc: 'Converts textbook diagrams, circuits, and formulas into mentally mappable audio narration.',
                    checked: spokenDiagrams,
                    onChange: (v) => setSpokenDiagrams(v)
                  },
                  {
                    id: 'high_contrast',
                    label: 'High Contrast Display (Low Vision)',
                    desc: 'Applies an ultra-contrast black and yellow color palette with large touch targets.',
                    checked: highContrast,
                    onChange: (v) => setHighContrast(v)
                  }
                ].map((pref) => (
                  <div
                    key={pref.id}
                    className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/40 flex items-start justify-between gap-4"
                  >
                    <div>
                      <div className="text-xs font-extrabold text-slate-900 dark:text-white">
                        {pref.label}
                      </div>
                      <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        {pref.desc}
                      </div>
                    </div>
                    <input
                      type="checkbox"
                      checked={pref.checked}
                      onChange={(e) => pref.onChange(e.target.checked)}
                      className="w-5 h-5 rounded text-indigo-600 focus:ring-indigo-500 cursor-pointer shrink-0 mt-0.5"
                      aria-label={pref.label}
                    />
                  </div>
                ))}
              </div>

              {/* Keyboard Shortcuts Cheat Sheet */}
              <div className="p-4 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
                <div className="text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center gap-1.5">
                  <HelpCircle size={14} className="text-indigo-600" />
                  <span>Keyboard Shortcuts Quick Guide</span>
                </div>
                <div className="grid sm:grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Jump to My Syllabus:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">Alt + 1</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Jump to Listen &amp; Learn:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">Alt + 2</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Jump to Practice:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">Alt + 3</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Jump to My Progress:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">Alt + 4</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Jump to Settings:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">Alt + 5</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Play / Pause Speech:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">Space</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Repeat Speech:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">R</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Stop Speech:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">S</kbd>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-200 dark:border-slate-700">
                    <span className="font-bold">Toggle Dictation Mic:</span>
                    <kbd className="px-2 py-0.5 rounded bg-white dark:bg-slate-900 border font-mono">M</kbd>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
