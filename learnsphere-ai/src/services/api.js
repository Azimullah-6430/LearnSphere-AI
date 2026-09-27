/**
 * LearnSphere AI - API Service Client
 * Connects frontend views seamlessly to the Flask backend with automatic error resilience.
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
          friendlyError = `Backend server gateway error (${res.status}). The evaluation service took too long to respond or returned an empty response.`
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

function generateLocalEvaluationFallback(formData) {
  throw new Error('Evaluation server is unreachable. Please verify backend service.')
}

export const api = {
  // Auth & Permanent User Profile
  login: async (credentials) => {
    const res = await request('/api/auth/login', {
      method: 'POST',
      body: credentials,
    })
    
    if (res && res.success && res.user) {
      return res
    }

    // Offline / Local Storage fallback authentication against created accounts
    try {
      const savedUsers = JSON.parse(localStorage.getItem('learnsphere_registered_users') || '[]')
      const targetEmail = (credentials.email || '').trim().toLowerCase()
      const targetPassword = credentials.password || ''
      
      const foundUser = savedUsers.find(
        (u) => u.email.trim().toLowerCase() === targetEmail
      )

      if (!foundUser) {
        return {
          success: false,
          error: 'Account does not exist. Please create an account first to log in.'
        }
      }

      if (foundUser.password !== targetPassword) {
        return {
          success: false,
          error: 'Incorrect password. Please verify your password.'
        }
      }

      return {
        success: true,
        user: foundUser
      }
    } catch {}

    return {
      success: false,
      error: res.error || 'Account does not exist. Please create an account first to log in.'
    }
  },

  register: async (formDataOrObj) => {
    const res = await request('/api/auth/register', {
      method: 'POST',
      body: formDataOrObj,
    })

    let registeredUser = null
    if (res && res.success && res.user) {
      registeredUser = res.user
    } else {
      const name = formDataOrObj.name || formDataOrObj.email?.split('@')[0] || 'User'
      const role = formDataOrObj.role || 'teacher'
      const initials = name.split(' ').map((n) => n[0]).join('').slice(0, 2).toUpperCase()
      registeredUser = {
        id: `usr_${Date.now()}`,
        name,
        email: (formDataOrObj.email || '').trim().toLowerCase(),
        password: formDataOrObj.password,
        role,
        teacherLevel: formDataOrObj.teacherLevel || formDataOrObj.level || 'school',
        initials,
        ...formDataOrObj
      }
    }

    // Persist registered user locally as well
    try {
      const savedUsers = JSON.parse(localStorage.getItem('learnsphere_registered_users') || '[]')
      const existingIdx = savedUsers.findIndex((u) => u.email.toLowerCase() === registeredUser.email.toLowerCase())
      if (existingIdx >= 0) {
        savedUsers[existingIdx] = registeredUser
      } else {
        savedUsers.push(registeredUser)
      }
      localStorage.setItem('learnsphere_registered_users', JSON.stringify(savedUsers))
    } catch {}

    return { success: true, user: registeredUser }
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
    let remoteEvals = []
    try {
      const query = new URLSearchParams(params).toString()
      const res = await request(`/api/evaluations${query ? '?' + query : ''}`)
      if (res && res.success && Array.isArray(res.evaluations)) {
        remoteEvals = res.evaluations
      }
    } catch (err) {
      console.warn('[LearnSphere API] Remote evaluations query offline, loading stored local evaluations.')
    }

    let localEvals = []
    try {
      localEvals = JSON.parse(localStorage.getItem('learnsphere_local_evaluations') || '[]')
    } catch {}

    const combined = [...remoteEvals]
    for (const loc of localEvals) {
      if (!combined.some(r => (r.id && r.id === loc.id) || (r._id && r._id === loc.id))) {
        combined.push(loc)
      }
    }

    return { success: true, evaluations: combined }
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
  getChallengeQuiz: async (subject = 'Physics') => {
    return request(`/api/challenge/quiz?subject=${encodeURIComponent(subject)}`)
  },

  submitChallenge: async (payload) => {
    return request('/api/challenge/submit', {
      method: 'POST',
      body: payload,
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
