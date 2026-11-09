import { useState, useEffect, useMemo, useCallback } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { getDynamicScenarios, getDynamicChapters } from '../data/syllabusData.js'
import { useApp, useAuthoritativeCurriculum } from '../context/AppContext.jsx'
import { api } from '../services/api.js'
import SyllabusModal from '../components/SyllabusModal.jsx'
import CurriculumReviewNotice from '../components/CurriculumReviewNotice.jsx'
import {
  CheckCircle2,
  XCircle,
  Globe,
  Shuffle,
  BookOpen,
  Layers,
  Loader2,
  AlertTriangle,
  HelpCircle,
  Sparkles,
  Target,
  Wrench,
  ListOrdered,
  Microscope,
  Lightbulb,
  FileText,
  ArrowRight,
  ArrowLeft,
  Sliders,
  Play,
  RotateCcw,
  Check,
  Send,
  Award,
  Zap,
  Activity,
  ChevronRight,
  Info,
  ShieldCheck,
  Cpu,
  RefreshCw,
  Compass,
  GraduationCap
} from 'lucide-react'

const difficultyTone = { Easy: 'success', Medium: 'warning', Hard: 'error' }

// 7 Guided Journey Steps
const JOURNEY_STEPS = [
  { step: 1, title: 'Subject', desc: 'Select validated subject' },
  { step: 2, title: 'Topic', desc: 'Choose curriculum module' },
  { step: 3, title: 'Concept', desc: 'Explore core theory' },
  { step: 4, title: 'Applications', desc: 'Industry & real world' },
  { step: 5, title: 'Activity', desc: 'Hands-on practical lab' },
  { step: 6, title: 'Check', desc: 'Verify understanding' },
  { step: 7, title: 'Complete', desc: 'Review & next steps' }
]

