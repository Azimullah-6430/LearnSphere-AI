/**
 * LearnSphere AI - Production API Service Client
 * Connects React Frontend to Flask/Render Backend.
 */

const isLocalhost = typeof window !== 'undefined' && 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 
  (isLocalhost && window.location.port !== '5000' ? 'http://localhost:5000' : '')

async function request(endpoint, options = {}, customBaseUrl = null) {
  try {
    const baseUrl = customBaseUrl !== null ? customBaseUrl : API_BASE_URL
    const url = `${baseUrl}${endpoint}`
    const headers = options.headers || {}
    
    let body = options.body
    if (body && !(body instanceof FormData) && typeof body !== 'string') {
      body = JSON.stringify(body)
      headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(url, { ...options, headers, body })
    const text = await res.text()
    let data = {}
    try {
      data = text ? JSON.parse(text) : {}
    } catch {
      // Response text was not JSON
    }

    if (!res.ok) {
      if (!data.error) {
        let friendlyError = `Server error (${res.status}).`
        if (res.status === 413) friendlyError = 'Uploaded files exceed server size limit. Please upload smaller files or compressed PDFs.'
        else if (res.status === 520 || res.status === 502 || res.status === 504) {
          friendlyError = `Backend server gateway error (${res.status}). The evaluation service took too long to respond.`
        } else if (text && text.length > 0 && text.length < 250 && !text.includes('<html')) {
          friendlyError = text
        }
        data = { success: false, error: friendlyError, status: res.status }
      }
    }

    return data
  } catch (err) {
    console.warn(`[LearnSphere API Notice] Endpoint ${endpoint}:`, err.message)
    return { success: false, error: err.message, isOffline: true }
  }
}

export const api = {
  // Auth & Permanent User Profile
  login: async (credentials) => {
    return request('/api/auth/login', {
      method: 'POST',
      body: credentials,
    })
  },

  register: async (formDataOrObj) => {
    return request('/api/auth/register', {
      method: 'POST',
      body: formDataOrObj,
    })
  },

  // Evaluation Pipeline
  evaluate: async (formData) => {
    const res = await request('/api/evaluate', {
      method: 'POST',
      body: formData,
    })

    if (res && res.success && res.result) {
      return res
    }
    if (res && res.error) {
      throw new Error(res.error)
    }
    throw new Error('Paper evaluation failed on server. Please check your uploaded files.')
  },

  getEvaluations: async (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/api/evaluations${query ? '?' + query : ''}`)
  },

  getEvaluationDetail: async (id) => {
    return request(`/api/evaluations/${id}`)
  },

  deleteEvaluation: async (id) => {
    return request(`/api/evaluations/${id}`, {
      method: 'DELETE'
    })
  },

  overrideEvaluationMarks: async (id, payload) => {
    return request(`/api/evaluations/${id}/override`, {
      method: 'PUT',
      body: payload
    })
  },

  downloadEvaluationPdf: (evalId) => {
    const url = `${API_BASE_URL}/api/evaluations/${evalId}/pdf`
    window.open(url, '_blank')
  },

  generatePdfReport: async (evalData) => {
    try {
      const url = `${API_BASE_URL}/api/generate-pdf`
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(evalData)
      })
      if (!res.ok) throw new Error('PDF generation failed.')
      const blob = await res.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = downloadUrl
      a.download = `Evaluation_Report_${(evalData?.subject || 'Paper').replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(downloadUrl)
    } catch (err) {
      console.error('PDF Report error:', err)
      alert('Could not download PDF report.')
    }
  },

  // Plagiarism
  getPlagiarismMatches: async () => {
    return request('/api/plagiarism/matches')
  },

  getPlagiarismSummary: async () => {
    return request('/api/plagiarism/summary')
  },

  // Students & Portfolio
  getStudents: async () => {
    return request('/api/students')
  },

  // Analytics & Dashboard
  getDashboardAnalytics: async (role = 'teacher', studentName = '') => {
    return request(`/api/analytics/dashboard?role=${role}&student_name=${encodeURIComponent(studentName)}`)
  },

  // AI Trainer & Tutor
  trainerChat: async (message, subject = 'Physics') => {
    return request('/api/trainer/chat', {
      method: 'POST',
      body: { message, subject },
    })
  },

  // Knowledge Challenge
  getChallengeQuiz: async (subject = 'Physics', module = 'All', difficulty = 'Medium') => {
    return request(`/api/challenge/quiz?subject=${encodeURIComponent(subject)}&module=${encodeURIComponent(module)}&difficulty=${encodeURIComponent(difficulty)}`)
  },

  submitChallenge: async (payload) => {
    return request('/api/challenge/submit', {
      method: 'POST',
      body: payload,
    })
  },

  // Self Evaluation API
  generateSelfEval: async (subject, topic, difficulty, syllabusContext) => {
    return request('/api/self-evaluation/generate', {
      method: 'POST',
      body: { subject, topic, difficulty, syllabus_context: syllabusContext }
    })
  },

  evaluateSelfEval: async (questionText, expectedConcept, studentResponse, subject) => {
    return request('/api/self-evaluation/evaluate', {
      method: 'POST',
      body: { question_text: questionText, expected_concept: expectedConcept, student_response: studentResponse, subject }
    })
  },

  // Reality Lab API
  generateRealityLab: async (subject, module, difficulty, syllabusContext) => {
    return request('/api/reality-lab/generate', {
      method: 'POST',
      body: { subject, module, difficulty, syllabus_context: syllabusContext }
    })
  },

  evaluateRealityLab: async (title, task, studentResponse, subject) => {
    return request('/api/reality-lab/evaluate', {
      method: 'POST',
      body: { title, task, student_response: studentResponse, subject }
    })
  },

  // Misconceptions & Memory
  getMisconceptions: async (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/api/misconceptions${query ? '?' + query : ''}`)
  },

  getMemoryCards: async (studentName = '') => {
    return request(`/api/memory/cards?student_name=${encodeURIComponent(studentName)}`)
  },

  reviewMemoryCard: async (cardId) => {
    return request('/api/memory/review', {
      method: 'POST',
      body: { id: cardId },
    })
  },

  // Notifications
  getNotifications: async (role = 'all', studentName = '') => {
    return request(`/api/notifications?role=${role}&student_name=${encodeURIComponent(studentName)}`)
  },

  markNotificationRead: async (id) => {
    return request(`/api/notifications/${id}/read`, {
      method: 'PUT',
    })
  },

  // Syllabus AI Analyzer
  analyzeSyllabus: async (formData) => {
    return request('/api/syllabus/analyze', {
      method: 'POST',
      body: formData,
    })
  },

  // Daily Fact-Checked Current Updates & Opportunities Feed
  getOpportunities: async (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`/api/opportunities${query ? '?' + query : ''}`)
  },

  // Teacher Action Center API
  getActionCenterItems: async () => {
    return request('/api/action-center')
  },

  updateActionCenterStatus: async (itemId, status) => {
    return request(`/api/action-center/${itemId}`, {
      method: 'PUT',
      body: { status }
    })
  }
}
