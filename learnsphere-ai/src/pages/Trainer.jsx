import { useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { PageHead, Badge, Button } from '../components/ui/Primitives.jsx'
import { studyTechniques } from '../data/mockData.js'
import { getDynamicSubjects, getDynamicChapters } from '../data/syllabusData.js'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import { ChevronRight, ChevronDown, ArrowLeft, Send, BookOpen, Target, Sparkles, Zap, Flame, Award, Loader2 } from 'lucide-react'

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
  const { user, profile, syllabusData, recordActivity, streakDays } = useApp()
  const location = useLocation()
  const activeProfile = { ...user, ...profile }

  const subjects = getDynamicSubjects(activeProfile, syllabusData)
  const [selectedSubject, setSelectedSubject] = useState(subjects[0] || 'Physics')
  const [expandedChapter, setExpandedChapter] = useState(null)
  const [selectedConcept, setSelectedConcept] = useState(null)
  
  const [selectedMethod, setSelectedMethod] = useState(STUDY_METHODS[0])
  const [selectedTechnique, setSelectedTechnique] = useState(studyTechniques[0])

  // Phase: 'setup' | 'method_picker' | 'session'
  const [phase, setPhase] = useState('setup')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loadingReply, setLoadingReply] = useState(false)
  const scrollRef = useRef(null)

  const chapters = getDynamicChapters(selectedSubject, activeProfile, syllabusData)

  // Handle location state navigation from MisconceptionMap
  useEffect(() => {
    if (location.state?.concept) {
      if (location.state.subject && subjects.includes(location.state.subject)) {
        setSelectedSubject(location.state.subject)
      }
      setSelectedConcept(location.state.concept)
      setPhase('method_picker')
    }
  }, [location.state])

  useEffect(() => {
    if (!subjects.includes(selectedSubject)) {
      setSelectedSubject(subjects[0] || 'Physics')
    }
  }, [subjects, selectedSubject])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loadingReply])

  const startSession = (method, technique) => {
    const m = method || selectedMethod
    const t = technique || selectedTechnique
    setSelectedMethod(m)
    setSelectedTechnique(t)

    // Record activity & update streak!
    recordActivity('trainer', `Studied "${selectedConcept}" in ${selectedSubject} (${m.name})`, {
      subject: selectedSubject,
      concept: selectedConcept
    })

    const targetContext = activeProfile?.level === 'college' ? `Semester ${activeProfile?.semester || 5}` : `Class ${activeProfile?.grade_level || activeProfile?.classLevel || 12}`

    const teachText = `📚 **Personal AI Trainer Initialized (${targetContext})**:\n\n` +
      `• **Subject**: ${selectedSubject}\n` +
      `• **Target Topic**: ${selectedConcept}\n` +
      `• **Strategy**: ${m.name}\n\n` +
      `Welcome! Today we are focusing on mastering **"${selectedConcept}"** to help you achieve >90% marks in your exams. Ask me any question or explain your understanding below!`

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
        concept: selectedConcept,
        study_method: selectedMethod?.name || selectedMethod?.id,
        level: activeProfile?.level || 'college',
        semester: activeProfile?.semester || 5,
        class_level: activeProfile?.grade_level || activeProfile?.classLevel || 12,
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

  return (
    <>
      <PageHead
        title="Personal AI Trainer & Exam Maximizer"
        subtitle="Classified subjects from your syllabus. Pick topics and study strategies tailored for exam high scores."
        action={
          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-amber-500/10 text-amber-600 border border-amber-500/20 rounded-full text-xs font-bold flex items-center gap-1">
              <Flame size={14} className="text-amber-500 animate-bounce" /> {streakDays} Day Streak
            </span>
          </div>
        }
      />

      <div className="h-[calc(100vh-220px)] min-h-[580px] border border-[var(--border)] rounded-xl overflow-hidden bg-[var(--surface)] flex">

        {/* LEFT: Dynamic Syllabus Tree (Subject → Chapter → Concept) */}
        <div className="w-[240px] shrink-0 border-r border-[var(--border)] flex flex-col overflow-hidden">
          <div className="p-3.5 border-b border-[var(--border)]">
            <div className="text-[10.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2">Classified Subjects</div>
            <div className="flex flex-col gap-1 max-h-[160px] overflow-y-auto">
              {subjects.map((s) => (
                <button
                  key={s}
                  onClick={() => { setSelectedSubject(s); setExpandedChapter(null); setSelectedConcept(null) }}
                  className={`text-left px-2.5 py-1.5 rounded-lg text-[12.5px] font-semibold transition-colors ${
                    selectedSubject === s
                      ? 'bg-[var(--accent-soft)] text-[var(--accent)] font-bold'
                      : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-2">
            <div className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-faint)] px-1.5 py-2">Syllabus Chapters & Topics</div>
            {chapters.map((ch, idx) => (
              <div key={ch.name || idx}>
                <button
                  onClick={() => setExpandedChapter(expandedChapter === ch.name ? null : ch.name)}
                  className="w-full flex items-center justify-between px-2 py-2 rounded-lg text-[12px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors"
                >
                  <span className="text-left leading-tight line-clamp-1">{ch.name}</span>
                  <ChevronDown size={12} className={`shrink-0 transition-transform ${expandedChapter === ch.name ? 'rotate-180' : ''}`} />
                </button>
                {expandedChapter === ch.name && (
                  <div className="ml-2 mb-1">
                    {ch.concepts.map((concept) => (
                      <button
                        key={concept}
                        onClick={() => { setSelectedConcept(concept); setPhase('method_picker') }}
                        className={`w-full text-left px-2.5 py-1.5 rounded-lg text-[11.5px] transition-colors mb-0.5 ${
                          selectedConcept === concept
                            ? 'bg-[var(--accent)] text-white font-semibold'
                            : 'text-[var(--text-faint)] hover:bg-[var(--surface-alt)] hover:text-[var(--text)]'
                        }`}
                      >
                        {concept}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* CENTER: Setup prompt → Study Method picker → AI Chat */}
        <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
          {phase === 'setup' && (
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="text-center max-w-[360px]">
                <div className="text-4xl mb-4">📖</div>
                <div className="text-[16px] font-extrabold mb-2">Select a topic from your syllabus</div>
                <div className="text-sm text-[var(--text-soft)] mb-5">
                  Choose a classified subject and chapter on the left, then select your exam study strategy to begin.
                </div>
                <div className="flex flex-col gap-2.5 text-[12.5px] text-[var(--text-faint)] text-left bg-[var(--surface-alt)] p-4 rounded-xl">
                  <div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] font-bold">1</span> Pick subject from your syllabus</div>
                  <div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] font-bold">2</span> Expand chapter & select a topic</div>
                  <div className="flex items-center gap-2"><span className="w-5 h-5 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center text-[10px] font-bold">3</span> Choose High-Score Exam Strategy</div>
                </div>
              </div>
            </div>
          )}

          {/* Strategy Picker (shown after topic selected) */}
          {phase === 'method_picker' && selectedConcept && (
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">Selected Topic</div>
                <div className="text-lg font-extrabold text-[var(--accent)]">{selectedConcept}</div>
                <div className="text-xs text-[var(--text-soft)]">{selectedSubject} · Syllabus Topic</div>
              </div>

              <div>
                <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] mb-3">1. Choose Exam Study Strategy</div>
                <div className="grid md:grid-cols-2 gap-3 mb-6">
                  {STUDY_METHODS.map((m) => (
                    <button
                      key={m.id}
                      onClick={() => setSelectedMethod(m)}
                      className={`text-left p-4 rounded-xl border transition-all ${
                        selectedMethod.id === m.id
                          ? 'border-[var(--accent)] bg-[var(--accent-soft)] shadow-sm'
                          : 'border-[var(--border)] hover:border-[var(--accent-dim)]'
                      }`}
                    >
                      <div className="font-bold text-[13.5px] mb-1">{m.name}</div>
                      <div className="text-[11.5px] text-[var(--text-soft)] mb-2 leading-relaxed">{m.description}</div>
                      <Badge tone="accent">{m.tagline}</Badge>
                    </button>
                  ))}
                </div>

                <div className="flex justify-end pt-2">
                  <Button onClick={() => startSession(selectedMethod, selectedTechnique)} className="flex items-center gap-2">
                    Start Learning Session <ChevronRight size={15} />
                  </Button>
                </div>
              </div>
            </div>
          )}

          {/* Chat session */}
          {phase === 'session' && (
            <div className="flex-1 flex flex-col min-h-0 overflow-hidden">
              <div className="px-4 py-2.5 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-alt)]/50">
                <div>
                  <div className="text-[13px] font-bold">{selectedConcept}</div>
                  <div className="text-[11px] text-[var(--text-faint)]">{selectedSubject} · {selectedMethod.name}</div>
                </div>
                <button onClick={() => setPhase('method_picker')} className="text-[11.5px] font-semibold text-[var(--text-faint)] hover:text-[var(--accent)] flex items-center gap-1 border border-[var(--border)] px-2.5 py-1 rounded-lg">
                  <ArrowLeft size={11} /> Switch strategy
                </button>
              </div>

              <div ref={scrollRef} className="flex-1 overflow-y-auto p-5 flex flex-col gap-4">
                {messages.map((m, i) => (
                  <div key={i} className={`max-w-[80%] px-4 py-3 rounded-xl text-[13.5px] leading-relaxed whitespace-pre-line ${
                    m.role === 'user'
                      ? 'bg-[var(--accent)] text-white self-end rounded-br-[3px]'
                      : 'bg-[var(--surface-alt)] self-start rounded-bl-[3px]'
                  }`}>
                    {m.text}
                  </div>
                ))}
                {loadingReply && (
                  <div className="bg-[var(--surface-alt)] self-start rounded-bl-[3px] px-4 py-3 rounded-xl text-[13.5px] text-[var(--text-soft)] flex items-center gap-2 animate-pulse">
                    <Loader2 size={16} className="animate-spin text-[var(--accent)]" />
                    <span>AI Personal Trainer is analyzing your question...</span>
                  </div>
                )}
              </div>

              <div className="p-4 border-t border-[var(--border)] space-y-2.5">
                {/* Quick Action Exam Booster Prompts */}
                <div className="flex items-center gap-1.5 overflow-x-auto pb-1 text-xs">
                  <span className="font-bold text-[var(--text-faint)] uppercase text-[10px] shrink-0 mr-1">Quick Actions:</span>
                  {[
                    { label: '🎯 Exam Marking Strategy', prompt: `Give me the exact examiner marking criteria, mandatory technical terms, and common traps for "${selectedConcept}" to score maximum marks.` },
                    { label: '📝 Generate Practice Problem', prompt: `Generate a high-yield exam-style practice numerical/conceptual problem for "${selectedConcept}" with step-by-step solution breakdown.` },
                    { label: '⚡ Key Formulas & Derivation', prompt: `List the core standard equations, SI units, and step-by-step mathematical derivation for "${selectedConcept}".` },
                    { label: '💡 Feynman Analogy Breakdown', prompt: `Explain "${selectedConcept}" using the Feynman technique with a simple intuitive real-world analogy.` }
                  ].map(({ label, prompt }) => (
                    <button
                      key={label}
                      disabled={loadingReply}
                      onClick={() => sendMessage(prompt)}
                      className="px-2.5 py-1 rounded-full border border-[var(--border-strong)] bg-[var(--surface-alt)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition-all shrink-0 font-semibold text-[11.5px]"
                    >
                      {label}
                    </button>
                  ))}
                </div>

                <div className="flex gap-2">
                  <input
                    value={input}
                    disabled={loadingReply}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder={loadingReply ? "AI Trainer is analyzing..." : "Ask a question or type your answer to test your knowledge..."}
                    className="flex-1 border border-[var(--border-strong)] rounded-lg px-3.5 py-[10px] text-[13.5px] bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)] disabled:opacity-50"
                  />
                  <button onClick={() => sendMessage()} disabled={loadingReply} className="px-4 py-[10px] rounded-lg bg-[var(--accent)] text-white text-[13.5px] font-semibold hover:bg-[var(--accent-dim)] disabled:opacity-50 flex items-center gap-2 shrink-0">
                    {loadingReply ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </>
  )
}

