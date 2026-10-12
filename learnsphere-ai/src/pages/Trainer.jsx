import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { studyTechniques } from '../data/mockData.js'
import { getDynamicChapters } from '../data/syllabusData.js'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import { 
  ChevronRight, 
  ChevronDown, 
  ArrowLeft, 
  Send, 
  BookOpen, 
  Target, 
  Sparkles, 
  Zap, 
  Flame, 
  Award, 
  Loader2, 
  UploadCloud,
  Copy,
  Check,
  Bot,
  User,
  HelpCircle,
  Code2,
  RefreshCw,
  Lightbulb,
  FileText,
  Layers,
  Compass
} from 'lucide-react'

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
    name: '💡 Conceptual Deep Dive (Feynman)',
    tagline: 'First Principles & Analogies',
    color: '#3b82f6',
    description: 'Understand core physical/mathematical/computational laws from scratch with real-world analogies, intuitive breakdowns, and flowcharts.',
    chatIntro: '💡 **Conceptual Deep Dive Active**: Let’s unpack this concept step by step. We will build an intuitive understanding from fundamentals using real-world analogies.'
  },
  {
    id: 'practice-problem-solving',
    name: '📝 Numerical & Step-by-Step Problem Solving',
    tagline: 'Hands-on Derivations & Code',
    color: '#22c55e',
    description: 'Solve past exam questions, mathematical derivations, and application problems with step-by-step guidance and solution breakdown.',
    chatIntro: '📝 **Practice Problem Solving Active**: Let’s solve exam-style problems together step by step to build speed and calculation accuracy.'
  },
  {
    id: 'rapid-revision',
    name: '⚡ Rapid Formula & Key Point Revision',
    tagline: 'Last-Minute Recall',
    color: '#eab308',
    description: 'Quickly review essential equations, definitions, theorem statements, and cheat-sheet summaries for rapid exam prep.',
    chatIntro: '⚡ **Rapid Revision Active**: Here are the high-yield formulas, definitions, and key points you must memorize.'
  }
]

// Interactive Quick Prompt Chips
const QUICK_PROMPTS = [
  { label: '💡 Feynman Analogy', prompt: 'Explain simply using the Feynman technique with an everyday analogy.' },
  { label: '🎯 Exam Blueprint (Marks)', prompt: 'Explain for exam: what are the key marks breakdown, mandatory keywords, diagrams, and examiner traps?' },
  { label: '📊 Flowchart & Diagram', prompt: 'Show a clear, precise ASCII/Unicode architectural flowchart and state diagram of how this works.' },
  { label: '🧮 Step-by-Step Numerical', prompt: 'Give a concrete step-by-step numerical or mathematical derivation example on this topic.' },
  { label: '🏢 Industry Application', prompt: 'Give a concrete real-world engineering and industry example of how this is applied.' },
  { label: '🧠 Quiz Me & Check', prompt: 'Test me: Ask me a challenging semester exam question on this topic and evaluate my answer.' },
  { label: '🔄 Explain Differently', prompt: "I don't understand: please explain again from a different angle and break it into simpler steps." }
]