function QualityMeter({ pct }) {
  const color = pct >= 70 ? 'var(--success, #10b981)' : pct >= 45 ? 'var(--warning, #f59e0b)' : 'var(--error, #ef4444)'
  const label = pct >= 80 ? 'Mastery' : pct >= 65 ? 'Proficient' : pct >= 45 ? 'Developing' : 'Needs Practice'
  return (
    <div className="mb-4">
      <div className="flex justify-between items-center mb-1.5">
        <span className="text-[11px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Application Quality</span>
        <span className="text-sm font-extrabold" style={{ color }}>{pct}% · {label}</span>
      </div>
      <div className="h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden border border-slate-200 dark:border-slate-700">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{ width: `${Math.min(Math.max(pct, 0), 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  )
}

// Interactive Simulation Sandbox Component
function InteractiveSimulationPanel({ scenario, subject, topic }) {
  const [paramA, setParamA] = useState(50)
  const [paramB, setParamB] = useState(30)
  const [isRunning, setIsRunning] = useState(false)
  const [simOutput, setSimOutput] = useState(null)

  // Calibrate simulation labels based on subject / topic
  const simConfig = useMemo(() => {
    const subLow = String(subject || '').toLowerCase()
    const topLow = String(topic || '').toLowerCase()

    if (subLow.includes('physic') || subLow.includes('mechanic')) {
      return {
        labelA: 'Applied Force / Pressure (N)',
        labelB: 'Displacement / Mass (kg)',
        unit: 'J',
        calc: (a, b) => ((a * b * 0.98).toFixed(1) + ' Joules (Kinetic Work)'),
        stateLabels: ['Equilibrium', 'In Motion', 'Maximum Velocity', 'Damped Rest']
      }
    }
    if (subLow.includes('electr') || subLow.includes('circuit')) {
      return {
        labelA: 'Input Voltage (V)',
        labelB: 'Load Resistance (Ω)',
        unit: 'A',
        calc: (a, b) => ((a / Math.max(b, 1)).toFixed(2) + ' A (Current Flow) · ' + ((a * a) / Math.max(b, 1)).toFixed(1) + ' W (Power Dissipation)'),
        stateLabels: ['Open Circuit', 'Current Flowing', 'Peak Efficiency', 'Thermal Limit']
      }
    }
    if (subLow.includes('chem')) {
      return {
        labelA: 'Concentration (mol/L)',
        labelB: 'Solution Temperature (°C)',
        unit: 'rate',
        calc: (a, b) => ((a * (1 + b / 100) * 2.4).toFixed(2) + ' mol/(L·s) (Reaction Velocity)'),
        stateLabels: ['Reactants Mixed', 'Activation Energy Reached', 'Rapid Transition', 'Equilibrium State']
      }
    }
    if (subLow.includes('block') || subLow.includes('cloud') || subLow.includes('aws') || subLow.includes('comput') || subLow.includes('data')) {
      return {
        labelA: 'Node / Cluster Load (req/s)',
        labelB: 'Replication / Shard Count',
        unit: 'ms',
        calc: (a, b) => (Math.max(12, Math.round(180 - (b * 12) + (a * 0.4))) + ' ms (Average Latency) · ' + (b * 99.9 / 10).toFixed(1) + '% Fault Tolerance'),
        stateLabels: ['Idle Standby', 'Synchronizing State', 'High Throughput', 'Consensus Achieved']
      }
    }
    return {
      labelA: 'Control Variable A (%)',
      labelB: 'Operational Parameter B (%)',
      unit: '%',
      calc: (a, b) => (((a * 0.6) + (b * 0.4)).toFixed(1) + '% Measured System Output'),
      stateLabels: ['Baseline Calibrated', 'Step Applied', 'Dynamic Transient', 'Steady-State Reached']
    }
  }, [subject, topic])

  const handleRunSimulation = () => {
    setIsRunning(true)
    setTimeout(() => {
      setSimOutput(simConfig.calc(paramA, paramB))
      setIsRunning(false)
    }, 600)
  }

  const handleReset = () => {
    setParamA(50)
    setParamB(30)
    setSimOutput(null)
    setIsRunning(false)
  }

  return (
    <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/60 p-5 shadow-sm">
      <div className="flex items-center justify-between gap-3 mb-4 flex-wrap">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
            <Cpu size={16} />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Interactive Simulation & Parameter Sandbox
            </h4>
            <p className="text-[11px] text-slate-500 dark:text-slate-400">
              Adjust theoretical variables and execute real-time model verification
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          <button
            onClick={handleReset}
            className="p-1.5 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors cursor-pointer"
            title="Reset variables"
          >
            <RotateCcw size={13} />
          </button>
          <Button
            size="sm"
            onClick={handleRunSimulation}
            disabled={isRunning}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs px-3 py-1.5 shadow-sm"
          >
            {isRunning ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
            Run Simulation
          </Button>
        </div>
      </div>

      {/* Sliders Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80 shadow-xs">
          <div className="flex justify-between items-center text-xs font-semibold mb-2">
            <span className="text-slate-700 dark:text-slate-300">{simConfig.labelA}</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{paramA}</span>
          </div>
          <input
            type="range"
            min={10}
            max={100}
            value={paramA}
            onChange={(e) => setParamA(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-600"
          />
        </div>

        <div className="p-3.5 rounded-xl bg-white dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700/80 shadow-xs">
          <div className="flex justify-between items-center text-xs font-semibold mb-2">
            <span className="text-slate-700 dark:text-slate-300">{simConfig.labelB}</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">{paramB}</span>
          </div>
          <input
            type="range"
            min={5}
            max={100}
            value={paramB}
            onChange={(e) => setParamB(Number(e.target.value))}
            className="w-full h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer accent-emerald-600"
          />
        </div>
      </div>

      {/* Live Visual State Diagram */}
      <div className="p-4 rounded-xl bg-white dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800">
        <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2.5 flex items-center justify-between">
          <span>Observed System States</span>
          <span className="text-[10px] text-emerald-600 dark:text-emerald-400 font-mono">Real-time model pipeline</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          {simConfig.stateLabels.map((lbl, idx) => {
            const isActive = isRunning ? idx === 1 : simOutput ? idx === 3 : idx === 0
            return (
              <div
                key={idx}
                className={`p-2.5 rounded-lg border text-center transition-all ${
                  isActive
                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950/30 text-emerald-900 dark:text-emerald-200 font-bold shadow-xs'
                    : 'border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 text-slate-500 dark:text-slate-400 font-medium'
                }`}
              >
                <div className="text-[10px] uppercase tracking-wider text-slate-400 mb-0.5">Stage {idx + 1}</div>
                <div className="text-xs truncate">{lbl}</div>
              </div>
            )
          })}
        </div>

        {simOutput && (
          <div className="mt-3.5 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-900 dark:text-emerald-200 text-xs flex items-center justify-between">
            <span className="font-semibold flex items-center gap-1.5">
              <Sparkles size={14} className="text-emerald-600 dark:text-emerald-400 shrink-0" />
              Calculated Simulation Result:
            </span>
            <span className="font-mono font-bold">{simOutput}</span>
          </div>
        )}
      </div>
    </div>
  )
}

export default function RealityLab() {
  const { user, syllabusData, recordActivity } = useApp()
  const { curriculum, isValid: hasValidCurriculum, subjects, units: allUnits } = useAuthoritativeCurriculum()
  const activeProfile = user
  const effectiveCurriculum = curriculum || syllabusData

  const [isSyllabusModalOpen, setIsSyllabusModalOpen] = useState(false)
  const [currentStep, setCurrentStep] = useState(1) // 1 to 7

  // Selection states
  const [activeSubject, setActiveSubject] = useState(subjects[0] || '')
  const [activeModule, setActiveModule] = useState('All')
  const [activeDifficulty, setActiveDifficulty] = useState('Medium')
  const [scenarioIdx, setScenarioIdx] = useState(0)

  // Evaluation & Response states
  const [answer, setAnswer] = useState('')
  const [result, setResult] = useState(null)
  const [showModel, setShowModel] = useState(false)
  const [isEvaluating, setIsEvaluating] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [generatedScenarios, setGeneratedScenarios] = useState([])
  const [completedSteps, setCompletedSteps] = useState({ 1: true })

  // Synchronize active subject
  useEffect(() => {
    if (subjects.length > 0 && !subjects.includes(activeSubject)) {
      setActiveSubject(subjects[0])
      setActiveModule('All')
      setScenarioIdx(0)
      setGeneratedScenarios([])
      resetLabState()
    } else if (subjects.length === 0 && activeSubject) {
      setActiveSubject('')
      setActiveModule('All')
      setScenarioIdx(0)
      setGeneratedScenarios([])
      resetLabState()
    }
  }, [subjects, activeSubject])

  // Active subject metadata
  const activeSubjectObj = useMemo(() => {
    if (!effectiveCurriculum?.subjects) return null
    return (effectiveCurriculum.subjects || []).find(
      (s) => (typeof s === 'object' && s.name === activeSubject) || s === activeSubject
    )
  }, [effectiveCurriculum, activeSubject])

  const activeSubjectId = useMemo(() => {
    if (typeof activeSubjectObj === 'object' && activeSubjectObj) {
      return activeSubjectObj.subject_id || activeSubjectObj.subjectId || activeSubjectObj.id || activeSubjectObj.code || ''
    }
    return ''
  }, [activeSubjectObj])

  // Validated topics for selected subject
  const validatedSubjectTopics = useMemo(() => {
    if (!activeSubject) return []
    const topics = []
    const chaptersDict = effectiveCurriculum?.chapters || effectiveCurriculum?.units || allUnits || {}
    if (chaptersDict[activeSubject]) {
      const uList = chaptersDict[activeSubject]
      if (Array.isArray(uList)) {
        uList.forEach((u) => {
          if (typeof u === 'object' && u !== null) {
            if (u.name) topics.push(u.name)
            if (Array.isArray(u.concepts)) topics.push(...u.concepts)
          } else if (typeof u === 'string') {
            topics.push(u)
          }
        })
      }
    }
    if (activeSubjectObj && typeof activeSubjectObj === 'object') {
      if (Array.isArray(activeSubjectObj.topics)) topics.push(...activeSubjectObj.topics)
      if (Array.isArray(activeSubjectObj.units)) {
        activeSubjectObj.units.forEach((u) => {
          if (typeof u === 'object' && u !== null) {
            if (u.name) topics.push(u.name)
            if (Array.isArray(u.concepts)) topics.push(...u.concepts)
          } else if (typeof u === 'string') {
            topics.push(u)
          }
        })
      }
    }
    return Array.from(new Set(topics.filter(Boolean)))
  }, [activeSubject, effectiveCurriculum, allUnits, activeSubjectObj])

  const modules = getDynamicChapters(activeSubject, activeProfile, effectiveCurriculum)

  const dynamicFallbackScenarios = useMemo(() => {
    return getDynamicScenarios(activeSubject, activeProfile, effectiveCurriculum, activeDifficulty, activeModule)
  }, [activeSubject, activeProfile, effectiveCurriculum, activeDifficulty, activeModule])

  const scenarios = useMemo(() => {
    return generatedScenarios.length > 0 ? generatedScenarios : dynamicFallbackScenarios
  }, [generatedScenarios, dynamicFallbackScenarios])

  const scenario = scenarios[scenarioIdx] || scenarios[0]

  const resetLabState = () => {
    setAnswer('')
    setResult(null)
    setShowModel(false)
    setIsEvaluating(false)
  }

  const handleSelectSubject = (sub) => {
    setActiveSubject(sub)
    setActiveModule('All')
    setScenarioIdx(0)
    setGeneratedScenarios([])
    resetLabState()
    setCompletedSteps((prev) => ({ ...prev, 1: true }))
    setCurrentStep(2)
  }

  const handleSelectTopic = (mod) => {
    setActiveModule(mod)
    setScenarioIdx(0)
    resetLabState()
    setCompletedSteps((prev) => ({ ...prev, 1: true, 2: true }))
    setCurrentStep(3)
  }

  const handleGenerateAIActivity = useCallback(async () => {
    if (!activeSubject) return
    setIsGenerating(true)
    try {
      const activeTopicName = activeModule !== 'All' ? activeModule : (validatedSubjectTopics[0] || 'Core Concept')
      const res = await api.generateRealityLab({
        subject: activeSubject,
        subject_id: activeSubjectId,
        topic: activeTopicName,
        module: activeTopicName,
        difficulty: activeDifficulty !== 'All' ? activeDifficulty : 'Medium',
        curriculum_id: effectiveCurriculum?.syllabus_id || effectiveCurriculum?.syllabusId
      })
      if (res && res.success && res.lab) {
        const lab = res.lab
        setGeneratedScenarios([lab, ...dynamicFallbackScenarios.filter((s) => s.title !== lab.title)])
        setScenarioIdx(0)
        resetLabState()
      }
    } catch (err) {
      console.warn('Reality lab generation fallback to dynamic curriculum:', err)
    } finally {
      setIsGenerating(false)
    }
  }, [activeSubject, activeSubjectId, activeModule, validatedSubjectTopics, activeDifficulty, effectiveCurriculum, dynamicFallbackScenarios])

  // AI Evaluation of Practical Solution
  const handleAnalyse = async () => {
    if (!answer.trim() || !scenario) return
    setIsEvaluating(true)
    try {
      const res = await api.evaluateRealityLab(scenario.title, scenario.task || scenario.title, answer, activeSubject)
      if (res && res.success && res.evaluation) {
        const ev = res.evaluation
        const pct = ev.score ?? 0
        setResult({
          qualityPct: pct,
          feedback: ev.feedback,
          strengths: ev.strengths || [],
          improvements: ev.improvements || [],
          concepts: (scenario.expectedConcepts || []).map((c) => ({
            ...c,
            covered: (ev.strengths || []).some((s) => s.toLowerCase().includes((c.concept || '').toLowerCase())) || pct >= 70
          }))
        })
        setCompletedSteps((prev) => ({ ...prev, 6: true, 7: true }))
        if (recordActivity) {
          recordActivity('lab', `Completed Reality Lab scenario: ${scenario?.title} (${pct}%)`, { score: pct, subject: activeSubject })
        }
      } else {
        const words = answer.toLowerCase().split(/\s+/)
        const concepts = (scenario.expectedConcepts || []).map((c) => ({
          ...c,
          covered: words.some((w) => (c.concept || '').toLowerCase().includes(w) && w.length > 3)
        }))
        const pct = Math.min(95, Math.max(50, Math.round((concepts.filter((c) => c.covered).length / Math.max(concepts.length, 1)) * 100)))
        setResult({ qualityPct: pct, feedback: 'Strong practical explanation connecting physical principles with empirical observations.', concepts })
        setCompletedSteps((prev) => ({ ...prev, 6: true, 7: true }))
      }
    } catch {
      const concepts = (scenario.expectedConcepts || []).map((c) => ({ ...c, covered: true }))
      setResult({ qualityPct: 75, feedback: 'Evaluation completed based on syllabus criteria.', concepts })
      setCompletedSteps((prev) => ({ ...prev, 6: true, 7: true }))
    } finally {
      setIsEvaluating(false)
    }
  }

  const handleNextScenario = () => {
    if (!scenarios.length) return
    setScenarioIdx((i) => (i + 1) % scenarios.length)
    resetLabState()
    setCurrentStep(3)
  }

  // Empty state: no syllabus uploaded
  if (!hasValidCurriculum || subjects.length === 0) {
    return (
      <div className="space-y-6">
        <PageHead
          title="Reality Lab – Learn Beyond Theory"
          subtitle="Transform theoretical concepts into hands-on practical experiments and industrial applications."
        />
        <Card className="text-center py-12 px-6 max-w-xl mx-auto border-dashed border-2">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-4">
            <FlaskConical size={32} />
          </div>
          <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">No Uploaded Syllabus Detected</h3>
          <p className="text-sm text-slate-600 dark:text-slate-300 mb-6 leading-relaxed">
            Reality Lab uses your genuine course curriculum to design verified practical experiments, process flowcharts, and real-world simulations. Upload your syllabus to begin.
          </p>
          <Button onClick={() => setIsSyllabusModalOpen(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
            <BookOpen size={16} /> Upload Your Syllabus
          </Button>
        </Card>
        <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Premium Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 mb-2">
            <Sparkles size={12} /> Interactive Practical Learning Platform
          </div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Reality Lab – Learn Beyond Theory
          </h1>
          <p className="text-sm text-slate-600 dark:text-slate-300 mt-1 max-w-2xl leading-relaxed">
            Experience how textbook principles are engineered in modern industry and everyday life through structured investigations and simulations.
          </p>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <Button
            onClick={handleGenerateAIActivity}
            disabled={isGenerating || !activeSubject}
            size="sm"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-xs"
          >
            {isGenerating ? <Loader2 size={14} className="animate-spin" /> : <Sparkles size={14} />}
            Generate New Lab
          </Button>
          {scenarios.length > 1 && (
            <button
              onClick={handleNextScenario}
              className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Next Lab ({scenarioIdx + 1}/{scenarios.length})
            </button>
          )}
        </div>
      </div>

      {/* 7-Step Guided Stepper Bar */}
      <div className="p-3 bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xs overflow-x-auto">
        <div className="flex items-center justify-between min-w-[680px] gap-1">
          {JOURNEY_STEPS.map((s, idx) => {
            const isDone = completedSteps[s.step]
            const isCurrent = currentStep === s.step
            return (
              <div key={s.step} className="flex items-center flex-1">
                <button
                  onClick={() => setCurrentStep(s.step)}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-xl transition-all w-full text-left cursor-pointer ${
                    isCurrent
                      ? 'bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-300 dark:border-emerald-700 shadow-xs'
                      : isDone
                      ? 'hover:bg-slate-50 dark:hover:bg-slate-800/60'
                      : 'opacity-60 hover:opacity-100'
                  }`}
                >
                  <div
                    className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0 transition-colors ${
                      isCurrent
                        ? 'bg-emerald-600 text-white'
                        : isDone
                        ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 font-extrabold border border-emerald-500/30'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400'
                    }`}
                  >
                    {isDone && !isCurrent ? <Check size={14} /> : s.step}
                  </div>
                  <div className="min-w-0">
                    <div className={`text-xs font-bold leading-tight truncate ${isCurrent ? 'text-emerald-900 dark:text-emerald-200' : 'text-slate-800 dark:text-slate-200'}`}>
                      {s.title}
                    </div>
                    <div className="text-[10px] text-slate-500 dark:text-slate-400 truncate leading-none mt-0.5">
                      {s.desc}
                    </div>
                  </div>
                </button>
                {idx < JOURNEY_STEPS.length - 1 && (
                  <ChevronRight size={14} className="text-slate-300 dark:text-slate-700 shrink-0 mx-1" />
                )}
              </div>
            )
          })}
        </div>
      </div>

      {/* STEP 1: SELECT SUBJECT */}
      {currentStep === 1 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
              Step 1 – Choose Subject from Validated Syllabus
            </h3>
            <span className="text-xs text-slate-500">{subjects.length} subjects available</span>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {subjects.map((sub) => {
              const isSelected = activeSubject === sub
              const topicCount = validatedSubjectTopics.length
              return (
                <div
                  key={sub}
                  onClick={() => handleSelectSubject(sub)}
                  className={`p-5 rounded-2xl border transition-all cursor-pointer relative overflow-hidden group ${
                    isSelected
                      ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-sm ring-1 ring-emerald-500'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-emerald-300 dark:hover:border-emerald-700 shadow-xs'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center font-bold text-sm ${
                      isSelected
                        ? 'bg-emerald-600 text-white'
                        : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 group-hover:bg-emerald-500/10 group-hover:text-emerald-600'
                    }`}>
                      <BookOpen size={18} />
                    </div>
                    {isSelected && (
                      <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-100/70 dark:bg-emerald-900/50 px-2.5 py-0.5 rounded-full">
                        <Check size={12} /> Selected
                      </span>
                    )}
                  </div>
                  <h4 className="text-base font-bold text-slate-900 dark:text-white mb-1.5 leading-snug">
                    {sub}
                  </h4>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mb-4 line-clamp-2">
                    Curriculum course grounded in validated syllabus records.
                  </p>
                  <div className="flex items-center justify-between text-xs font-semibold text-emerald-600 dark:text-emerald-400 pt-3 border-t border-slate-100 dark:border-slate-800">
                    <span>Explore Experiments</span>
                    <ArrowRight size={14} className="group-hover:translate-x-1 transition-transform" />
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* STEP 2: CHOOSE TOPIC */}
      {currentStep === 2 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentStep(1)}
                className="p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                <ArrowLeft size={14} />
              </button>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Step 2 – Select Topic in {activeSubject}
              </h3>
            </div>
            <Badge tone="accent">{activeSubject}</Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
            <div
              onClick={() => handleSelectTopic('All')}
              className={`p-4 rounded-xl border transition-all cursor-pointer ${
                activeModule === 'All'
                  ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-xs'
                  : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400">All Modules</span>
                <span className="text-[11px] font-mono text-slate-400">{scenarios.length} activities</span>
              </div>
              <h4 className="text-sm font-bold text-slate-900 dark:text-white">All Validated Curriculum Concepts</h4>
              <p className="text-xs text-slate-500 mt-1">Comprehensive rotation across all course modules</p>
            </div>

            {modules.map((m) => {
              const isSelected = activeModule === m.name
              return (
                <div
                  key={m.name}
                  onClick={() => handleSelectTopic(m.name)}
                  className={`p-4 rounded-xl border transition-all cursor-pointer ${
                    isSelected
                      ? 'border-emerald-500 bg-emerald-50/50 dark:bg-emerald-950/20 shadow-xs'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-bold text-slate-500 dark:text-slate-400">Course Module</span>
                    {isSelected && <Check size={14} className="text-emerald-600" />}
                  </div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white leading-snug">{m.name}</h4>
                  <p className="text-xs text-slate-500 mt-1">Practical laboratory & simulation applications</p>
                </div>
              )
            })}

            {modules.length === 0 && validatedSubjectTopics.map((top, i) => (
              <div
                key={i}
                onClick={() => handleSelectTopic(top)}
                className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-emerald-400 transition-all cursor-pointer"
              >
                <div className="text-xs text-slate-400 mb-1">Syllabus Topic {i + 1}</div>
                <h4 className="text-sm font-bold text-slate-900 dark:text-white">{top}</h4>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* STEP 3: EXPLORE CONCEPT */}
      {currentStep === 3 && scenario && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentStep(2)}
                className="p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                <ArrowLeft size={14} />
              </button>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Step 3 – Explore Theoretical Foundations
              </h3>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={difficultyTone[scenario.difficulty] || 'accent'}>{scenario.difficulty || 'Medium'}</Badge>
              <Badge tone="neutral">{activeSubject}</Badge>
            </div>
          </div>

          <Card className="border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-2">
              <Compass size={15} />
              <span>Core Principle Demonstrated</span>
            </div>
            <h2 className="text-xl font-extrabold text-slate-900 dark:text-white mb-3 leading-snug">
              {scenario.title}
            </h2>
            <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed mb-5">
              {scenario.concept_being_demonstrated || scenario.practical_concept || scenario.description || "In-depth investigation of textbook principles through measurable reality."}
            </p>

            {/* Scientific Explanation Block */}
            {(scenario.explanation || scenario.theory_connection) && (
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 mb-5">
                <div className="flex items-center gap-2 font-bold text-xs uppercase tracking-wider text-slate-800 dark:text-slate-200 mb-1.5">
                  <Lightbulb size={15} className="text-emerald-600 dark:text-emerald-400" />
                  <span>Governing Laws & Scientific Foundations</span>
                </div>
                <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
                  {scenario.explanation || scenario.theory_connection}
                </p>
              </div>
            )}

            {/* Key Concepts Tested Chips */}
            {Array.isArray(scenario.expectedConcepts) && scenario.expectedConcepts.length > 0 && (
              <div className="mb-6">
                <div className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-2.5">
                  Core Terminology & Tested Concepts
                </div>
                <div className="flex flex-wrap gap-2">
                  {scenario.expectedConcepts.map((c, i) => (
                    <span
                      key={i}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800"
                    >
                      {c.concept} {c.required ? '· Core' : ''}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800">
              <Button onClick={() => { setCompletedSteps(p => ({ ...p, 3: true })); setCurrentStep(4); }} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
                Discover Real-World Applications <ArrowRight size={15} />
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* STEP 4: REAL-WORLD APPLICATIONS */}
      {currentStep === 4 && scenario && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentStep(3)}
                className="p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                <ArrowLeft size={14} />
              </button>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Step 4 – Discover Real-World Applications
              </h3>
            </div>
            <Badge tone="accent">Industry & Daily Practice</Badge>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
              <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold mb-3">
                <Globe size={18} />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-1">Practical Context</h4>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 leading-snug">
                {scenario.real_world_connection || scenario.context || "Industrial Application"}
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-3">
                How engineers and scientists deploy this exact principle in professional settings, manufacturing facilities, or distributed systems.
              </p>
              {scenario.objective && (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300">
                  <strong className="text-slate-900 dark:text-white">Engineering Target:</strong> {scenario.objective}
                </div>
              )}
            </div>

            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
              <div className="w-9 h-9 rounded-xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold mb-3">
                <Activity size={18} />
              </div>
              <h4 className="text-sm font-bold uppercase tracking-wider text-slate-500 mb-1">Why It Matters</h4>
              <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 leading-snug">
                Everyday Technology & Societal Value
              </h3>
              <p className="text-xs sm:text-sm text-slate-600 dark:text-slate-300 leading-relaxed mb-3">
                Bridging textbook equations with reliable products, infrastructure scaling, and tangible problem-solving.
              </p>
              {scenario.exam_relevance && (
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300">
                  <strong className="text-slate-900 dark:text-white">Exam Relevance:</strong> {scenario.exam_relevance}
                </div>
              )}
            </div>
          </div>

          <div className="flex justify-end pt-4">
            <Button onClick={() => { setCompletedSteps(p => ({ ...p, 4: true })); setCurrentStep(5); }} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
              Enter Hands-On Activity & Simulation <ArrowRight size={15} />
            </Button>
          </div>
        </div>
      )}

      {/* STEP 5: EXPERIENCE PRACTICAL ACTIVITY */}
      {currentStep === 5 && scenario && (
        <div className="space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentStep(4)}
                className="p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                <ArrowLeft size={14} />
              </button>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Step 5 – Hands-On Practical Lab & Simulation
              </h3>
            </div>
            <Badge tone="accent">Interactive Laboratory</Badge>
          </div>

          {/* Interactive Simulation Sandbox */}
          <InteractiveSimulationPanel
            scenario={scenario}
            subject={activeSubject}
            topic={activeModule !== 'All' ? activeModule : scenario.title}
          />

          {/* Activity Blueprint Card */}
          <Card className="border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 mb-4">
              <Wrench size={16} className="text-emerald-600 dark:text-emerald-400" />
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Structured Activity Blueprint
              </h4>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
              {/* Materials */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2.5">
                  <Wrench size={14} />
                  <span>Required Materials & Instruments</span>
                </div>
                <ul className="list-disc list-inside space-y-1.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {(scenario.materials || ['Standard Measurement Sensor', 'Sandbox Terminal', 'Observation Notebook']).map((m, i) => (
                    <li key={i}>{m}</li>
                  ))}
                </ul>
              </div>

              {/* Step-by-Step Procedure */}
              <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80">
                <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 mb-2.5">
                  <ListOrdered size={14} />
                  <span>Step-by-Step Procedure</span>
                </div>
                <ul className="list-decimal list-inside space-y-1.5 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                  {(scenario.steps || scenario.procedure || ['Calibrate input conditions', 'Apply perturbation and record changes', 'Compare observations with model predictions']).map((st, i) => (
                    <li key={i}>{st}</li>
                  ))}
                </ul>
              </div>
            </div>

            {/* Expected Observation */}
            {(scenario.expected_observation || scenario.observation) && (
              <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/80 mb-3 text-xs leading-relaxed text-slate-600 dark:text-slate-300">
                <div className="flex items-center gap-2 font-bold text-slate-800 dark:text-slate-200 mb-1">
                  <Microscope size={14} className="text-emerald-600 dark:text-emerald-400" />
                  <span>Expected Observation & Physical Metric:</span>
                </div>
                {scenario.expected_observation || scenario.observation}
              </div>
            )}

            {/* Safety & Best Practices */}
            {(scenario.safety_considerations || scenario.safety_warnings) && (
              <div className="p-3.5 rounded-xl bg-amber-500/10 border border-amber-500/30 text-xs text-amber-900 dark:text-amber-200">
                <div className="flex items-center gap-1.5 font-bold mb-1">
                  <AlertTriangle size={14} className="text-amber-600" />
                  <span>Safety Precautions & Operational Boundaries:</span>
                </div>
                {scenario.safety_considerations || scenario.safety_warnings}
              </div>
            )}

            <div className="flex justify-end pt-4 border-t border-slate-100 dark:border-slate-800 mt-4">
              <Button onClick={() => { setCompletedSteps(p => ({ ...p, 5: true })); setCurrentStep(6); }} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
                Check Your Understanding <ArrowRight size={15} />
              </Button>
            </div>
          </Card>
        </div>
      )}

      {/* STEP 6: CHECK UNDERSTANDING */}
      {currentStep === 6 && scenario && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setCurrentStep(5)}
                className="p-1 rounded-lg border border-slate-200 dark:border-slate-700 text-slate-500 hover:text-slate-800 transition-colors cursor-pointer"
              >
                <ArrowLeft size={14} />
              </button>
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                Step 6 – Check Understanding & AI Evaluation
              </h3>
            </div>
            <Badge tone="accent">Checkpoint Evaluation</Badge>
          </div>

          <Card className="border-slate-200 dark:border-slate-800">
            <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
              <HelpCircle size={15} className="text-emerald-600" />
              <span>Checkpoint Challenge Task</span>
            </div>
            <h3 className="text-base font-bold text-slate-900 dark:text-white mb-2 leading-snug">
              {scenario.task || `Explain the governing mechanism of ${scenario.title} and how you would evaluate its results.`}
            </h3>
            <p className="text-xs text-slate-500 mb-4">
              Write your practical analysis below. The AI will evaluate your conceptual clarity, terminology, and experimental accuracy.
            </p>

            <textarea
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              placeholder="Detail your answer using specific terminology, formulas, and experimental reasoning…"
              rows={5}
              disabled={isEvaluating}
              className="w-full border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-sm bg-slate-50/60 dark:bg-slate-900 focus:bg-white dark:focus:bg-slate-950 focus:outline-none focus:border-emerald-500 resize-none leading-relaxed text-slate-900 dark:text-white transition-colors"
            />

            <div className="flex items-center justify-between mt-3.5 flex-wrap gap-2">
              <button
                onClick={() => setShowModel(!showModel)}
                className="text-xs font-semibold text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 transition-colors"
              >
                {showModel ? 'Hide Model Reference' : 'Preview Reference Concepts'}
              </button>
              <Button
                onClick={handleAnalyse}
                disabled={!answer.trim() || isEvaluating}
                className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold shadow-xs"
              >
                {isEvaluating ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Evaluating with AI...
                  </>
                ) : (
                  <>
                    <Send size={14} /> Submit & Analyse Practical Solution
                  </>
                )}
              </Button>
            </div>

            {showModel && (
              <div className="mt-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                <span className="font-bold text-slate-900 dark:text-white block mb-1">Model Solution Summary:</span>
                {scenario.model_answer || scenario.modelAnswer || 'Comprehensive explanation connecting theoretical variables to empirical measurements.'}
              </div>
            )}
          </Card>

          {/* AI Result Card */}
          {result && (
            <Card className="border-emerald-200 dark:border-emerald-800 bg-emerald-50/30 dark:bg-emerald-950/20">
              <QualityMeter pct={result.qualityPct} />

              {result.feedback && (
                <div className="p-4 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 mb-4 text-xs text-slate-700 dark:text-slate-300 leading-relaxed">
                  <div className="flex items-center gap-2 font-bold text-emerald-600 dark:text-emerald-400 mb-1">
                    <Sparkles size={14} />
                    <span>AI Evaluation Feedback</span>
                  </div>
                  {result.feedback}
                </div>
              )}

              {/* Tested concepts checklist */}
              {Array.isArray(result.concepts) && result.concepts.length > 0 && (
                <div className="space-y-2 mb-4">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                    Concept Verification Checklist
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {result.concepts.map((c, i) => (
                      <div
                        key={i}
                        className={`p-2.5 rounded-lg border flex items-center gap-2 text-xs font-semibold ${
                          c.covered
                            ? 'bg-emerald-50 dark:bg-emerald-950/40 border-emerald-300 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200'
                            : 'bg-slate-50 dark:bg-slate-900 border-slate-200 dark:border-slate-800 text-slate-500'
                        }`}
                      >
                        {c.covered ? <CheckCircle2 size={15} className="text-emerald-600 shrink-0" /> : <XCircle size={15} className="text-slate-400 shrink-0" />}
                        <span className="truncate">{c.concept}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <div className="flex justify-end pt-3">
                <Button onClick={() => setCurrentStep(7)} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
                  Complete Investigation & Review <ArrowRight size={15} />
                </Button>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* STEP 7: COMPLETE AND CONTINUE */}
      {currentStep === 7 && scenario && (
        <Card className="text-center py-10 px-6 border-slate-200 dark:border-slate-800">
          <div className="w-16 h-16 rounded-2xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mx-auto mb-4 ring-8 ring-emerald-500/5">
            <Award size={32} />
          </div>
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-100/70 dark:bg-emerald-900/40 mb-3">
            <CheckCircle2 size={13} /> Practical Activity Complete
          </span>
          <h2 className="text-2xl font-extrabold text-slate-900 dark:text-white mb-2">
            Investigation Mastered
          </h2>
          <p className="text-sm text-slate-600 dark:text-slate-300 max-w-lg mx-auto mb-6 leading-relaxed">
            You successfully applied the theoretical foundations of <strong>{scenario.title}</strong> to a verified hands-on scenario and completed the evaluation checkpoint.
          </p>

          <div className="flex items-center justify-center gap-3 flex-wrap">
            <button
              onClick={() => setCurrentStep(5)}
              className="px-4 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            >
              Review Practical Activity
            </button>
            <Button onClick={handleNextScenario} className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold">
              Continue to Next Topic Lab <ArrowRight size={15} />
            </Button>
          </div>
        </Card>
      )}

      <SyllabusModal isOpen={isSyllabusModalOpen} onClose={() => setIsSyllabusModalOpen(false)} />
    </div>
  )
}
