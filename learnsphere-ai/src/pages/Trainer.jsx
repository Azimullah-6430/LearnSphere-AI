import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { studyTechniques } from '../data/mockData.js'
import { getActiveValidatedCurriculum, getDynamicChapters } from '../data/syllabusData.js'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import { ChevronRight, ChevronDown, ArrowLeft, Send, BookOpen, Target, Sparkles, Zap, Flame, Award, Loader2, UploadCloud } from 'lucide-react'

// Custom Study Methods for Exam High-Score & Deep Understanding
const STUDY_METHODS = [
  {
    id: 'exam-score-strategy',
    name: '🎯 Exam High-Score Strategy',
    tagline: 'Score Maximum Marks',
    color: 'var(--accent)',
    description: 'Master mandatory marking criteria, high-weightage keywords, common examiner traps, and step-by-step scoring templates.',
    chatIntro: '🎯 **Exam Scoring Strategy Active**: I will teach you the exact technical terminology, diagram conventions, and mark breakdown evaluators look for to award full marks.'
  },
  {
    id: 'conceptual-deep-dive',
    name: '💡 Conceptual Deep Dive',
    tagline: 'First Principles',
    color: '#3b82f6',
    description: 'Understand core physical/mathematical/computational laws from scratch with real-world analogies and intuitive breakdowns.',
    chatIntro: '💡 **Conceptual Deep Dive Active**: Let’s unpack this concept step by step. We will build an intuitive understanding from fundamentals.'
  },
  {
    id: 'rapid-revision',
    name: '⚡ Rapid Formula & Key Point Revision',
    tagline: 'Last-Minute Recall',
    color: '#eab308',
    description: 'Quickly review essential equations, definitions, theorem statements, and cheat-sheet summaries for rapid exam prep.',
    chatIntro: '⚡ **Rapid Revision Active**: Here are the high-yield formulas, definitions, and key points you must memorize.'
  },
  {
    id: 'practice-problem-solving',
    name: '📝 Practice Problem Solving',
    tagline: 'Hands-on Numerical & Coding',
    color: '#22c55e',
    description: 'Solve past exam questions and application problems with step-by-step guidance and solution breakdown.',
    chatIntro: '📝 **Practice Problem Solving Active**: Let’s solve exam-style problems together step by step to build speed and accuracy.'
  }
]

function generateReply(method, technique, concept, subject, input) {
  const lower = input.toLowerCase()
  
  if (method?.id === 'exam-score-strategy') {
    return `🎯 **Examiner Tip for "${concept}" (${subject})**:\n\n` +
      `When writing an exam answer for "${concept}", strictly structure your response in 3 clear parts:\n` +
      `1. **Definition & Law** (1 mark): State the precise technical definition using bold keywords.\n` +
      `2. **Mathematical/Logical Derivation** (2 marks): Draw neat labelled diagrams or state governing formulas.\n` +
      `3. **Key Conditions & Exceptions** (1 mark): Explicitly state the boundaries where this concept applies.\n\n` +
      `*Common Trap*: Students often lose marks by skipping unit dimensions or using informal phrasing. Try re-stating your explanation using formal academic terms!`
  }
  
  if (method?.id === 'rapid-revision') {
    return `⚡ **Rapid Memory Summary for "${concept}"**:\n\n` +
      `• **Core Formula / Principle**: Standard mathematical/logical expression of ${concept}.\n` +
      `• **SI Units / Notation**: Standard SI units and variable definitions.\n` +
      `• **Key takeaway**: Remember that ${concept} directly links to the core principles of ${subject}.\n\n` +
      `*Self-Check*: Can you state the key formula for "${concept}" from memory right now?`
  }

  // Technique-based fallback
  const t = technique?.id || 'active-recall'
  if (t === 'active-recall') {
    const questions = [
      `Good attempt! Now without looking at your notes: What is the core principle behind "${concept}" in ${subject}?`,
      `Let me challenge your exam prep: Can you explain "${concept}" in 2 bullet points with exact technical terms?`,
      `Recall test: What equation or formula is central to "${concept}"? State it from memory.`,
      `Final test: Give me a real-life example where "${concept}" is visibly at work.`,
    ]
    return questions[Math.floor(Math.random() * questions.length)]
  }

  return `Great progress! Let's continue mastering "${concept}" in ${subject}. What specific part would you like to review next?`
}