function formatInlineText(text) {
  const parts = []
  let remaining = text

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/^([\s\S]*?)\*\*(.+?)\*\*([\s\S]*)$/)
    const codeMatch = remaining.match(/^([\s\S]*?)`([^`]+)`([\s\S]*)$/)
    const italicMatch = remaining.match(/^([\s\S]*?)\*([^*]+)\*([\s\S]*)$/)

    const matches = [
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

    if (first.type === 'bold') {
      parts.push(<strong key={parts.length} className="font-bold text-[var(--text)]">{content}</strong>)
    } else if (first.type === 'code') {
      parts.push(<code key={parts.length} className="px-1.5 py-0.5 rounded bg-[var(--surface-alt)] border border-[var(--border)] font-mono text-xs text-[var(--accent)]">{content}</code>)
    } else if (first.type === 'italic') {
      parts.push(<em key={parts.length} className="italic text-[var(--text-soft)]">{content}</em>)
    }

    remaining = post
  }

  return parts
}

function CodeBlockRenderer({ code, language }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const isDiagram = code.includes('┌') || code.includes('│') || code.includes('─') || code.includes('▼') || code.includes('──>') || code.includes('[')

  return (
    <div className="my-3 rounded-2xl border border-[var(--border)] overflow-hidden bg-[#0d1117] text-[#e6edf3] shadow-md">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#30363d] text-xs font-mono text-gray-400">
        <span className="flex items-center gap-2 font-semibold text-gray-300">
          <Code2 size={14} className="text-[var(--accent)]" />
          {isDiagram ? '📊 ASCII Architecture & Schematic Flow' : (language || 'Code / Formula')}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 hover:text-white transition-colors px-2.5 py-1 rounded-lg hover:bg-white/10 cursor-pointer"
          title="Copy code"
        >
          {copied ? <Check size={13} className="text-emerald-400" /> : <Copy size={13} />}
          <span>{copied ? 'Copied' : 'Copy'}</span>
        </button>
      </div>
      <div className="p-4 overflow-x-auto text-xs md:text-sm font-mono leading-relaxed whitespace-pre font-normal tracking-wide selection:bg-[var(--accent)] selection:text-white">
        {code}
      </div>
    </div>
  )
}

function RichAcademicMessage({ text, onAnswerCheckPrompt }) {
  const blocks = []
  const lines = text.split('\n')
  let inCode = false
  let currentCode = []
  let codeLang = ''
  let currentParagraph = []

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      blocks.push({ type: 'text', lines: [...currentParagraph] })
      currentParagraph = []
    }
  }

  for (let line of lines) {
    if (line.trim().startsWith('```')) {
      if (inCode) {
        blocks.push({ type: 'code', code: currentCode.join('\n'), language: codeLang })
        currentCode = []
        codeLang = ''
        inCode = false
      } else {
        flushParagraph()
        inCode = true
        codeLang = line.trim().replace(/^```/, '').trim()
      }
    } else if (inCode) {
      currentCode.push(line)
    } else {
      currentParagraph.push(line)
    }
  }

  if (inCode && currentCode.length > 0) {
    blocks.push({ type: 'code', code: currentCode.join('\n'), language: codeLang })
  }
  flushParagraph()

  return (
    <div className="space-y-3">
      {blocks.map((block, bIdx) => {
        if (block.type === 'code') {
          return <CodeBlockRenderer key={bIdx} code={block.code} language={block.language} />
        }

        return (
          <div key={bIdx} className="space-y-2">
            {block.lines.map((line, lIdx) => {
              const trimmed = line.trim()
              if (!trimmed) return <div key={lIdx} className="h-2" />

              if (trimmed.startsWith('# ')) {
                return (
                  <h1 key={lIdx} className="text-xl md:text-2xl font-extrabold text-[var(--text)] mt-4 mb-2 pb-1 border-b border-[var(--border)]">
                    {trimmed.replace(/^#\s+/, '')}
                  </h1>
                )
              }
              if (trimmed.startsWith('## ')) {
                return (
                  <h2 key={lIdx} className="text-lg md:text-xl font-bold text-[var(--accent)] mt-3 mb-1.5 flex items-center gap-2">
                    <Sparkles size={16} />
                    <span>{trimmed.replace(/^##\s+/, '')}</span>
                  </h2>
                )
              }
              if (trimmed.startsWith('### ')) {
                return (
                  <h3 key={lIdx} className="text-base font-bold text-[var(--text)] mt-2.5 mb-1">
                    {trimmed.replace(/^###\s+/, '')}
                  </h3>
                )
              }

              if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                return (
                  <div key={lIdx} className="flex items-start gap-2.5 pl-2 text-sm leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span className="flex-1">{formatInlineText(trimmed.replace(/^[-•*]\s+/, ''))}</span>
                  </div>
                )
              }

              if (trimmed.startsWith('👉') || trimmed.includes('Check Your Understanding:')) {
                return (
                  <div key={lIdx} className="my-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-800 dark:text-amber-200 text-sm flex items-start justify-between gap-3 shadow-xs">
                    <div className="flex-1">{formatInlineText(trimmed)}</div>
                    {onAnswerCheckPrompt && (
                      <button
                        onClick={() => onAnswerCheckPrompt(trimmed)}
                        className="px-3 py-1 rounded-lg bg-amber-500 text-white font-bold text-xs shrink-0 hover:bg-amber-600 cursor-pointer shadow-xs"
                      >
                        Answer Now
                      </button>
                    )}
                  </div>
                )
              }

              return (
                <p key={lIdx} className="text-sm md:text-[14.5px] leading-relaxed text-[var(--text)]">
                  {formatInlineText(line)}
                </p>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

function generateReply(method, technique, concept, subject, userQuery) {
  return `### Academic Breakdown: ${concept || subject}\n\n` +
    `• **Core Definition**: In the accredited syllabus for **${subject}**, ${concept || 'this topic'} forms an essential foundational pillar.\n\n` +
    `• **Exam Strategy**: Always highlight governing laws, write standard formulas clearly with units, and accompany numerical solutions with free-body or state diagrams.\n\n` +
    `👉 *Check Your Understanding: Can you summarize the primary governing rule for ${concept || 'this topic'} in your own words?*`
}

export default function Trainer() {
  const { user, streakDays, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, subjectObjects, units: allUnits } = useAuthoritativeCurriculum()
  const activeProfile = user
  const activeCurriculum = curriculum
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)

  const [phase, setPhase] = useState('setup')
  const [selectedSubject, setSelectedSubject] = useState(subjects[0] || '')
  const [selectedMethod, setSelectedMethod] = useState(STUDY_METHODS[0])
  const [selectedTechnique, setSelectedTechnique] = useState(studyTechniques[0])
  const [selectedUnit, setSelectedUnit] = useState(null)
  const [selectedChapter, setSelectedChapter] = useState(null)
  const [selectedConcept, setSelectedConcept] = useState(null)
  const [expandedUnit, setExpandedUnit] = useState(null)
  const [mobileTab, setMobileTab] = useState('chat')

  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loadingReply, setLoadingReply] = useState(false)

  const scrollRef = useRef(null)
  const inputRef = useRef(null)

  const location = useLocation()

  useEffect(() => {
    if (subjects.length > 0 && !subjects.includes(selectedSubject)) {
      setSelectedSubject(subjects[0])
      setSelectedUnit(null)
      setSelectedChapter(null)
      setSelectedConcept(null)
    }
  }, [subjects, selectedSubject])

  useEffect(() => {
    if (location.state?.concept) {
      if (location.state.subject && subjects.includes(location.state.subject)) {
        setSelectedSubject(location.state.subject)
      }
      setSelectedConcept(location.state.concept)
      setPhase('method_picker')
    }
  }, [location.state, subjects])

  const currentSubjectObj = (subjectObjects || []).find((s) =>
    typeof s === 'object' && (s.name === selectedSubject || s.code === selectedSubject || s.id === selectedSubject)
  ) || { name: selectedSubject, code: '', credits: '' }

  const activeSubjectId = currentSubjectObj.subject_id || currentSubjectObj.id || currentSubjectObj.code || ''
  const activeCurriculumId = activeCurriculum?.syllabus_id || activeCurriculum?.syllabusId || activeCurriculum?.id || ''

  const units = allUnits[selectedSubject] || []

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
    setMobileTab('chat')
  }

  const startSession = (method, technique) => {
    const m = method || selectedMethod
    const t = technique || selectedTechnique
    setSelectedMethod(m)
    setSelectedTechnique(t)

    recordActivity('trainer', `Studied "${selectedConcept}" in ${selectedSubject} (${m.name})`, {
      subject: selectedSubject,
      subjectId: activeSubjectId,
      curriculumId: activeCurriculumId,
      unit: selectedUnit,
      concept: selectedConcept
    })

    const semLabel = activeCurriculum.semester ? `Semester ${activeCurriculum.semester}` : 'Current Semester'
    const progLabel = activeCurriculum.degree || activeCurriculum.department || 'Degree Program'

    const teachText = `📚 **Personal AI Academic Tutor Initialized (${progLabel} · ${semLabel})**:\n\n` +
      `• **Validated Subject**: ${currentSubjectObj.code ? `[${currentSubjectObj.code}] ` : ''}${selectedSubject}\n` +
      `• **Unit / Module**: ${selectedUnit || 'Core Syllabus Unit'}\n` +
      `• **Target Topic**: ${selectedConcept}\n` +
      `• **Study Strategy**: ${m.name}\n\n` +
      `Welcome! I am your dedicated academic AI tutor for **"${selectedConcept}"**. Ask any question below or pick a prompt chip!`

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
        subject: selectedSubject || 'Academic Studies',
        subject_id: activeSubjectId,
        subjectId: activeSubjectId,
        curriculum_id: activeCurriculumId,
        syllabus_id: activeCurriculumId,
        unit: selectedUnit || 'General Syllabus Unit',
        chapter: selectedChapter || selectedUnit || '',
        topic: selectedConcept || userText.slice(0, 40),
        concept: selectedConcept || userText.slice(0, 40),
        study_method: selectedMethod?.name || selectedMethod?.id,
        level: activeProfile?.level || 'college',
        semester: activeCurriculum.semester || activeProfile?.semester || '',
        degree: activeCurriculum.degree || activeProfile?.degree || '',
        department: activeCurriculum.department || activeProfile?.department || '',
        class_level: activeProfile?.grade_level || activeProfile?.classLevel || '',
        history: newMsgList.slice(-8)
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

  const handleAnswerCheckPrompt = (promptLine) => {
    setInput(`My answer: `)
    inputRef.current?.focus()
  }

  if (!hasValidCurriculum) {
    return (
      <>
        <PageHead title="Personal AI Academic Tutor" />
        <CurriculumReviewNotice
          curriculum={activeCurriculum}
          featureName="Personal AI Academic Tutor"
          onOpenSyllabusModal={() => setIsSyllabusModalOpen(true)}
        />
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </>
    )
  }

  const semBadge = activeCurriculum.semester ? `Semester ${activeCurriculum.semester}` : 'Semester Active'

  return (
    <>
      <PageHead
        title="Personal Academic Tutor"
        subtitle="Interactive subject coaching, step-by-step problem solving, and concept mastery aligned with your syllabus."
        action={
          <div className="flex items-center gap-2.5">
            <span className="px-3.5 py-1.5 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-xs">
              <Sparkles size={14} className="text-emerald-500" /> Syllabus Aligned
            </span>
            <span className="px-3.5 py-1.5 bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-xs whitespace-nowrap">
              <Flame size={14} className="text-amber-500 shrink-0" strokeWidth={1.8} /> 🔥 {streakDays || 1} {streakDays === 1 ? 'Day' : 'Days'}
            </span>
          </div>
        }
      />

      {/* Mobile View Switcher (phones and portrait tablets) */}
      <div className="flex lg:hidden items-center p-1 bg-[var(--surface-alt)] rounded-2xl border border-[var(--border)] mb-3 gap-1">
        <button
          onClick={() => setMobileTab('syllabus')}
          className={`flex-1 min-h-[42px] py-2 px-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
            mobileTab === 'syllabus'
              ? 'bg-[var(--surface)] text-[var(--accent)] shadow-xs border border-[var(--border)]'
              : 'text-[var(--text-soft)] hover:text-[var(--text)]'
          }`}
        >
          <BookOpen size={16} />
          <span>Syllabus Modules ({units.length})</span>
        </button>
        <button
          onClick={() => setMobileTab('chat')}
          className={`flex-1 min-h-[42px] py-2 px-3 rounded-xl text-xs sm:text-sm font-bold flex items-center justify-center gap-2 transition-all cursor-pointer ${
            mobileTab === 'chat'
              ? 'bg-[var(--surface)] text-[var(--accent)] shadow-xs border border-[var(--border)]'
              : 'text-[var(--text-soft)] hover:text-[var(--text)]'
          }`}
        >
          <Bot size={16} />
          <span>AI Tutor ({selectedConcept ? 'Session' : 'Chat'})</span>
        </button>
      </div>

      <div className="h-[calc(100vh-210px)] sm:h-[calc(100vh-220px)] min-h-[500px] sm:min-h-[600px] border border-[var(--border)] rounded-2xl sm:rounded-3xl overflow-hidden bg-[var(--surface)] flex flex-col lg:flex-row shadow-sm">
        {/* LEFT: 4-Level Syllabus Tree */}
        <div className={`w-full lg:w-[320px] shrink-0 border-b lg:border-b-0 lg:border-r border-[var(--border)] flex flex-col overflow-hidden bg-[var(--surface-alt)]/40 ${
          mobileTab === 'syllabus' ? 'flex flex-1' : 'hidden lg:flex'
        }`}>
          <div className="p-4 border-b border-[var(--border)]">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] flex items-center gap-1.5">
                <BookOpen size={14} className="text-[var(--accent)]" />
                {semBadge} ({subjects.length})
              </span>
              <Badge tone="accent">{activeCurriculum.department ? activeCurriculum.department.slice(0, 14) : 'Courses'}</Badge>
            </div>

            {/* Subject Selector Tabs */}
            <div className="flex flex-col gap-1.5 max-h-[200px] overflow-y-auto pr-1 scrollbar-thin">
              {subjects.map((s) => {
                const sObj = (subjectObjects || []).find((item) => typeof item === 'object' && item.name === s)
                const isSelected = selectedSubject === s
                return (
                  <button
                    key={s}
                    onClick={() => handleSelectSubject(s)}
                    className={`text-left px-3.5 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all flex flex-col gap-1 border cursor-pointer ${
                      isSelected
                        ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                        : 'border-transparent text-[var(--text-soft)] hover:bg-[var(--surface)] hover:border-[var(--border)]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      {sObj?.code && (
                        <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded font-bold ${isSelected ? 'bg-white/20 text-white' : 'bg-[var(--surface-alt)] text-[var(--text-faint)]'}`}>
                          {sObj.code}
                        </span>
                      )}
                      {sObj?.credits && (
                        <span className={`text-[10px] font-medium ${isSelected ? 'text-white/80' : 'text-[var(--text-faint)]'}`}>
                          {sObj.credits} Credits
                        </span>
                      )}
                    </div>
                    <span className="truncate leading-tight">{s}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Unit / Topic Hierarchy */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
            <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] px-2 py-1 flex items-center justify-between">
              <span>Syllabus Modules</span>
              <span className="text-xs font-normal text-[var(--text-faint)]">{units.length} Units</span>
            </div>

            {units.map((unit, uIdx) => {
              const isExpanded = expandedUnit === unit.name || (!expandedUnit && uIdx === 0)
              return (
                <div key={unit.name || uIdx} className="rounded-2xl border border-[var(--border)] overflow-hidden bg-[var(--surface)] shadow-xs">
                  <button
                    onClick={() => setExpandedUnit(isExpanded ? '__collapsed' : unit.name)}
                    className={`w-full flex items-center justify-between px-3.5 py-2.5 text-xs md:text-sm font-bold text-left transition-colors cursor-pointer ${
                      isExpanded ? 'bg-[var(--accent-soft)] text-[var(--accent)]' : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                    }`}
                  >
                    <span className="truncate leading-tight">{unit.name}</span>
                    <ChevronDown size={15} className={`shrink-0 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                  </button>

                  {isExpanded && (
                    <div className="p-2 bg-[var(--surface)] border-t border-[var(--border)] space-y-1">
                      {(unit.concepts || []).map((concept, cIdx) => {
                        const isSelected = selectedConcept === concept && selectedUnit === unit.name
                        return (
                          <button
                            key={concept || cIdx}
                            onClick={() => handleSelectTopic(unit.name, concept)}
                            className={`w-full text-left px-3 py-2 rounded-xl text-xs md:text-sm transition-all flex items-center gap-2 cursor-pointer ${
                              isSelected
                                ? 'bg-[var(--accent)] text-white font-bold shadow-xs'
                                : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
                            }`}
                          >
                            <span className={`w-2 h-2 rounded-full shrink-0 ${isSelected ? 'bg-white' : 'bg-[var(--accent)]'}`} />
                            <span className="truncate">{concept}</span>
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

        {/* CENTER: AI Conversational Canvas */}
        <div className={`flex-1 flex-col min-w-0 overflow-hidden bg-[var(--surface)] ${
          mobileTab === 'chat' ? 'flex' : 'hidden lg:flex'
        }`}>
          {phase === 'setup' && (
            <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
              <div className="text-center max-w-xl">
                <div className="w-18 h-18 rounded-3xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto text-2xl mb-5 shadow-sm border border-[var(--accent)]/20">
                  <Bot size={36} />
                </div>
                <h2 className="text-2xl font-extrabold mb-2 text-[var(--text)]">
                  {selectedSubject ? `${selectedSubject} Academic Tutor` : 'Personal AI Academic Study Assistant'}
                </h2>
                <p className="text-sm text-[var(--text-soft)] mb-7 leading-relaxed max-w-md mx-auto">
                  Syllabus-aligned conversational AI tutor. Ask questions, solve mathematical derivations, generate ASCII flowcharts, or master concepts with the Feynman technique.
                </p>

                {/* Instant Action Starters */}
                <div className="flex flex-wrap gap-2.5 justify-center mb-8">
                  <button
                    onClick={() => {
                      setSelectedConcept("Semester Syllabus Overview")
                      setSelectedUnit("All Modules")
                      setPhase('session')
                      sendMessage(`Provide an executive academic overview of all core subjects and modules for my ${semBadge}.`)
                    }}
                    className="px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-xs md:text-sm font-semibold text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all cursor-pointer shadow-xs"
                  >
                    📋 Overview of {semBadge}
                  </button>
                  <button
                    onClick={() => {
                      if (units[0]?.concepts?.[0]) {
                        handleSelectTopic(units[0].name, units[0].concepts[0])
                      }
                    }}
                    className="px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-xs md:text-sm font-semibold text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all cursor-pointer shadow-xs"
                  >
                    🎯 Coach on Module 1
                  </button>
                  <button
                    onClick={() => {
                      setSelectedConcept("Exam Preparation Blueprint")
                      setSelectedUnit("All Modules")
                      setPhase('session')
                      sendMessage(`How do I prepare to score 90%+ in ${selectedSubject || 'my semester subjects'}? What are high-weightage topics and examiner expectations?`)
                    }}
                    className="px-4 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-xs md:text-sm font-semibold text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all cursor-pointer shadow-xs"
                  >
                    🏆 90%+ Exam Strategy Blueprint
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-3 text-xs text-[var(--text-soft)] bg-[var(--surface-alt)]/60 p-4 rounded-2xl border border-[var(--border)]">
                  <div className="flex flex-col items-center text-center p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                    <Lightbulb size={20} className="text-amber-500 mb-1.5" />
                    <span className="font-bold text-[var(--text)]">Feynman Method</span>
                    <span className="text-[11px] text-[var(--text-faint)] mt-0.5">Simple analogies</span>
                  </div>
                  <div className="flex flex-col items-center text-center p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                    <Code2 size={20} className="text-blue-500 mb-1.5" />
                    <span className="font-bold text-[var(--text)]">Crisp Flowcharts</span>
                    <span className="text-[11px] text-[var(--text-faint)] mt-0.5">ASCII schematics</span>
                  </div>
                  <div className="flex flex-col items-center text-center p-3 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                    <Target size={20} className="text-emerald-500 mb-1.5" />
                    <span className="font-bold text-[var(--text)]">Socratic Testing</span>
                    <span className="text-[11px] text-[var(--text-faint)] mt-0.5">Active recall</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Strategy Picker */}
          {phase === 'method_picker' && selectedConcept && (
            <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-7">
              <div className="p-6 rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)]/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-[var(--accent)] mb-1">
                    <span>{semBadge}</span> · <span>{selectedSubject}</span>
                  </div>
                  <h3 className="text-2xl font-extrabold text-[var(--text)]">{selectedConcept}</h3>
                  <div className="text-sm text-[var(--text-soft)] mt-1">
                    Unit: <strong>{selectedUnit || 'Core Syllabus Unit'}</strong>
                  </div>
                </div>
                <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center font-bold">
                  <Sparkles size={24} />
                </div>
              </div>

              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-3">
                  1. Choose Teaching Strategy
                </div>
                <div className="grid md:grid-cols-2 gap-4 mb-8">
                  {STUDY_METHODS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setSelectedMethod(m)}
                      className={`text-left p-5 rounded-2xl border transition-all cursor-pointer ${
                        selectedMethod.id === m.id
                          ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm ring-2 ring-[var(--accent)]/30'
                          : 'border-[var(--border)] hover:border-[var(--accent)] bg-[var(--surface)]'
                      }`}
                    >
                      <div className="font-bold text-base mb-1 text-[var(--text)]">{m.name}</div>
                      <div className="text-xs md:text-sm text-[var(--text-soft)] mb-3 leading-relaxed">{m.description}</div>
                      <Badge tone="accent">{m.tagline}</Badge>
                    </button>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-4 border-t border-[var(--border)]">
                  <Button variant="ghost" onClick={() => setPhase('setup')}>
                    <ArrowLeft size={16} /> Back to Syllabus
                  </Button>
                  <Button size="lg" onClick={() => startSession(selectedMethod, selectedTechnique)} className="flex items-center gap-2">
                    Launch AI Tutor Session <ChevronRight size={16} />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Chat Stream */}
          {phase === 'session' && (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Header */}
              <div className="p-4 px-6 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-alt)]/40 shrink-0">
                <div className="flex items-center gap-3 truncate">
                  <button
                    onClick={() => setPhase('setup')}
                    className="p-2 rounded-xl hover:bg-[var(--surface)] text-[var(--text-soft)] transition-colors cursor-pointer"
                    title="Back to topics"
                  >
                    <ArrowLeft size={18} />
                  </button>
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-xl bg-[var(--accent)] text-white flex items-center justify-center font-bold shadow-xs">
                      <Bot size={18} />
                    </div>
                    <div className="truncate">
                      <div className="text-sm font-bold truncate flex items-center gap-1.5">
                        <span className="text-[var(--text)]">{selectedSubject}</span>
                        <span className="text-[var(--text-faint)]">›</span>
                        <span className="text-[var(--accent)]">{selectedConcept || 'Study Session'}</span>
                      </div>
                      <div className="text-xs text-[var(--text-soft)] truncate flex items-center gap-1.5 mt-0.5">
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span>{selectedUnit || 'Curriculum'} · {selectedMethod.name}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => {
                      setMessages([])
                      startSession(selectedMethod, selectedTechnique)
                    }}
                    className="px-3 py-1.5 border border-[var(--border)] rounded-xl text-xs font-semibold text-[var(--text-soft)] hover:bg-[var(--surface)] flex items-center gap-1 transition-colors cursor-pointer"
                    title="Reset chat"
                  >
                    <RefreshCw size={13} />
                    <span>Reset</span>
                  </button>
                  <button
                    onClick={() => setPhase('method_picker')}
                    className="px-3 py-1.5 border border-[var(--border)] rounded-xl text-xs font-semibold text-[var(--text-soft)] hover:bg-[var(--surface)] transition-colors cursor-pointer"
                  >
                    Switch Style
                  </button>
                </div>
              </div>

              {/* Message Feed */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 sm:p-7 space-y-6 scrollbar-thin">
                {messages.map((m, idx) => (
                  <div key={idx} className={`flex gap-3.5 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {m.role === 'bot' && (
                      <div className="w-8 h-8 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 font-bold shadow-xs mt-0.5">
                        <Bot size={16} />
                      </div>
                    )}

                    <div
                      className={`max-w-[85%] rounded-2xl p-5 text-sm md:text-[14.5px] leading-relaxed shadow-xs transition-all ${
                        m.role === 'user'
                          ? 'bg-[var(--accent)] text-white font-medium rounded-tr-none'
                          : 'bg-[var(--surface)] border border-[var(--border)] text-[var(--text)] rounded-tl-none shadow-sm'
                      }`}
                    >
                      {m.role === 'user' ? (
                        <div className="whitespace-pre-wrap">{m.text}</div>
                      ) : (
                        <RichAcademicMessage
                          text={m.text}
                          onAnswerCheckPrompt={handleAnswerCheckPrompt}
                        />
                      )}
                    </div>

                    {m.role === 'user' && (
                      <div className="w-8 h-8 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)] flex items-center justify-center shrink-0 font-bold shadow-xs mt-0.5">
                        <User size={16} />
                      </div>
                    )}
                  </div>
                ))}

                {loadingReply && (
                  <div className="flex items-start gap-3.5">
                    <div className="w-8 h-8 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0 font-bold shadow-xs">
                      <Bot size={16} />
                    </div>
                    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl rounded-tl-none p-4 flex items-center gap-3 text-sm text-[var(--text-soft)] shadow-xs">
                      <Loader2 size={16} className="animate-spin text-[var(--accent)]" />
                      <span>Generating precise academic explanation, ASCII flowcharts & exam insights…</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="p-4 sm:p-5 border-t border-[var(--border)] bg-[var(--surface)] space-y-3">
                {/* Prompt Pills */}
                <div className="flex items-center gap-2 overflow-x-auto pb-1.5 scrollbar-thin">
                  <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] shrink-0 mr-1 flex items-center gap-1">
                    <Sparkles size={13} className="text-[var(--accent)]" /> Quick Prompts:
                  </span>
                  {QUICK_PROMPTS.map((qp, qIdx) => (
                    <button
                      key={qIdx}
                      type="button"
                      onClick={() => sendMessage(qp.prompt)}
                      disabled={loadingReply}
                      className="px-3.5 py-1.5 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1.5 text-xs font-semibold cursor-pointer"
                    >
                      {qp.label}
                    </button>
                  ))}
                </div>

                {/* Form */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    sendMessage()
                  }}
                  className="flex items-center gap-2.5"
                >
                  <input
                    ref={inputRef}
                    type="text"
                    aria-label="Ask AI Academic Tutor question"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Ask AI Academic Tutor anything about ${selectedConcept || selectedSubject || 'your curriculum'}…`}
                    className="flex-1 px-4 py-3.5 text-sm md:text-base bg-[var(--surface-alt)] border border-[var(--border-strong)] rounded-2xl text-[var(--text)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] transition-all placeholder:text-[var(--text-faint)]"
                    disabled={loadingReply}
                  />
                  <Button
                    type="submit"
                    aria-label="Send question to tutor"
                    disabled={!input.trim() || loadingReply}
                    className="px-6 py-3.5 rounded-2xl shrink-0 flex items-center gap-2 shadow-sm"
                  >
                    <Send size={16} />
                    <span className="hidden sm:inline">Send</span>
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
