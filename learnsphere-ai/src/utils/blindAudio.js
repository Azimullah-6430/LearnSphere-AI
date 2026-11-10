/**
 * LearnSphere AI - Blind Audio Utilities
 * Production-Grade Speech Synthesis & Math Verbalizer Engine.
 * 
 * Solves all known browser SpeechSynthesis issues:
 * 1. Chromium 14-second cutoff bug (via sentence chunking + keepalive pause/resume pulse).
 * 2. V8 Garbage Collection bug (persists active utterance on window.__activeUtterance).
 * 3. Cancel-then-speak collision (asynchronous cancel settling delay).
 * 4. Missing voices on initial load (async voiceschanged listener + English fallback).
 * 5. Browser autoplay gesture requirements (unlock on first user interaction).
 */

// ── Math & Academic Text Verbalizer ──────────────────────────────────────────
export function narrateMathClient(text) {
  if (!text || typeof text !== 'string') return ''
  let out = text

  // Derivatives
  out = out.replace(/\\frac\{d([a-zA-Z])\}\{d([a-zA-Z])\}/g, 'd $1 by d $2')
  out = out.replace(/\bdy\/dx\b/g, 'd y by d x')
  out = out.replace(/\bdu\/dx\b/g, 'd u by d x')

  // LaTeX Fractions: \frac{num}{den}
  out = out.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, 'the fraction $1 divided by $2')
  out = out.replace(/(\b\w+)\s*\/\s*(\b\w+)/g, '$1 divided by $2')

  // Square roots
  out = out.replace(/\\sqrt\{([^{}]+)\}/g, 'the square root of $1')

  // Powers
  out = out.replace(/([\w\)]+)\^2\b/g, '$1 squared')
  out = out.replace(/([\w\)]+)\^3\b/g, '$1 cubed')
  out = out.replace(/\^2\b/g, ' squared')
  out = out.replace(/\^3\b/g, ' cubed')
  out = out.replace(/([\w\)]+)\^\{([^}]+)\}/g, '$1 to the power of $2')

  // Common Subscripts & Circuit Notations
  out = out.replace(/([a-zA-Z])_\{th\}/gi, '$1 Thevenin')
  out = out.replace(/([a-zA-Z])_th\b/gi, '$1 Thevenin')
  out = out.replace(/([a-zA-Z])_\{eq\}/gi, '$1 equivalent')
  out = out.replace(/([a-zA-Z])_eq\b/gi, '$1 equivalent')
  out = out.replace(/([a-zA-Z])_\{N\}/gi, '$1 Norton')
  out = out.replace(/([a-zA-Z])_N\b/gi, '$1 Norton')
  out = out.replace(/([a-zA-Z])_\{([^}]+)\}/g, '$1 sub $2')

  // Symbols & Units
  out = out.replace(/\\cdot/g, ' times ')
  out = out.replace(/\\times/g, ' times ')
  out = out.replace(/\*/g, ' times ')
  out = out.replace(/\\pm/g, ' plus or minus ')
  out = out.replace(/\+/g, ' plus ')
  out = out.replace(/=/g, ' equals ')
  out = out.replace(/\\Omega/g, ' Ohms ')
  out = out.replace(/\\mu F/g, ' microfarads ')
  out = out.replace(/\\pi/g, ' pi ')
  out = out.replace(/\$/g, '')

  return out.replace(/\s+/g, ' ').trim()
}

