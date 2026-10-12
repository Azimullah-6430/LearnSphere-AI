import { useState, useEffect, useRef } from 'react'
import { PageHead, Card, Button, Badge } from '../components/ui/Primitives.jsx'
import { useApp } from '../context/AppContext.jsx'
import { getDynamicSubjects } from '../data/syllabusData.js'
import {
  Play,
  Pause,
  Square,
  Timer,
  Volume2,
  VolumeX,
  Sparkles,
  CheckCircle2,
  Maximize2,
  Minimize2,
  BookOpen,
  Award,
  Zap,
  RotateCcw
} from 'lucide-react'

// Web Audio Ambient Noise Generator (Pure JS Web Audio API - Zero Assets Required)
class AmbientAudioGenerator {
  constructor() {
    this.audioCtx = null
    this.noiseNode = null
    this.gainNode = null
    this.isPlaying = false
  }

  start(type = 'pink') {
    if (this.isPlaying) this.stop()
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext
      if (!AudioCtx) return
      this.audioCtx = new AudioCtx()

      const bufferSize = 2 * this.audioCtx.sampleRate
      const noiseBuffer = this.audioCtx.createBuffer(1, bufferSize, this.audioCtx.sampleRate)
      const output = noiseBuffer.getChannelData(0)

      let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0
      for (let i = 0; i < bufferSize; i++) {
        const white = Math.random() * 2 - 1
        if (type === 'pink') {
          b0 = 0.99886 * b0 + white * 0.0555179
          b1 = 0.99332 * b1 + white * 0.0750759
          b2 = 0.96900 * b2 + white * 0.1538520
          b3 = 0.86650 * b3 + white * 0.3104856
          b4 = 0.55000 * b4 + white * 0.5329522
          b5 = -0.7616 * b5 - white * 0.0168980
          output[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
          output[i] *= 0.11
          b6 = white * 0.115926
        } else if (type === 'binaural') {
          // Low gentle sine binaural pulse
          output[i] = Math.sin((i / this.audioCtx.sampleRate) * 2 * Math.PI * 180) * 0.15
        } else {
          output[i] = white * 0.08
        }
      }

      const whiteNoise = this.audioCtx.createBufferSource()
      whiteNoise.buffer = noiseBuffer
      whiteNoise.loop = true

      this.gainNode = this.audioCtx.createGain()
      this.gainNode.gain.setValueAtTime(0.08, this.audioCtx.currentTime)

      whiteNoise.connect(this.gainNode)
      this.gainNode.connect(this.audioCtx.destination)

      whiteNoise.start()
      this.noiseNode = whiteNoise
      this.isPlaying = true
    } catch (e) {
      console.warn('Web Audio Ambient synth notice:', e)
    }
  }

  stop() {
    try {
      if (this.noiseNode) {
        this.noiseNode.stop()
        this.noiseNode.disconnect()
      }
      if (this.audioCtx) {
        this.audioCtx.close()
      }
    } catch (e) {}
    this.noiseNode = null
    this.audioCtx = null
    this.isPlaying = false
  }
}

const ambientSynth = new AmbientAudioGenerator()

const DURATION_PRESETS = [
  { label: '25 Min', minutes: 25, sub: 'Pomodoro Focus' },
  { label: '45 Min', minutes: 45, sub: 'Deep Study' },
  { label: '60 Min', minutes: 60, sub: 'Exam Sprint' },
  { label: '15 Min', minutes: 15, sub: 'Quick Review' }
]

