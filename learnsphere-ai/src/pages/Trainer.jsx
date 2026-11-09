import { useEffect, useRef, useState, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import katex from 'katex'
import 'katex/dist/katex.min.css'
import mermaid from 'mermaid'
import {
  BookOpen,
  Layers,
  Compass,
  GraduationCap,
  HelpCircle,
  Award,
  CheckCircle2,
  Circle,
  Clock,
  ArrowLeft,
  ArrowRight,
  ChevronRight,
  ChevronDown,
  Sparkles,
  Zap,
  Flame,
  Lightbulb,
  Send,
  Loader2,
  RefreshCw,
  RotateCcw,
  UploadCloud,
  Check,
  Copy,
  Code2,
  Bot,
  User,
  CheckCheck,
  ArrowUpRight,
  ListOrdered,
  AlertCircle
} from 'lucide-react'

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: 'inherit'
})

const QUICK_ACTIONS = [
  { label: '💡 Explain simply', query: 'Can you explain this more simply in everyday language using an intuitive analogy?' },
  { label: '🏢 Give another example', query: 'Can you provide another concrete real-world or industry engineering example?' },
  { label: '📊 Show a diagram', query: 'Can you provide a clear Mermaid flowchart diagram illustrating this process step-by-step?' },
  { label: '📝 Summarize this answer', query: 'Can you summarize the key takeaways, exam keywords, and formulas in a short revision cheat-sheet?' },
  { label: '🧠 Test my understanding', query: 'Can you give me a focused checkpoint question to test my understanding of this?' }
]

// ── 6-Step Journey Definition ──────────────────────────────────────────────────
const JOURNEY_STEPS = [
  { id: 1, label: 'Subject', fullTitle: 'Select Subject', icon: BookOpen },
  { id: 2, label: 'Topic', fullTitle: 'Choose Topic', icon: Layers },
  { id: 3, label: 'Method', fullTitle: 'Learning Method', icon: Compass },
  { id: 4, label: 'Learn', fullTitle: 'Start Learning', icon: GraduationCap },
  { id: 5, label: 'Quiz', fullTitle: 'Check Understanding', icon: HelpCircle },
  { id: 6, label: 'Complete', fullTitle: 'Complete & Continue', icon: Award }
]

// ── Step 3 Learning Methods ────────────────────────────────────────────────────
const LEARNING_METHODS = [
  {
    id: 'concept',
    title: 'Learn a Concept',
    subtitle: 'Understand the topic with clear explanations',
    description: 'Explore fundamental principles, core definitions, and mechanisms explained with intuitive clarity.',
    icon: Lightbulb,
    badge: 'Fundamental Clarity',
    color: 'emerald',
    prompt: (topic, subject, unit) =>
      `You are an expert personal academic tutor. Teach "${topic}" from the accredited course "${subject}" (Unit: "${unit || 'Core Syllabus'}").\n` +
      `Provide a comprehensive conceptual explanation using:\n` +
      `1. Clear Overview and Core Definition\n` +
      `2. Governing Principles and How It Works\n` +
      `3. Key Technical Terminology and Essential Rules\n` +
      `4. High-Yield Exam Takeaways\n\n` +
      `Format with clean headings (##), bullet points, and highlight important terms in **bold**.`
  },
  {
    id: 'step-by-step',
    title: 'Step-by-Step Learning',
    subtitle: 'Learn complex concepts in smaller steps',
    description: 'Break complex mechanisms and processes into sequential, bite-sized chronological stages.',
    icon: ListOrdered,
    badge: 'Structured Breakdown',
    color: 'blue',
    prompt: (topic, subject, unit) =>
      `You are an expert personal academic tutor. Break down "${topic}" from "${subject}" (Unit: "${unit || 'Core Syllabus'}") into progressive, sequential steps.\n` +
      `Structure the lesson as:\n` +
      `• Step 1: Foundational Prerequisites & Purpose\n` +
      `• Step 2: The Core Mechanism / Process Breakdown\n` +
      `• Step 3: Detailed Working & Edge Cases\n` +
      `• Step 4: Verification, Outcome & Common Traps\n\n` +
      `Make each step easy to digest with numbered headings and concise paragraphs.`
  },
  {
    id: 'real-world',
    title: 'Real-World Examples',
    subtitle: 'Understand practical applications',
    description: 'Connect theoretical topics directly to modern industry systems, engineering tools, and everyday case studies.',
    icon: Compass,
    badge: 'Industry Applied',
    color: 'amber',
    prompt: (topic, subject, unit) =>
      `You are an expert personal academic tutor. Explain "${topic}" from "${subject}" (Unit: "${unit || 'Core Syllabus'}") through concrete practical applications.\n` +
      `Include:\n` +
      `1. Intuitive Everyday Analogy (The Feynman Technique)\n` +
      `2. Real-World Industry Application & Case Study (e.g. how companies and engineers apply this)\n` +
      `3. Why This Matters in Practice\n` +
      `4. Key Takeaways for Academic & Industry Success`
  },
  {
    id: 'revision',
    title: 'Quick Revision',
    subtitle: 'Review important concepts',
    description: 'Fast-paced review with bulleted cheat-sheets, mandatory definitions, essential formulas, and exam keywords.',
    icon: Zap,
    badge: 'High-Yield Recall',
    color: 'purple',
    prompt: (topic, subject, unit) =>
      `You are an expert personal academic tutor. Provide an executive Quick Revision Cheat-Sheet for "${topic}" in "${subject}".\n` +
      `Include:\n` +
      `• High-Weightage Keywords and Mandatory Definitions\n` +
      `• Essential Formulas, Theorems, or Governing Laws\n` +
      `• Common Mistakes & Examiner Traps to Avoid\n` +
      `• 3 Crucial Points You Must Mention in Exam Answers`
  },
  {
    id: 'practice',
    title: 'Practice Questions',
    subtitle: 'Test understanding',
    description: 'Step-by-step walkthrough of exam problems, numerical questions, or conceptual analysis with full solutions.',
    icon: HelpCircle,
    badge: 'Exam Mastery',
    color: 'rose',
    prompt: (topic, subject, unit) =>
      `You are an expert personal academic tutor. Provide 2 targeted exam-style practice questions on "${topic}" from "${subject}".\n` +
      `For each question:\n` +
      `1. Clearly state the Question\n` +
      `2. Provide the Step-by-Step Solution Breakdown\n` +
      `3. Highlight the Marking Criteria (what evaluators check for full marks)\n` +
      `4. Add a Self-Check Tip for the student.`
  }
]

// ── LaTeX, Mermaid & Code Formatting Helpers ───────────────────────────────────

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
  let remaining = text

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
  const chartId = useMemo(() => `mermaid-svg-${Math.random().toString(36).substring(2, 9)}`, [])

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
        if (active) {
          setSvgHtml(svg)
        }
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
      <div className="my-3 rounded-2xl border border-[var(--border)] overflow-hidden bg-[#0d1117] text-[#e6edf3] shadow-md">
        <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#30363d] text-xs font-mono text-gray-400">
          <span className="flex items-center gap-2 font-semibold text-amber-400">
            <Sparkles size={14} className="text-amber-400" />
            Visual Diagram / Flowchart
          </span>
        </div>
        <div className="p-4 overflow-x-auto text-xs md:text-sm font-mono leading-relaxed whitespace-pre text-gray-300">
          {code}
        </div>
      </div>
    )
  }

  return (
    <div className="my-4 rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] p-4 sm:p-6 shadow-xs overflow-x-auto flex justify-center items-center">
      <div
        className="mermaid-wrapper max-w-full [&>svg]:max-w-full [&>svg]:h-auto"
        dangerouslySetInnerHTML={{ __html: svgHtml }}
      />
    </div>
  )
}

