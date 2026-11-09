import { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
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
  Settings as SettingsIcon
} from 'lucide-react'
import { Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'

export default function BlindCompanion() {
  const { user, onOpenSyllabusModal } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, subjectObjects, units: allUnits } = useAuthoritativeCurriculum()

  // Companion Settings
  const userSettings = user?.blind_companion_settings || {}
  const [audioSpeed, setAudioSpeed] = useState(userSettings.audio_speed || 1.0)
  const [explanationMode, setExplanationMode] = useState(userSettings.explanation_mode || 'detailed')
  const [audioFirst] = useState(userSettings.audio_first !== false)
  const [voiceQuestions] = useState(userSettings.voice_questions !== false)
  const [spokenDiagrams] = useState(userSettings.spoken_diagrams !== false)

  // Speech Synthesis State
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isPaused, setIsPaused] = useState(false)
  const [currentSpeechText, setCurrentSpeechText] = useState('')
  const [speechLabel, setSpeechLabel] = useState('Ready to assist')
  const synthRef = useRef(window.speechSynthesis || null)

  // Speech Recognition (Voice Input) State
  const [isListening, setIsListening] = useState(false)
  const [voiceTranscript, setVoiceTranscript] = useState('')
  const [voiceSupported, setVoiceSupported] = useState(false)
  const recognitionRef = useRef(null)

  // Curriculum Navigation State
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedUnit, setSelectedUnit] = useState(null)
  const [selectedTopic, setSelectedTopic] = useState(null)

  // AI Tutor Teaching Intelligence State (Integrated with Personal Trainer)
  const [teachingMode, setTeachingMode] = useState('structured_10_step') // 'structured_10_step' | 'concept_to_sense' | 'simple' | 'detailed' | 'quick_revision'
  const [activeLesson, setActiveLesson] = useState(null)
  const [loadingLesson, setLoadingLesson] = useState(false)
  const [conversationHistory, setConversationHistory] = useState([])
  const [studentQuestion, setStudentQuestion] = useState('')

  // Concept-to-Sense Component Explorer State
  const [activeComponent, setActiveComponent] = useState(null)

  // Evidence-Based Learning Gaps & Topic Status State
  const [learningGaps, setLearningGaps] = useState([])
  const [topicStatusMap, setTopicStatusMap] = useState({})
  const [loadingGaps, setLoadingGaps] = useState(false)

  // Adaptive Learning Path State (Prompt 4)
  const [learningPath, setLearningPath] = useState(null)
  const [loadingPath, setLoadingPath] = useState(false)
  const [activeCommandResult, setActiveCommandResult] = useState(null)
  const [voiceListening, setVoiceListening] = useState(false)

  // Practice & Checkpoint State
  const [practiceAnswer, setPracticeAnswer] = useState('')
  const [practiceSubmitted, setPracticeSubmitted] = useState(false)
  const [practiceFeedback, setPracticeFeedback] = useState('')
  const [assessingPractice, setAssessingPractice] = useState(false)

  // Accessible Display States
  const [showHelpModal, setShowHelpModal] = useState(false)
  const [highContrast, setHighContrast] = useState(false)

  // Access Isolation Check
  const isCompanionEnabled = Boolean(user?.is_disabled_student || user?.blind_companion_enabled)

  // ── Speech Synthesis Engine ────────────────────────────────────────────────
  const speakText = useCallback((text, label = 'Audio Reader') => {
    if (!synthRef.current) return
    const synth = synthRef.current
    synth.cancel()

    if (!text || typeof text !== 'string') return

    // Clean formatting while verbalizing equations and punctuation pauses
    const cleanText = text
      .replace(/###/g, '')
      .replace(/##/g, '')
      .replace(/#/g, '')
      .replace(/\*\*/g, '')
      .replace(/\*/g, '')
      .replace(/```mermaid[\s\S]*?```/g, ' Diagram workflow is narrated below. ')
      .replace(/```[\s\S]*?```/g, ' Code snippet. ')
      .replace(/\$([^\$]+)\$/g, '$1')
      .replace(/\s+/g, ' ')
      .trim()

    if (!cleanText) return

    const utterance = new SpeechSynthesisUtterance(cleanText)
    utterance.rate = audioSpeed
    utterance.pitch = 1.0

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

  // ── Speech Recognition Engine (Voice Questions) ───────────────────────────
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (SpeechRecognition) {
      setVoiceSupported(true)
      const recognizer = new SpeechRecognition()
      recognizer.continuous = false
      recognizer.interimResults = true
      recognizer.lang = 'en-US'

      recognizer.onstart = () => {
        setIsListening(true)
        setSpeechLabel('Listening to your spoken question...')
      }

      recognizer.onresult = (event) => {
        const transcript = Array.from(event.results)
          .map(r => r[0].transcript)
          .join('')
        setVoiceTranscript(transcript)
        setStudentQuestion(transcript)
      }

      recognizer.onerror = () => {
        setIsListening(false)
      }

      recognizer.onend = () => {
        setIsListening(false)
      }

      recognitionRef.current = recognizer
    }
  }, [])

  const toggleVoiceInput = useCallback(() => {
    if (!recognitionRef.current) {
      speakText('Speech recognition is not supported in this browser. You can type your question in the text box.', 'Voice Notice')
      return
    }

    if (isListening) {
      recognitionRef.current.stop()
      setIsListening(false)
    } else {
      // Pause TTS before listening
      if (synthRef.current) synthRef.current.cancel()
      setIsSpeaking(false)
      setVoiceTranscript('')
      try {
        recognitionRef.current.start()
      } catch (err) {
        console.warn('Recognition start error', err)
      }
    }
  }, [isListening, speakText])

  // ── Keyboard Shortcuts Listener ───────────────────────────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) return

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
      } else if (key === 'v') {
        e.preventDefault()
        toggleVoiceInput()
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
  }, [isSpeaking, isPaused, resumeSpeech, pauseSpeech, repeatSpeech, stopSpeech, toggleVoiceInput, currentSpeechText])

  // ── Load Authentic Learning Gaps & Topic Status ────────────────────────────
  const fetchLearningGaps = useCallback(async () => {
    setLoadingGaps(true)
    try {
      const res = await api.getBlindLearningGaps()
      if (res && res.success) {
        setLearningGaps(res.learning_gaps || [])
        setTopicStatusMap(res.topic_status_map || {})
      }
    } catch (err) {
      console.warn('Failed to load learning gaps', err)
    } finally {
      setLoadingGaps(false)
    }
  }, [])

  useEffect(() => {
    fetchLearningGaps()
  }, [fetchLearningGaps])

  // ── Load Personalized Adaptive Learning Path (Prompt 4) ────────────────────
  const fetchLearningPath = useCallback(async () => {
    setLoadingPath(true)
    try {
      const res = await api.getBlindLearningPath()
      if (res && res.success) {
        setLearningPath(res)
      }
    } catch (err) {
      console.warn('Failed to load adaptive learning path', err)
    } finally {
      setLoadingPath(false)
    }
  }, [])

  useEffect(() => {
    fetchLearningPath()
  }, [fetchLearningPath])

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

  // ── Core Teaching Intelligence Invocation (Personal Trainer Integration) ──
  const requestAITeaching = useCallback(async (mode = teachingMode, customMsg = null) => {
    if (!selectedTopic) {
      speakText('Please select a syllabus subject and topic first.', 'Notice')
      return
    }

    setLoadingLesson(true)
    const topicTitle = selectedTopic.title
    const unitTitle = selectedUnit?.title || selectedUnit?.name || 'Unit'
    const subjectTitle = selectedSubject || 'Curriculum Subject'

    let promptMessage = customMsg
    if (!promptMessage) {
      if (mode === 'structured_10_step') {
        promptMessage = `Teach me ${topicTitle} from ${unitTitle} in ${subjectTitle} following the complete 10-step structured teaching workflow.`
      } else if (mode === 'concept_to_sense') {
        promptMessage = `Explain the visual diagram, circuit architecture, mathematical equations, and component breakdown for ${topicTitle} using Concept-to-Sense audio intelligence.`
      } else if (mode === 'quick_revision') {
        promptMessage = `Provide a rapid-fire high-yield exam revision for ${topicTitle} in ${subjectTitle}.`
      } else if (mode === 'simple') {
        promptMessage = `Explain ${topicTitle} using simple language, everyday analogies, and clear intuition.`
      } else {
        promptMessage = `Provide a detailed subject-specific explanation of ${topicTitle} grounded in our syllabus.`
      }
    }

    const payload = {
      message: promptMessage,
      subject: subjectTitle,
      unit: unitTitle,
      chapter: unitTitle,
      topic: topicTitle,
      concept: topicTitle,
      subtopic: topicTitle,
      learning_objectives: selectedTopic.objectives || [],
      teaching_mode: mode,
      diagram_type: (subjectTitle.toLowerCase().includes('physic') || subjectTitle.toLowerCase().includes('electr') || subjectTitle.toLowerCase().includes('circuit'))
        ? 'Circuit Diagram'
        : (subjectTitle.toLowerCase().includes('math') ? 'Mathematical Graph / Expression' : 'Architectural Flowchart'),
      audio_friendly: true,
      explanation_mode: mode === 'simple' ? 'simple' : 'detailed',
      history: conversationHistory.slice(-6)
    }

    try {
      const res = await api.trainerChat(payload)
      if (res && res.success && res.reply) {
        const replyText = res.reply
        setActiveLesson({
          mode,
          title: topicTitle,
          unit: unitTitle,
          subject: subjectTitle,
          text: replyText,
          timestamp: new Date()
        })

        // Update multi-turn history
        setConversationHistory(prev => [
          ...prev,
          { role: 'user', text: promptMessage },
          { role: 'model', text: replyText }
        ])

        // Auto-narrate if audioFirst is enabled
        const labelText = mode === 'concept_to_sense'
          ? `Concept-to-Sense Audio: ${topicTitle}`
          : (mode === 'structured_10_step' ? `10-Step Lesson: ${topicTitle}` : `Tutor: ${topicTitle}`)
        speakText(replyText, labelText)
      } else {
        const errMsg = res?.error || 'Teaching engine could not generate explanation. Please try again.'
        speakText(errMsg, 'AI Error')
      }
    } catch (err) {
      console.error('Teaching intelligence error', err)
      speakText('Connection error communicating with the Personal Trainer teaching engine.', 'Connection Error')
    } finally {
      setLoadingLesson(false)
    }
  }, [selectedTopic, selectedUnit, selectedSubject, teachingMode, conversationHistory, speakText])

  // Handle Asking Custom Question
  const handleAskQuestion = (e) => {
    if (e) e.preventDefault()
    if (!studentQuestion.trim()) return
    const q = studentQuestion.trim()
    setStudentQuestion('')
    requestAITeaching(teachingMode, q)
  }

  // Handle Practice Submit & AI Assessment
  const handlePracticeSubmit = async (e) => {
    e.preventDefault()
    if (!practiceAnswer.trim()) return
    setAssessingPractice(true)

    const evaluationPrompt = `Evaluate the student's answer for the topic '${selectedTopic?.title || 'this topic'}'.
Student Answer: "${practiceAnswer.trim()}"
Provide concise verbal marks/score out of 5, highlight what was done correctly, and explain any missing points or arithmetic/conceptual errors.`

    try {
      const res = await api.trainerChat({
        message: evaluationPrompt,
        subject: selectedSubject,
        unit: selectedUnit?.title || selectedUnit?.name || '',
        topic: selectedTopic?.title,
        teaching_mode: 'practice_assessment',
        audio_friendly: true
      })
      if (res && res.success && res.reply) {
        const feedbackText = res.reply
        const isCorrect = !feedbackText.toLowerCase().includes('0/5') &&
                          !feedbackText.toLowerCase().includes('1/5') &&
                          !feedbackText.toLowerCase().includes('incorrect')
        const scoreVal = isCorrect ? 4.5 : 2.0

        // Dynamically submit attempt to Learning Gap Detector to update status & gaps without reload
        try {
          const submitRes = await api.submitBlindPractice({
            subject: selectedSubject,
            unit: selectedUnit?.title || selectedUnit?.name || '',
            topic: selectedTopic?.title,
            subtopic: selectedTopic?.title,
            question_text: `State the core principle of ${selectedTopic?.title} and explain how it solves an everyday engineering or theoretical problem.`,
            student_answer: practiceAnswer.trim(),
            expected_answer: `Core theoretical definitions, boundary constraints, and practical applications for ${selectedTopic?.title}.`,
            is_correct: isCorrect,
            score: scoreVal,
            max_score: 5.0,
            feedback: feedbackText
          })
          if (submitRes && submitRes.success) {
            if (submitRes.learning_gaps) setLearningGaps(submitRes.learning_gaps)
            if (submitRes.topic_status_map) setTopicStatusMap(submitRes.topic_status_map)
            fetchLearningPath()
          }
        } catch (subErr) {
          console.warn('Practice attempt record error', subErr)
        }

        setPracticeSubmitted(true)
        setPracticeFeedback(feedbackText)
        if (voiceQuestions) {
          speakText(feedbackText, 'Checkpoint Assessment Result')
        }
      }
    } catch (err) {
      setPracticeFeedback('Thank you. Your answer has been registered.')
    } finally {
      setAssessingPractice(false)
    }
  }

  // ── Adaptive Learning Path Voice Commands & Step Progression (Prompt 4) ───
  const handlePathCommand = useCallback(async (cmdText) => {
    if (!cmdText) return
    try {
      speakText(`Processing audio command: ${cmdText}`, 'Voice Command')
      const res = await api.executeBlindPathCommand({ command: cmdText })
      if (res && res.spoken_response) {
        setActiveCommandResult(res)
        speakText(res.spoken_response, `Assistant: ${res.command || 'Recommendation'}`)

        // If action is load_lesson, switch to the topic and begin teaching
        if (res.action === 'load_lesson' && res.active_step) {
          const step = res.active_step
          if (step.subject) {
            setSelectedSubject(step.subject)
          }
          if (res.suggested_teaching_mode) {
            setTeachingMode(res.suggested_teaching_mode)
          }
          setTimeout(() => {
            requestAITeaching(res.suggested_teaching_mode || 'simple', `Teach me ${step.topic} following ${step.title}`)
          }, 350)
        }
      }
    } catch (err) {
      console.error('Learning path command error', err)
      speakText('Sorry, could not process that command right now.', 'Error')
    }
  }, [speakText, requestAITeaching])

  const toggleVoiceCommandInput = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
    if (!SpeechRecognition) {
      speakText('Speech recognition is not supported in this browser. Please use the quick command buttons.', 'Notice')
      return
    }

    if (voiceListening) {
      setVoiceListening(false)
      return
    }

    try {
      const recognition = new SpeechRecognition()
      recognition.lang = 'en-US'
      recognition.interimResults = false
      recognition.maxAlternatives = 1

      recognition.onstart = () => {
        setVoiceListening(true)
        speakText('Listening for command. Say: What should I study next, Why was this topic recommended, Start learning, Give me another example, or Show my learning progress.', 'Listening')
      }

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setVoiceListening(false)
        handlePathCommand(transcript)
      }

      recognition.onerror = () => {
        setVoiceListening(false)
      }

      recognition.onend = () => {
        setVoiceListening(false)
      }

      recognition.start()
    } catch (err) {
      console.warn('Speech recognition start error', err)
      setVoiceListening(false)
    }
  }, [voiceListening, speakText, handlePathCommand])

  const handleCompleteStep = useCallback(async (step) => {
    if (!step) return
    try {
      const res = await api.completeBlindPathStep({
        step_id: step.step_id,
        subject: step.subject,
        topic: step.topic,
        unit: step.unit
      })
      if (res && res.success) {
        if (res.path) {
          setLearningPath(res.path)
        } else {
          fetchLearningPath()
        }
        speakText(`Step completed: ${step.title}. Your syllabus progress has been saved.`, 'Progress Saved')
      }
    } catch (err) {
      console.error('Failed to complete step', err)
      speakText('Could not save step progress.', 'Error')
    }
  }, [fetchLearningPath, speakText])

  // Welcome Announcement
  const handleAnnounceWelcome = () => {
    const welcomeMsg = `Welcome to the Blind Learning Companion teaching suite, ${user?.name || 'Student'}. ` +
      (hasValidCurriculum
        ? `You are enrolled in ${authoritativeSubjects.length} subjects. Selected subject is ${selectedSubject || 'none'}. Selected topic is ${selectedTopic?.title || 'none'}. You can press P to play or pause, V to dictate a question, or question mark for keyboard help.`
        : `You currently have no validated syllabus uploaded. Please select Upload Syllabus to import your course document.`)
    speakText(welcomeMsg, 'Welcome Greeting')
  }

  // Component-by-Component Explorer Audio
  const handleExploreComponent = (compName, compDetails) => {
    setActiveComponent(compName)
    const msg = `Component Inspection: ${compName}. ${compDetails}`
    speakText(msg, `Component: ${compName}`)
  }

  // Access check
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
      aria-label="Blind Learning Companion Teaching Suite"
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
                  Blind Learning Companion · Teaching Suite
                </h1>
                <Badge className="bg-indigo-600 text-white font-bold text-[10px] uppercase tracking-wider">
                  Concept-to-Sense
                </Badge>
              </div>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                Syllabus-aware AI teaching, 10-step structured lessons, and mental-mapping visual explanations.
              </p>
            </div>
          </div>
        </div>

        {/* Global Controls */}
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
              aria-label="Open Companion Settings"
            >
              <SettingsIcon size={15} />
              <span>Settings</span>
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
          {voiceSupported && (
            <Button
              type="button"
              onClick={toggleVoiceInput}
              className={`text-xs font-bold flex items-center gap-1.5 px-3.5 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-white transition-all ${
                isListening ? 'bg-red-600 hover:bg-red-500 text-white animate-pulse' : 'bg-indigo-600 hover:bg-indigo-500 text-white'
              }`}
              aria-label={isListening ? 'Stop Listening' : 'Speak a Question (Hotkey: V)'}
            >
              {isListening ? <MicOff size={16} /> : <Mic size={16} />}
              <span>{isListening ? 'Listening...' : 'Voice Question'}</span>
            </Button>
          )}

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
              onClick={() => requestAITeaching(teachingMode)}
              disabled={!selectedTopic || loadingLesson}
              className="bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 px-3.5 py-2 rounded-xl focus-visible:ring-4 focus-visible:ring-white disabled:opacity-50"
              aria-label="Start AI Lesson (Hotkey: P or Space)"
            >
              <Play size={16} />
              <span>{loadingLesson ? 'Generating...' : 'Start Lesson'}</span>
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

      {/* ── Section: Active Syllabus Navigation ────────────────────────────── */}
      <section aria-labelledby="curriculum-select-heading" className="space-y-4">
        <div className="flex items-center justify-between gap-3 border-b border-[var(--border)] pb-2">
          <div className="flex items-center gap-2">
            <BookOpen size={18} className="text-indigo-600" />
            <h2 id="curriculum-select-heading" className="text-base font-bold text-slate-900 dark:text-white">
              Syllabus Selection (Subject · Unit · Topic)
            </h2>
          </div>
          <button
            onClick={onOpenSyllabusModal}
            className="text-xs font-semibold text-indigo-600 hover:underline flex items-center gap-1 cursor-pointer focus-visible:ring-2 focus-visible:ring-indigo-500 rounded p-1"
          >
            <UploadCloud size={14} />
            <span>Switch Syllabus</span>
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
              To experience syllabus-grounded audio teaching, please upload your official semester course document.
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
                1. Subject ({authoritativeSubjects.length})
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
            </div>

            {/* Unit Selector */}
            <div className="p-4 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
              <label htmlFor="unit-select" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                2. Unit / Module ({activeUnits.length})
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
            </div>

            {/* Topic Selector */}
            <div className="p-4 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700 space-y-2">
              <label htmlFor="topic-select" className="block text-xs font-bold text-slate-700 dark:text-slate-300">
                3. Topic / Subtopic ({activeTopics.length})
              </label>
              <select
                id="topic-select"
                value={selectedTopic ? selectedTopic.title : ''}
                onChange={(e) => {
                  const t = activeTopics.find(top => top.title === e.target.value)
                  setSelectedTopic(t)
                  const st = topicStatusMap[`${selectedSubject}::${e.target.value}`] || 'Not started'
                  speakText(`Selected topic: ${e.target.value}. Learning status: ${st}.`, 'Topic Switch')
                }}
                className="w-full px-3 py-2 rounded-lg border border-slate-300 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 text-xs font-semibold focus-visible:ring-4 focus-visible:ring-indigo-500"
              >
                {activeTopics.map((top, idx) => {
                  const status = topicStatusMap[`${selectedSubject}::${top.title}`] || 'Not started'
                  return (
                    <option key={idx} value={top.title}>
                      {top.title} · [{status}]
                    </option>
                  )
                })}
              </select>
            </div>
          </div>
        )}
      </section>

      {/* ── Section: Teaching Mode & Intelligent Action Bar ───────────────── */}
      <section aria-labelledby="teaching-modes-heading" className="p-5 rounded-2xl bg-indigo-50/80 dark:bg-indigo-950/30 border border-indigo-200 dark:border-indigo-900/60 space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 id="teaching-modes-heading" className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-600" />
              <span>Teaching Intelligence Mode</span>
            </h2>
            <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
              Select how the AI Personal Trainer delivers this syllabus concept.
            </p>
          </div>

          <div className="flex items-center gap-2 flex-wrap">
            <Button
              type="button"
              onClick={() => {
                setTeachingMode('structured_10_step')
                requestAITeaching('structured_10_step')
              }}
              disabled={loadingLesson}
              className={`text-xs font-bold px-3 py-2 rounded-xl transition-all ${
                teachingMode === 'structured_10_step'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              10-Step Master Lesson
            </Button>

            <Button
              type="button"
              onClick={() => {
                setTeachingMode('concept_to_sense')
                requestAITeaching('concept_to_sense')
              }}
              disabled={loadingLesson}
              className={`text-xs font-bold px-3 py-2 rounded-xl transition-all ${
                teachingMode === 'concept_to_sense'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              Concept-to-Sense Audio
            </Button>

            <Button
              type="button"
              onClick={() => {
                setTeachingMode('simple')
                requestAITeaching('simple')
              }}
              disabled={loadingLesson}
              className={`text-xs font-bold px-3 py-2 rounded-xl transition-all ${
                teachingMode === 'simple'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              Simple Mode
            </Button>

            <Button
              type="button"
              onClick={() => {
                setTeachingMode('detailed')
                requestAITeaching('detailed')
              }}
              disabled={loadingLesson}
              className={`text-xs font-bold px-3 py-2 rounded-xl transition-all ${
                teachingMode === 'detailed'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              Detailed Mode
            </Button>

            <Button
              type="button"
              onClick={() => {
                setTeachingMode('quick_revision')
                requestAITeaching('quick_revision')
              }}
              disabled={loadingLesson}
              className={`text-xs font-bold px-3 py-2 rounded-xl transition-all ${
                teachingMode === 'quick_revision'
                  ? 'bg-indigo-600 text-white shadow-md'
                  : 'bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700'
              }`}
            >
              Quick Revision
            </Button>
          </div>
        </div>

        {/* Quick Conversational Prompt Actions */}
        <div className="pt-2 border-t border-indigo-200/60 dark:border-indigo-900/40 flex items-center gap-2 flex-wrap">
          <span className="text-[11px] font-bold text-indigo-900 dark:text-indigo-300">
            Quick Follow-ups:
          </span>
          <button
            type="button"
            disabled={loadingLesson}
            onClick={() => requestAITeaching(teachingMode, `Explain ${selectedTopic?.title} more simply using an everyday analogy.`)}
            className="text-[11px] font-semibold bg-white dark:bg-slate-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300 px-2.5 py-1 rounded-lg border border-indigo-200 dark:border-indigo-800 cursor-pointer"
          >
            💡 Simpler Explanation
          </button>
          <button
            type="button"
            disabled={loadingLesson}
            onClick={() => requestAITeaching(teachingMode, `Give me another concrete real-world engineering or practical example of ${selectedTopic?.title}.`)}
            className="text-[11px] font-semibold bg-white dark:bg-slate-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300 px-2.5 py-1 rounded-lg border border-indigo-200 dark:border-indigo-800 cursor-pointer"
          >
            🔄 Another Example
          </button>
          <button
            type="button"
            disabled={loadingLesson}
            onClick={() => requestAITeaching('concept_to_sense', `Break down and explore the individual components and connections of the diagram for ${selectedTopic?.title}.`)}
            className="text-[11px] font-semibold bg-white dark:bg-slate-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300 px-2.5 py-1 rounded-lg border border-indigo-200 dark:border-indigo-800 cursor-pointer"
          >
            🔍 Explore Diagram Components
          </button>
          <button
            type="button"
            disabled={loadingLesson}
            onClick={() => requestAITeaching('quick_revision', `Give me a 60-second rapid revision checklist of ${selectedTopic?.title} for exam recall.`)}
            className="text-[11px] font-semibold bg-white dark:bg-slate-800 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-800 dark:text-indigo-300 px-2.5 py-1 rounded-lg border border-indigo-200 dark:border-indigo-800 cursor-pointer"
          >
            ⚡ Short Revision
          </button>
        </div>
      </section>

      {/* ── Active Teaching Lesson Presentation ───────────────────────────── */}
      {loadingLesson ? (
        <Card className="p-8 text-center space-y-3">
          <div className="w-12 h-12 rounded-2xl bg-indigo-100 dark:bg-indigo-950 text-indigo-600 mx-auto flex items-center justify-center animate-spin">
            <RefreshCw size={24} />
          </div>
          <div className="text-sm font-bold text-slate-900 dark:text-white">
            Teaching Engine Generating Lesson for {selectedTopic?.title || 'Selected Topic'}...
          </div>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Grounded directly in your validated syllabus ({selectedSubject} · {selectedUnit?.title || 'Unit'}). Text-to-speech narration will begin automatically.
          </p>
        </Card>
      ) : activeLesson ? (
        <Card className="p-6 space-y-4 border-2 border-indigo-200 dark:border-indigo-900/50 shadow-md">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  {activeLesson.title}
                </h3>
                <Badge className="bg-indigo-600 text-white text-[10px] uppercase font-bold">
                  {activeLesson.mode.replace('_', ' ')}
                </Badge>
              </div>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {activeLesson.subject} · {activeLesson.unit}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                onClick={() => speakText(activeLesson.text, `Lesson: ${activeLesson.title}`)}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold flex items-center gap-1.5 px-3.5 py-2 rounded-xl shadow-xs"
              >
                <Volume2 size={16} />
                <span>Re-Listen Lesson</span>
              </Button>
            </div>
          </div>

          {/* Render Lesson Content cleanly with accessible reading typography */}
          <div className="prose dark:prose-invert max-w-none text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed space-y-3 whitespace-pre-wrap">
            {activeLesson.text}
          </div>
        </Card>
      ) : null}

      {/* ── Section: Concept-to-Sense Interactive Component Explorer ───────── */}
      <section aria-labelledby="visual-explorer-heading" className="p-6 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[var(--border)] pb-3">
          <div className="flex items-center gap-2">
            <Cpu size={18} className="text-indigo-600" />
            <h2 id="visual-explorer-heading" className="text-base font-bold text-slate-900 dark:text-white">
              Concept-to-Sense Visual Audio Explorer
            </h2>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => requestAITeaching('concept_to_sense')}
            disabled={loadingLesson || !selectedTopic}
            className="text-xs font-bold flex items-center gap-1.5 self-start sm:self-center"
          >
            <Activity size={15} />
            <span>Generate Full Mental Map</span>
          </Button>
        </div>

        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
          Translates textbook diagrams, electrical circuits, mathematical curves, and scientific illustrations into tactile mental models. Select any component below to hear its isolated role, interconnections, and signal path:
        </p>

        {/* Interactive Component Pills */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-1">
          <button
            type="button"
            onClick={() => handleExploreComponent(
              'Active Potential Source (Driver V1)',
              'Provides nominal 12 Volts DC excitation potential. Located at top-left rail, driving clockwise continuous charge/signal flow into series impedance.'
            )}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeComponent?.includes('Source')
                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 shadow-xs'
                : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 hover:border-indigo-400'
            }`}
          >
            <div className="flex items-center gap-2 text-indigo-600 mb-1">
              <Zap size={16} />
              <span className="text-xs font-bold">1. Excitation Source</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
              12V Nominal Reference Driver
            </p>
          </button>

          <button
            type="button"
            onClick={() => handleExploreComponent(
              'Control Gate / Series Switch S1',
              'Located in series on the upper positive conductor rail. In closed state, establishes closed loop continuity. If opened, resistance becomes infinite, immediately interrupting loop flow.'
            )}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeComponent?.includes('Switch')
                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 shadow-xs'
                : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 hover:border-indigo-400'
            }`}
          >
            <div className="flex items-center gap-2 text-indigo-600 mb-1">
              <Sliders size={16} />
              <span className="text-xs font-bold">2. Series Switch S1</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
              Physical Loop Continuity Gate
            </p>
          </button>

          <button
            type="button"
            onClick={() => handleExploreComponent(
              'Primary Impedance / Load R1',
              'Rated at 100 Ohms. Connected between upper switched rail and ground return node. Generates a proportional voltage drop according to Ohm\'s Law, drawing 120 milliamperes of current.'
            )}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeComponent?.includes('Impedance')
                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 shadow-xs'
                : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 hover:border-indigo-400'
            }`}
          >
            <div className="flex items-center gap-2 text-indigo-600 mb-1">
              <Cpu size={16} />
              <span className="text-xs font-bold">3. Load Element R1</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
              100 Ohm Rated Working Impedance
            </p>
          </button>

          <button
            type="button"
            onClick={() => handleExploreComponent(
              'Ground Reference / Return Node',
              'Zero volt system reference rail. Completes the closed path back to the negative terminal of driver V1, ensuring zero floating potentials.'
            )}
            className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
              activeComponent?.includes('Ground')
                ? 'border-indigo-600 bg-indigo-50 dark:bg-indigo-950/60 shadow-xs'
                : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/60 hover:border-indigo-400'
            }`}
          >
            <div className="flex items-center gap-2 text-indigo-600 mb-1">
              <ShieldCheck size={16} />
              <span className="text-xs font-bold">4. Ground Reference</span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-tight">
              0V Return Conductor Node
            </p>
          </button>
        </div>
      </section>

      {/* ── Section: Interactive Spoken Q&A Box ────────────────────────────── */}
      <section aria-labelledby="interactive-qa-heading" className="p-6 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 space-y-4">
        <div className="flex items-center gap-2 border-b border-[var(--border)] pb-2">
          <Mic size={18} className="text-indigo-600" />
          <h2 id="interactive-qa-heading" className="text-base font-bold text-slate-900 dark:text-white">
            Interactive Audio Tutoring (Ask Questions via Voice or Text)
          </h2>
        </div>

        <form onSubmit={handleAskQuestion} className="space-y-3">
          <div className="relative">
            <textarea
              rows={2}
              value={studentQuestion}
              onChange={(e) => setStudentQuestion(e.target.value)}
              placeholder="Ask anything about this concept (e.g. 'Why does voltage divide in series?', 'Give another example', 'Explore the current path')..."
              className="w-full p-3 pr-24 rounded-xl border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-xs text-slate-900 dark:text-white outline-none focus-visible:ring-4 focus-visible:ring-indigo-500"
            />
            <div className="absolute right-2 top-2 flex items-center gap-1.5">
              {voiceSupported && (
                <button
                  type="button"
                  onClick={toggleVoiceInput}
                  className={`p-2 rounded-lg text-white transition-all cursor-pointer ${
                    isListening ? 'bg-red-600 animate-pulse' : 'bg-indigo-600 hover:bg-indigo-700'
                  }`}
                  aria-label={isListening ? 'Stop Listening' : 'Speak Question (Hotkey: V)'}
                  title="Speak your question"
                >
                  <Mic size={16} />
                </button>
              )}
              <button
                type="submit"
                disabled={!studentQuestion.trim() || loadingLesson}
                className="p-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 cursor-pointer"
                aria-label="Submit Question to AI Tutor"
                title="Send Question"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </form>
      </section>

      {/* ── Section: Adaptive Learning Path (Syllabus-Integrated Recommendations) ─── */}
      <section aria-labelledby="adaptive-path-heading" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--border)] pb-2">
          <div className="flex items-center gap-2">
            <Compass size={18} className="text-indigo-600 dark:text-indigo-400" />
            <h2 id="adaptive-path-heading" className="text-base font-bold text-slate-900 dark:text-white">
              Adaptive Learning Path (What to Study Next)
            </h2>
          </div>
          {learningPath && (
            <div className="flex items-center gap-2 text-xs">
              <span className="font-bold text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60 px-2.5 py-0.5 rounded-full border border-indigo-200 dark:border-indigo-800">
                Focus: {learningPath.focus_topic}
              </span>
              <span className="text-slate-500 dark:text-slate-400">
                {learningPath.completed_count || 0} of {learningPath.total_steps || 0} steps completed
              </span>
            </div>
          )}
        </div>

        {/* ── Audio-First Command Bar (Prompt 4 Requirement 4) ── */}
        <Card className="p-4 rounded-2xl bg-gradient-to-r from-indigo-900/10 via-purple-900/10 to-indigo-900/10 dark:from-indigo-950/40 dark:via-purple-950/40 dark:to-slate-900 border border-indigo-200 dark:border-indigo-800/60 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-600 dark:text-indigo-400" />
              <span className="text-xs font-bold text-slate-900 dark:text-white">
                Audio-First Voice & Quick Commands
              </span>
            </div>
            <button
              type="button"
              onClick={toggleVoiceCommandInput}
              className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all cursor-pointer ${
                voiceListening
                  ? 'bg-red-600 text-white animate-pulse'
                  : 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
              }`}
              aria-label={voiceListening ? 'Stop Listening for Voice Command' : 'Activate Voice Command via Microphone'}
            >
              <Mic size={14} />
              <span>{voiceListening ? 'Listening...' : 'Voice Command'}</span>
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-2 pt-1">
            <button
              type="button"
              onClick={() => handlePathCommand('what should i study next')}
              className="p-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 text-left text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 cursor-pointer transition-colors"
              aria-label="Ask audio companion: What should I study next?"
            >
              <Headphones size={15} className="text-indigo-600 shrink-0" />
              <span>"What should I study next?"</span>
            </button>

            <button
              type="button"
              onClick={() => handlePathCommand('why was this topic recommended')}
              className="p-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 text-left text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 cursor-pointer transition-colors"
              aria-label="Ask audio companion: Why was this topic recommended?"
            >
              <HelpCircle size={15} className="text-amber-600 shrink-0" />
              <span>"Why this topic?"</span>
            </button>

            <button
              type="button"
              onClick={() => handlePathCommand('start learning')}
              className="p-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 text-left text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 cursor-pointer transition-colors"
              aria-label="Trigger audio companion: Start learning"
            >
              <Play size={15} className="text-emerald-600 shrink-0" />
              <span>"Start learning."</span>
            </button>

            <button
              type="button"
              onClick={() => handlePathCommand('give me another example')}
              className="p-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 text-left text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 cursor-pointer transition-colors"
              aria-label="Ask audio companion: Give me another example"
            >
              <Zap size={15} className="text-purple-600 shrink-0" />
              <span>"Another example."</span>
            </button>

            <button
              type="button"
              onClick={() => handlePathCommand('show my learning progress')}
              className="p-2.5 rounded-xl bg-white dark:bg-slate-800 hover:bg-indigo-50 dark:hover:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800/60 text-left text-xs font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2 cursor-pointer transition-colors"
              aria-label="Ask audio companion: Show my learning progress"
            >
              <Award size={15} className="text-blue-600 shrink-0" />
              <span>"Show my progress."</span>
            </button>
          </div>

          {/* Active Command Output Card */}
          {activeCommandResult && (
            <div className="mt-2 p-3.5 rounded-xl bg-white dark:bg-slate-800 border border-indigo-300 dark:border-indigo-700/80 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-600 dark:text-indigo-400">
                  Spoken Response Transcript
                </span>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() => speakText(activeCommandResult.spoken_response, 'Voice Response')}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 p-1 rounded"
                    aria-label="Replay audio response"
                  >
                    <Volume2 size={13} />
                    <span>Replay Audio</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setActiveCommandResult(null)}
                    className="text-xs text-slate-400 hover:text-slate-600 p-1"
                    aria-label="Close command response"
                  >
                    <X size={13} />
                  </button>
                </div>
              </div>
              <p className="text-xs text-slate-800 dark:text-slate-200 leading-relaxed">
                {activeCommandResult.spoken_response}
              </p>

              {/* If an example was returned */}
              {activeCommandResult.example && (
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-800 text-xs space-y-2">
                  <div className="font-bold text-slate-900 dark:text-white">
                    Worked Problem:
                  </div>
                  <p className="text-slate-700 dark:text-slate-300">
                    {activeCommandResult.example.problem_statement}
                  </p>
                  <div className="space-y-1 pt-1 font-mono text-[11px] text-indigo-700 dark:text-indigo-300">
                    {activeCommandResult.example.worked_steps?.map((st, idx) => (
                      <div key={idx}>{st}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>

        {/* ── Sequenced Learning Path Steps (Prompt 4 Req 1, 2, 5) ── */}
        {loadingPath ? (
          <Card className="p-6 text-center text-xs text-slate-500">
            Generating syllabus-integrated adaptive path...
          </Card>
        ) : !learningPath?.steps || learningPath.steps.length === 0 ? (
          <Card className="p-6 text-center text-xs text-slate-500">
            No active learning path steps found. Upload your course syllabus to begin guided learning.
          </Card>
        ) : (
          <div className="space-y-3">
            {learningPath.steps.map((step) => {
              const isCompleted = Boolean(step.completed)
              const badgeColor =
                step.step_type === 'revise_prerequisite'
                  ? 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200 border-purple-200 dark:border-purple-800'
                  : (step.step_type === 'concept_breakdown'
                      ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200 border-blue-200 dark:border-blue-800'
                      : (step.step_type === 'guided_example'
                          ? 'bg-indigo-100 text-indigo-800 dark:bg-indigo-950 dark:text-indigo-200 border-indigo-200 dark:border-indigo-800'
                          : (step.step_type === 'independent_practice'
                              ? 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200 border-amber-200 dark:border-amber-800'
                              : 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-200 border-emerald-200 dark:border-emerald-800')))

              return (
                <div
                  key={step.step_id}
                  className={`p-4 rounded-2xl border transition-all ${
                    isCompleted
                      ? 'bg-slate-50/70 dark:bg-slate-900/40 border-slate-200 dark:border-slate-800 opacity-80'
                      : 'bg-white dark:bg-slate-800/90 border-slate-200 dark:border-slate-700 shadow-xs hover:border-indigo-400'
                  }`}
                >
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${badgeColor}`}>
                        Step {step.step_number} · {step.step_type.replace('_', ' ')}
                      </span>
                      <span className="text-[11px] font-semibold text-slate-500 dark:text-slate-400">
                        {step.subject} · {step.unit}
                      </span>
                      {isCompleted && (
                        <span className="text-[10px] font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-full flex items-center gap-1 border border-emerald-200 dark:border-emerald-800">
                          <CheckCircle2 size={11} />
                          <span>Completed</span>
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={() => {
                          const narration = `${step.title}. Recommended because: ${step.why_recommended} Supporting evidence: ${step.evidence_basis}. Activity: ${step.activity_description}. Mastery check: ${step.mastery_check}`
                          speakText(narration, `Step ${step.step_number} Guidance`)
                        }}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 p-1 rounded"
                        aria-label={`Listen to step ${step.step_number} guidance spoken aloud`}
                      >
                        <Volume2 size={14} />
                        <span>Listen</span>
                      </button>

                      <button
                        type="button"
                        onClick={() => {
                          if (step.subject && authoritativeSubjects.includes(step.subject)) {
                            setSelectedSubject(step.subject)
                          }
                          const mode = step.step_type === 'revise_prerequisite' ? 'simple' : 'structured_10_step'
                          setTeachingMode(mode)
                          requestAITeaching(mode, `Teach me ${step.topic} for ${step.title}`)
                        }}
                        className="text-xs font-bold bg-indigo-600 hover:bg-indigo-700 text-white px-2.5 py-1 rounded-lg flex items-center gap-1 cursor-pointer shadow-2xs"
                        aria-label={`Start learning step ${step.step_number}: ${step.title}`}
                      >
                        <Play size={12} />
                        <span>Start Step</span>
                      </button>

                      {!isCompleted && (
                        <button
                          type="button"
                          onClick={() => handleCompleteStep(step)}
                          className="text-xs font-bold bg-slate-100 hover:bg-emerald-100 dark:bg-slate-700 dark:hover:bg-emerald-950/60 text-slate-700 hover:text-emerald-800 dark:text-slate-200 dark:hover:text-emerald-300 px-2.5 py-1 rounded-lg flex items-center gap-1 cursor-pointer border border-slate-200 dark:border-slate-600 transition-colors"
                          aria-label={`Mark step ${step.step_number} as completed`}
                        >
                          <CheckCircle2 size={12} />
                          <span>Complete</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-2.5 space-y-2">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                      {step.title}
                    </h3>
                    <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                      <strong>Focus:</strong> {step.what_to_study}
                    </p>

                    {/* Recommendation Transparency Box (Prompt 4 Req 5) */}
                    <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-900/60 border border-slate-200 dark:border-slate-700/80 text-[11px] space-y-1.5">
                      <div className="text-indigo-700 dark:text-indigo-300">
                        <strong className="text-slate-900 dark:text-white">Why Recommended:</strong> {step.why_recommended}
                      </div>
                      <div className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-900 dark:text-white">Learning Evidence:</strong> {step.evidence_basis}
                      </div>
                      <div className="text-slate-600 dark:text-slate-400">
                        <strong className="text-slate-900 dark:text-white">Activity:</strong> {step.activity_description} ({step.activity_type})
                      </div>
                      <div className="text-emerald-700 dark:text-emerald-400">
                        <strong className="text-slate-900 dark:text-white">Mastery Check:</strong> {step.mastery_check}
                      </div>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* ── Section: Concepts I Need to Improve (Evidence-Based Learning Gaps) ─── */}
      <section aria-labelledby="improve-heading" className="space-y-3">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-2">
          <div className="flex items-center gap-2">
            <AlertTriangle size={18} className="text-amber-600" />
            <h2 id="improve-heading" className="text-base font-bold text-slate-900 dark:text-white">
              Concepts I Need to Improve (Evidence-Based Learning Gaps)
            </h2>
          </div>
          <span className="text-xs text-slate-500 dark:text-slate-400">
            {learningGaps.length} diagnosed gap{learningGaps.length === 1 ? '' : 's'}
          </span>
        </div>

        {loadingGaps ? (
          <Card className="p-6 text-center text-xs text-slate-500">
            Analyzing authentic student learning records...
          </Card>
        ) : learningGaps.length === 0 ? (
          <Card className="p-5 rounded-xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200 dark:border-emerald-900/50 flex items-start gap-3">
            <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-emerald-900 dark:text-emerald-200">
                No Active Learning Gaps Detected
              </div>
              <p className="text-xs text-emerald-700 dark:text-emerald-400 mt-0.5">
                Your evaluated assessments and practice attempts show solid understanding. Any specific calculation, formula, diagram, or conceptual gaps will appear here automatically when detected.
              </p>
            </div>
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 gap-3.5">
            {learningGaps.map((gap, i) => (
              <div
                key={gap.gap_id || i}
                className="p-4 rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 space-y-2.5 hover:border-amber-400 transition-colors shadow-xs"
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-indigo-700 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-950/60 px-2 py-0.5 rounded">
                      {gap.subject}
                    </span>
                    <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                      gap.mistake_nature?.includes('Calculation')
                        ? 'bg-blue-100 text-blue-800 dark:bg-blue-950 dark:text-blue-200'
                        : (gap.mistake_nature?.includes('Diagram') || gap.mistake_nature?.includes('Graph')
                            ? 'bg-purple-100 text-purple-800 dark:bg-purple-950 dark:text-purple-200'
                            : 'bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-200')
                    }`}>
                      {gap.mistake_nature}
                    </span>
                    <span className="text-[10px] font-semibold text-slate-500 bg-slate-100 dark:bg-slate-700/60 px-1.5 py-0.5 rounded">
                      {gap.evidence_strength}
                    </span>
                  </div>

                  <button
                    type="button"
                    onClick={() => {
                      const msg = `Identified learning gap in ${gap.subject}, topic: ${gap.topic}. Nature of mistake: ${gap.mistake_nature}. Evidence strength: ${gap.evidence_strength}. Learning status: ${gap.status}. Why this occurred: ${gap.why_learning_gap}. Recommended next step: ${gap.recommended_action}`
                      speakText(msg, `Diagnosis: ${gap.topic}`)
                    }}
                    className="text-xs font-bold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 focus-visible:ring-2 focus-visible:ring-indigo-500 rounded p-1 shrink-0"
                    aria-label={`Listen to spoken diagnosis and remedy for ${gap.topic}`}
                  >
                    <Volume2 size={14} />
                    <span>Listen</span>
                  </button>
                </div>

                <div>
                  <div className="font-bold text-xs text-slate-900 dark:text-white">
                    {gap.topic} {gap.subtopic && gap.subtopic !== gap.topic ? `· ${gap.subtopic}` : ''}
                  </div>
                  {gap.question_ref && (
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                      <strong>Activity:</strong> {gap.question_ref}
                    </div>
                  )}
                </div>

                {gap.student_answer && gap.student_answer !== 'Not provided' && (
                  <div className="p-2 bg-slate-50 dark:bg-slate-900/60 rounded-lg text-[11px] text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800">
                    <span className="font-semibold block text-slate-700 dark:text-slate-300">Your Submitted Answer:</span>
                    <p className="truncate">"{gap.student_answer}"</p>
                  </div>
                )}

                <p className="text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  <strong>Why this indicates a gap:</strong> {gap.why_learning_gap}
                </p>

                {gap.recommended_action && (
                  <div className="text-[11px] text-indigo-800 dark:text-indigo-200 bg-indigo-50/70 dark:bg-indigo-950/40 p-2.5 rounded-lg border border-indigo-200/50 dark:border-indigo-900/50">
                    <strong>Recommended Next Step:</strong> {gap.recommended_action}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Section: Practice & Audio Assessment Checkpoint ───────────────── */}
      <section aria-labelledby="practice-heading" className="p-6 rounded-2xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Award size={18} className="text-indigo-600" />
            <h2 id="practice-heading" className="text-base font-bold text-slate-900 dark:text-white">
              Practice & Assess (AI Audio Checkpoint)
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
                Spoken evaluation will play automatically upon submission.
              </span>
              <Button
                type="submit"
                disabled={!practiceAnswer.trim() || assessingPractice}
                className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2 rounded-xl disabled:opacity-50"
              >
                {assessingPractice ? 'Evaluating...' : 'Submit Answer'}
              </Button>
            </div>
          </form>

          {practiceSubmitted && practiceFeedback && (
            <div className="mt-4 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-200 flex items-start gap-3">
              <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <strong className="block font-bold mb-0.5">Assessment Evaluation:</strong>
                <p className="leading-relaxed whitespace-pre-wrap">{practiceFeedback}</p>
              </div>
            </div>
          )}
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
                <span className="font-semibold text-slate-700 dark:text-slate-300">Voice Question (Mic)</span>
                <kbd className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded font-mono font-bold text-slate-900 dark:text-white">V</kbd>
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
