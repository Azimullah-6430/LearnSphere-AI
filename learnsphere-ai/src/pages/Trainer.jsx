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
  // Regex to split on bold **text**, italics *text*, and inline `code`
  const parts = []
  let remaining = text

  while (remaining.length > 0) {
    const boldMatch = remaining.match(/^([\s\S]*?)\*\*(.+?)\*\*([\s\S]*)$/)
    const codeMatch = remaining.match(/^([\s\S]*?)`([^`]+)`([\s\S]*)$/)
    const italicMatch = remaining.match(/^([\s\S]*?)\*([^*]+)\*([\s\S]*)$/)

    // Find first occurrence among markdown markers
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
      parts.push(<code key={parts.length} className="px-1.5 py-0.5 rounded bg-[var(--surface-alt)] border border-[var(--border)] font-mono text-[11.5px] text-[var(--accent)]">{content}</code>)
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
    <div className="my-3 rounded-xl border border-[var(--border)] overflow-hidden bg-[#0d1117] text-[#e6edf3] shadow-md">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#161b22] border-b border-[#30363d] text-[11px] font-mono text-gray-400">
        <span className="flex items-center gap-1.5 font-semibold text-gray-300">
          <Code2 size={13} className="text-[var(--accent)]" />
          {isDiagram ? '📊 ASCII Architecture & Flowchart Schematic' : (language || 'Diagram / Code')}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 hover:text-white transition-colors px-2 py-0.5 rounded hover:bg-white/10"
          title="Copy to clipboard"
        >
          {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
          <span>{copied ? 'Copied!' : 'Copy'}</span>
        </button>
      </div>
      <div className="p-3.5 overflow-x-auto text-[11.5px] font-mono leading-relaxed whitespace-pre font-normal tracking-wide selection:bg-[var(--accent)] selection:text-white">
        {code}
      </div>
    </div>
  )
}

function RichAcademicMessage({ text, onAnswerCheckPrompt }) {
  const [copiedAll, setCopiedAll] = useState(false)

  const handleCopyAll = () => {
    navigator.clipboard.writeText(text)
    setCopiedAll(true)
    setTimeout(() => setCopiedAll(false), 2000)
  }

  // Parse code blocks vs regular text
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

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    if (line.trim().startsWith('```')) {
      if (inCode) {
        blocks.push({ type: 'code', code: currentCode.join('\n'), language: codeLang })
        currentCode = []
        inCode = false
      } else {
        flushParagraph()
        inCode = true
        codeLang = line.trim().replace(/^```/, '') || 'text'
      }
    } else if (inCode) {
      currentCode.push(line)
    } else {
      currentParagraph.push(line)
    }
  }
  flushParagraph()
  if (inCode && currentCode.length > 0) {
    blocks.push({ type: 'code', code: currentCode.join('\n'), language: codeLang })
  }

  return (
    <div className="space-y-2.5">
      {blocks.map((block, bIdx) => {
        if (block.type === 'code') {
          return <CodeBlockRenderer key={bIdx} code={block.code} language={block.language} />
        }

        return (
          <div key={bIdx} className="space-y-1.5">
            {block.lines.map((rawLine, lIdx) => {
              const line = rawLine.trim()
              if (!line) return <div key={lIdx} className="h-1.5" />

              // Section Header ### or ##
              if (line.startsWith('### ') || line.startsWith('## ')) {
                const headerText = line.replace(/^#{2,3}\s+/, '')
                return (
                  <h4 key={lIdx} className="text-[13.5px] font-extrabold text-[var(--text)] mt-3 mb-1.5 flex items-center gap-1.5 border-b border-[var(--border)] pb-1">
                    <span className="w-1.5 h-3.5 bg-[var(--accent)] rounded-full shrink-0" />
                    <span>{headerText}</span>
                  </h4>
                )
              }

              // Interactive Socratic Question Card (👉 *Check Your Understanding* or 👉 *Check*)
              if (line.includes('👉') || line.startsWith('*Check Your Understanding*') || line.startsWith('*Self-Check*')) {
                return (
                  <div key={lIdx} className="my-2.5 p-3 rounded-xl border border-[var(--accent)]/40 bg-[var(--accent-soft)]/50 text-[var(--text)] flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 shadow-xs">
                    <div className="flex items-start gap-2 text-[12.5px] font-medium leading-snug">
                      <Sparkles size={16} className="text-[var(--accent)] shrink-0 mt-0.5" />
                      <div>{formatInlineText(line)}</div>
                    </div>
                    {onAnswerCheckPrompt && (
                      <button
                        onClick={() => onAnswerCheckPrompt(line)}
                        className="shrink-0 px-2.5 py-1 bg-[var(--accent)] text-white text-[11px] font-bold rounded-lg hover:opacity-90 transition-all flex items-center gap-1 shadow-xs"
                      >
                        Answer Prompt <ChevronRight size={13} />
                      </button>
                    )}
                  </div>
                )
              }

              // Warning / Examiner Trap Alert (⚠️)
              if (line.startsWith('⚠️')) {
                return (
                  <div key={lIdx} className="my-2 p-2.5 rounded-xl border border-amber-500/30 bg-amber-500/10 text-[var(--text)] text-[12px] flex items-start gap-2">
                    <span className="text-amber-500 font-bold shrink-0">⚠️</span>
                    <div className="leading-snug">{formatInlineText(line.replace(/^⚠️\s*/, ''))}</div>
                  </div>
                )
              }

              // Bullet List Item (• or - or 1.)
              if (line.startsWith('• ') || line.startsWith('- ')) {
                const bulletText = line.replace(/^[•-]\s+/, '')
                return (
                  <div key={lIdx} className="flex items-start gap-2 text-[12.5px] pl-1.5">
                    <span className="text-[var(--accent)] font-bold shrink-0 mt-0.5">•</span>
                    <div className="leading-relaxed">{formatInlineText(bulletText)}</div>
                  </div>
                )
              }

              // Regular Paragraph
              return (
                <p key={lIdx} className="text-[12.5px] leading-relaxed text-[var(--text)]">
                  {formatInlineText(line)}
                </p>
              )
            })}
          </div>
        )
      })}

      {/* Message Utility Bar */}
      <div className="flex items-center justify-end gap-2 pt-1 border-t border-[var(--border)]/40 text-[10.5px] text-[var(--text-faint)]">
        <button
          onClick={handleCopyAll}
          className="flex items-center gap-1 hover:text-[var(--accent)] transition-colors px-1.5 py-0.5 rounded"
        >
          {copiedAll ? <Check size={11} className="text-emerald-500" /> : <Copy size={11} />}
          <span>{copiedAll ? 'Copied Lesson' : 'Copy Explanation'}</span>
        </button>
      </div>
    </div>
  )
}

function generateReply(method, technique, concept, subject, input) {
  if (method?.id === 'exam-score-strategy') {
    return `🎯 **Examiner Scoring Blueprint for "${concept}" (${subject})**:\n\n` +
      `### 1. Mandatory Technical Definition (2 Marks)\n` +
      `State the formal law governing **${concept}** with precise keywords.\n\n` +
      `### 2. Neat Monospace Block Diagram (2 Marks)\n` +
      `\`\`\`text\n` +
      `[ Input Signals / Parameters ] ──> [ ${concept} Processing Core ] ──> [ Output Invariants ]\n` +
      `\`\`\`\n\n` +
      `### 3. Key Working Equations & Boundary Rules (3 Marks)\n` +
      `• **Key Equation**: Mathematical governing relations.\n` +
      `• **Evaluator Scoring Criterion**: Clearly highlight SI units and state boundary conditions.\n\n` +
      `### 4. Common Mistakes Evaluators Penalize\n` +
      `⚠️ Omitting the labeled block diagram (costs 2 marks immediately).\n\n` +
      `👉 *How would you state the one-sentence formal definition of ${concept} for the first 2 marks? Give it a try!*`
  }
  
  if (method?.id === 'rapid-revision') {
    return `⚡ **Rapid Memory Summary for "${concept}"**:\n\n` +
      `### 1. Core Law & Formula\n` +
      `• **Formula**: Key governing equations for ${concept}.\n` +
      `• **SI Units**: Standard unit dimensions and parameters.\n\n` +
      `### 2. High-Yield Takeaway\n` +
      `Remember that **${concept}** maintains determinism and stability in ${subject}.\n\n` +
      `👉 *Self-Check: Can you state the primary formula or law of ${concept} from memory right now?*`
  }

  return `📚 **Academic Explanation: ${concept} (${subject})**\n\n` +
    `### 1. Core Intuition (Feynman Technique)\n` +
    `Think of **${concept}** as an automated controller that guarantees safety and precision in ${subject}.\n\n` +
    `### 2. Architecture Diagram\n` +
    `\`\`\`text\n` +
    `[ State S0 ] ──( Verification )──> [ ${concept} Core ] ──( Deterministic )──> [ Target State S1 ]\n` +
    `\`\`\`\n\n` +
    `### 3. Check Your Understanding\n` +
    `👉 *What is the primary constraint that ${concept} must enforce during state execution?*`
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
  const inputRef = useRef(null)

  const units = (allUnits && allUnits[selectedSubject]) ? allUnits[selectedSubject] : getDynamicChapters(selectedSubject, activeProfile, curriculum)

  // Find active subject metadata (subjectId, code, category, credits)
  const currentSubjectObj = subjectObjects.find(s => 
    (typeof s === 'object' && (s.name === selectedSubject || s.code === selectedSubject || s.subject_id === selectedSubject || s.id === selectedSubject))
  ) || { name: selectedSubject, code: '', subject_id: '', type: 'Semester Subject' }

  const activeSubjectId = currentSubjectObj.subject_id || currentSubjectObj.id || currentSubjectObj.code || ''
  const activeCurriculumId = activeCurriculum?.syllabus_id || activeCurriculum?.syllabusId || activeCurriculum?.id || ''

  // Handle location state navigation from MisconceptionMap or Dashboard
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

    const teachText = `📚 **Personal AI Academic Tutor Initialized (${progLabel} · ${semLabel})**:\n\n` +
      `• **Validated Subject**: ${currentSubjectObj.code ? `[${currentSubjectObj.code}] ` : ''}${selectedSubject}\n` +
      `• **Unit / Module**: ${selectedUnit || 'Core Syllabus Unit'}\n` +
      `• **Target Topic**: ${selectedConcept}\n` +
      `• **Study Strategy**: ${m.name}\n\n` +
      `Welcome! I am your dedicated academic AI tutor for **"${selectedConcept}"**. I will teach you with precision, intuitive analogies, ASCII flowcharts, step-by-step math, and interactive questions to guarantee top marks. Ask any question below or pick a prompt!`

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
    const cleanPrompt = promptLine.replace(/^👉\s*\*/, '').replace(/\*$/, '').replace(/^Check Your Understanding:\s*/, '')
    setInput(`My answer: `)
    inputRef.current?.focus()
  }

  if (!hasValidCurriculum) {
    return (
      <>
        <PageHead title="AI Academic Tutor" />
        <CurriculumReviewNotice
          curriculum={activeCurriculum}
          featureName="AI Academic Tutor"
          onOpenSyllabusModal={() => setIsSyllabusModalOpen(true)}
        />
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </>
    )
  }

  return (
    <>
      <PageHead
        title="AI Academic Tutor"
        action={
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5">
              <Sparkles size={13} className="text-emerald-500" /> AI Tutor Active
            </span>
            <span className="px-3 py-1 bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1">
              <Flame size={14} className="text-amber-500" /> {streakDays} Day Streak
            </span>
          </div>
        }
      />

      <div className="h-[calc(100vh-210px)] min-h-[620px] border border-[var(--border)] rounded-2xl overflow-hidden bg-[var(--surface)] flex shadow-sm">

        {/* LEFT: 4-Level Syllabus Tree & Subject Navigation */}
        <div className="w-[300px] shrink-0 border-r border-[var(--border)] flex flex-col overflow-hidden bg-[var(--surface-alt)]/40">
          <div className="p-3.5 border-b border-[var(--border)]">
            <div className="flex items-center justify-between mb-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-faint)] flex items-center gap-1">
                <BookOpen size={12} className="text-[var(--accent)]" />
                {semBadge} Subjects ({subjects.length})
              </span>
              <Badge tone="accent">{activeCurriculum.department || 'Curriculum'}</Badge>
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
                    className={`text-left px-3 py-2 rounded-xl text-[12px] font-semibold transition-all flex flex-col gap-0.5 border ${
                      isSelected
                        ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                        : 'border-transparent text-[var(--text-soft)] hover:bg-[var(--surface)] hover:border-[var(--border)]'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      {sObj?.code && (
                        <span className={`text-[9.5px] font-mono px-1.5 py-0.2 rounded font-bold ${isSelected ? 'bg-white/20 text-white' : 'bg-[var(--surface-alt)] text-[var(--text-faint)]'}`}>
                          {sObj.code}
                        </span>
                      )}
                      {sObj?.credits && (
                        <span className={`text-[9.5px] font-medium ${isSelected ? 'text-white/80' : 'text-[var(--text-faint)]'}`}>
                          {sObj.credits} Credits
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
              <span>Syllabus Modules & Topics</span>
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

        {/* CENTER: ChatGPT / Gemini AI Conversational Canvas */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden bg-[var(--surface)]">
          {phase === 'setup' && (
            <div className="flex-1 flex items-center justify-center p-8 overflow-y-auto">
              <div className="text-center max-w-[560px]">
                <div className="w-16 h-16 rounded-3xl bg-gradient-to-tr from-[var(--accent)] to-purple-500 text-white flex items-center justify-center mx-auto text-2xl mb-4 shadow-lg shadow-[var(--accent)]/20 animate-pulse">
                  <Bot size={32} />
                </div>
                <div className="text-xl font-extrabold mb-1.5 text-[var(--text)]">
                  {selectedSubject ? `${selectedSubject} Academic AI Tutor` : 'Personal AI Academic Study Assistant'}
                </div>
                <div className="text-xs text-[var(--text-soft)] mb-6 max-w-[460px] mx-auto leading-relaxed">
                  Specialized AI tutor for university and college students. Ask any question, solve exam numericals, get step-by-step flowcharts, or master concepts with the Feynman technique.
                </div>

                {/* Instant Action Starters */}
                <div className="flex flex-wrap gap-2 justify-center mb-6">
                  <button
                    onClick={() => {
                      setSelectedConcept("Semester Syllabus Overview")
                      setSelectedUnit("All Modules")
                      setPhase('session')
                      sendMessage(`What are all the core subjects and modules for my ${semBadge}? Give an executive academic overview.`)
                    }}
                    className="px-3.5 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-[12px] font-semibold text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)] hover:shadow-xs transition-all flex items-center gap-1.5"
                  >
                    📋 Executive Overview of {semBadge}
                  </button>
                  <button
                    onClick={() => {
                      if (units[0]?.concepts?.[0]) {
                        handleSelectTopic(units[0].name, units[0].concepts[0])
                      }
                    }}
                    className="px-3.5 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-[12px] font-semibold text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)] hover:shadow-xs transition-all flex items-center gap-1.5"
                  >
                    🎯 Start Coaching on Module 1
                  </button>
                  <button
                    onClick={() => {
                      setSelectedConcept("Exam Preparation Blueprint")
                      setSelectedUnit("All Modules")
                      setPhase('session')
                      sendMessage(`How do I prepare to score 90%+ in ${selectedSubject || 'my semester subjects'}? What are high-weightage topics and examiner expectations?`)
                    }}
                    className="px-3.5 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-[12px] font-semibold text-[var(--text)] hover:border-[var(--accent)] hover:text-[var(--accent)] hover:shadow-xs transition-all flex items-center gap-1.5"
                  >
                    🏆 90%+ Exam Strategy Blueprint
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2.5 text-[11px] text-[var(--text-soft)] bg-[var(--surface-alt)]/60 p-3.5 rounded-2xl border border-[var(--border)]">
                  <div className="flex flex-col items-center text-center p-2 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                    <Lightbulb size={18} className="text-amber-500 mb-1" />
                    <span className="font-bold text-[var(--text)]">Feynman Method</span>
                    <span className="text-[10px] text-[var(--text-faint)]">Simple everyday analogies</span>
                  </div>
                  <div className="flex flex-col items-center text-center p-2 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                    <Code2 size={18} className="text-blue-500 mb-1" />
                    <span className="font-bold text-[var(--text)]">Crisp Flowcharts</span>
                    <span className="text-[10px] text-[var(--text-faint)]">Monospace ASCII schematics</span>
                  </div>
                  <div className="flex flex-col items-center text-center p-2 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                    <Target size={18} className="text-emerald-500 mb-1" />
                    <span className="font-bold text-[var(--text)]">Socratic Testing</span>
                    <span className="text-[10px] text-[var(--text-faint)]">Active recall & feedback</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Strategy Picker (shown after topic selected) */}
          {phase === 'method_picker' && selectedConcept && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div className="p-4 rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)]/60 flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-wider text-[var(--accent)] mb-1">
                    <span>{semBadge}</span> · <span>{selectedSubject}</span>
                  </div>
                  <div className="text-xl font-extrabold text-[var(--text)]">{selectedConcept}</div>
                  <div className="text-xs text-[var(--text-soft)] mt-0.5">
                    Module: <strong>{selectedUnit || 'Core Syllabus Unit'}</strong>
                  </div>
                </div>
                <div className="hidden sm:flex items-center gap-2">
                  <span className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center font-bold">
                    <Sparkles size={20} />
                  </span>
                </div>
              </div>

              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-3">
                  1. Select Study Technique & Teaching Style
                </div>
                <div className="grid md:grid-cols-2 gap-3 mb-6">
                  {STUDY_METHODS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setSelectedMethod(m)}
                      className={`text-left p-4 rounded-2xl border transition-all ${
                        selectedMethod.id === m.id
                          ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm ring-2 ring-[var(--accent)]/30'
                          : 'border-[var(--border)] hover:border-[var(--accent-dim)] bg-[var(--surface)]'
                      }`}
                    >
                      <div className="font-bold text-[14px] mb-1 text-[var(--text)]">{m.name}</div>
                      <div className="text-[11.5px] text-[var(--text-soft)] mb-2.5 leading-relaxed">{m.description}</div>
                      <Badge tone="accent">{m.tagline}</Badge>
                    </button>
                  ))}
                </div>

                <div className="flex items-center justify-between pt-3 border-t border-[var(--border)]">
                  <Button variant="ghost" onClick={() => setPhase('setup')}>
                    <ArrowLeft size={14} /> Back to Syllabus
                  </Button>
                  <Button onClick={() => startSession(selectedMethod, selectedTechnique)} className="flex items-center gap-2">
                    Launch AI Tutor Session <ChevronRight size={15} />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Chat / Conversational Session (ChatGPT & Gemini Styled) */}
          {phase === 'session' && (
            <div className="flex-1 flex flex-col min-h-0">
              {/* ChatGPT / Gemini Header */}
              <div className="p-3 px-5 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-alt)]/40 shrink-0">
                <div className="flex items-center gap-3 truncate">
                  <button
                    onClick={() => setPhase('setup')}
                    className="p-1.5 rounded-xl hover:bg-[var(--surface)] text-[var(--text-soft)] transition-colors"
                    title="Back to topics"
                  >
                    <ArrowLeft size={16} />
                  </button>
                  <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-[var(--accent)] to-purple-500 text-white flex items-center justify-center text-xs font-bold shadow-xs">
                      <Bot size={16} />
                    </div>
                    <div className="truncate">
                      <div className="text-[13px] font-bold truncate flex items-center gap-1.5">
                        <span className="text-[var(--text)]">{selectedSubject}</span>
                        <span className="text-[var(--text-faint)]">›</span>
                        <span className="text-[var(--accent)]">{selectedConcept || 'Study Session'}</span>
                      </div>
                      <div className="text-[10px] text-[var(--text-faint)] truncate flex items-center gap-1.5">
                        <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
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
                    className="px-2.5 py-1 border border-[var(--border)] rounded-xl text-[11px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface)] flex items-center gap-1 transition-colors"
                    title="Restart session"
                  >
                    <RefreshCw size={12} />
                    <span className="hidden sm:inline">Reset</span>
                  </button>
                  <button
                    onClick={() => setPhase('method_picker')}
                    className="px-2.5 py-1 border border-[var(--border)] rounded-xl text-[11px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface)] transition-colors"
                  >
                    Switch Style
                  </button>
                </div>
              </div>

              {/* Chat Message Stream */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
                {messages.map((m, idx) => (
                  <div key={idx} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {m.role === 'bot' && (
                      <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[var(--accent)] to-purple-500 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs mt-0.5">
                        <Bot size={14} />
                      </div>
                    )}
                    
                    <div
                      className={`max-w-[88%] rounded-2xl p-4 text-[13px] leading-relaxed shadow-xs transition-all ${
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
                      <div className="w-7 h-7 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)] flex items-center justify-center shrink-0 text-xs font-bold shadow-xs mt-0.5">
                        <User size={14} />
                      </div>
                    )}
                  </div>
                ))}

                {loadingReply && (
                  <div className="flex items-start gap-3">
                    <div className="w-7 h-7 rounded-xl bg-gradient-to-tr from-[var(--accent)] to-purple-500 text-white flex items-center justify-center shrink-0 text-xs font-bold shadow-xs">
                      <Bot size={14} />
                    </div>
                    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl rounded-tl-none p-3.5 flex items-center gap-2.5 text-xs text-[var(--text-soft)] shadow-xs">
                      <Loader2 size={15} className="animate-spin text-[var(--accent)]" />
                      <span>Generating precise academic explanation, ASCII flowcharts & exam insights...</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Human Tutor Prompt Chips & Input Box */}
              <div className="p-3 sm:p-4 border-t border-[var(--border)] bg-[var(--surface)] space-y-2.5">
                {/* Scrollable Quick Prompt Pills */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-[11px] no-scrollbar">
                  <span className="text-[10px] font-bold uppercase text-[var(--text-faint)] shrink-0 mr-1 flex items-center gap-1">
                    <Sparkles size={11} className="text-[var(--accent)]" /> Quick Prompts:
                  </span>
                  {QUICK_PROMPTS.map((qp, qIdx) => (
                    <button
                      key={qIdx}
                      type="button"
                      onClick={() => sendMessage(qp.prompt)}
                      disabled={loadingReply}
                      className="px-3 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] text-[var(--text-soft)] transition-all shrink-0 flex items-center gap-1 font-medium hover:bg-[var(--accent-soft)]/20"
                    >
                      {qp.label}
                    </button>
                  ))}
                </div>

                {/* Chat Input Form */}
                <form
                  onSubmit={(e) => {
                    e.preventDefault()
                    sendMessage()
                  }}
                  className="flex items-center gap-2"
                >
                  <input
                    ref={inputRef}
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder={`Ask AI Academic Tutor anything about ${selectedConcept || selectedSubject || 'your studies'}...`}
                    className="flex-1 px-4 py-3 text-xs bg-[var(--surface-alt)] border border-[var(--border)] rounded-2xl text-[var(--text)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 transition-all placeholder:text-[var(--text-faint)]"
                    disabled={loadingReply}
                  />
                  <Button
                    type="submit"
                    disabled={!input.trim() || loadingReply}
                    className="px-5 py-3 rounded-2xl shrink-0 flex items-center gap-1.5 shadow-md shadow-[var(--accent)]/20"
                  >
                    <Send size={15} />
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
