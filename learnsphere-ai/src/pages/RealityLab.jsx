import { useState, useEffect } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { getActiveValidatedCurriculum, getDynamicScenarios, getDynamicChapters } from '../data/syllabusData.js'
import { useApp } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import { CheckCircle2, XCircle, FlaskConical, Globe, Shuffle, Eye, BookOpen, Layers, UploadCloud, Loader2 } from 'lucide-react'

const difficultyTone = { Easy: 'success', Medium: 'warning', Hard: 'error' }

function analyseAnswer(answer, concepts) {
  const lower = answer.toLowerCase()
  return (concepts || []).map((c) => {
    const keywords = c.concept.toLowerCase().split(/[\s/,()]+/).filter((w) => w.length > 3)
    const hit = keywords.some((kw) => lower.includes(kw))
    return { ...c, covered: hit }
  })
}

function QualityMeter({ pct }) {
  const color = pct >= 70 ? 'var(--success)' : pct >= 45 ? 'var(--warning)' : 'var(--error)'
  const label = pct >= 80 ? 'Excellent' : pct >= 65 ? 'Good' : pct >= 45 ? 'Partial' : 'Needs work'
  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1.5">
        <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)]">Application quality</div>
        <div className="text-[13.5px] font-extrabold" style={{ color }}>{pct}% · {label}</div>
      </div>
      <div className="h-2.5 bg-[var(--surface-alt)] rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  )
}

