import { useState } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { getDynamicSubjects, getDynamicChapters } from '../data/syllabusData.js'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import {
  Brain, ChevronRight, Sparkles, CheckCircle2, AlertTriangle, HelpCircle,
  RotateCcw, BookOpen, UploadCloud, Loader2, Award
} from 'lucide-react'

export default function SelfEvaluation() {
  const { user, profile, syllabusData, recordActivity } = useApp()
  const activeProfile = { ...user, ...profile }

  const subjects = getDynamicSubjects(activeProfile, syllabusData)
  const hasSubjects = subjects.length > 0
  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)

  const [activeSubject, setActiveSubject] = useState(subjects[0] || '')
  const [activeTopic, setActiveTopic] = useState('')
  const [difficulty, setDifficulty] = useState('Medium')

  const [question, setQuestion] = useState(null)
  const [studentAnswer, setStudentAnswer] = useState('')
  const [evaluation, setEvaluation] = useState(null)

  const [loadingQuestion, setLoadingQuestion] = useState(false)
  const [evaluating, setEvaluating] = useState(false)
  const [error, setError] = useState(null)

  const chapters = getDynamicChapters(activeSubject, activeProfile, syllabusData)

  const handleGenerateQuestion = async () => {
    setLoadingQuestion(true)
    setError(null)
    setQuestion(null)
    setEvaluation(null)
    setStudentAnswer('')

    try {
      const targetTopic = activeTopic || (chapters[0] ? chapters[0].name : 'Core Concepts')
      const res = await api.generateSelfEval(activeSubject, targetTopic, difficulty, JSON.stringify(syllabusData || {}))
      if (res && res.success && res.question) {
        setQuestion(res.question)
        recordActivity('self-eval', `Started Self-Evaluation on ${activeSubject}: ${targetTopic} (${difficulty})`)
      } else {
        setError(res.error || 'Failed to generate question from Gemini. Please try again.')
      }
    } catch (err) {
      setError(err.message || 'Error communicating with AI service.')
    } finally {
      setLoadingQuestion(false)
    }
  }

  const handleSubmitResponse = async () => {
    if (!studentAnswer.trim() || !question) return
    setEvaluating(true)
    setError(null)

    try {
      const res = await api.evaluateSelfEval(
        question.question_text,
        question.expected_concept || '',
        studentAnswer,
        activeSubject
      )
      if (res && res.success && res.evaluation) {
        setEvaluation(res.evaluation)
        recordActivity('self-eval', `Completed Self-Evaluation in ${activeSubject} (Score: ${res.evaluation.score}/100)`)
      } else {
        setError(res.error || 'Could not evaluate response. Please try again.')
      }
    } catch (err) {
      setError(err.message || 'Evaluation request failed.')
    } finally {
      setEvaluating(false)
    }
  }

  return (
    <>
      <PageHead
        title="Dynamic AI Self Evaluation"
        subtitle="Test your comprehension against dynamically generated AI questions from your exact course syllabus."
      />

      {!hasSubjects ? (
        <div className="p-8 max-w-[600px] mx-auto text-center space-y-4">
          <div className="w-16 h-16 rounded-2xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto text-2xl">
            <BookOpen size={32} />
          </div>
          <h2 className="text-xl font-extrabold text-[var(--text)]">Syllabus Document Required</h2>
          <p className="text-sm text-[var(--text-soft)]">
            Self Evaluation generates personalized questions based on your course syllabus. Please upload your syllabus document to unlock Self Evaluation.
          </p>
          <div className="pt-2">
            <button
              onClick={() => setIsSyllabusModalOpen(true)}
              className="px-5 py-2.5 bg-[var(--accent)] text-white text-xs font-bold rounded-xl hover:bg-[var(--accent-dim)] inline-flex items-center gap-2 shadow-md"
            >
              <UploadCloud size={16} /> Upload Syllabus Document
            </button>
          </div>
          <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
        </div>
      ) : (
        <div className="max-w-[760px]">
          {/* Subject & Difficulty Selection Bar */}
          <Card className="mb-6">
            <div className="space-y-4">
              <div>
                <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] block mb-1.5">Select Subject</label>
                <div className="flex gap-2 flex-wrap">
                  {subjects.map((sub) => (
                    <button
                      key={sub}
                      onClick={() => { setActiveSubject(sub); setActiveTopic(''); setQuestion(null); setEvaluation(null); }}
                      className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold border transition-all ${
                        activeSubject === sub
                          ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                          : 'border-[var(--border-strong)] text-[var(--text-soft)] hover:border-[var(--accent-dim)]'
                      }`}
                    >
                      {sub}
                    </button>
                  ))}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] block mb-1.5">Topic / Chapter</label>
                  <select
                    value={activeTopic}
                    onChange={(e) => setActiveTopic(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl border border-[var(--border-strong)] text-[13px] bg-[var(--surface)] text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                  >
                    <option value="">All Topics in {activeSubject}</option>
                    {chapters.map((ch) => (
                      <option key={ch.name} value={ch.name}>{ch.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] block mb-1.5">Difficulty Level</label>
                  <div className="flex gap-2">
                    {['Easy', 'Medium', 'Hard'].map((lvl) => (
                      <button
                        key={lvl}
                        onClick={() => setDifficulty(lvl)}
                        className={`flex-1 py-1.5 rounded-xl text-xs font-bold border transition-all ${
                          difficulty === lvl
                            ? 'bg-[var(--surface)] text-[var(--text)] border-[var(--accent)] shadow-sm'
                            : 'border-[var(--border)] text-[var(--text-faint)] hover:text-[var(--text-soft)]'
                        }`}
                      >
                        {lvl === 'Easy' ? '🟢 Easy' : lvl === 'Medium' ? '🟡 Medium' : '🔴 Hard'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              <Button
                onClick={handleGenerateQuestion}
                disabled={loadingQuestion}
                className="w-full justify-center mt-2"
              >
                {loadingQuestion ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Generating AI Question...
                  </>
                ) : (
                  <>
                    <Sparkles size={16} /> Generate Dynamic AI Question
                  </>
                )}
              </Button>
            </div>
          </Card>

          {error && (
            <div className="p-4 mb-6 rounded-xl bg-red-500/10 border border-red-500/20 text-red-500 text-xs font-medium flex items-center gap-2">
              <AlertTriangle size={16} className="shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Active Question Display */}
          {question && (
            <div className="space-y-4 mb-6">
              <Card className="border-[var(--accent-dim)] bg-gradient-to-br from-[var(--surface)] to-[var(--surface-alt)]">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <Badge tone="accent">{question.subject || activeSubject}</Badge>
                    <Badge tone="neutral">{question.topic || activeTopic || 'General Topic'}</Badge>
                    <Badge tone={difficulty === 'Easy' ? 'success' : difficulty === 'Medium' ? 'warning' : 'error'}>
                      {difficulty}
                    </Badge>
                  </div>
                  <Brain size={20} className="text-[var(--accent)]" />
                </div>

                <div className="text-[15px] font-bold leading-relaxed text-[var(--text)] mb-4">
                  {question.question_text}
                </div>

                <div className="space-y-2">
                  <label className="text-xs font-bold uppercase tracking-wider text-[var(--text-faint)] block">
                    Your Response
                  </label>
                  <textarea
                    value={studentAnswer}
                    onChange={(e) => setStudentAnswer(e.target.value)}
                    placeholder="Write your response clearly here. Include steps, formulas, or key concepts..."
                    rows={6}
                    disabled={evaluating || !!evaluation}
                    className="w-full p-3.5 border border-[var(--border-strong)] rounded-xl text-sm bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)] resize-none leading-relaxed"
                  />
                </div>

                {!evaluation && (
                  <Button
                    onClick={handleSubmitResponse}
                    disabled={evaluating || !studentAnswer.trim()}
                    className="w-full justify-center mt-4"
                  >
                    {evaluating ? (
                      <>
                        <Loader2 size={16} className="animate-spin" /> Evaluating Answer with Gemini...
                      </>
                    ) : (
                      <>
                        Submit Response for Evaluation <ChevronRight size={16} />
                      </>
                    )}
                  </Button>
                )}
              </Card>
            </div>
          )}

          {/* Evaluation Results */}
          {evaluation && (
            <Card className="space-y-4 border-2 border-[var(--accent)]">
              <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-2xl bg-[var(--accent-soft)] flex items-center justify-center text-[var(--accent)] font-black text-xl">
                    {evaluation.score}
                  </div>
                  <div>
                    <h3 className="font-extrabold text-base text-[var(--text)]">Evaluation Score: {evaluation.score}/100</h3>
                    <p className="text-xs text-[var(--text-soft)]">Assessed dynamically against expected concept & syllabus</p>
                  </div>
                </div>
                <Award size={28} className="text-[var(--accent)]" />
              </div>

              {evaluation.why && (
                <div className="space-y-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-[var(--accent)]">Why this score</span>
                  <p className="text-xs leading-relaxed text-[var(--text-soft)] bg-[var(--surface-alt)] p-3 rounded-xl border border-[var(--border)]">
                    {evaluation.why}
                  </p>
                </div>
              )}

              {evaluation.mistake && (
                <div className="space-y-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-red-500">Mistakes / Errors Identified</span>
                  <p className="text-xs leading-relaxed text-red-400 bg-red-500/10 p-3 rounded-xl border border-red-500/20">
                    {evaluation.mistake}
                  </p>
                </div>
              )}

              {evaluation.correct_reasoning && (
                <div className="space-y-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-emerald-500">Correct Reasoning & Model Answer</span>
                  <p className="text-xs leading-relaxed text-emerald-400 bg-emerald-500/10 p-3 rounded-xl border border-emerald-500/20">
                    {evaluation.correct_reasoning}
                  </p>
                </div>
              )}

              {evaluation.how_to_improve && (
                <div className="space-y-1">
                  <span className="text-xs font-bold uppercase tracking-wider text-[var(--warning)]">How to Improve</span>
                  <p className="text-xs leading-relaxed text-[var(--text)] bg-[var(--warning-soft)] p-3 rounded-xl border border-[var(--border)]">
                    {evaluation.how_to_improve}
                  </p>
                </div>
              )}

              <Button onClick={handleGenerateQuestion} variant="secondary" className="w-full justify-center mt-4">
                <RotateCcw size={14} /> Try Another Question
              </Button>
            </Card>
          )}
        </div>
      )}

      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </>
  )
}
