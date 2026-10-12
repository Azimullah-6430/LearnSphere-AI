import { useState, useEffect } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { getActiveValidatedCurriculum, getDynamicTransferQuestions, getDynamicChapters } from '../data/syllabusData.js'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import {
  ChevronRight, CheckCircle2, XCircle, Lightbulb, Target, Brain, Star,
  RotateCcw, BookOpen, Zap, Layers, UploadCloud
} from 'lucide-react'

function ScoreRing({ score, size = 88 }) {
  const r = (size - 10) / 2
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="8" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="8"
        strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.8s ease' }}
      />
    </svg>
  )
}

export default function KnowledgeChallenge() {
  const { user, syllabusData, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, subjectObjects } = useAuthoritativeCurriculum()
  const activeProfile = user
  const activeCurriculum = curriculum
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)

  const [phase, setPhase] = useState('intro') // 'intro' | 'question' | 'feedback' | 'done'
  const [activeSubject, setActiveSubject] = useState(subjects[0] || '')
  const [activeDifficulty, setActiveDifficulty] = useState('All')
  const [activeModule, setActiveModule] = useState('All')
  const [rounds, setRounds] = useState([])
  const [roundIdx, setRoundIdx] = useState(0)
  const [answer, setAnswer] = useState('')
  const [showHint, setShowHint] = useState(false)
  const [showAnswer, setShowAnswer] = useState(false)
  const [scores, setScores] = useState([])

  const currentSubjectObj = (subjectObjects || []).find(s =>
    typeof s === 'object' && (s.name === activeSubject || s.code === activeSubject || s.subject_id === activeSubject || s.id === activeSubject)
  ) || { name: activeSubject, code: '', subject_id: '' }

  const activeSubjectId = currentSubjectObj.subject_id || currentSubjectObj.id || currentSubjectObj.code || ''
  const activeCurriculumId = activeCurriculum?.syllabus_id || activeCurriculum?.syllabusId || activeCurriculum?.id || ''

  useEffect(() => {
    if (subjects.length > 0 && !subjects.includes(activeSubject)) {
      setActiveSubject(subjects[0])
      setActiveModule('All')
      setPhase('intro')
      setRounds([])
      setScores([])
    } else if (subjects.length === 0 && activeSubject) {
      setActiveSubject('')
      setActiveModule('All')
      setPhase('intro')
      setRounds([])
      setScores([])
    }
  }, [subjects, activeSubject])

  const effectiveCurriculum = activeCurriculum || syllabusData
  const modules = getDynamicChapters(activeSubject, activeProfile, effectiveCurriculum)
  const pool = getDynamicTransferQuestions(activeSubject, activeProfile, effectiveCurriculum, activeDifficulty, activeModule)
  const currentRound = rounds[roundIdx]

  const switchSubject = (sub) => {
    if (phase === 'intro') {
      setActiveSubject(sub)
      setActiveModule('All')
    }
  }

  const startSession = () => {
    const shuffled = [...pool].sort(() => Math.random() - 0.5).slice(0, Math.min(5, pool.length))
    setRounds(shuffled)
    setRoundIdx(0)
    setAnswer('')
    setShowHint(false)
    setShowAnswer(false)
    setScores([])
    setPhase('question')
    recordActivity('challenge', `Started Knowledge Challenge in ${activeSubject} (${activeDifficulty})`, {
      subject: activeSubject,
      subjectId: activeSubjectId,
      curriculumId: activeCurriculumId,
      difficulty: activeDifficulty
    })
  }

  const submitAnswer = async () => {
    const score = currentRound.transferScore || 85
    const roundSubmission = {
      round: currentRound.round || roundIdx + 1,
      score,
      answer,
      subject: activeSubject,
      subjectId: activeSubjectId,
      topicId: currentRound.id || currentRound.chapter || activeModule,
      question: currentRound.scenario || currentRound.question,
      correctAnswer: currentRound.modelAnswer || currentRound.correct_answer,
      explanation: currentRound.concept_explanation || currentRound.explanation,
      difficulty: currentRound.difficulty || activeDifficulty,
      timestamp: new Date().toISOString()
    }
    setScores((prev) => [...prev, roundSubmission])
    setPhase('feedback')

    try {
      await api.submitChallenge({
        subject: activeSubject,
        subject_id: activeSubjectId,
        subjectId: activeSubjectId,
        topic_id: roundSubmission.topicId,
        question: roundSubmission.question,
        student_answer: answer,
        correct_answer: roundSubmission.correctAnswer,
        explanation: roundSubmission.explanation,
        difficulty: roundSubmission.difficulty,
        score: score,
        total_questions: 100
      })
    } catch {}
  }

  const nextRound = () => {
    if (roundIdx + 1 >= rounds.length) {
      setPhase('done')
      const finalAvg = scores.length ? Math.round(scores.reduce((a, b) => a + b.score, 0) / scores.length) : 80
      recordActivity('challenge', `Completed Knowledge Challenge in ${activeSubject} (${finalAvg}%)`, {
        score: finalAvg,
        subject: activeSubject,
        subjectId: activeSubjectId,
        curriculumId: activeCurriculumId
      })
    } else {
      setRoundIdx((i) => i + 1)
      setAnswer('')
      setShowHint(false)
      setShowAnswer(false)
      setPhase('question')
    }
  }

  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b.score, 0) / scores.length) : 0
  const diffTone = { Easy: 'success', Medium: 'warning', Hard: 'error', Difficult: 'error' }

  return (
    <>
      <PageHead
        title="Knowledge Transfer Challenge"
        subtitle="Apply syllabus concepts to novel real-world engineering and scientific scenarios to test practical mastery."
      />

      {!hasValidCurriculum ? (
        <>
          <CurriculumReviewNotice
            curriculum={activeCurriculum}
            featureName="Knowledge Transfer Challenge"
            onOpenSyllabusModal={() => setIsSyllabusModalOpen(true)}
          />
          <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
        </>
      ) : (
        <>
          {/* Subject Tabs */}
          {phase !== 'done' && (
            <div className="flex gap-2 flex-wrap mb-5">
              {subjects.map((sub) => (
                <button
                  key={sub}
                  onClick={() => switchSubject(sub)}
                  disabled={phase !== 'intro'}
                  className={`px-4 py-2 rounded-xl text-xs md:text-sm font-bold border transition-all cursor-pointer disabled:opacity-50 ${
                    activeSubject === sub
                      ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-xs'
                      : 'border-[var(--border-strong)] bg-[var(--surface)] text-[var(--text-soft)] hover:border-[var(--accent)]'
                  }`}
                >
                  {sub}
                </button>
              ))}
            </div>
          )}

          {/* Module & Difficulty Filter Bar */}
          {phase === 'intro' && (
            <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-4 mb-7 p-3 bg-[var(--surface)] rounded-2xl border border-[var(--border)] max-w-3xl shadow-xs">
              {/* Module Selector */}
              <div className="flex items-center gap-2.5">
                <Layers size={16} className="text-[var(--accent)] ml-1" />
                <span className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)]">Module:</span>
                <select
                  value={activeModule}
                  onChange={(e) => setActiveModule(e.target.value)}
                  className="px-3.5 py-1.5 rounded-xl border border-[var(--border-strong)] text-xs md:text-sm font-semibold bg-[var(--surface-alt)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] max-w-[280px] truncate"
                >
                  <option value="All">All Modules ({pool.length} Qs)</option>
                  {modules.map((m) => (
                    <option key={m.name} value={m.name}>{m.name}</option>
                  ))}
                </select>
              </div>

              {/* Difficulty Selector */}
              <div className="flex items-center gap-1.5">
                {[
                  { id: 'All', label: 'All Modes' },
                  { id: 'Easy', label: 'Easy' },
                  { id: 'Medium', label: 'Medium' },
                  { id: 'Hard', label: 'Hard' }
                ].map(({ id, label }) => (
                  <button
                    key={id}
                    onClick={() => setActiveDifficulty(id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      activeDifficulty === id
                        ? 'bg-[var(--accent-soft)] text-[var(--accent)] shadow-xs border border-[var(--accent)]/20'
                        : 'text-[var(--text-soft)] hover:bg-[var(--surface-alt)]'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="max-w-3xl">
            {/* Intro */}
            {phase === 'intro' && (
              <Card className="space-y-6">
                <div className="flex items-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-[var(--accent-soft)] flex items-center justify-center shrink-0">
                    <Brain size={26} className="text-[var(--accent)]" />
                  </div>
                  <div>
                    <h3 className="font-bold text-lg md:text-xl text-[var(--text)]">Ready to Test Concept Transfer?</h3>
                    <p className="text-sm text-[var(--text-soft)] mt-0.5">
                      {pool.length} curriculum questions available in <strong>{activeSubject}</strong> ({activeDifficulty} mode)
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  {[
                    { label: 'Session Length', value: `${Math.min(5, pool.length)} Questions`, icon: Target },
                    { label: 'Practical Context', value: '100%', icon: Zap },
                    { label: 'Difficulty Mode', value: activeDifficulty, icon: Star },
                  ].map(({ label, value, icon: Icon }) => (
                    <div key={label} className="bg-[var(--surface-alt)] rounded-2xl p-4 text-center border border-[var(--border)]">
                      <Icon size={18} className="mx-auto mb-1.5 text-[var(--accent)]" />
                      <div className="text-base md:text-lg font-extrabold text-[var(--text)]">{value}</div>
                      <div className="text-xs text-[var(--text-soft)] mt-0.5">{label}</div>
                    </div>
                  ))}
                </div>

                <div className="border border-[var(--border)] rounded-2xl p-4 text-sm text-[var(--text-soft)] leading-relaxed bg-[var(--surface-alt)]/40">
                  <strong className="text-[var(--text)]">Transfer Objective:</strong> Each scenario presents an unfamiliar real-world context. Identify the governing law, theorem, or architecture from your syllabus and explain your solution.
                </div>

                <Button size="lg" onClick={startSession} disabled={!pool.length} className="w-full justify-center">
                  Start {activeSubject} ({activeDifficulty}) Challenge <ChevronRight size={18} />
                </Button>
              </Card>
            )}

            {/* Question Phase */}
            {phase === 'question' && currentRound && (
              <div className="space-y-5">
                {/* Progress Bar */}
                <div className="flex items-center gap-3">
                  {rounds.map((_, i) => (
                    <div key={i} className={`h-2 flex-1 rounded-full transition-colors ${
                      i < roundIdx ? 'bg-[var(--accent)]' : i === roundIdx ? 'bg-[var(--accent)] opacity-60' : 'bg-[var(--border)]'
                    }`} />
                  ))}
                  <span className="text-xs text-[var(--text-soft)] font-bold shrink-0">{roundIdx + 1}/{rounds.length}</span>
                </div>

                {/* Scenario Header */}
                <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface)] p-5 sm:p-6 shadow-xs">
                  <div className="flex items-center gap-2 mb-3 flex-wrap">
                    {currentRound.difficulty && <Badge tone={diffTone[currentRound.difficulty] || 'neutral'}>{currentRound.difficulty}</Badge>}
                    <Badge tone="accent">{activeSubject}</Badge>
                    <Badge tone="neutral">{currentRound.exact_syllabus_topic || currentRound.chapter || 'Curriculum Topic'}</Badge>
                  </div>
                  <h2 className="text-base md:text-lg font-bold leading-snug mb-2.5 text-[var(--text)]">
                    {currentRound.scenario}
                  </h2>
                  {currentRound.real_world_application && (
                    <p className="text-xs md:text-[13px] text-[var(--text-soft)] leading-relaxed">
                      <strong className="text-[var(--text)]">Real-World Application: </strong> {currentRound.real_world_application}
                    </p>
                  )}
                </div>

                {/* Academic Context Card */}
                <Card className="space-y-4">
                  <div className="flex items-center gap-2">
                    <BookOpen size={18} className="text-[var(--accent)]" />
                    <h3 className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)]">
                      Syllabus Concept Foundations
                    </h3>
                  </div>

                  {currentRound.concept_explanation && (
                    <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-sm text-[var(--text-soft)] leading-relaxed">
                      <strong className="text-[var(--text)] block mb-1">📖 Academic Concept:</strong>
                      {currentRound.concept_explanation}
                    </div>
                  )}

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    {currentRound.practical_connection && (
                      <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs md:text-sm text-[var(--text-soft)]">
                        <strong className="text-[var(--accent)] block mb-1">⚡ Practical Connection:</strong>
                        {currentRound.practical_connection}
                      </div>
                    )}
                    {currentRound.example && (
                      <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] text-xs md:text-sm text-[var(--text-soft)]">
                        <strong className="text-[var(--accent)] block mb-1">💡 Engineering Application:</strong>
                        {currentRound.example}
                      </div>
                    )}
                  </div>
                </Card>

                {/* Solution Input */}
                <Card>
                  <label htmlFor="solution-input" className="block text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-2.5">
                    Your Transfer Solution
                  </label>
                  <textarea
                    id="solution-input"
                    aria-label="Your transfer solution"
                    value={answer}
                    onChange={(e) => setAnswer(e.target.value)}
                    placeholder="Apply your curriculum knowledge to solve this scenario…"
                    rows={4}
                    className="w-full border border-[var(--border-strong)] rounded-xl p-4 text-sm md:text-base bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent-soft)] resize-none leading-relaxed"
                  />
                  <div className="flex items-center justify-between mt-4 flex-wrap gap-3">
                    <div className="flex gap-2.5">
                      <button
                        onClick={() => setShowHint(!showHint)}
                        className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold border border-[var(--border)] rounded-xl text-[var(--warning)] hover:bg-[var(--warning-soft)] transition-colors cursor-pointer"
                      >
                        <Lightbulb size={14} /> {showHint ? 'Hide hint' : 'Show hint'}
                      </button>
                      <button
                        onClick={() => setShowAnswer(!showAnswer)}
                        className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold border border-[var(--border)] rounded-xl text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors cursor-pointer"
                      >
                        <BookOpen size={14} /> Show model solution
                      </button>
                    </div>
                    <Button onClick={submitAnswer} disabled={!answer.trim() && !showAnswer} className="shadow-xs">
                      Submit Solution <ChevronRight size={16} />
                    </Button>
                  </div>

                  {showHint && (
                    <div className="mt-4 p-4 bg-[var(--warning-soft)] border border-[var(--warning)]/30 rounded-xl text-xs md:text-sm text-[var(--warning)] leading-relaxed">
                      <strong>Hint:</strong> {currentRound.hint}
                    </div>
                  )}
                  {showAnswer && (
                    <div className="mt-4 p-4 bg-[var(--accent-soft)] border border-[var(--accent)]/30 rounded-xl text-xs md:text-sm text-[var(--accent)] leading-relaxed">
                      <strong>Model Solution:</strong> {currentRound.modelAnswer}
                    </div>
                  )}
                </Card>
              </div>
            )}

            {/* Feedback Phase */}
            {phase === 'feedback' && currentRound && (
              <div className="space-y-5">
                <Card className="space-y-5">
                  <div className="flex items-center gap-5">
                    <div className="relative shrink-0">
                      <ScoreRing score={currentRound.transferScore} />
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-lg font-extrabold text-[var(--text)]">{currentRound.transferScore}</span>
                      </div>
                    </div>
                    <div>
                      <h3 className="text-lg md:text-xl font-extrabold text-[var(--text)]">Round {roundIdx + 1} Evaluated</h3>
                      <p className="text-sm text-[var(--text-soft)] mt-0.5">
                        Subject: <strong>{activeSubject}</strong> · Topic: <strong>{currentRound.exact_syllabus_topic || currentRound.chapter || 'Core Module'}</strong>
                      </p>
                    </div>
                  </div>

                  <div className="p-4 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)]">
                    <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-1.5">Model Transfer Solution</div>
                    <div className="text-sm text-[var(--text)] leading-relaxed">{currentRound.modelAnswer}</div>
                  </div>

                  {answer && (
                    <div className="p-4 rounded-xl bg-[var(--surface)] border border-[var(--border)]">
                      <div className="text-xs font-bold uppercase tracking-wider text-[var(--text-soft)] mb-1.5">Your Submitted Solution</div>
                      <div className="text-sm text-[var(--text-soft)] leading-relaxed">{answer}</div>
                    </div>
                  )}
                </Card>

                <Button size="lg" onClick={nextRound} className="w-full justify-center shadow-xs">
                  {roundIdx + 1 < rounds.length ? `Next Scenario (${roundIdx + 2}/${rounds.length})` : 'View Final Summary'} <ChevronRight size={18} />
                </Button>
              </div>
            )}

            {/* Done Phase */}
            {phase === 'done' && (
              <Card className="text-center p-8 sm:p-10 space-y-6">
                <div>
                  <div className="relative inline-block mb-4">
                    <ScoreRing score={avgScore} size={110} />
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="text-2xl font-extrabold text-[var(--text)]">{avgScore}</span>
                    </div>
                  </div>
                  <h2 className="text-2xl font-extrabold text-[var(--text)] mb-1.5">
                    {avgScore >= 80 ? '🏆 Cognitive Transfer Champion!' : avgScore >= 65 ? '⚡ Great Transfer Mastery' : '📚 Continue Practice'}
                  </h2>
                  <p className="text-sm text-[var(--text-soft)]">
                    Average transfer score across {scores.length} scenarios in {activeSubject}
                  </p>
                </div>

                <div className="space-y-2.5 max-w-md mx-auto text-left">
                  {scores.map((s, i) => (
                    <div key={i} className="flex items-center justify-between p-3.5 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] text-sm">
                      <span className="font-semibold text-[var(--text)]">Round {i + 1}</span>
                      <span className="font-extrabold text-[var(--accent)]">{s.score} / 100</span>
                    </div>
                  ))}
                </div>

                <Button size="lg" onClick={() => setPhase('intro')} className="w-full max-w-md mx-auto justify-center">
                  <RotateCcw size={16} /> Practice Another Challenge
                </Button>
              </Card>
            )}
          </div>
        </>
      )}
      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </>
  )
}