export default function RealityLab() {
  const { user, syllabusData, recordActivity } = useApp()
  const activeProfile = user
  const isCollege = activeProfile?.level === 'college'

  const activeCurriculum = getActiveValidatedCurriculum(activeProfile, syllabusData)
  const subjects = activeCurriculum.subjectNames
  const hasValidCurriculum = activeCurriculum.isValid && subjects.length > 0
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)

  const [activeSubject, setActiveSubject] = useState(subjects[0] || '')
  const [activeDifficulty, setActiveDifficulty] = useState('All')
  const [activeModule, setActiveModule] = useState('All')
  const [scenarioIdx, setScenarioIdx] = useState(0)
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState(null)
  const [showModel, setShowModel] = useState(false)
  const [showAnswer, setShowAnswer] = useState(false)
  const [isEvaluating, setIsEvaluating] = useState(false)

  useEffect(() => {
    if (subjects.length > 0 && !subjects.includes(activeSubject)) {
      setActiveSubject(subjects[0])
      setActiveModule('All')
      setScenarioIdx(0)
      resetState()
    } else if (subjects.length === 0 && activeSubject) {
      setActiveSubject('')
      setActiveModule('All')
      setScenarioIdx(0)
      resetState()
    }
  }, [subjects, activeSubject])

  const modules = getDynamicChapters(activeSubject, activeProfile, syllabusData)
  const scenarios = getDynamicScenarios(activeSubject, activeProfile, syllabusData, activeDifficulty, activeModule)
  const scenario = scenarios[scenarioIdx]

  const switchSubject = (sub) => {
    setActiveSubject(sub)
    setActiveModule('All')
    setScenarioIdx(0)
    resetState()
  }

  const switchDifficulty = (diff) => {
    setActiveDifficulty(diff)
    setScenarioIdx(0)
    resetState()
  }

  const switchModule = (mod) => {
    setActiveModule(mod)
    setScenarioIdx(0)
    resetState()
  }

  const resetState = () => {
    setAnswer('')
    setResult(null)
    setShowModel(false)
    setShowAnswer(false)
    setIsEvaluating(false)
  }

  const handleAnalyse = async () => {
    if (!answer.trim() || !scenario) return
    setIsEvaluating(true)
    try {
      const res = await api.evaluateRealityLab(scenario.title, scenario.title, answer, activeSubject)
      if (res && res.success && res.evaluation) {
        const ev = res.evaluation
        const pct = ev.score ?? 0
        setResult({
          qualityPct: pct,
          feedback: ev.feedback,
          concepts: (scenario.expectedConcepts || []).map(c => ({
            ...c,
            covered: (ev.strengths || []).some(s => s.toLowerCase().includes(c.concept.toLowerCase())) || pct >= 70
          }))
        })
        recordActivity('lab', `Completed Reality Lab scenario: ${scenario?.title} (${pct}%)`, { score: pct, subject: activeSubject })
      } else {
        const analysed = analyseAnswer(answer, scenario.expectedConcepts)
        const required = analysed.filter((c) => c.required)
        const coveredRequired = required.filter((c) => c.covered).length
        const pct = Math.round((coveredRequired / Math.max(required.length, 1)) * 100)
        setResult({ concepts: analysed, qualityPct: pct })
        recordActivity('lab', `Completed Reality Lab scenario: ${scenario?.title} (${pct}%)`, { score: pct, subject: activeSubject })
      }
    } catch {
      const analysed = analyseAnswer(answer, scenario.expectedConcepts)
      const required = analysed.filter((c) => c.required)
      const coveredRequired = required.filter((c) => c.covered).length
      const pct = Math.round((coveredRequired / Math.max(required.length, 1)) * 100)
      setResult({ concepts: analysed, qualityPct: pct })
    } finally {
      setIsEvaluating(false)
    }
  }

  const handleNext = () => {
    if (!scenarios.length) return
    setScenarioIdx((i) => (i + 1) % scenarios.length)
    resetState()
  }

  const handleRandom = () => {
    if (!scenarios.length) return
    const candidates = scenarios.map((_, i) => i).filter((i) => i !== scenarioIdx)
    setScenarioIdx(candidates[Math.floor(Math.random() * candidates.length)] ?? 0)
    resetState()
  }

  if (!hasValidCurriculum) {
    return (
      <>
        <PageHead
          title="Knowledge-to-Reality Lab"
          subtitle="Apply your textbook knowledge to explain real-world engineering & everyday phenomena."
        />
        <CurriculumReviewNotice
          curriculum={activeCurriculum}
          featureName="Knowledge-to-Reality Lab"
          onOpenSyllabusModal={() => setIsSyllabusModalOpen(true)}
        />
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </>
    )
  }

  if (!scenario) return (
    <div className="p-8">
      <div className="flex gap-1.5 flex-wrap mb-5">
        {subjects.map((sub) => (
          <button key={sub} onClick={() => switchSubject(sub)} className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold border ${activeSubject === sub ? 'bg-[var(--accent)] text-white border-[var(--accent)]' : 'border-[var(--border-strong)] text-[var(--text-soft)]'}`}>{sub}</button>
        ))}
      </div>
      <div className="p-6 border border-[var(--border)] rounded-xl text-center text-[var(--text-soft)]">No scenarios found for this filter. <button onClick={() => { setActiveDifficulty('All'); setActiveModule('All'); }} className="text-[var(--accent)] underline font-bold ml-1">Reset Filters</button></div>
      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </div>
  )

  return (
    <>
      <PageHead
        title="Knowledge-to-Reality Lab"
        subtitle="Apply your textbook knowledge to explain real-world engineering & everyday phenomena."
        action={
          <div className="flex items-center gap-2">
            <span className="text-[12px] text-[var(--text-faint)] font-semibold">{scenarioIdx + 1}/{scenarios.length}</span>
            <button onClick={handleNext} className="px-3 py-1.5 border border-[var(--border)] rounded-lg text-[12px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors">Next</button>
            <button onClick={handleRandom} className="flex items-center gap-1 px-3 py-1.5 border border-[var(--border)] rounded-lg text-[12px] font-semibold text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors">
              <Shuffle size={12} /> Random
            </button>
          </div>
        }
      />

      {/* Subject Tabs */}
      <div className="flex gap-1.5 flex-wrap mb-4">
        {subjects.map((sub) => (
          <button
            key={sub}
            onClick={() => switchSubject(sub)}
            className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold border transition-all ${
              activeSubject === sub
                ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
            }`}
          >
            {sub}
          </button>
        ))}
      </div>

      {/* Module & Difficulty Filter Bar */}
      <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-5 p-2 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Layers size={14} className="text-[var(--accent)] ml-1" />
          <span className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)]">Module:</span>
          <select
            value={activeModule}
            onChange={(e) => switchModule(e.target.value)}
            className="px-3 py-1 rounded-lg border border-[var(--border-strong)] text-[12px] font-semibold bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] max-w-[280px] truncate"
          >
            <option value="All">All Modules ({scenarios.length} total Qs)</option>
            {modules.map((m) => (
              <option key={m.name} value={m.name}>{m.name}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1">
          {[
            { id: 'All', label: 'All Modes' },
            { id: 'Easy', label: '🟢 Easy' },
            { id: 'Medium', label: '🟡 Medium' },
            { id: 'Hard', label: '🔴 Hard' }
          ].map(({ id, label }) => (
            <button
              key={id}
              onClick={() => switchDifficulty(id)}
              className={`px-2.5 py-1 rounded-md text-[11.5px] font-bold transition-all ${
                activeDifficulty === id
                  ? 'bg-[var(--surface)] text-[var(--text)] shadow-sm'
                  : 'text-[var(--text-faint)] hover:text-[var(--text-soft)]'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="max-w-[760px] space-y-4">
        {/* Scenario Header with Semester & Syllabus grounding */}
        <div className="relative overflow-hidden rounded-xl border border-[var(--border)] bg-gradient-to-br from-[var(--accent-soft)] to-[var(--surface-alt)] p-6">
          <div className="absolute top-4 right-5 opacity-8">
            <FlaskConical size={72} strokeWidth={1} />
          </div>
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <Globe size={13} className="text-[var(--accent)]" />
            <span className="text-[11px] font-bold uppercase tracking-wider text-[var(--accent)]">{scenario.context || "Industry Application"}</span>
            <span className="mx-1 text-[var(--border-strong)]">·</span>
            <Badge tone={difficultyTone[scenario.difficulty]}>{scenario.difficulty}</Badge>
            <Badge tone="accent">{scenario.semester || (activeProfile?.current_semester ? `Semester ${activeProfile.current_semester}` : 'Active Semester')}</Badge>
            <Badge tone="neutral">{scenario.subject || activeSubject}</Badge>
            {(scenario.syllabus_topic || scenario.chapter) && <Badge tone="neutral">{scenario.syllabus_topic || scenario.chapter}</Badge>}
          </div>
          <h2 className="text-[17px] font-extrabold leading-snug max-w-[540px] mb-2">{scenario.title}</h2>
          {scenario.practical_concept && (
            <p className="text-[13px] text-[var(--text-soft)] font-medium">
              <strong className="text-[var(--text)]">Practical Concept:</strong> {scenario.practical_concept}
            </p>
          )}
        </div>

        {/* Unsupported purely theoretical topic fallback */}
        {scenario.is_supported === false ? (
          <Card>
            <div className="p-4 bg-[var(--surface-alt)] border border-[var(--warning)] rounded-xl text-center">
              <p className="text-[13.5px] font-semibold text-[var(--text)] mb-2">
                ⚠️ {scenario.unsupported_message || "No suitable practical activity is defined for this specific theoretical topic in the uploaded syllabus."}
              </p>
              <p className="text-[12px] text-[var(--text-faint)] mb-4">
                Please select an applied engineering module or a practical/laboratory course from your Semester curriculum.
              </p>
              <Button onClick={handleNext}>Explore Next Module Activity</Button>
            </div>
          </Card>
        ) : (
          <>
            {/* 10-Field Practical Activity Blueprint Card */}
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={16} className="text-[var(--accent)]" />
                <h3 className="text-[13px] font-bold uppercase tracking-wider text-[var(--text-faint)]">
                  Practical Activity Blueprint
                </h3>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5 mb-4 text-[12.5px]">
                <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)]">
                  <span className="font-bold text-[var(--accent)] block mb-1">🛠️ Materials & Tools:</span>
                  <ul className="list-disc list-inside space-y-0.5 text-[var(--text-soft)]">
                    {(scenario.materials || ["Engineering Simulator", "Analytical Profiler"]).map((m, i) => (
                      <li key={i}>{m}</li>
                    ))}
                  </ul>
                </div>

                <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)]">
                  <span className="font-bold text-[var(--accent)] block mb-1">📋 Procedure:</span>
                  <ul className="list-decimal list-inside space-y-0.5 text-[var(--text-soft)]">
                    {(scenario.procedure || ["Step 1: Configure testbed", "Step 2: Measure metrics"]).map((p, i) => (
                      <li key={i}>{p}</li>
                    ))}
                  </ul>
                </div>
              </div>

              <div className="space-y-2.5 text-[12.5px]">
                {scenario.observation && (
                  <div className="p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                    <strong className="text-[var(--text)]">🔬 Expected Observation: </strong>
                    {scenario.observation}
                  </div>
                )}
                {scenario.theory_connection && (
                  <div className="p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                    <strong className="text-[var(--text)]">📐 Theory Connection: </strong>
                    {scenario.theory_connection}
                  </div>
                )}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                  {scenario.learning_outcome && (
                    <div className="p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                      <strong className="text-[var(--text)]">🎯 Learning Outcome: </strong>
                      {scenario.learning_outcome}
                    </div>
                  )}
                  {scenario.exam_relevance && (
                    <div className="p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                      <strong className="text-[var(--text)]">📝 Exam Relevance: </strong>
                      {scenario.exam_relevance}
                    </div>
                  )}
                </div>
              </div>
            </Card>

            {!result && !showAnswer ? (
              <>
                <Card>
                  <div className="text-[12px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2">Your Practical Explanation / Solution</div>
                  <textarea
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Explain this practical activity using academic concepts, formulas, and experimental reasoning from your semester syllabus…"
                    rows={5}
                    disabled={isEvaluating}
                    className="w-full border border-[var(--border-strong)] rounded-lg px-3.5 py-3 text-[13.5px] bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)] resize-none leading-relaxed"
                  />
                  <div className="flex items-center justify-between mt-3">
                    <button
                      onClick={() => setShowAnswer(true)}
                      className="flex items-center gap-1.5 text-[12px] text-[var(--text-faint)] hover:text-[var(--text-soft)] transition-colors font-semibold"
                    >
                      <Eye size={13} /> Show model solution directly
                    </button>
                    <Button onClick={handleAnalyse} disabled={!answer.trim() || isEvaluating}>
                      {isEvaluating ? <><Loader2 size={14} className="animate-spin" /> Evaluating with AI...</> : 'Analyse My Practical Solution'}
                    </Button>
                  </div>
                </Card>

                <Card>
                  <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2.5">Key Concepts Tested</div>
                  <div className="flex flex-wrap gap-2">
                    {(scenario.expectedConcepts || []).map((c, i) => (
                      <span key={i} className={`px-2.5 py-1 rounded-full text-[11.5px] font-semibold border ${
                        c.required
                          ? 'bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent-soft-strong)]'
                          : 'bg-[var(--surface-alt)] text-[var(--text-soft)] border-[var(--border)]'
                      }`}>
                        {c.concept}{!c.required && <span className="ml-1 opacity-60">· bonus</span>}
                      </span>
                    ))}
                  </div>
                </Card>
              </>
            ) : showAnswer && !result ? (
              <Card>
                <div className="flex items-center gap-2 mb-4">
                  <BookOpen size={15} className="text-[var(--accent)]" />
                  <div className="text-[12px] font-bold uppercase tracking-wider text-[var(--accent)]">Model Practical Solution</div>
                </div>
                <div className="text-[13.5px] leading-relaxed mb-5">{scenario.modelAnswer}</div>
                <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2.5">Key concepts covered</div>
                <div className="flex flex-wrap gap-2 mb-4">
                  {(scenario.expectedConcepts || []).filter(c => c.required).map((c, i) => (
                    <span key={i} className="px-2.5 py-1 rounded-full text-[11.5px] font-semibold border bg-[var(--accent-soft)] text-[var(--accent)] border-[var(--accent-soft-strong)]">
                      {c.concept}
                    </span>
                  ))}
                </div>
                <Button onClick={handleNext} className="w-full justify-center">Next Practical Activity</Button>
              </Card>
            ) : (
              <>
                <Card>
                  <QualityMeter pct={result.qualityPct} />
                  {result.feedback && (
                    <div className="p-3 mb-4 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-xs text-[var(--text-soft)]">
                      <span className="font-bold text-[var(--accent)] block mb-1">AI Evaluation & Engineering Assessment</span>
                      {result.feedback}
                    </div>
                  )}
                  <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-3">Concept coverage</div>
                  <div className="space-y-2 mb-5">
                    {result.concepts.map((c, i) => (
                      <div key={i} className={`flex items-start gap-2.5 px-3.5 py-2.5 rounded-lg border ${
                        c.covered ? 'border-[var(--border)] bg-[var(--success-soft)]' : 'border-[var(--border)] bg-[var(--surface-alt)]'
                      }`}>
                        {c.covered
                          ? <CheckCircle2 size={15} className="text-[var(--success)] shrink-0 mt-px" />
                          : <XCircle size={15} className="text-[var(--error)] shrink-0 mt-px" />
                        }
                        <div className="flex-1 min-w-0">
                          <span className="text-[13px] font-semibold">{c.concept}</span>
                          {!c.required && <span className="ml-2 text-[10.5px] text-[var(--text-faint)] font-medium">bonus</span>}
                        </div>
                      </div>
                    ))}
                  </div>

                  <div className="bg-[var(--surface-alt)] rounded-lg p-3.5 mb-4">
                    <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1.5">Your submitted solution</div>
                    <div className="text-[13px] leading-relaxed text-[var(--text-soft)]">{answer}</div>
                  </div>

                  {!showModel ? (
                    <button onClick={() => setShowModel(true)} className="text-[12.5px] font-semibold text-[var(--accent)] hover:opacity-70 transition-opacity">
                      Show full engineering model answer →
                    </button>
                  ) : (
                    <div className="border border-[var(--border)] rounded-lg p-3.5">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1.5">Model engineering solution</div>
                      <div className="text-[13.5px] leading-relaxed">{scenario.modelAnswer}</div>
                    </div>
                  )}
                </Card>

                <Button onClick={handleNext} className="w-full justify-center">Next Practical Activity</Button>
              </>
            )}
          </>
        )}
      </div>
      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </>
  )
}
