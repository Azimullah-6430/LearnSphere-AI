import { useState, useEffect } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { getActiveValidatedCurriculum, getDynamicTransferQuestions, getDynamicChapters } from '../data/syllabusData.js'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import {
  ChevronRight, CheckCircle2, XCircle, Lightbulb, Target, Brain, Star,
  RotateCcw, BookOpen, Zap, Layers, UploadCloud
} from 'lucide-react'

function ScoreRing({ score, size = 80 }) {
  const r = (size - 8) / 2
  const circ = 2 * Math.PI * r
  const dash = (score / 100) * circ
  const color = score >= 80 ? '#22c55e' : score >= 60 ? '#f59e0b' : '#ef4444'
  return (
    <svg width={size} height={size} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth="7" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="7"
        strokeDasharray={`${dash} ${circ - dash}`} strokeLinecap="round"
        style={{ transition: 'stroke-dasharray 0.8s ease' }}
      />
    </svg>
  )
}

export default function KnowledgeChallenge() {
  const { user, recordActivity } = useApp()
  const { curriculum, curriculumStatus, isValid: hasValidCurriculum, subjects, units: allUnits } = useAuthoritativeCurriculum()
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

  const modules = getDynamicChapters(activeSubject, activeProfile, syllabusData)
  const pool = getDynamicTransferQuestions(activeSubject, activeProfile, syllabusData, activeDifficulty, activeModule)
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
    recordActivity('challenge', `Started Knowledge Challenge in ${activeSubject} (${activeDifficulty})`, { subject: activeSubject, difficulty: activeDifficulty })
  }

  const submitAnswer = () => {
    const score = currentRound.transferScore
    setScores((prev) => [...prev, { round: currentRound.round, score, answer }])
    setPhase('feedback')
  }

  const nextRound = () => {
    if (roundIdx + 1 >= rounds.length) {
      setPhase('done')
      const finalAvg = scores.length ? Math.round(scores.reduce((a, b) => a + b.score, 0) / scores.length) : 80
      recordActivity('challenge', `Completed Knowledge Challenge in ${activeSubject} (${finalAvg}%)`, { score: finalAvg, subject: activeSubject })
    } else {
      setRoundIdx((i) => i + 1)
      setAnswer('')
      setShowHint(false)
      setShowAnswer(false)
      setPhase('question')
    }
  }

  const avgScore = scores.length ? Math.round(scores.reduce((a, b) => a + b.score, 0) / scores.length) : 0

  const diffTone = { Easy: 'success', Medium: 'warning', Hard: 'error' }

  return (
    <>
      <PageHead
        title="Knowledge Transfer Challenge"
        subtitle="Can your knowledge survive an unfamiliar real-world problem? 20 Questions per Module."
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
        <div className="flex gap-1.5 flex-wrap mb-4">
          {subjects.map((sub) => (
            <button
              key={sub}
              onClick={() => switchSubject(sub)}
              disabled={phase !== 'intro'}
              className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold border transition-all disabled:opacity-50 ${
                activeSubject === sub
                  ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                  : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
              }`}
            >
              {sub}
            </button>
          ))}
        </div>
      )}

      {/* Module & Difficulty Filter Bar */}
      {phase === 'intro' && (
        <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-3 mb-6 p-2 bg-[var(--surface-alt)] rounded-xl border border-[var(--border)] max-w-[680px]">
          {/* Module Selector */}
          <div className="flex items-center gap-2">
            <Layers size={14} className="text-[var(--accent)] ml-1" />
            <span className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)]">Module:</span>
            <select
              value={activeModule}
              onChange={(e) => setActiveModule(e.target.value)}
              className="px-3 py-1 rounded-lg border border-[var(--border-strong)] text-[12px] font-semibold bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)] max-w-[280px] truncate"
            >
              <option value="All">All Modules ({pool.length} total Qs)</option>
              {modules.map((m) => (
                <option key={m.name} value={m.name}>{m.name}</option>
              ))}
            </select>
          </div>

          {/* Difficulty Selector */}
          <div className="flex items-center gap-1">
            {[
              { id: 'All', label: 'All Modes' },
              { id: 'Easy', label: '🟢 Easy' },
              { id: 'Medium', label: '🟡 Medium' },
              { id: 'Hard', label: '🔴 Hard' }
            ].map(({ id, label }) => (
              <button
                key={id}
                onClick={() => setActiveDifficulty(id)}
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
      )}

      <div className="max-w-[680px]">

        {/* Intro */}
        {phase === 'intro' && (
          <Card>
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-xl bg-[var(--accent-soft)] flex items-center justify-center">
                <Brain size={22} className="text-[var(--accent)]" />
              </div>
              <div>
                <div className="font-bold text-[15px]">Ready to test your transfer ability?</div>
                <div className="text-sm text-[var(--text-soft)]">{pool.length} real-world questions from <strong>{activeSubject}</strong> ({activeDifficulty} mode)</div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-6">
              {[
                { label: 'Session Length', value: `${Math.min(5, pool.length)} Questions`, icon: Target },
                { label: 'Real-world framing', value: '100%', icon: Zap },
                { label: 'Difficulty Mode', value: activeDifficulty, icon: Star },
              ].map(({ label, value, icon: Icon }) => (
                <div key={label} className="bg-[var(--surface-alt)] rounded-lg p-3 text-center">
                  <Icon size={16} className="mx-auto mb-1 text-[var(--accent)]" />
                  <div className="text-[14px] font-extrabold">{value}</div>
                  <div className="text-[11px] text-[var(--text-faint)]">{label}</div>
                </div>
              ))}
            </div>

            <div className="border border-[var(--border)] rounded-lg p-3.5 mb-5 text-[13px] text-[var(--text-soft)]">
              <strong className="text-[var(--text)]">How it works:</strong> Each question takes a key concept from your {activeSubject} syllabus and frames it in an unfamiliar real-world scenario.
              Analyze the scenario, identify the underlying principle, and write your solution.
            </div>

            <Button onClick={startSession} disabled={!pool.length} className="w-full justify-center">
              Start {activeSubject} ({activeDifficulty}) Challenge <ChevronRight size={15} />
            </Button>
          </Card>
        )}

        {/* Question Phase */}
        {phase === 'question' && currentRound && (
          <div className="space-y-4">
            {/* Progress Bar */}
            <div className="flex items-center gap-3">
              {rounds.map((_, i) => (
                <div key={i} className={`h-1.5 flex-1 rounded-full transition-colors ${
                  i < roundIdx ? 'bg-[var(--accent)]' : i === roundIdx ? 'bg-[var(--accent)] opacity-60' : 'bg-[var(--border)]'
                }`} />
              ))}
              <span className="text-[12px] text-[var(--text-faint)] font-semibold shrink-0">{roundIdx + 1}/{rounds.length}</span>
            </div>

            {/* Header Blueprint */}
            <div className="relative overflow-hidden rounded-xl border border-[var(--border)] bg-gradient-to-br from-[var(--accent-soft)] to-[var(--surface-alt)] p-6">
              <div className="absolute top-3 right-4 opacity-10"><Brain size={64} strokeWidth={1} /></div>
              <div className="flex items-center gap-2 mb-3 flex-wrap">
                {currentRound.difficulty && <Badge tone={diffTone[currentRound.difficulty] || 'neutral'}>{currentRound.difficulty}</Badge>}
                <Badge tone="accent">{currentRound.semester || (activeProfile?.current_semester ? `Semester ${activeProfile.current_semester}` : 'Active Semester')}</Badge>
                <Badge tone="neutral">{currentRound.exact_subject || activeSubject}</Badge>
                <Badge tone="neutral">{currentRound.exact_syllabus_topic || currentRound.chapter}</Badge>
              </div>
              <h2 className="text-[16.5px] font-extrabold leading-snug mb-2">{currentRound.scenario}</h2>
              {currentRound.real_world_application && (
                <p className="text-[12.5px] text-[var(--text-soft)]">
                  <strong className="text-[var(--text)]">🌍 Real-World Application: </strong> {currentRound.real_world_application}
                </p>
              )}
            </div>

            {/* Academic & Practical Transfer Blueprint (9 Dimensions) */}
            <Card>
              <div className="flex items-center gap-2 mb-3">
                <BookOpen size={16} className="text-[var(--accent)]" />
                <h3 className="text-[12.5px] font-bold uppercase tracking-wider text-[var(--text-faint)]">
                  Knowledge Transfer Foundations
                </h3>
              </div>

              <div className="space-y-3 text-[12.5px]">
                {currentRound.concept_explanation && (
                  <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                    <strong className="text-[var(--text)] block mb-1">📖 Academic Concept Explanation:</strong>
                    {currentRound.concept_explanation}
                  </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {currentRound.practical_connection && (
                    <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                      <strong className="text-[var(--accent)] block mb-1">⚡ Practical Connection:</strong>
                      {currentRound.practical_connection}
                    </div>
                  )}
                  {currentRound.example && (
                    <div className="p-3 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[var(--text-soft)]">
                      <strong className="text-[var(--accent)] block mb-1">💡 Engineering Example:</strong>
                      {currentRound.example}
                    </div>
                  )}
                </div>

                {currentRound.common_misconception && (
                  <div className="p-3 rounded-lg bg-[var(--warning-soft)] border border-[var(--warning)] text-[var(--text)]">
                    <strong className="text-[var(--warning)] block mb-1">⚠️ Common Misconception:</strong>
                    {currentRound.common_misconception}
                  </div>
                )}

                {currentRound.exam_relevance && (
                  <div className="p-2.5 rounded-lg bg-[var(--surface-alt)] border border-[var(--border)] text-[12px] text-[var(--text-soft)]">
                    <strong className="text-[var(--text)]">📝 University Exam Relevance: </strong>
                    {currentRound.exam_relevance}
                  </div>
                )}
              </div>
            </Card>

            {/* Quick Understanding Question Interactive Check */}
            {currentRound.quick_understanding_question && (
              <Card>
                <div className="flex items-center gap-2 mb-2">
                  <Target size={15} className="text-[var(--accent)]" />
                  <div className="text-[12px] font-bold uppercase tracking-wider text-[var(--text-faint)]">Quick Understanding Check</div>
                </div>
                <p className="text-[13px] font-semibold mb-3 text-[var(--text)]">
                  {currentRound.quick_understanding_question.question}
                </p>
                <div className="space-y-1.5 mb-3">
                  {(currentRound.quick_understanding_question.options || []).map((opt, idx) => (
                    <div key={idx} className="p-2.5 rounded-lg border border-[var(--border)] bg-[var(--surface-alt)] text-[12.5px] font-medium text-[var(--text-soft)]">
                      <span className="font-bold text-[var(--accent)] mr-2">{String.fromCharCode(65 + idx)}.</span> {opt}
                    </div>
                  ))}
                </div>
              </Card>
            )}

            {/* Student Explanation / Solution Input */}
            <Card>
              <div className="text-[12px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2">Your Transfer Solution</div>
              <textarea
                value={answer}
                onChange={(e) => setAnswer(e.target.value)}
                placeholder="Apply your syllabus knowledge to solve this transfer scenario…"
                rows={4}
                className="w-full border border-[var(--border-strong)] rounded-lg px-3.5 py-3 text-[13.5px] bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)] resize-none leading-relaxed"
              />
              <div className="flex items-center justify-between mt-3">
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowHint(!showHint)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold border border-[var(--border)] rounded-lg text-[var(--warning)] hover:bg-[var(--warning-soft)] transition-colors"
                  >
                    <Lightbulb size={13} /> {showHint ? 'Hide hint' : 'Hint'}
                  </button>
                  <button
                    onClick={() => setShowAnswer(!showAnswer)}
                    className="flex items-center gap-1.5 px-3 py-1.5 text-[12px] font-semibold border border-[var(--border)] rounded-lg text-[var(--text-soft)] hover:bg-[var(--surface-alt)] transition-colors"
                  >
                    <BookOpen size={13} /> Show model solution
                  </button>
                </div>
                <Button onClick={submitAnswer} disabled={!answer.trim() && !showAnswer}>
                  Submit Solution <ChevronRight size={14} />
                </Button>
              </div>

              {showHint && (
                <div className="mt-3 p-3 bg-[var(--warning-soft)] border border-[var(--border)] rounded-lg">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--warning)] mb-1">Hint</div>
                  <div className="text-[13px] text-[var(--text-soft)]">{currentRound.hint}</div>
                </div>
              )}
              {showAnswer && (
                <div className="mt-3 p-3 bg-[var(--accent-soft)] border border-[var(--border)] rounded-lg">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--accent)] mb-1">Model Solution</div>
                  <div className="text-[13px]">{currentRound.modelAnswer}</div>
                </div>
              )}
            </Card>
          </div>
        )}

        {/* Feedback Phase */}
        {phase === 'feedback' && currentRound && (
          <div className="space-y-4">
            <Card>
              <div className="flex items-center gap-4 mb-5">
                <div className="relative">
                  <ScoreRing score={currentRound.transferScore} />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-[15px] font-extrabold">{currentRound.transferScore}</span>
                  </div>
                </div>
                <div>
                  <div className="text-[15px] font-extrabold">Round {roundIdx + 1} Complete</div>
                  <div className="text-sm text-[var(--text-soft)]">
                    Validated Subject: <strong>{currentRound.exact_subject || activeSubject}</strong> · Topic: <strong>{currentRound.exact_syllabus_topic || currentRound.chapter}</strong>
                  </div>
                </div>
              </div>

              {currentRound.quick_understanding_question && (
                <div className="p-3 mb-4 rounded-lg bg-[var(--success-soft)] border border-[var(--border)] text-[12.5px]">
                  <strong className="text-[var(--success)] block mb-1">✓ Correct Understanding:</strong>
                  {currentRound.quick_understanding_question.correct_answer} — {currentRound.quick_understanding_question.explanation}
                </div>
              )}

              <div className="mb-4">
                <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-2">Concepts Applied & Mastered</div>
                <div className="flex flex-wrap gap-2">
                  {(currentRound.conceptsApplied || []).map((c, i) => (
                    <span key={i} className="flex items-center gap-1 px-2.5 py-1 bg-[var(--accent-soft)] text-[var(--accent)] rounded-full text-[11.5px] font-semibold">
                      <CheckCircle2 size={11} /> {c}
                    </span>
                  ))}
                </div>
              </div>

              <div className="border border-[var(--border)] rounded-lg p-3.5 mb-3">
                <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">Model Transfer Solution</div>
                <div className="text-[13px] leading-relaxed">{currentRound.modelAnswer}</div>
              </div>

              {answer && (
                <div className="bg-[var(--surface-alt)] rounded-lg p-3.5">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">Your Submitted Answer</div>
                  <div className="text-[13px] text-[var(--text-soft)] leading-relaxed">{answer}</div>
                </div>
              )}
            </Card>

            <Button onClick={nextRound} className="w-full justify-center">
              {roundIdx + 1 < rounds.length ? `Next Question (${roundIdx + 2}/${rounds.length})` : 'See Final Results'} <ChevronRight size={15} />
            </Button>
          </div>
        )}

        {/* Done */}
        {phase === 'done' && (
          <Card>
            <div className="text-center mb-6">
              <div className="relative inline-block mb-3">
                <ScoreRing score={avgScore} size={100} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-[22px] font-extrabold">{avgScore}</span>
                </div>
              </div>
              <div className="text-[18px] font-extrabold mb-1">
                {avgScore >= 80 ? '🏆 Transfer Champion!' : avgScore >= 65 ? '⚡ Great Transfer Ability' : '📚 Keep Practising'}
              </div>
              <div className="text-sm text-[var(--text-soft)]">Average transfer score across {scores.length} questions from {activeSubject}</div>
            </div>

            <div className="space-y-2 mb-6">
              {scores.map((s, i) => (
                <div key={i} className="flex items-center gap-3 p-3 bg-[var(--surface-alt)] rounded-lg">
                  <div className={`w-2 h-2 rounded-full ${s.score >= 80 ? 'bg-green-500' : s.score >= 65 ? 'bg-amber-500' : 'bg-red-500'}`} />
                  <span className="text-[13px] font-semibold flex-1">Round {i + 1}</span>
                  <span className="text-[13px] font-extrabold">{s.score}/100</span>
                </div>
              ))}
            </div>

            <Button onClick={() => setPhase('intro')} className="w-full justify-center">
              <RotateCcw size={14} /> Try Again
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