export default function Focus() {
  const { profile, syllabusData, recordActivity } = useApp()

  // Available subjects for focus
  const dynamicSubjects = getDynamicSubjects(profile, syllabusData)
  const [selectedSubject, setSelectedSubject] = useState(dynamicSubjects[0] || 'Academic Studies')
  const [customGoal, setCustomGoal] = useState('')

  // Duration & Timer State
  const [selectedDuration, setSelectedDuration] = useState(25) // minutes
  const [totalSeconds, setTotalSeconds] = useState(25 * 60)
  const [remainingSeconds, setRemainingSeconds] = useState(25 * 60)

  // Manual ON / OFF Focus Session State
  const [isSessionActive, setIsSessionActive] = useState(false) // ON / OFF
  const [isPaused, setIsPaused] = useState(false)
  const [isFullscreen, setIsFullscreen] = useState(false)

  // Ambient sound state: 'off' | 'pink' | 'binaural'
  const [ambientSound, setAmbientSound] = useState('off')

  // Session Summary Stats
  const [completedSessionsCount, setCompletedSessionsCount] = useState(0)
  const [totalFocusMinutesToday, setTotalFocusMinutesToday] = useState(0)
  const [sessionCompletedModal, setSessionCompletedModal] = useState(false)

  const timerRef = useRef(null)

  // Update timer target when duration changes (only if session is OFF)
  useEffect(() => {
    if (!isSessionActive) {
      const secs = selectedDuration * 60
      setTotalSeconds(secs)
      setRemainingSeconds(secs)
    }
  }, [selectedDuration, isSessionActive])

  // Timer Tick Interval
  useEffect(() => {
    if (isSessionActive && !isPaused) {
      timerRef.current = setInterval(() => {
        setRemainingSeconds((prev) => {
          if (prev <= 1) {
            clearInterval(timerRef.current)
            handleFinishSession(true)
            return 0
          }
          return prev - 1
        })
      }, 1000)
    } else {
      clearInterval(timerRef.current)
    }
    return () => clearInterval(timerRef.current)
  }, [isSessionActive, isPaused])

  // Handle Ambient Audio Toggle
  useEffect(() => {
    if (isSessionActive && ambientSound !== 'off') {
      ambientSynth.start(ambientSound)
    } else {
      ambientSynth.stop()
    }
    return () => ambientSynth.stop()
  }, [isSessionActive, ambientSound])

  useEffect(() => {
    if (!sessionCompletedModal) return
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') setSessionCompletedModal(false)
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [sessionCompletedModal])

  // Manual ON: Start Session
  const handleStartSession = () => {
    setIsSessionActive(true)
    setIsPaused(false)
    recordActivity('focus', `Started focus session on ${selectedSubject} (${selectedDuration}m)`)
  }

  // Manual OFF: End Session
  const handleStopSession = () => {
    ambientSynth.stop()
    clearInterval(timerRef.current)
    handleFinishSession(false)
  }

  // Finish session calculation
  const handleFinishSession = (completedNaturally = false) => {
    const elapsedSecs = totalSeconds - remainingSeconds
    const elapsedMins = Math.max(1, Math.round(elapsedSecs / 60))

    if (elapsedSecs >= 30) {
      setTotalFocusMinutesToday((prev) => prev + elapsedMins)
      setCompletedSessionsCount((prev) => prev + 1)
      recordActivity('focus', `Completed ${elapsedMins}m focus session: ${selectedSubject}`)
    }

    setIsSessionActive(false)
    setIsPaused(false)
    setRemainingSeconds(totalSeconds)

    if (completedNaturally) {
      setSessionCompletedModal(true)
    }
  }

  // Reset Timer
  const handleResetTimer = () => {
    setRemainingSeconds(totalSeconds)
    setIsPaused(false)
  }

  // Format time e.g., 25:00
  const minutesStr = Math.floor(remainingSeconds / 60).toString().padStart(2, '0')
  const secondsStr = (remainingSeconds % 60).toString().padStart(2, '0')

  // Progress percentage for circular ring
  const progressPercent = totalSeconds > 0 ? ((totalSeconds - remainingSeconds) / totalSeconds) * 100 : 0
  const strokeDashoffset = 440 - (440 * progressPercent) / 100

  return (
    <div className={`transition-all duration-300 ${isFullscreen ? 'fixed inset-0 z-50 bg-[var(--bg)] p-8 flex flex-col justify-between overflow-y-auto' : ''}`}>
      <PageHead
        title="Focus Session"
        subtitle="Structured study intervals, custom subject targets, and ambient focus acoustics for deep work."
        action={
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsFullscreen(!isFullscreen)}
              className="flex items-center gap-2 px-3.5 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface)] text-xs font-bold text-[var(--text-soft)] hover:text-[var(--text)] transition-colors shadow-xs cursor-pointer"
            >
              {isFullscreen ? <Minimize2 size={16} /> : <Maximize2 size={16} />}
              <span>{isFullscreen ? 'Exit Zen Mode' : 'Zen Fullscreen'}</span>
            </button>
          </div>
        }
      />

      {/* Main Focus Dashboard */}
      <div className="max-w-[880px] mx-auto space-y-6">
        {/* Session Inactive (OFF) Customizer Controls */}
        {!isSessionActive && (
          <Card className="border-[var(--border)] bg-[var(--surface)] shadow-sm p-6 sm:p-7">
            <div className="flex items-center justify-between mb-5 pb-3.5 border-b border-[var(--border)]">
              <div className="flex items-center gap-2.5 font-bold text-base text-[var(--text)]">
                <BookOpen size={19} className="text-[var(--accent)]" />
                <span>Configure Focus Session</span>
              </div>
              <Badge tone="neutral">Study Timer</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
              {/* Subject Selector */}
              <div>
                <label className="block text-xs font-bold text-[var(--text-soft)] mb-2 uppercase tracking-wider">
                  Target Subject
                </label>
                <select
                  value={selectedSubject}
                  onChange={(e) => setSelectedSubject(e.target.value)}
                  className="w-full px-3.5 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm font-semibold text-[var(--text)] focus:bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)]"
                >
                  {dynamicSubjects.map((sub) => (
                    <option key={sub} value={sub}>{sub}</option>
                  ))}
                </select>
              </div>

              {/* Optional Custom Topic / Goal */}
              <div>
                <label className="block text-xs font-bold text-[var(--text-soft)] mb-2 uppercase tracking-wider">
                  Specific Topic / Goal (Optional)
                </label>
                <input
                  type="text"
                  value={customGoal}
                  onChange={(e) => setCustomGoal(e.target.value)}
                  placeholder="e.g., Chapter 3 Derivations & Formulas"
                  className="w-full px-3.5 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-sm font-medium text-[var(--text)] focus:bg-[var(--surface)] focus:outline-none focus:border-[var(--accent)]"
                />
              </div>
            </div>

            {/* Duration Presets */}
            <div className="mb-6">
              <label className="block text-xs font-bold text-[var(--text-soft)] mb-2.5 uppercase tracking-wider">
                Session Duration
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {DURATION_PRESETS.map(({ label, minutes, sub }) => (
                  <button
                    key={minutes}
                    onClick={() => setSelectedDuration(minutes)}
                    className={`p-4 rounded-xl border text-left transition-all cursor-pointer ${
                      selectedDuration === minutes
                        ? 'bg-[var(--accent)] text-white border-[var(--accent)] shadow-sm'
                        : 'bg-[var(--surface-alt)] border-[var(--border)] text-[var(--text-soft)] hover:border-[var(--accent-dim)] hover:text-[var(--text)]'
                    }`}
                  >
                    <div className="text-base font-extrabold">{label}</div>
                    <div className={`text-xs font-medium mt-0.5 ${selectedDuration === minutes ? 'text-white/85' : 'text-[var(--text-faint)]'}`}>
                      {sub}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Ambient Audio Options */}
            <div className="flex items-center justify-between pt-5 border-t border-[var(--border)] flex-wrap gap-4">
              <div className="flex items-center gap-2.5 text-xs font-semibold text-[var(--text-soft)]">
                <Volume2 size={17} className="text-[var(--accent)]" />
                <span>Ambient Soundscape:</span>
                <select
                  value={ambientSound}
                  onChange={(e) => setAmbientSound(e.target.value)}
                  className="px-3 py-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-xs font-bold text-[var(--text)] focus:outline-none focus:border-[var(--accent)]"
                >
                  <option value="off">Off (Silent)</option>
                  <option value="pink">Pink Noise (Deep Focus)</option>
                  <option value="binaural">Binaural Alpha Waves (Concentration)</option>
                </select>
              </div>

              {/* Big Start Button */}
              <button
                onClick={handleStartSession}
                className="w-full md:w-auto px-8 py-3.5 rounded-xl text-sm font-bold bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] shadow-sm hover:shadow transition-all flex items-center justify-center gap-2 cursor-pointer"
              >
                <Play size={18} fill="currentColor" />
                <span>Start Focus Session</span>
              </button>
            </div>
          </Card>
        )}

        {/* Session Active (ON) View */}
        {isSessionActive && (
          <Card className="text-center py-10 px-6 border-2 border-[var(--accent)] bg-[var(--surface)] shadow-md relative overflow-hidden">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[var(--accent-soft)] text-[var(--accent)] font-bold text-[12px] mb-4">
              <span className="w-2 h-2 rounded-full bg-[var(--accent)]" />
              <span>Session In Progress</span>
            </div>

            <div className="text-[18px] font-extrabold text-[var(--text)] mb-1">
              {selectedSubject}
            </div>
            {customGoal && (
              <div className="text-[13.5px] text-[var(--text-soft)] font-medium mb-6">
                Goal: {customGoal}
              </div>
            )}

            {/* Circular Timer Display */}
            <div className="relative w-56 h-56 sm:w-64 sm:h-64 mx-auto my-6 flex items-center justify-center">
              <svg className="w-full h-full transform -rotate-90" viewBox="0 0 160 160">
                <circle
                  cx="80"
                  cy="80"
                  r="70"
                  stroke="var(--border)"
                  strokeWidth="8"
                  fill="transparent"
                />
                <circle
                  cx="80"
                  cy="80"
                  r="70"
                  stroke="var(--accent)"
                  strokeWidth="8"
                  strokeDasharray="440"
                  strokeDashoffset={strokeDashoffset}
                  strokeLinecap="round"
                  fill="transparent"
                  className="transition-all duration-1000 ease-linear"
                />
              </svg>

              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <div className="text-[44px] sm:text-[54px] font-extrabold tracking-tight tabular-nums text-[var(--text)] leading-none">
                  {minutesStr}:{secondsStr}
                </div>
                <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mt-2">
                  {isPaused ? 'PAUSED' : 'DEEP WORK'}
                </div>
              </div>
            </div>

            {/* Active Control Buttons */}
            <div className="flex items-center justify-center gap-4 mt-6 flex-wrap">
              <button
                onClick={() => setIsPaused(!isPaused)}
                className={`px-6 py-2.5 rounded-xl text-[13.5px] font-bold border transition-all flex items-center gap-2 ${
                  isPaused
                    ? 'bg-[var(--accent)] text-white border-[var(--accent)]'
                    : 'bg-[var(--surface)] border-[var(--border-strong)] text-[var(--text)] hover:bg-[var(--surface-alt)]'
                }`}
              >
                {isPaused ? <Play size={16} fill="currentColor" /> : <Pause size={16} />}
                <span>{isPaused ? 'Resume Session' : 'Pause'}</span>
              </button>

              <button
                onClick={handleResetTimer}
                className="px-4 py-2.5 rounded-xl text-[13.5px] font-semibold border border-[var(--border)] bg-[var(--surface)] text-[var(--text-soft)] hover:text-[var(--text)] transition-colors flex items-center gap-1.5"
              >
                <RotateCcw size={15} />
                <span>Reset</span>
              </button>

              {/* Manual OFF Button */}
              <button
                onClick={handleStopSession}
                className="px-6 py-2.5 rounded-xl text-[13.5px] font-bold bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)]/30 hover:bg-[var(--error)] hover:text-white transition-all flex items-center gap-2 cursor-pointer"
              >
                <Square size={15} fill="currentColor" />
                <span>End Session</span>
              </button>
            </div>
          </Card>
        )}

        {/* Minimalist Stats & Daily Progress */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <Card className="text-center p-4">
            <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
              Focus Time Today
            </div>
            <div className="text-[24px] font-extrabold text-[var(--accent)]">
              {totalFocusMinutesToday} Mins
            </div>
          </Card>

          <Card className="text-center p-4">
            <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
              Sessions Completed
            </div>
            <div className="text-[24px] font-extrabold text-[var(--text)]">
              {completedSessionsCount}
            </div>
          </Card>

          <Card className="text-center p-4">
            <div className="text-[11.5px] font-bold uppercase tracking-wider text-[var(--text-faint)] mb-1">
              Current Target
            </div>
            <div className="text-[14px] font-bold text-[var(--text)] truncate">
              {selectedSubject}
            </div>
          </Card>
        </div>
      </div>

      {/* Completion Modal */}
      {sessionCompletedModal && (
        <div 
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setSessionCompletedModal(false); }}
        >
          <Card 
            role="dialog"
            aria-modal="true"
            aria-labelledby="focus-modal-title"
            className="max-w-[420px] w-full text-center py-6 px-6 bg-[var(--surface)] border-2 border-[var(--success)] shadow-2xl"
          >
            <div className="w-14 h-14 rounded-full bg-[var(--success-soft)] text-[var(--success)] mx-auto mb-3 flex items-center justify-center">
              <CheckCircle2 size={32} />
            </div>
            <h2 id="focus-modal-title" className="text-[20px] font-extrabold mb-1">Great Focus Session!</h2>
            <p className="text-[13px] text-[var(--text-soft)] mb-6">
              You completed a <strong>{selectedDuration} minute</strong> deep work session on <strong>{selectedSubject}</strong>.
            </p>
            <Button
              onClick={() => setSessionCompletedModal(false)}
              className="w-full py-2.5 text-[14px] font-bold"
            >
              Continue Learning
            </Button>
          </Card>
        </div>
      )}
    </div>
  )
}