export default function Trainer() {
  const { user, recordActivity, streakDays } = useApp()
  const { curriculum, curriculumStatus, isValid: hasValidCurriculum, subjects, subjectObjects, units: allUnits } = useAuthoritativeCurriculum()
  const location = useLocation()
  const activeProfile = user
  const activeCurriculum = curriculum
  
  const [selectedSubject, setSelectedSubject] = useState(subjects[0] || '')
  const [selectedUnit, setSelectedUnit] = useState(null)
  const [selectedChapter, setSelectedChapter] = useState(null)
  const [selectedConcept, setSelectedConcept] = useState(null)
  const [expandedUnit, setExpandedUnit] = useState(null)
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)
  
  const [selectedMethod, setSelectedMethod] = useState(STUDY_METHODS[0])
  const [selectedTechnique, setSelectedTechnique] = useState(studyTechniques[0])

  // Phase: 'setup' | 'method_picker' | 'session'
  const [phase, setPhase] = useState('setup')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loadingReply, setLoadingReply] = useState(false)
  const scrollRef = useRef(null)

  const units = (allUnits && allUnits[selectedSubject]) ? allUnits[selectedSubject] : getDynamicChapters(selectedSubject, activeProfile, curriculum)

  // Find active subject metadata (subjectId, code, category, credits)
  const currentSubjectObj = subjectObjects.find(s => 
    (typeof s === 'object' && (s.name === selectedSubject || s.code === selectedSubject || s.subject_id === selectedSubject || s.id === selectedSubject))
  ) || { name: selectedSubject, code: '', subject_id: '', type: 'Semester Subject' }

  const activeSubjectId = currentSubjectObj.subject_id || currentSubjectObj.id || currentSubjectObj.code || ''
  const activeCurriculumId = activeCurriculum?.syllabus_id || activeCurriculum?.syllabusId || activeCurriculum?.id || ''

  // Handle location state navigation from MisconceptionMap
  useEffect(() => {
    if (location.state?.concept) {
      if (location.state.subject && subjects.includes(location.state.subject)) {
        setSelectedSubject(location.state.subject)
      }
      setSelectedConcept(location.state.concept)
      setSelectedChapter(location.state.chapter || null)
      setSelectedUnit(location.state.unit || null)
      setPhase('method_picker')
    }
  }, [location.state, subjects])

  useEffect(() => {
    if (subjects.length > 0 && !subjects.includes(selectedSubject)) {
      setSelectedSubject(subjects[0])
      setSelectedUnit(null)
      setSelectedChapter(null)
      setSelectedConcept(null)
      setMessages([])
    } else if (subjects.length === 0 && selectedSubject) {
      setSelectedSubject('')
      setSelectedUnit(null)
      setSelectedChapter(null)
      setSelectedConcept(null)
      setMessages([])
    }
  }, [subjects, selectedSubject])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loadingReply])

  const handleSelectSubject = (subj) => {
    setSelectedSubject(subj)
    setSelectedUnit(null)
    setSelectedChapter(null)
    setSelectedConcept(null)
    setExpandedUnit(null)
    if (phase === 'session') {
      setPhase('setup')
      setMessages([])
    }
  }

  const handleSelectTopic = (unitName, topicName, chapterName = null) => {
    setSelectedUnit(unitName)
    setSelectedChapter(chapterName || unitName)
    setSelectedConcept(topicName)
    setPhase('method_picker')
  }

  const startSession = (method, technique) => {
    const m = method || selectedMethod
    const t = technique || selectedTechnique
    setSelectedMethod(m)
    setSelectedTechnique(t)

    // Record activity & update streak!
    recordActivity('trainer', `Studied "${selectedConcept}" in ${selectedSubject} (${m.name})`, {
      subject: selectedSubject,
      subjectId: activeSubjectId,
      curriculumId: activeCurriculumId,
      unit: selectedUnit,
      concept: selectedConcept
    })

    const semLabel = activeCurriculum.semester ? `Semester ${activeCurriculum.semester}` : 'Current Semester'
    const progLabel = activeCurriculum.degree || activeCurriculum.department || 'Degree Program'

    const teachText = `📚 **Personal AI Trainer Initialized (${progLabel} · ${semLabel})**:\n\n` +
      `• **Validated Subject**: ${currentSubjectObj.code ? `[${currentSubjectObj.code}] ` : ''}${selectedSubject}\n` +
      `• **Unit / Module**: ${selectedUnit || 'Core Syllabus Unit'}\n` +
      `• **Target Topic**: ${selectedConcept}\n` +
      `• **Study Strategy**: ${m.name}\n\n` +
      `Welcome! We are mastering **"${selectedConcept}"** from your official ${semLabel} curriculum to achieve top exam scores. Feel free to ask questions, solve exam problems, or check your understanding below!`

    setMessages([
      { role: 'bot', text: teachText },
      { role: 'bot', text: m.chatIntro }
    ])
    setPhase('session')
  }

  const sendMessage = async (text) => {
    const userText = text || input.trim()
    if (!userText || loadingReply) return
    setInput('')
    
    const newMsgList = [...messages, { role: 'user', text: userText }]
    setMessages(newMsgList)
    setLoadingReply(true)

    try {
      const res = await api.trainerChat({
        message: userText,
        subject: selectedSubject,
        subject_id: activeSubjectId,
        subjectId: activeSubjectId,
        curriculum_id: activeCurriculumId,
        syllabus_id: activeCurriculumId,
        unit: selectedUnit,
        chapter: selectedChapter,
        topic: selectedConcept,
        concept: selectedConcept,
        study_method: selectedMethod?.name || selectedMethod?.id,
        level: activeProfile?.level || 'college',
        semester: activeCurriculum.semester || activeProfile?.semester || '',
        degree: activeCurriculum.degree || activeProfile?.degree || '',
        department: activeCurriculum.department || activeProfile?.department || '',
        class_level: activeProfile?.grade_level || activeProfile?.classLevel || '',
        history: newMsgList.slice(-6)
      })

      if (res && res.success && res.reply) {
        setMessages((m) => [...m, { role: 'bot', text: res.reply }])
      } else {
        const fallback = generateReply(selectedMethod, selectedTechnique, selectedConcept, selectedSubject, userText)
        setMessages((m) => [...m, { role: 'bot', text: fallback }])
      }
    } catch (err) {
      const fallback = generateReply(selectedMethod, selectedTechnique, selectedConcept, selectedSubject, userText)
      setMessages((m) => [...m, { role: 'bot', text: fallback }])
    } finally {
      setLoadingReply(false)
    }
  }

  if (!hasValidCurriculum) {
    return (
      <>
        <PageHead
          title="Personal AI Trainer & Exam Maximizer"
          subtitle="Classified subjects from your syllabus. Pick topics and study strategies tailored for exam high scores."
        />
        <CurriculumReviewNotice
          curriculum={activeCurriculum}
          featureName="Personal AI Trainer"
          onOpenSyllabusModal={() => setIsSyllabusModalOpen(true)}
        />
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </>
    )
  }

  const semBadge = activeCurriculum.semester ? `Semester ${activeCurriculum.semester}` : 'Semester Active'
  const progBadge = activeCurriculum.degree ? `${activeCurriculum.degree}` : 'College'

  return (
    <>
      <PageHead
        title="Personal AI Trainer & Exam Maximizer"
        subtitle={`Validated ${semBadge} Curriculum · ${progBadge} · Structured Topic Coaching`}
        action={
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
              <BookOpen size={13} /> {semBadge} Validated
            </span>
            <span className="px-3 py-1 bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1">
              <Flame size={14} className="text-amber-500 animate-bounce" /> {streakDays} Day Streak
            </span>
          </div>
        }
      />

      <div className="h-[calc(100vh-220px)] min-h-[600px] border border-[var(--border)] rounded-xl overflow-hidden bg-[var(--surface)] flex">

        {/* LEFT: 4-Level Syllabus Tree (Semester Subjects → Units/Modules → Chapters → Topics) */}
        <div className="w-[280px] shrink-0 border-r border-[var(--border)] flex flex-col overflow-hidden bg-[var(--surface-alt)]/40">
          <div className="p-3.5 border-b border-[var(--border)]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-faint)]">
                {semBadge} Subjects ({subjects.length})
              </span>
              <Badge tone="accent">{activeCurriculum.department || 'Core'}</Badge>
            </div>
            
            {/* Subject Selector Tabs */}
            <div className="flex flex-col gap-1 max-h-[190px] overflow-y-auto pr-1">
              {subjects.map((s) => {
                const sObj = subjectObjects.find(item => typeof item === 'object' && item.name === s)
                const isSelected = selectedSubject === s
                return (
                  <button
                    key={s}
                    onClick={() => handleSelectSubject(s)}
                    className={`text-left px-2.5 py-2 rounded-xl text-[12px] font-semibold transition-all flex flex-col gap-0.5 border ${
                      isSelected
                        ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                        : 'border-transparent text-[var(--text-soft)] hover:bg-[var(--surface)] hover:border-[var(--border)]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      {sObj?.code && (
                        <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded font-bold ${isSelected ? 'bg-white/20 text-white' : 'bg-[var(--surface-alt)] text-[var(--text-faint)]'}`}>
                          {sObj.code}
                        </span>
                      )}
                      {sObj?.credits && (
                        <span className={`text-[9.5px] font-medium ${isSelected ? 'text-white/80' : 'text-[var(--text-faint)]'}`}>
                          {sObj.credits} Cr
                        </span>
                      )}
                    </div>
                    <span className="line-clamp-1 leading-tight">{s}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Unit / Module / Chapter / Topic Hierarchy */}
          <div className="flex-1 overflow-y-auto p-2.5 space-y-1">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-faint)] px-1.5 py-1 flex items-center justify-between">
              <span>Units & Topics</span>
              <span className="text-[9.5px] font-normal">{units.length} Modules</span>
            </div>

            {units.map((unit, uIdx) => {
              const isExpanded = expandedUnit === unit.name || (!expandedUnit && uIdx === 0)
              return (
                <div key={unit.name || uIdx} className="rounded-xl border border-[var(--border)] overflow-hidden bg-[var(--surface)]">
                  <button
                    onClick={() => setExpandedUnit(isExpanded ? '__collapsed' : unit.name)}
                    className={`w-full flex items-center justify-between px-3 py-2 text-[11.5px] font-bold text-left transition-colors ${
                      isExpanded ? 'bg-[var(--accent-soft)]/60 text-[var(--accent)]' : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                    }`}
                  >
                    <span className="line-clamp-1 leading-tight">{unit.name}</span>
                    <ChevronDown size={13} className={`shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                  </button>

                  {isExpanded && (
                    <div className="p-1.5 bg-[var(--surface)] border-t border-[var(--border)] space-y-0.5">
                      {(unit.concepts || []).map((concept, cIdx) => {
                        const isSelected = selectedConcept === concept && selectedUnit === unit.name
                        return (
                          <button
                            key={concept || cIdx}
                            onClick={() => handleSelectTopic(unit.name, concept)}
                            className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11px] transition-all flex items-center gap-1.5 ${
                              isSelected
                                ? 'bg-[var(--accent)] text-white font-semibold shadow-xs'
                                : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
                            }`}
                          >
                            <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isSelected ? 'bg-white' : 'bg-[var(--accent)]/50'}`} />
                            <span className="line-clamp-1">{concept}</span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* CENTER: Setup prompt → Study Method picker → AI Chat */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[var(--surface)]">
          {phase === 'setup' && (
            <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
              <div className="text-center max-w-[500px]">
                <div className="w-14 h-14 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto text-2xl mb-3 shadow-inner">
                  <BookOpen size={28} />
                </div>
                <div className="text-[17px] font-extrabold mb-1.5">
                  {selectedSubject ? `${selectedSubject}` : 'Select a Topic from Your Curriculum'}
                </div>
                <div className="text-xs text-[var(--text-soft)] mb-5 max-w-[420px] mx-auto leading-relaxed">
                  Navigate through <strong>{semBadge}</strong> units and topics on the left panel, or ask instant questions about your semester syllabus.
                </div>

                {/* Instant Action Pills */}
                <div className="flex flex-wrap gap-2 justify-center mb-6">
                  <button
                    onClick={() => {
                      setSelectedConcept("Semester Syllabus Overview")
                      setSelectedUnit("All Subjects")
                      setPhase('session')
                      sendMessage(`What are my ${semBadge} subjects?`)
                    }}
                    className="px-3 py-1.5 rounded-full border border-[var(--border-strong)] bg-[var(--surface-alt)] text-[11.5px] font-semibold text-[var(--text-soft)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all flex items-center gap-1.5"
                  >
                    📋 What are my {semBadge} subjects?
                  </button>
                  <button
                    onClick={() => {
                      if (units[0]?.concepts?.[0]) {
                        handleSelectTopic(units[0].name, units[0].concepts[0])
                      }
                    }}
                    className="px-3 py-1.5 rounded-full border border-[var(--border-strong)] bg-[var(--surface-alt)] text-[11.5px] font-semibold text-[var(--text-soft)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all flex items-center gap-1.5"
                  >
                    🎯 Start Coaching on Unit I
                  </button>
                </div>

                <div className="flex flex-col gap-2 text-[12px] text-[var(--text-faint)] text-left bg-[var(--surface-alt)] p-4 rounded-xl border border-[var(--border)]">
                  <div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] font-bold">1</span> <strong>Subject</strong>: Pick validated {semBadge} course</div>
                  <div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] font-bold">2</span> <strong>Unit/Module</strong>: Expand exact syllabus chapter</div>
                  <div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] font-bold">3</span> <strong>Topic</strong>: Select key concept for exam scoring strategy</div>
                </div>
              </div>
            </div>
          )}

          {/* Strategy Picker (shown after topic selected) */}
          {phase === 'method_picker' && selectedConcept && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)]/60">
                <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[var(--accent)] mb-1">
                  <span>{semBadge}</span> · <span>{selectedSubject}</span>
                </div>
                <div className="text-lg font-extrabold text-[var(--text)]">{selectedConcept}</div>
                <div className="text-xs text-[var(--text-soft)] mt-0.5">
                  Unit: <strong>{selectedUnit || 'Core Module'}</strong>
                </div>
              </div>

              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-3">1. Choose Exam Coaching Strategy</div>
                <div className="grid md:grid-cols-2 gap-3 mb-6">
                  {STUDY_METHODS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setSelectedMethod(m)}
                      className={`text-left p-4 rounded-xl border transition-all ${
                        selectedMethod.id === m.id
                          ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm ring-1 ring-[var(--accent)]'
                          : 'border-[var(--border)] hover:border-[var(--accent-dim)] bg-[var(--surface)]'
                      }`}
                    >
                      <div className="font-bold text-[13.5px] mb-1">{m.name}</div>
                      <div className="text-[11.5px] text-[var(--text-soft)] mb-2 leading-relaxed">{m.description}</div>
                      <Badge tone="accent">{m.tagline}</Badge>
                    </button>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-[var(--border)]">
                  <Button variant="ghost" onClick={() => setPhase('setup')}>
                    <ArrowLeft size={14} /> Back to Syllabus Tree
                  </Button>
                  <Button onClick={() => startSession(selectedMethod, selectedTechnique)} className="flex items-center gap-2">
                    Start Learning Session <ChevronRight size={15} />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Chat / Coaching Session */}
          {phase === 'session' && (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Context Header */}
              <div className="p-3 px-4 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-alt)]/40 shrink-0">
                <div className="flex items-center gap-2 truncate">
                  <button
                    onClick={() => setPhase('setup')}
                    className="p-1 rounded-lg hover:bg-[var(--surface)] text-[var(--text-soft)]"
                    title="Back to topics"
                  >
                    <ArrowLeft size={16} />
                  </button>
                  <div className="truncate">
                    <div className="text-[13px] font-bold truncate flex items-center gap-1.5">
                      <span>{selectedSubject}</span>
                      <span className="text-[var(--text-faint)]">›</span>
                      <span className="text-[var(--accent)]">{selectedConcept}</span>
                    </div>
                    <div className="text-[10.5px] text-[var(--text-faint)] truncate">
                      {selectedUnit || 'Syllabus Module'} · {selectedMethod.name}
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => setPhase('method_picker')}
                    className="px-2.5 py-1 border border-[var(--border)] rounded-lg text-[11px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface)]"
                  >
                    Switch Strategy
                  </button>
                </div>
              </div>

              {/* Chat Message Stream */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((m, idx) => (
                  <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div
                      className={`max-w-[85%] rounded-2xl p-4 text-[13px] leading-relaxed shadow-xs ${
                        m.role === 'user'
                          ? 'bg-[var(--accent)] text-white font-medium rounded-br-none'
                          : 'bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text)] rounded-bl-none prose dark:prose-invert max-w-none'
                      }`}
                    >
                      {m.text.split('\n').map((line, lIdx) => (
                        <p key={lIdx} className="mb-2 last:mb-0 whitespace-pre-wrap">{line}</p>
                      ))}
                    </div>
                  </div>
                ))}
                {loadingReply && (
                  <div className="flex justify-start">
                    <div className="bg-[var(--surface-alt)] border border-[var(--border)] rounded-2xl rounded-bl-none p-3.5 flex items-center gap-2 text-xs text-[var(--text-soft)]">
                      <Loader2 size={14} className="animate-spin text-[var(--accent)]" />
                      Preparing personalized explanation from your semester syllabus...
                    </div>
                  </div>
                )}
              </div>

              {/* Human Tutor Prompt Chips & Input Box */}
              <div className="p-3 border-t border-[var(--border)] bg-[var(--surface)] space-y-2">
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] no-scrollbar">
                  <span className="text-[10px] font-bold uppercase text-[var(--text-faint)] shrink-0 mr-1">Tutor Prompts:</span>
                  <button
                    type="button"
                    onClick={() => sendMessage("Explain simply using the Feynman technique and everyday analogies.")}
                    disabled={loadingReply}
                    className="px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1"
                  >
                    💡 Explain simply
                  </button>
                  <button
                    type="button"
                    onClick={() => sendMessage("Explain for exam: what are the key marks breakdown, mandatory keywords, diagrams, and examiner traps?")}
                    disabled={loadingReply}
                    className="px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1"
                  >
                    🎯 Explain for exam
                  </button>
                  <button
                    type="button"
                    onClick={() => sendMessage("Give another concrete real-world engineering example of this concept.")}
                    disabled={loadingReply}
                    className="px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1"
                  >
                    🌟 Another example
                  </button>
                  <button
                    type="button"
                    onClick={() => sendMessage("Test me: Ask me a challenging semester exam question on this topic and grade my answer.")}
                    disabled={loadingReply}
                    className="px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1"
                  >
                    🧠 Test me
                  </button>
                  <button
                    type="button"
                    onClick={() => sendMessage("I don't understand: please explain again from a different perspective and break it into smaller steps.")}
                    disabled={loadingReply}
                    className="px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1"
                  >
                    🔄 Explain again
                  </button>
                </div>

                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    sendMessage()
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Ask about ${selectedConcept || selectedSubject} (e.g., "Explain simply", "Test me", "Step by step numerical")...`}
                    className="flex-1 px-4 py-2.5 text-xs bg-[var(--surface-alt)] border border-[var(--border)] rounded-xl text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                    disabled={loadingReply}
                  />
                  <Button type="submit" disabled={!input.trim() || loadingReply} className="px-4 py-2.5">
                    <Send size={14} />
                  </Button>
                </form>
              </div>
            </div>
          )}
        </div>
      </div>

      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </>
  )
}