export function cleanTextForSpeech(text) {
  if (!text || typeof text !== 'string') return ''
  return text
    .replace(/\$([^\$]+)\$/g, (_, expr) => narrateMathClient(expr))
    .replace(/###/g, '')
    .replace(/##/g, '')
    .replace(/#/g, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/```mermaid[\s\S]*?```/g, ' Diagram workflow is narrated below. ')
    .replace(/```[\s\S]*?```/g, ' Code block. ')
    .replace(/`([^`]+)`/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/\s+/g, ' ')
    .trim()
}

// ── Voice Management & Preloading ────────────────────────────────────────────
let cachedVoices = []

function loadVoices() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return []
  cachedVoices = window.speechSynthesis.getVoices() || []
  return cachedVoices
}

if (typeof window !== 'undefined' && window.speechSynthesis) {
  loadVoices()
  if (window.speechSynthesis.onvoiceschanged !== undefined) {
    window.speechSynthesis.onvoiceschanged = () => {
      loadVoices()
    }
  }
}

export function getBestVoice() {
  const voices = cachedVoices.length ? cachedVoices : loadVoices()
  if (!voices || !voices.length) return null

  // Prioritize natural sounding English voices across OS platforms
  const preferred = voices.find(
    (v) =>
      v.lang.startsWith('en') &&
      (v.name.includes('Natural') ||
        v.name.includes('Google') ||
        v.name.includes('Microsoft') ||
        v.name.includes('David') ||
        v.name.includes('Zira') ||
        v.name.includes('Jenny') ||
        v.name.includes('Samantha') ||
        v.name.includes('Daniel') ||
        v.default)
  )

  if (preferred) return preferred
  return voices.find((v) => v.lang.startsWith('en')) || voices[0] || null
}

// ── Text Chunking Engine ─────────────────────────────────────────────────────
// Splits long paragraphs into natural sentences/clauses of <= 200 chars to avoid Chromium timeouts
function splitIntoSpeechChunks(text) {
  if (!text || text.length <= 220) return [text]

  const sentences = text.match(/[^.!?;\n]+[.!?;\n]+|[^.!?;\n]+$/g) || [text]
  const chunks = []
  let currentChunk = ''

  for (const sentence of sentences) {
    const trimmed = sentence.trim()
    if (!trimmed) continue

    if (currentChunk.length + trimmed.length + 1 <= 220) {
      currentChunk = currentChunk ? `${currentChunk} ${trimmed}` : trimmed
    } else {
      if (currentChunk) chunks.push(currentChunk)
      // If a single sentence exceeds 220 chars, split on comma or words
      if (trimmed.length > 220) {
        const words = trimmed.split(' ')
        let subChunk = ''
        for (const w of words) {
          if (subChunk.length + w.length + 1 <= 200) {
            subChunk = subChunk ? `${subChunk} ${w}` : w
          } else {
            if (subChunk) chunks.push(subChunk)
            subChunk = w
          }
        }
        if (subChunk) currentChunk = subChunk
        else currentChunk = ''
      } else {
        currentChunk = trimmed
      }
    }
  }

  if (currentChunk) chunks.push(currentChunk)
  return chunks.length ? chunks : [text]
}

// ── Speech Controller State ──────────────────────────────────────────────────
let speechQueue = []
let isSpeakingActive = false
let currentUtteranceInstance = null
let keepAliveTimer = null
let activeOnEndCallback = null

function clearKeepAlive() {
  if (keepAliveTimer) {
    clearInterval(keepAliveTimer)
    keepAliveTimer = null
  }
}

function startKeepAlive() {
  clearKeepAlive()
  keepAliveTimer = setInterval(() => {
    if (typeof window === 'undefined' || !window.speechSynthesis) return
    const synth = window.speechSynthesis
    if (synth.speaking && !synth.paused) {
      // Periodic pulse to keep Chromium speech engine alive past 14 seconds
      synth.pause()
      synth.resume()
    }
  }, 9000)
}

function processNextChunk() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return

  const synth = window.speechSynthesis

  if (!speechQueue.length) {
    isSpeakingActive = false
    clearKeepAlive()
    currentUtteranceInstance = null
    if (typeof window !== 'undefined') {
      window.__activeUtterance = null
    }
    if (activeOnEndCallback) {
      const cb = activeOnEndCallback
      activeOnEndCallback = null
      try {
        cb()
      } catch (err) {
        console.warn('onEnd callback error:', err)
      }
    }
    return
  }

  const item = speechQueue.shift()
  const utterance = new SpeechSynthesisUtterance(item.text)
  utterance.rate = item.rate || 1.0
  utterance.pitch = item.pitch || 1.0

  const voice = getBestVoice()
  if (voice) {
    utterance.voice = voice
    utterance.lang = voice.lang || 'en-US'
  } else {
    utterance.lang = 'en-US'
  }

  // Prevent Garbage Collection in Chromium V8
  currentUtteranceInstance = utterance
  if (typeof window !== 'undefined') {
    window.__activeUtterance = utterance
  }

  utterance.onstart = () => {
    if (item.onStart && !isSpeakingActive) {
      try {
        item.onStart()
      } catch {}
    }
    isSpeakingActive = true
    startKeepAlive()
  }

  utterance.onend = () => {
    // Process next sentence
    processNextChunk()
  }

  utterance.onerror = (evt) => {
    // If canceled by user, don't treat as error
    if (evt.error === 'canceled' || evt.error === 'interrupted') {
      speechQueue = []
      isSpeakingActive = false
      clearKeepAlive()
      return
    }
    console.warn('[SpeechSynthesis] Chunk error:', evt.error)
    processNextChunk()
  }

  try {
    synth.speak(utterance)
  } catch (err) {
    console.warn('[SpeechSynthesis] speak error:', err)
    processNextChunk()
  }
}

// ── Public API ───────────────────────────────────────────────────────────────

/**
 * Stop any active speech and clear the queue.
 */
export function stopSpeech() {
  speechQueue = []
  isSpeakingActive = false
  activeOnEndCallback = null
  clearKeepAlive()

  if (typeof window !== 'undefined' && window.speechSynthesis) {
    const synth = window.speechSynthesis
    if (synth.paused) {
      synth.resume()
    }
    synth.cancel()
    window.__activeUtterance = null
  }
}

/**
 * Pause active speech.
 */
export function pauseSpeech() {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    const synth = window.speechSynthesis
    if (synth.speaking && !synth.paused) {
      synth.pause()
    }
  }
}

/**
 * Resume active speech.
 */
export function resumeSpeech() {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    const synth = window.speechSynthesis
    if (synth.paused) {
      synth.resume()
    }
  }
}

/**
 * Checks if speech synthesis is currently active.
 */
export function isSpeaking() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return false
  return isSpeakingActive || window.speechSynthesis.speaking
}

/**
 * Robust Text-to-Speech function that speaks text aloud.
 * @param {string} text - Raw or markdown text to speak.
 * @param {object|string} [options] - Options object or string label.
 * @param {function} [onComplete] - Callback when complete.
 */
export function speakText(text, options = {}, onComplete) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return

  const synth = window.speechSynthesis

  // Ensure speech synthesis is unlocked
  if (synth.paused) {
    synth.resume()
  }

  // Cancel prior speech
  stopSpeech()

  if (!text || typeof text !== 'string') return

  const clean = cleanTextForSpeech(text)
  if (!clean) return

  const opts = typeof options === 'string' ? { label: options } : options || {}
  const rate = typeof opts.rate === 'number' ? opts.rate : (opts.audioSpeed || 1.0)
  const pitch = typeof opts.pitch === 'number' ? opts.pitch : 1.0

  if (typeof onComplete === 'function') {
    activeOnEndCallback = onComplete
  } else if (typeof opts.onEnd === 'function') {
    activeOnEndCallback = opts.onEnd
  }

  // Chunk long text into natural sentences
  const chunks = splitIntoSpeechChunks(clean)
  speechQueue = chunks.map((chunkText, idx) => ({
    text: chunkText,
    rate,
    pitch,
    onStart: idx === 0 ? opts.onStart : null
  }))

  // Wait 40ms to let synth.cancel() settle in Chromium before starting queue
  setTimeout(() => {
    if (synth.paused) synth.resume()
    processNextChunk()
  }, 40)
}

/**
 * Unlocks Web Speech synthesis on first user interaction gesture.
 */
export function unlockAudio() {
  if (typeof window === 'undefined' || !window.speechSynthesis) return
  const synth = window.speechSynthesis
  if (synth.paused) {
    synth.resume()
  }
  loadVoices()
}
