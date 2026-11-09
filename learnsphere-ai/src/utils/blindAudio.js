/**
 * LearnSphere AI - Blind Audio Utilities
 * Shared helper for Accessible Learning across Student Learning Features.
 */

// Natural Language Math Translation
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

  // Common Subscripts
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

// Text-to-Speech Narrator
export function speakText(text, label = 'Audio Reader') {
  if (typeof window === 'undefined' || !window.speechSynthesis) return

  const synth = window.speechSynthesis
  synth.cancel()

  if (!text || typeof text !== 'string') return

  const cleanText = text
    .replace(/###/g, '')
    .replace(/##/g, '')
    .replace(/#/g, '')
    .replace(/\*\*/g, '')
    .replace(/\*/g, '')
    .replace(/```[\s\S]*?```/g, ' Code block. ')
    .replace(/\$([^\$]+)\$/g, (_, expr) => narrateMathClient(expr))
    .replace(/\s+/g, ' ')
    .trim()

  if (!cleanText) return

  const utterance = new SpeechSynthesisUtterance(cleanText)
  utterance.rate = 1.0
  utterance.pitch = 1.0

  synth.speak(utterance)
}

export function stopSpeech() {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel()
  }
}