function TableRenderer({ rows }) {
  if (!rows || rows.length < 2) return null
  const parseRow = (line) =>
    line.split('|').map(c => c.trim()).filter((_, idx, arr) => idx > 0 && idx < arr.length - 1)

  const headerCols = parseRow(rows[0])
  const bodyRows = rows.slice(2).map(r => parseRow(r))

  return (
    <div className="my-4 overflow-x-auto rounded-2xl border border-[var(--border)] shadow-xs">
      <table className="w-full text-left text-xs sm:text-sm border-collapse">
        <thead className="bg-[var(--surface-alt)] border-b border-[var(--border)] text-[var(--text)] font-bold">
          <tr>
            {headerCols.map((col, idx) => (
              <th key={idx} className="p-3.5 font-bold uppercase tracking-wider text-[11px] text-[var(--text-soft)]">
                {formatInlineText(col)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--border)] bg-[var(--surface)]">
          {bodyRows.map((r, rIdx) => (
            <tr key={rIdx} className="hover:bg-[var(--surface-alt)]/40 transition-colors">
              {r.map((cell, cIdx) => (
                <td key={cIdx} className="p-3 text-[var(--text)] leading-relaxed">
                  {formatInlineText(cell)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function CodeBlockRenderer({ code, language }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(code)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="my-3 rounded-2xl border border-[var(--border)] overflow-hidden bg-[#0d1117] text-[#e6edf3] shadow-md">
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#30363d] text-xs font-mono text-gray-400">
        <span className="flex items-center gap-2 font-semibold text-gray-300">
          <Code2 size={14} className="text-[var(--accent)]" />
          {language || 'Code'}
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

function FormattedContent({ text }) {
  if (!text) return null
  const blocks = []
  const lines = text.split('\n')
  let inCode = false
  let currentCode = []
  let codeLang = ''
  let currentParagraph = []
  let inTable = false
  let currentTable = []

  const flushParagraph = () => {
    if (currentParagraph.length > 0) {
      blocks.push({ type: 'text', lines: [...currentParagraph] })
      currentParagraph = []
    }
  }

  const flushTable = () => {
    if (currentTable.length > 0) {
      blocks.push({ type: 'table', rows: [...currentTable] })
      currentTable = []
      inTable = false
    }
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed.startsWith('```')) {
      flushTable()
      if (inCode) {
        blocks.push({ type: 'code', code: currentCode.join('\n'), language: codeLang })
        currentCode = []
        codeLang = ''
        inCode = false
      } else {
        flushParagraph()
        inCode = true
        codeLang = trimmed.replace(/^```/, '').trim().toLowerCase()
      }
      continue
    }

    if (inCode) {
      currentCode.push(line)
      continue
    }

    const isTableRow = trimmed.startsWith('|') && trimmed.endsWith('|') && trimmed.length > 2
    if (isTableRow) {
      flushParagraph()
      inTable = true
      currentTable.push(trimmed)
      continue
    } else if (inTable) {
      flushTable()
    }

    currentParagraph.push(line)
  }

  if (inCode && currentCode.length > 0) {
    blocks.push({ type: 'code', code: currentCode.join('\n'), language: codeLang })
  }
  flushTable()
  flushParagraph()

  return (
    <div className="space-y-3.5 text-[var(--text)]">
      {blocks.map((block, bIdx) => {
        if (block.type === 'code') {
          if (block.language === 'mermaid') {
            return <MermaidRenderer key={bIdx} code={block.code} />
          }
          return <CodeBlockRenderer key={bIdx} code={block.code} language={block.language} />
        }

        if (block.type === 'table') {
          return <TableRenderer key={bIdx} rows={block.rows} />
        }

        return (
          <div key={bIdx} className="space-y-2">
            {block.lines.map((line, lIdx) => {
              const trimmed = line.trim()
              if (!trimmed) return <div key={lIdx} className="h-1.5" />

              if (trimmed.startsWith('$$') && trimmed.endsWith('$$') && trimmed.length > 4) {
                const formula = trimmed.slice(2, -2).trim()
                return (
                  <div
                    key={lIdx}
                    className="my-3 p-3 overflow-x-auto text-center rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-sm sm:text-base font-serif"
                    dangerouslySetInnerHTML={{ __html: renderKatexMath(formula, true) }}
                  />
                )
              }

              if (trimmed.startsWith('# ')) {
                return (
                  <h1 key={lIdx} className="text-xl sm:text-2xl font-extrabold text-[var(--text)] mt-4 mb-2 pb-1.5 border-b border-[var(--border)] tracking-tight">
                    {trimmed.replace(/^#\s+/, '')}
                  </h1>
                )
              }
              if (trimmed.startsWith('## ')) {
                return (
                  <h2 key={lIdx} className="text-lg sm:text-xl font-bold text-[var(--accent)] mt-4 mb-2 flex items-center gap-2">
                    <Sparkles size={16} className="text-[var(--accent)] shrink-0" />
                    <span>{trimmed.replace(/^##\s+/, '')}</span>
                  </h2>
                )
              }
              if (trimmed.startsWith('### ')) {
                return (
                  <h3 key={lIdx} className="text-base font-bold text-[var(--text)] mt-3 mb-1">
                    {trimmed.replace(/^###\s+/, '')}
                  </h3>
                )
              }

              if (trimmed.startsWith('• ') || trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
                return (
                  <div key={lIdx} className="flex items-start gap-2.5 pl-2 text-sm md:text-[14.5px] leading-relaxed">
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] mt-2 shrink-0" />
                    <span className="flex-1">{formatInlineText(trimmed.replace(/^[-•*]\s+/, ''))}</span>
                  </div>
                )
              }

              if (trimmed.match(/^\d+\.\s+/)) {
                const num = trimmed.match(/^(\d+)\.\s+/)[1]
                const content = trimmed.replace(/^\d+\.\s+/, '')
                return (
                  <div key={lIdx} className="flex items-start gap-3 pl-2 text-sm md:text-[14.5px] leading-relaxed my-1.5">
                    <span className="w-6 h-6 rounded-lg bg-[var(--accent-soft)] text-[var(--accent)] font-bold text-xs flex items-center justify-center shrink-0 mt-0.5">
                      {num}
                    </span>
                    <span className="flex-1">{formatInlineText(content)}</span>
                  </div>
                )
              }

              if (trimmed.startsWith('👉') || trimmed.includes('Key Takeaway:') || trimmed.includes('Exam Note:') || trimmed.includes('Checkpoint:')) {
                return (
                  <div key={lIdx} className="my-3 p-4 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-900 dark:text-amber-200 text-sm flex items-start gap-2.5 shadow-xs">
                    <Sparkles size={16} className="text-amber-500 shrink-0 mt-0.5" />
                    <div className="flex-1">{formatInlineText(trimmed)}</div>
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

// ── Main Guided Personal Trainer Component ─────────────────────────────────────

export default function Trainer() {
  const { user, streakDays, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, subjectObjects, units: allUnits } = useAuthoritativeCurriculum()

  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)
  const location = useLocation()

  // ── Step Navigation State (1 to 6) ─────────────────────────────────────────
  const [currentStep, setCurrentStep] = useState(1)

  // Selections (preserved when navigating backwards)
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedUnit, setSelectedUnit] = useState('')
  const [selectedTopic, setSelectedTopic] = useState('')
  const [selectedMethod, setSelectedMethod] = useState(LEARNING_METHODS[0])

  // Lesson State (Step 4)
  const [lessonContent, setLessonContent] = useState('')
  const [lessonLoading, setLessonLoading] = useState(false)
  const [lessonError, setLessonError] = useState(null)
  const [tutorQna, setTutorQna] = useState([])
  const [followUpInput, setFollowUpInput] = useState('')
  const [followUpLoading, setFollowUpLoading] = useState(false)

  // Check Understanding State (Step 5)
  const [quizQuestion, setQuizQuestion] = useState('')
  const [quizLoading, setQuizLoading] = useState(false)
  const [quizError, setQuizError] = useState(null)
  const [studentAnswer, setStudentAnswer] = useState('')
  const [answerEvaluating, setAnswerEvaluating] = useState(false)
  const [evaluationFeedback, setEvaluationFeedback] = useState(null)
  const [evalError, setEvalError] = useState(null)

  // Topic filter in Step 2 ('all', 'in_progress', 'completed')
  const [topicFilter, setTopicFilter] = useState('all')

  const lessonScrollRef = useRef(null)

  // ── Persistent Progress Storage ────────────────────────────────────────────
  const userIdentifier = user?.id || user?._id || user?.email || 'default'
  const progressStorageKey = `learnsphere_trainer_progress_${userIdentifier}`

  const [userProgress, setUserProgress] = useState(() => {
    try {
      const raw = localStorage.getItem(progressStorageKey)
      return raw ? JSON.parse(raw) : {}
    } catch {
      return {}
    }
  })

  const saveProgress = (updatedProgress) => {
    setUserProgress(updatedProgress)
    try {
      localStorage.setItem(progressStorageKey, JSON.stringify(updatedProgress))
    } catch {}
  }

  // Auto-select first subject if none selected
  useEffect(() => {
    if (subjects && subjects.length > 0 && (!selectedSubject || !subjects.includes(selectedSubject))) {
      setSelectedSubject(subjects[0])
    }
  }, [subjects, selectedSubject])

  // Deep-link integration from Dashboard or Misconception Map
  useEffect(() => {
    if (location.state?.concept) {
      const targetSubj = location.state.subject && subjects.includes(location.state.subject)
        ? location.state.subject
        : (subjects[0] || '')
      if (targetSubj) setSelectedSubject(targetSubj)
      setSelectedTopic(location.state.concept)
      setSelectedUnit(location.state.unit || '')
      setCurrentStep(3) // Jump to Choose Learning Method
    }
  }, [location.state, subjects])

  // Active Subject Object & Units from Syllabus
  const currentSubjectObj = useMemo(() => {
    return (subjectObjects || []).find(
      (s) => typeof s === 'object' && (s.name === selectedSubject || s.code === selectedSubject || s.id === selectedSubject)
    ) || { name: selectedSubject, code: '', credits: '' }
  }, [subjectObjects, selectedSubject])

  const activeSubjectId = currentSubjectObj.subject_id || currentSubjectObj.id || currentSubjectObj.code || ''
  const activeCurriculumId = curriculum?.syllabus_id || curriculum?.syllabusId || curriculum?.id || ''
  const subjectUnits = useMemo(() => allUnits[selectedSubject] || [], [allUnits, selectedSubject])

  // Calculate Progress Stats for all subjects
  const subjectProgressMap = useMemo(() => {
    const map = {}
    subjects.forEach((subj) => {
      const uList = allUnits[subj] || []
      let total = 0
      let completed = 0
      let inProgress = 0
      uList.forEach((u) => {
        (u.concepts || []).forEach((c) => {
          total++
          const status = userProgress[subj]?.[c]
          if (status === 'completed') completed++
          else if (status === 'in_progress') inProgress++
        })
      })
      const percent = total > 0 ? Math.round((completed / total) * 100) : 0
      map[subj] = { total, completed, inProgress, remaining: Math.max(0, total - completed), percent }
    })
    return map
  }, [subjects, allUnits, userProgress])

  // Current Subject Progress Stats
  const currentSubjectStats = subjectProgressMap[selectedSubject] || { total: 0, completed: 0, inProgress: 0, remaining: 0, percent: 0 }

  // ── Step 1 Action: Select Subject ──────────────────────────────────────────
  const handleSelectSubject = (subj) => {
    setSelectedSubject(subj)
    setSelectedUnit('')
    setSelectedTopic('')
    setCurrentStep(2)
  }

  // ── Step 2 Action: Select Topic ────────────────────────────────────────────
  const handleSelectTopic = (unitName, topicName) => {
    setSelectedUnit(unitName)
    setSelectedTopic(topicName)

    // Mark as in_progress if not already completed
    const currentStatus = userProgress[selectedSubject]?.[topicName]
    if (currentStatus !== 'completed') {
      const updated = {
        ...userProgress,
        [selectedSubject]: {
          ...(userProgress[selectedSubject] || {}),
          [topicName]: 'in_progress'
        }
      }
      saveProgress(updated)
    }

    setCurrentStep(3)
  }

  // ── Step 3 Action: Select Method & Start Learning ──────────────────────────
  const handleSelectMethod = (method) => {
    setSelectedMethod(method)
  }

  const handleStartLearning = async () => {
    setCurrentStep(4)
    setTutorQna([])
    setLessonLoading(true)
    setLessonError(null)
    setLessonContent('')

    recordActivity('trainer', `Studied "${selectedTopic}" in ${selectedSubject} (${selectedMethod.title})`, {
      subject: selectedSubject,
      subjectId: activeSubjectId,
      curriculumId: activeCurriculumId,
      unit: selectedUnit,
      concept: selectedTopic
    })

    try {
      const prompt = selectedMethod.prompt(selectedTopic, selectedSubject, selectedUnit)
      const res = await api.trainerChat({
        message: prompt,
        subject: selectedSubject || 'Academic Studies',
        subject_id: activeSubjectId,
        subjectId: activeSubjectId,
        curriculum_id: activeCurriculumId,
        syllabus_id: activeCurriculumId,
        unit: selectedUnit || 'General Syllabus Unit',
        chapter: selectedUnit || '',
        topic: selectedTopic,
        concept: selectedTopic,
        study_method: selectedMethod.title,
        level: user?.level || 'college',
        semester: curriculum?.semester || user?.semester || '',
        degree: curriculum?.degree || user?.degree || '',
        department: curriculum?.department || user?.department || '',
        class_level: user?.grade_level || user?.classLevel || '',
        history: []
      })

      if (res && res.success && res.reply) {
        setLessonContent(res.reply)
      } else {
        setLessonError(res?.error || 'AI generation encountered an issue. Please click Retry.')
      }
    } catch (err) {
      setLessonError(err?.message || 'Connection error while communicating with AI service. Please retry.')
    } finally {
      setLessonLoading(false)
    }
  }

  // Follow-up question during Step 4
  const handleSendFollowUp = async (customQueryOrEvent) => {
    let query = ''
    if (typeof customQueryOrEvent === 'string') {
      query = customQueryOrEvent.trim()
    } else if (customQueryOrEvent?.preventDefault) {
      customQueryOrEvent.preventDefault()
      query = followUpInput.trim()
    } else {
      query = followUpInput.trim()
    }
    if (!query || followUpLoading) return

    setFollowUpInput('')
    const newHistory = [...tutorQna, { role: 'user', text: query }]
    setTutorQna(newHistory)
    setFollowUpLoading(true)

    try {
      const res = await api.trainerChat({
        message: query,
        subject: selectedSubject,
        subject_id: activeSubjectId,
        curriculum_id: activeCurriculumId,
        unit: selectedUnit,
        topic: selectedTopic,
        concept: selectedTopic,
        study_method: selectedMethod.title,
        history: newHistory.filter(h => h.role !== 'error').slice(-6)
      })

      if (res && res.success && res.reply) {
        setTutorQna([...newHistory, { role: 'bot', text: res.reply }])
      } else {
        setTutorQna([...newHistory, {
          role: 'error',
          text: res?.error || 'Tutor response was interrupted. Please retry.',
          query
        }])
      }
    } catch (err) {
      setTutorQna([...newHistory, {
        role: 'error',
        text: err?.message || 'Connection interrupted. Please retry.',
        query
      }])
    } finally {
      setFollowUpLoading(false)
      setTimeout(() => {
        lessonScrollRef.current?.scrollTo({ top: lessonScrollRef.current.scrollHeight, behavior: 'smooth' })
      }, 100)
    }
  }

  // ── Step 4 Action: Move to Step 5 (Check Understanding) ────────────────────
  const handleProceedToCheckUnderstanding = async () => {
    setCurrentStep(5)
    setStudentAnswer('')
    setEvaluationFeedback(null)
    setEvalError(null)
    setQuizError(null)
    setQuizLoading(true)

    try {
      const res = await api.trainerChat({
        message: `Generate one clear, focused semester exam question to check understanding of "${selectedTopic}" in "${selectedSubject}" (Unit: "${selectedUnit}"). Ask only the question and state what should be explained.`,
        subject: selectedSubject,
        subject_id: activeSubjectId,
        curriculum_id: activeCurriculumId,
        unit: selectedUnit,
        topic: selectedTopic,
        concept: selectedTopic,
        study_method: 'Practice Questions'
      })

      if (res && res.success && res.reply) {
        setQuizQuestion(res.reply)
      } else {
        setQuizError(res?.error || 'Unable to generate knowledge check question. Please click Retry.')
      }
    } catch (err) {
      setQuizError(err?.message || 'Connection error while generating question. Please click Retry.')
    } finally {
      setQuizLoading(false)
    }
  }

  // Submit Answer in Step 5
  const handleSubmitQuizAnswer = async (e) => {
    if (e) e.preventDefault()
    const ans = studentAnswer.trim()
    if (!ans || answerEvaluating) return

    setAnswerEvaluating(true)
    setEvalError(null)
    setEvaluationFeedback(null)

    try {
      const evalPrompt =
        `A student answered a check-understanding question on "${selectedTopic}" in "${selectedSubject}".\n` +
        `Question: ${quizQuestion}\n` +
        `Student Answer: "${ans}"\n\n` +
        `Evaluate their answer as an encouraging personal tutor:\n` +
        `1. What was explained correctly and clearly\n` +
        `2. Any missing keywords or formulas that would earn full marks in an exam\n` +
        `3. A brief, ideal summary answer\n` +
        `Be supportive, clear, and constructive.`

      const res = await api.trainerChat({
        message: evalPrompt,
        subject: selectedSubject,
        subject_id: activeSubjectId,
        curriculum_id: activeCurriculumId,
        unit: selectedUnit,
        topic: selectedTopic,
        concept: selectedTopic,
        study_method: 'Practice Questions'
      })

      if (res && res.success && res.reply) {
        setEvaluationFeedback(res.reply)
      } else {
        setEvalError(res?.error || 'Evaluation could not be completed. Please click Retry.')
      }
    } catch (err) {
      setEvalError(err?.message || 'Connection error during evaluation. Please click Retry.')
    } finally {
      setAnswerEvaluating(false)
    }
  }

  // ── Step 5 Action: Complete Topic & Move to Step 6 ─────────────────────────
  const handleCompleteTopic = () => {
    // Strictly update progress ONLY when completed
    const updated = {
      ...userProgress,
      [selectedSubject]: {
        ...(userProgress[selectedSubject] || {}),
        [selectedTopic]: 'completed'
      }
    }
    saveProgress(updated)
    setCurrentStep(6)
  }

  // ── Step 6 Actions: Continue Learning ──────────────────────────────────────
  const handleContinueNextTopic = () => {
    // Find next uncompleted topic in the subject
    let nextT = null
    let nextU = null
    for (const u of subjectUnits) {
      for (const c of (u.concepts || [])) {
        if (userProgress[selectedSubject]?.[c] !== 'completed') {
          nextT = c
          nextU = u.name
          break
        }
      }
      if (nextT) break
    }

    if (nextT) {
      setSelectedUnit(nextU)
      setSelectedTopic(nextT)
      setCurrentStep(3) // Go to choose method for next topic
    } else {
      // All topics completed in subject! Return to subjects
      setCurrentStep(1)
    }
  }

  const handleReviseCurrentTopic = () => {
    setCurrentStep(4) // Re-open lesson
  }

  const handleChooseAnotherSubject = () => {
    setCurrentStep(1)
  }

  // ── Empty Syllabus State ───────────────────────────────────────────────────
  if (!hasValidCurriculum || !subjects || subjects.length === 0) {
    return (
      <div className="space-y-6">
        <PageHead
          title="Personal Academic Tutor"
          subtitle="Guided, syllabus-aligned interactive coaching designed for your semester."
        />
        <div className="max-w-2xl mx-auto my-8 p-8 md:p-10 rounded-3xl bg-[var(--surface)] border border-[var(--border)] text-center shadow-sm">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-5 border border-emerald-500/20">
            <UploadCloud size={32} />
          </div>
          <h2 className="text-2xl font-bold text-[var(--text)] mb-3">Upload Your Syllabus to Start</h2>
          <p className="text-sm md:text-base text-[var(--text-soft)] mb-7 leading-relaxed max-w-lg mx-auto">
            Personal Trainer guides you step-by-step through subjects and topics extracted directly from your official syllabus. Please upload your syllabus file to unlock your personalized learning journey.
          </p>
          <div className="flex justify-center gap-3">
            <Button size="lg" onClick={() => setIsSyllabusModalOpen(true)} className="flex items-center gap-2">
              <UploadCloud size={18} /> Upload Syllabus
            </Button>
          </div>
        </div>
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </div>
    )
  }

  return (
    <div className="space-y-6 pb-12">
      {/* Page Header */}
      <PageHead
        title="Personal Academic Tutor"
        subtitle="A guided step-by-step tutor aligned to your official syllabus and learning pace."
        action={
          <div className="flex items-center gap-2.5">
            <span className="px-3.5 py-1.5 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-xs">
              <Sparkles size={14} className="text-emerald-500" /> Syllabus Aligned
            </span>
            <span className="px-3.5 py-1.5 bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/30 rounded-full text-xs font-bold flex items-center gap-1.5 shadow-xs whitespace-nowrap">
              <Flame size={14} className="text-amber-500 shrink-0" strokeWidth={1.8} /> {streakDays || 1} {streakDays === 1 ? 'Day' : 'Days'} Streak
            </span>
          </div>
        }
      />

      {/* ── Visual Stepper Tracker ─────────────────────────────────────────── */}
      <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-3 sm:p-4 shadow-xs">
        {/* Desktop Stepper */}
        <div className="hidden md:flex items-center justify-between">
          {JOURNEY_STEPS.map((st, idx) => {
            const isCompleted = currentStep > st.id
            const isActive = currentStep === st.id
            const isSelectable = currentStep >= st.id
            const StepIcon = st.icon

            return (
              <div key={st.id} className="flex items-center flex-1 last:flex-initial">
                <button
                  type="button"
                  onClick={() => {
                    if (isSelectable) setCurrentStep(st.id)
                  }}
                  disabled={!isSelectable}
                  className={`flex items-center gap-2.5 px-3 py-1.5 rounded-xl transition-all cursor-pointer ${
                    isActive
                      ? 'bg-[var(--accent)] text-white shadow-xs font-bold'
                      : isCompleted
                      ? 'text-emerald-600 dark:text-emerald-400 font-semibold hover:bg-[var(--surface-alt)]'
                      : 'text-[var(--text-faint)] cursor-not-allowed opacity-60'
                  }`}
                  aria-label={`Step ${st.id}: ${st.fullTitle}`}
                >
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs shrink-0 ${
                    isActive
                      ? 'bg-white/20 text-white font-bold'
                      : isCompleted
                      ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                      : 'bg-[var(--surface-alt)] border border-[var(--border)]'
                  }`}>
                    {isCompleted ? <Check size={14} strokeWidth={2.5} /> : <StepIcon size={14} />}
                  </div>
                  <div className="text-left">
                    <div className="text-[10px] uppercase tracking-wider opacity-75">Step {st.id}</div>
                    <div className="text-xs sm:text-sm font-semibold truncate leading-tight">{st.label}</div>
                  </div>
                </button>

                {idx < JOURNEY_STEPS.length - 1 && (
                  <div className="flex-1 mx-2 h-0.5 bg-[var(--border)] rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all duration-300 ${
                        currentStep > st.id ? 'bg-emerald-500' : 'bg-transparent'
                      }`}
                    />
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Mobile Stepper Banner */}
        <div className="flex md:hidden items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-6 h-6 rounded-lg bg-[var(--accent)] text-white font-bold text-xs flex items-center justify-center">
              {currentStep}
            </span>
            <span className="text-xs font-bold text-[var(--text)]">
              Step {currentStep} of 6: {JOURNEY_STEPS[currentStep - 1]?.fullTitle}
            </span>
          </div>
          {currentStep > 1 && (
            <button
              onClick={() => setCurrentStep(prev => prev - 1)}
              className="px-2.5 py-1 text-xs font-semibold text-[var(--text-soft)] hover:text-[var(--text)] flex items-center gap-1 cursor-pointer"
            >
              <ArrowLeft size={13} /> Back
            </button>
          )}
        </div>
      </div>

      {/* ═══════════════════════════════════════════════════════════════════════
          STEP 1: SELECT SUBJECT
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentStep === 1 && (
        <div className="space-y-5 animate-in fade-in duration-200">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-2">
            <div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text)]">Step 1: Select a Subject</h2>
              <p className="text-sm text-[var(--text-soft)] mt-0.5">
                Choose a course from your official syllabus to start your personal learning session.
              </p>
            </div>
            <div className="text-xs font-semibold text-[var(--text-faint)]">
              {subjects.length} Subjects in Syllabus
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {subjects.map((subj) => {
              const sObj = (subjectObjects || []).find(item => typeof item === 'object' && item.name === subj)
              const stats = subjectProgressMap[subj] || { total: 0, completed: 0, percent: 0 }
              const isSelected = selectedSubject === subj

              return (
                <div
                  key={subj}
                  onClick={() => handleSelectSubject(subj)}
                  className={`p-5 rounded-2xl border transition-all duration-200 cursor-pointer flex flex-col justify-between group ${
                    isSelected
                      ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm ring-2 ring-[var(--accent)]/20'
                      : 'border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] hover:shadow-xs'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2 mb-2.5">
                      {sObj?.code ? (
                        <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-bold bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--accent)]">
                          {sObj.code}
                        </span>
                      ) : (
                        <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
                      )}
                      <span className="text-xs font-medium text-[var(--text-soft)]">
                        {stats.completed}/{stats.total} Topics Mastered
                      </span>
                    </div>

                    <h3 className="font-bold text-base sm:text-lg text-[var(--text)] group-hover:text-[var(--accent)] transition-colors leading-snug mb-3">
                      {subj}
                    </h3>
                  </div>

                  <div className="pt-3 border-t border-[var(--border)]/70 space-y-2">
                    {/* Progress Bar */}
                    <div className="flex items-center justify-between text-xs font-semibold">
                      <span className="text-[var(--text-soft)]">Progress</span>
                      <span className="text-[var(--accent)]">{stats.percent}%</span>
                    </div>
                    <div className="w-full h-2 bg-[var(--surface-alt)] rounded-full overflow-hidden border border-[var(--border)]">
                      <div
                        className="h-full bg-[var(--accent)] rounded-full transition-all duration-500"
                        style={{ width: `${stats.percent}%` }}
                      />
                    </div>

                    <div className="flex items-center justify-end pt-1">
                      <span className="text-xs font-bold text-[var(--accent)] flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                        Select Subject <ChevronRight size={14} />
                      </span>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          STEP 2: CHOOSE TOPIC
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentStep === 2 && (
        <div className="space-y-5 animate-in fade-in duration-200">
          {/* Header & Back Button */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-[var(--border)]/70">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Button variant="ghost" size="sm" onClick={() => setCurrentStep(1)} className="gap-1 px-2.5">
                  <ArrowLeft size={14} /> Change Subject
                </Button>
                <span className="text-xs font-bold text-[var(--text-faint)]">·</span>
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">{selectedSubject}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text)]">Step 2: Choose Topic</h2>
              <p className="text-sm text-[var(--text-soft)] mt-0.5">
                Select a topic from your syllabus to study with your tutor.
              </p>
            </div>

            {/* Filter Pills */}
            <div className="flex items-center gap-1.5 p-1 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-xs font-semibold self-start sm:self-auto">
              <button
                onClick={() => setTopicFilter('all')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                  topicFilter === 'all' ? 'bg-[var(--surface)] text-[var(--text)] font-bold shadow-xs' : 'text-[var(--text-soft)]'
                }`}
              >
                All Topics ({currentSubjectStats.total})
              </button>
              <button
                onClick={() => setTopicFilter('in_progress')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                  topicFilter === 'in_progress' ? 'bg-[var(--surface)] text-[var(--text)] font-bold shadow-xs' : 'text-[var(--text-soft)]'
                }`}
              >
                In Progress ({currentSubjectStats.inProgress})
              </button>
              <button
                onClick={() => setTopicFilter('completed')}
                className={`px-3 py-1 rounded-lg transition-all cursor-pointer ${
                  topicFilter === 'completed' ? 'bg-[var(--surface)] text-[var(--text)] font-bold shadow-xs' : 'text-[var(--text-soft)]'
                }`}
              >
                Completed ({currentSubjectStats.completed})
              </button>
            </div>
          </div>

          {/* Unit / Topic Modules */}
          <div className="space-y-4">
            {subjectUnits.length === 0 ? (
              <div className="p-8 rounded-2xl bg-[var(--surface)] border border-[var(--border)] text-center text-sm text-[var(--text-soft)]">
                No topics extracted for this subject yet. Please check your syllabus file.
              </div>
            ) : (
              subjectUnits.map((unit, uIdx) => {
                const concepts = unit.concepts || []
                const filteredConcepts = concepts.filter(c => {
                  const status = userProgress[selectedSubject]?.[c]
                  if (topicFilter === 'completed') return status === 'completed'
                  if (topicFilter === 'in_progress') return status === 'in_progress'
                  return true
                })

                if (filteredConcepts.length === 0 && topicFilter !== 'all') return null

                return (
                  <div key={unit.name || uIdx} className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] overflow-hidden shadow-xs">
                    <div className="px-5 py-3.5 bg-[var(--surface-alt)]/60 border-b border-[var(--border)] flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <BookOpen size={15} className="text-[var(--accent)]" />
                        <span className="font-bold text-sm text-[var(--text)]">{unit.name}</span>
                      </div>
                      <span className="text-xs font-semibold text-[var(--text-faint)]">
                        {concepts.length} Topics
                      </span>
                    </div>

                    <div className="p-3 grid grid-cols-1 md:grid-cols-2 gap-2.5">
                      {filteredConcepts.map((concept, cIdx) => {
                        const status = userProgress[selectedSubject]?.[concept]
                        const isCompleted = status === 'completed'
                        const isInProgress = status === 'in_progress'
                        const isSelected = selectedTopic === concept

                        return (
                          <div
                            key={concept || cIdx}
                            onClick={() => handleSelectTopic(unit.name, concept)}
                            className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-center justify-between gap-3 group ${
                              isSelected
                                ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-xs ring-1 ring-[var(--accent)]/30'
                                : 'border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--surface-alt)]'
                            }`}
                          >
                            <div className="flex items-center gap-3 min-w-0">
                              <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
                                isCompleted
                                  ? 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400'
                                  : isInProgress
                                  ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400'
                                  : 'bg-[var(--surface-alt)] text-[var(--text-faint)] border border-[var(--border)]'
                              }`}>
                                {isCompleted ? <CheckCircle2 size={16} /> : isInProgress ? <Clock size={16} /> : <Circle size={14} />}
                              </div>
                              <div className="min-w-0">
                                <span className="font-semibold text-xs sm:text-sm text-[var(--text)] group-hover:text-[var(--accent)] transition-colors truncate block">
                                  {concept}
                                </span>
                              </div>
                            </div>

                            {/* Status Badge */}
                            <div className="shrink-0">
                              {isCompleted ? (
                                <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20">
                                  Completed
                                </span>
                              ) : isInProgress ? (
                                <span className="px-2 py-0.5 rounded-md text-[11px] font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/20">
                                  In Progress
                                </span>
                              ) : (
                                <span className="px-2 py-0.5 rounded-md text-[11px] font-medium text-[var(--text-faint)] group-hover:text-[var(--accent)]">
                                  Select →
                                </span>
                              )}
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )
              })
            )}
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          STEP 3: CHOOSE LEARNING METHOD
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentStep === 3 && (
        <div className="space-y-6 animate-in fade-in duration-200 max-w-4xl mx-auto">
          {/* Header & Back Button */}
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]/70">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Button variant="ghost" size="sm" onClick={() => setCurrentStep(2)} className="gap-1 px-2.5">
                  <ArrowLeft size={14} /> Change Topic
                </Button>
                <span className="text-xs font-bold text-[var(--text-faint)]">·</span>
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">{selectedSubject}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text)]">Step 3: Choose Learning Method</h2>
              <p className="text-sm text-[var(--text-soft)] mt-0.5">
                How would you like to master <strong className="text-[var(--text)]">"{selectedTopic}"</strong> today?
              </p>
            </div>
          </div>

          {/* Active Topic Banner */}
          <div className="p-4 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-between gap-3">
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-0.5">
                Selected Topic
              </div>
              <div className="font-extrabold text-base sm:text-lg text-[var(--text)]">
                {selectedTopic}
              </div>
              {selectedUnit && (
                <div className="text-xs text-[var(--text-soft)] mt-0.5">
                  Unit: {selectedUnit}
                </div>
              )}
            </div>
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center shrink-0">
              <GraduationCap size={20} />
            </div>
          </div>

          {/* 5 Distinct Learning Methods */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            {LEARNING_METHODS.map((m) => {
              const Icon = m.icon
              const isSelected = selectedMethod.id === m.id

              return (
                <div
                  key={m.id}
                  onClick={() => handleSelectMethod(m)}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer flex flex-col justify-between group ${
                    isSelected
                      ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm ring-2 ring-[var(--accent)]/30'
                      : 'border-[var(--border)] bg-[var(--surface)] hover:border-[var(--accent)] hover:shadow-xs'
                  }`}
                >
                  <div className="flex items-start gap-3.5 mb-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                      isSelected
                        ? 'bg-[var(--accent)] text-white shadow-xs'
                        : 'bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)] group-hover:text-[var(--accent)]'
                    }`}>
                      <Icon size={20} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-bold text-base text-[var(--text)] leading-snug">{m.title}</h3>
                        {isSelected && <Check size={16} className="text-[var(--accent)]" />}
                      </div>
                      <p className="text-xs text-[var(--text-soft)] font-medium mt-0.5">{m.subtitle}</p>
                    </div>
                  </div>

                  <p className="text-xs leading-relaxed text-[var(--text-soft)] mb-3">
                    {m.description}
                  </p>

                  <div className="flex items-center justify-between pt-2 border-t border-[var(--border)]/70 text-xs">
                    <span className="font-semibold text-[var(--accent)]">{m.badge}</span>
                    <span className={`font-bold flex items-center gap-1 ${isSelected ? 'text-[var(--accent)]' : 'text-[var(--text-faint)]'}`}>
                      {isSelected ? 'Selected' : 'Select'}
                    </span>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Bottom Actions */}
          <div className="flex items-center justify-between pt-4 border-t border-[var(--border)]">
            <Button variant="secondary" onClick={() => setCurrentStep(2)} className="gap-2">
              <ArrowLeft size={16} /> Back to Topics
            </Button>
            <Button size="lg" onClick={handleStartLearning} className="gap-2 px-6">
              Start Learning <ArrowRight size={18} />
            </Button>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          STEP 4: START LEARNING (READING & INTERACTION)
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentStep === 4 && (
        <div className="space-y-5 animate-in fade-in duration-200 max-w-4xl mx-auto">
          {/* Header Navigation */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[var(--border)]/70">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Button variant="ghost" size="sm" onClick={() => setCurrentStep(3)} className="gap-1 px-2.5">
                  <ArrowLeft size={14} /> Back to Methods
                </Button>
                <span className="text-xs font-bold text-[var(--text-faint)]">·</span>
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">{selectedSubject}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text)]">Step 4: Study Concept</h2>
              <div className="text-xs sm:text-sm text-[var(--text-soft)] flex items-center gap-2 mt-0.5">
                <span>Topic: <strong className="text-[var(--text)]">{selectedTopic}</strong></span>
                <span>•</span>
                <span className="text-[var(--accent)] font-semibold">{selectedMethod.title}</span>
              </div>
            </div>

            <Button onClick={handleProceedToCheckUnderstanding} className="gap-2 shrink-0">
              Check Understanding <ChevronRight size={16} />
            </Button>
          </div>

          {/* Clean Lesson Reading Container */}
          <div className="rounded-3xl border border-[var(--border)] bg-[var(--surface)] p-6 sm:p-8 shadow-xs min-h-[350px]">
            {lessonLoading ? (
              <div className="py-16 text-center space-y-4">
                <Loader2 size={32} className="animate-spin text-[var(--accent)] mx-auto" />
                <div className="font-bold text-base text-[var(--text)]">
                  Your Personal AI Tutor is preparing your lesson…
                </div>
                <p className="text-xs sm:text-sm text-[var(--text-soft)] max-w-md mx-auto">
                  Aligning syllabus modules, structuring clear explanations, and highlighting exam-scoring takeaways.
                </p>
              </div>
            ) : lessonError ? (
              <div className="py-12 px-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center space-y-4 my-auto">
                <div className="w-12 h-12 rounded-full bg-rose-500/20 text-rose-500 flex items-center justify-center mx-auto">
                  <AlertCircle size={24} />
                </div>
                <div className="space-y-1">
                  <h4 className="font-bold text-base text-[var(--text)]">Learning Content Generation Interrupted</h4>
                  <p className="text-xs sm:text-sm text-[var(--text-soft)] max-w-md mx-auto">{lessonError}</p>
                </div>
                <Button variant="primary" onClick={handleStartLearning} className="gap-2 mx-auto">
                  <RefreshCw size={14} /> Retry Generation
                </Button>
              </div>
            ) : (
              <div ref={lessonScrollRef} className="space-y-6">
                {/* Lesson Body */}
                <FormattedContent text={lessonContent} />

                {/* Follow-up Q&A Stream */}
                {tutorQna.length > 0 && (
                  <div className="mt-8 pt-6 border-t border-[var(--border)] space-y-4">
                    <div className="text-xs font-bold uppercase tracking-wider text-[var(--accent)] flex items-center gap-1.5">
                      <Bot size={15} /> Tutor Clarifications
                    </div>
                    {tutorQna.map((item, qIdx) => {
                      if (item.role === 'error') {
                        return (
                          <div key={qIdx} className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-600 dark:text-rose-400 flex items-center justify-between gap-3 mr-6">
                            <div className="flex items-center gap-2">
                              <AlertCircle size={15} className="shrink-0" />
                              <span>{item.text}</span>
                            </div>
                            <button
                              onClick={() => handleSendFollowUp(item.query)}
                              className="px-2.5 py-1 rounded-lg bg-rose-500/20 hover:bg-rose-500/30 text-rose-700 dark:text-rose-300 font-bold flex items-center gap-1 cursor-pointer transition-colors shrink-0"
                            >
                              <RefreshCw size={12} /> Retry
                            </button>
                          </div>
                        )
                      }

                      return (
                        <div key={qIdx} className={`p-4 rounded-2xl text-sm leading-relaxed ${
                          item.role === 'user'
                            ? 'bg-[var(--accent-soft)] text-[var(--text)] ml-6 font-medium'
                            : 'bg-[var(--surface-alt)] border border-[var(--border)] mr-6'
                        }`}>
                          <div className="text-[11px] font-bold text-[var(--text-soft)] mb-1">
                            {item.role === 'user' ? 'You asked:' : 'Tutor explained:'}
                          </div>
                          <FormattedContent text={item.text} />
                        </div>
                      )
                    })}
                  </div>
                )}

                {followUpLoading && (
                  <div className="flex items-center gap-2.5 p-3 rounded-xl bg-[var(--surface-alt)] text-xs text-[var(--text-soft)]">
                    <Loader2 size={14} className="animate-spin text-[var(--accent)]" />
                    <span>Tutor is explaining…</span>
                  </div>
                )}

                {/* Quick Action Chips & Input Container */}
                <div className="mt-6 pt-5 border-t border-[var(--border)]/70 space-y-3">
                  <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                    <span className="text-[11px] font-bold text-[var(--text-faint)] uppercase tracking-wider shrink-0 mr-1">
                      Quick Actions:
                    </span>
                    {QUICK_ACTIONS.map((action, aIdx) => (
                      <button
                        key={aIdx}
                        type="button"
                        onClick={() => handleSendFollowUp(action.query)}
                        disabled={followUpLoading}
                        className="px-3 py-1.5 rounded-full bg-[var(--surface-alt)] hover:bg-[var(--accent-soft)] hover:text-[var(--accent)] border border-[var(--border)] text-[var(--text)] font-medium text-xs whitespace-nowrap transition-all cursor-pointer shrink-0 disabled:opacity-50"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>

                  {/* Ask a Follow-up Question to Tutor */}
                  <form onSubmit={handleSendFollowUp} className="flex items-center gap-2">
                    <input
                      type="text"
                      value={followUpInput}
                      onChange={(e) => setFollowUpInput(e.target.value)}
                      placeholder={`Ask tutor for clarification on ${selectedTopic}…`}
                      className="flex-1 px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]"
                      disabled={followUpLoading}
                    />
                    <Button type="submit" disabled={!followUpInput.trim() || followUpLoading} className="px-5 py-3">
                      <Send size={15} />
                    </Button>
                  </form>
                </div>
              </div>
            )}
          </div>

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between pt-2">
            <Button variant="secondary" onClick={() => setCurrentStep(3)} className="gap-2">
              <ArrowLeft size={16} /> Choose Another Method
            </Button>
            <Button size="lg" onClick={handleProceedToCheckUnderstanding} className="gap-2 px-6">
              Next: Check Understanding <ArrowRight size={18} />
            </Button>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          STEP 5: CHECK UNDERSTANDING
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentStep === 5 && (
        <div className="space-y-6 animate-in fade-in duration-200 max-w-3xl mx-auto">
          {/* Header & Back Button */}
          <div className="flex items-center justify-between pb-2 border-b border-[var(--border)]/70">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <Button variant="ghost" size="sm" onClick={() => setCurrentStep(4)} className="gap-1 px-2.5">
                  <ArrowLeft size={14} /> Back to Lesson
                </Button>
                <span className="text-xs font-bold text-[var(--text-faint)]">·</span>
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">{selectedSubject}</span>
              </div>
              <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text)]">Step 5: Check Understanding</h2>
              <p className="text-sm text-[var(--text-soft)] mt-0.5">
                Answer the question below to test your mastery of <strong className="text-[var(--text)]">"{selectedTopic}"</strong>.
              </p>
            </div>
          </div>

          {/* Question Card */}
          <div className="p-6 rounded-3xl border border-[var(--border)] bg-[var(--surface)] shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20 flex items-center gap-1.5">
                <HelpCircle size={14} /> Knowledge Check
              </span>
              <button
                onClick={handleProceedToCheckUnderstanding}
                disabled={quizLoading}
                className="text-xs font-semibold text-[var(--text-soft)] hover:text-[var(--accent)] flex items-center gap-1 cursor-pointer"
                title="Generate another question"
              >
                <RefreshCw size={12} /> Try New Question
              </button>
            </div>

            {quizLoading ? (
              <div className="py-8 text-center text-sm text-[var(--text-soft)] flex items-center justify-center gap-2">
                <Loader2 size={16} className="animate-spin text-[var(--accent)]" />
                <span>Generating a targeted question for {selectedTopic}…</span>
              </div>
            ) : quizError ? (
              <div className="p-5 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-center space-y-3">
                <p className="text-xs sm:text-sm text-rose-600 dark:text-rose-400 font-medium">{quizError}</p>
                <Button variant="secondary" size="sm" onClick={handleProceedToCheckUnderstanding} className="gap-1.5 mx-auto">
                  <RefreshCw size={13} /> Retry Generating Question
                </Button>
              </div>
            ) : (
              <div className="text-base sm:text-lg font-bold text-[var(--text)] leading-relaxed">
                <FormattedContent text={quizQuestion} />
              </div>
            )}

            {/* Answer Input */}
            <form onSubmit={handleSubmitQuizAnswer} className="space-y-3 pt-3 border-t border-[var(--border)]/70">
              <label htmlFor="answer-input" className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)]">
                Your Answer
              </label>
              <textarea
                id="answer-input"
                rows={4}
                value={studentAnswer}
                onChange={(e) => setStudentAnswer(e.target.value)}
                placeholder="Type your explanation or answer in your own words here…"
                className="w-full p-4 rounded-2xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm text-[var(--text)] focus:outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] resize-y leading-relaxed"
                disabled={answerEvaluating}
              />
              <div className="flex items-center justify-between">
                <span className="text-xs text-[var(--text-faint)]">
                  Take your time. Explain concepts, formulas, or steps clearly.
                </span>
                <Button
                  type="submit"
                  disabled={!studentAnswer.trim() || answerEvaluating}
                  className="gap-2"
                >
                  {answerEvaluating && <Loader2 size={14} className="animate-spin" />}
                  <span>{answerEvaluating ? 'Evaluating…' : 'Submit Answer'}</span>
                </Button>
              </div>
            </form>

            {/* Evaluation Error */}
            {evalError && (
              <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-xs text-rose-600 dark:text-rose-400 flex items-center justify-between gap-3 mt-4">
                <div className="flex items-center gap-2">
                  <AlertCircle size={15} className="shrink-0" />
                  <span>{evalError}</span>
                </div>
                <Button size="sm" onClick={handleSubmitQuizAnswer} className="gap-1">
                  <RefreshCw size={12} /> Retry Evaluation
                </Button>
              </div>
            )}

            {/* AI Tutor Feedback */}
            {evaluationFeedback && (
              <div className="p-5 rounded-2xl bg-emerald-500/10 border border-emerald-500/25 space-y-3 mt-4 animate-in fade-in">
                <div className="flex items-center gap-2 text-xs font-bold text-emerald-700 dark:text-emerald-300">
                  <CheckCheck size={16} /> Tutor Evaluation & Feedback
                </div>
                <FormattedContent text={evaluationFeedback} />
              </div>
            )}
          </div>

          {/* Bottom Actions */}
          <div className="flex items-center justify-between pt-2">
            <Button variant="secondary" onClick={() => setCurrentStep(4)} className="gap-2">
              <ArrowLeft size={16} /> Back to Reading
            </Button>
            <Button size="lg" onClick={handleCompleteTopic} className="gap-2 px-6">
              Complete & Continue <ArrowRight size={18} />
            </Button>
          </div>
        </div>
      )}

      {/* ═══════════════════════════════════════════════════════════════════════
          STEP 6: COMPLETE AND CONTINUE
          ═══════════════════════════════════════════════════════════════════════ */}
      {currentStep === 6 && (
        <div className="space-y-6 animate-in fade-in duration-200 max-w-2xl mx-auto">
          {/* Completion Celebration Card */}
          <div className="p-8 sm:p-10 rounded-3xl border border-[var(--border)] bg-[var(--surface)] text-center shadow-sm space-y-6">
            <div className="w-20 h-20 rounded-3xl bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto border border-emerald-500/25 shadow-sm">
              <Award size={40} />
            </div>

            <div>
              <span className="px-3.5 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/20 inline-flex items-center gap-1.5 mb-2.5">
                <CheckCircle2 size={13} /> Topic Mastered
              </span>
              <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight">
                Great Job! Topic Completed
              </h2>
              <p className="text-sm sm:text-base text-[var(--text-soft)] mt-1.5 max-w-md mx-auto">
                You have successfully studied and verified your understanding of <strong className="text-[var(--text)]">"{selectedTopic}"</strong> in <strong className="text-[var(--text)]">{selectedSubject}</strong>.
              </p>
            </div>

            {/* Subject Progress Summary Card */}
            <div className="p-5 rounded-2xl bg-[var(--surface-alt)] border border-[var(--border)] text-left space-y-3">
              <div className="flex items-center justify-between text-xs font-bold uppercase tracking-wider text-[var(--text-soft)]">
                <span>{selectedSubject} Progress</span>
                <span className="text-[var(--accent)]">{currentSubjectStats.percent}% Complete</span>
              </div>

              <div className="w-full h-2.5 bg-[var(--surface)] rounded-full overflow-hidden border border-[var(--border)]">
                <div
                  className="h-full bg-[var(--accent)] rounded-full transition-all duration-500"
                  style={{ width: `${currentSubjectStats.percent}%` }}
                />
              </div>

              <div className="grid grid-cols-3 gap-2 pt-2 text-center">
                <div className="p-2.5 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-lg font-extrabold text-emerald-600 dark:text-emerald-400">{currentSubjectStats.completed}</div>
                  <div className="text-[11px] font-semibold text-[var(--text-soft)]">Topics Completed</div>
                </div>
                <div className="p-2.5 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-lg font-extrabold text-amber-500">{currentSubjectStats.remaining}</div>
                  <div className="text-[11px] font-semibold text-[var(--text-soft)]">Topics Remaining</div>
                </div>
                <div className="p-2.5 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                  <div className="text-lg font-extrabold text-[var(--text)]">{currentSubjectStats.total}</div>
                  <div className="text-[11px] font-semibold text-[var(--text-soft)]">Total in Syllabus</div>
                </div>
              </div>
            </div>

            {/* Clear Next Actions */}
            <div className="flex flex-col sm:flex-row gap-3 pt-2">
              <Button
                size="lg"
                onClick={handleContinueNextTopic}
                className="flex-1 gap-2 py-3.5"
              >
                <span>Continue to Next Topic</span>
                <ArrowRight size={16} />
              </Button>
              <Button
                variant="secondary"
                size="lg"
                onClick={handleReviseCurrentTopic}
                className="gap-2 py-3.5"
              >
                <RotateCcw size={15} />
                <span>Revise this Topic</span>
              </Button>
            </div>

            <div>
              <button
                onClick={handleChooseAnotherSubject}
                className="text-xs font-bold text-[var(--text-soft)] hover:text-[var(--accent)] transition-colors cursor-pointer"
              >
                ← Return to Subject Selection
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Syllabus Upload / View Modal */}
      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </div>
  )
}
