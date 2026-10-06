/**
 * LearnSphere AI - Production API Service
 *
 * Fixes applied:
 *   - credentials: 'include' on every request (required for session cookies)
 *   - authMe() added — used by AppContext on startup
 *   - logout() added
 *   - getMySyllabus() added — fetches server-persisted syllabus
 *   - evaluate() FormData field 'rubric' corrected to 'rubrics' to match backend
 *   - No localhost hardcoding in production — uses VITE_API_BASE_URL or same-origin
 */

const isLocalhost = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')

// In production on Render or any cloud host, frontend and backend share the same origin,
// so relative paths work automatically with cookies and zero CORS issues.
// In local development, the backend runs on :5000 while Vite dev server runs on :5173.
const rawBase = import.meta.env.VITE_API_BASE_URL || ''
const API_BASE_URL = !isLocalhost
  ? ''
  : (rawBase || (typeof window !== 'undefined' && window.location.port !== '5000' ? 'http://localhost:5000' : ''))

async function request(endpoint, options = {}) {
  try {
    const url     = `${API_BASE_URL}${endpoint}`
    const headers = { ...(options.headers || {}) }

    let body = options.body
    if (body && !(body instanceof FormData) && typeof body !== 'string') {
      body = JSON.stringify(body)
      headers['Content-Type'] = 'application/json'
    }

    const res = await fetch(url, {
      ...options,
      headers,
      body,
      credentials: 'include',   // always send session cookie
    })

    const text = await res.text()
    let data = {}
    try { data = text ? JSON.parse(text) : {} } catch { /* non-JSON response */ }

    if (!res.ok) {
      if (!data.error) {
        let msg = `Server error (${res.status}).`
        if (res.status === 401) msg = data.error || 'Not authenticated. Please sign in.'
        else if (res.status === 403) msg = data.error || 'Access denied.'
        else if (res.status === 413) msg = 'Files exceed server size limit. Please upload smaller files.'
        else if (res.status === 409) msg = data.error || 'Conflict — record already exists.'
        else if ([502, 503, 504, 520].includes(res.status)) msg = `Server temporarily unavailable (${res.status}). Please try again.`
        else if (text && text.length < 250 && !text.includes('<html')) msg = text
        data = { success: false, error: msg, status: res.status }
      }
    }

    return data
  } catch (err) {
    console.warn(`[API] ${endpoint}:`, err.message)
    return { success: false, error: err.message, isOffline: true }
  }
}

export const api = {

  // ── Auth ──────────────────────────────────────────────────────────────────

  /** Validate current session. Called by AppContext on every app load. */
  authMe: () => request('/api/auth/me'),

  login: (credentials) => request('/api/auth/login', {
    method: 'POST',
    body: credentials,
  }),

  register: (payload) => request('/api/auth/register', {
    method: 'POST',
    body: payload,
  }),

  /** Invalidate server session and clear cookie. */
  logout: () => request('/api/auth/logout', { method: 'POST' }),

  /** Update authenticated user profile in MongoDB. */
  updateProfile: (payload) => request('/api/user/profile', {
    method: 'PUT',
    body: payload,
  }),

  // ── Evaluation ────────────────────────────────────────────────────────────

  /**
   * Run evaluation pipeline (teacher or student portal — same engine).
   * FormData must include: question_paper, answer_script, role, subject,
   *   student_name, roll_number, assessment_title, level, board, stream, semester.
   * Optional: rubrics, syllabus.
   */
  evaluate: async (formData) => {
    const res = await request('/api/evaluate', { method: 'POST', body: formData })
    if (res && res.success && res.result) return res
    throw new Error(res?.error || 'Evaluation failed on server. Please check uploaded files.')
  },

  getEvaluations: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/evaluations${qs ? '?' + qs : ''}`)
  },

  getEvaluationDetail: (id) => request(`/api/evaluations/${id}`),

  deleteEvaluation: (id) => request(`/api/evaluations/${id}`, { method: 'DELETE' }),

  overrideEvaluationMarks: (id, payload) => request(`/api/evaluations/${id}/override`, {
    method: 'PUT',
    body: payload,
  }),

  downloadEvaluationPdf: (evalId) => {
    window.open(`${API_BASE_URL}/api/evaluations/${evalId}/pdf`, '_blank')
  },

  generatePdfReport: async (evalData) => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/generate-pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(evalData),
      })
      if (!res.ok) throw new Error('PDF generation failed.')
      const blob = await res.blob()
      const url  = window.URL.createObjectURL(blob)
      const a    = document.createElement('a')
      a.href = url
      a.download = `Evaluation_Report_${(evalData?.subject || 'Paper').replace(/\s+/g, '_')}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (err) {
      console.error('[API] PDF report:', err)
      alert('Could not download PDF report.')
    }
  },

  // ── Syllabus ──────────────────────────────────────────────────────────────

  /**
   * Analyze and PERSIST a syllabus. Returns { analysis, syllabus_id, syllabus }.
   * Backend stores it against the authenticated user.
   */
  analyzeSyllabus: (formData) => request('/api/syllabus/analyze', {
    method: 'POST',
    body: formData,
  }),

  /** Return the authenticated user's latest active semester-mapped syllabus. */
  getMySyllabus: () => request('/api/syllabus'),

  /** Return the authoritative active validated curriculum object consumed across all learning agents. */
  getActiveCurriculum: () => request('/api/curriculum/active'),

  /** Get complete source evidence for all subjects in the active curriculum. */
  getCurriculumEvidence: () => request('/api/syllabus/evidence'),

  /** Get source evidence for a specific course code or name. */
  getSubjectEvidence: (subjectId) => request(`/api/syllabus/subject-evidence/${encodeURIComponent(subjectId)}`),

  /** Confirm and activate a syllabus flagged as NEEDS_REVIEW or override. */
  confirmSyllabusOverride: (syllabusId) => request('/api/syllabus/confirm-override', {
    method: 'POST',
    body: { syllabus_id: syllabusId }
  }),

  /** Deactivate / archive syllabus. */
  deleteSyllabus: () => request('/api/syllabus', {
    method: 'DELETE'
  }),

  // ── Plagiarism ────────────────────────────────────────────────────────────

  getPlagiarismMatches:  () => request('/api/plagiarism/matches'),
  getPlagiarismSummary:  () => request('/api/plagiarism/summary'),

  // ── Students ──────────────────────────────────────────────────────────────

  getStudents: () => request('/api/students'),

  // ── Analytics ────────────────────────────────────────────────────────────

  getDashboardAnalytics: (role = 'teacher', studentName = '') =>
    request(`/api/analytics/dashboard?role=${role}&student_name=${encodeURIComponent(studentName)}`),

  getStudentAnalytics: (studentId = '') =>
    request(`/api/analytics/student${studentId ? `?student_id=${encodeURIComponent(studentId)}` : ''}`),

  // ── AI Trainer ────────────────────────────────────────────────────────────

  trainerChat: (payload) => request('/api/trainer/chat', { method: 'POST', body: payload }),

  // ── Knowledge Challenge ───────────────────────────────────────────────────

  getChallengeQuiz: (subject = 'General', module = 'All', difficulty = 'Medium') =>
    request(`/api/challenge/quiz?subject=${encodeURIComponent(subject)}&module=${encodeURIComponent(module)}&difficulty=${encodeURIComponent(difficulty)}`),

  submitChallenge: (payload) => request('/api/challenge/submit', { method: 'POST', body: payload }),

  // ── Self Evaluation (uses same backend engine as teacher portal) ──────────

  generateSelfEval: (subject, topic, difficulty, syllabusContext) =>
    request('/api/self-evaluation/generate', {
      method: 'POST',
      body: { subject, topic, difficulty, syllabus_context: syllabusContext },
    }),

  evaluateSelfEval: (questionText, expectedConcept, studentResponse, subject) =>
    request('/api/self-evaluation/evaluate', {
      method: 'POST',
      body: {
        question_text: questionText,
        expected_concept: expectedConcept,
        student_response: studentResponse,
        subject,
      },
    }),

  // ── Reality Lab ───────────────────────────────────────────────────────────

  generateRealityLab: (subject, module, difficulty, syllabusContext) =>
    request('/api/reality-lab/generate', {
      method: 'POST',
      body: { subject, module, difficulty, syllabus_context: syllabusContext },
    }),

  evaluateRealityLab: (title, task, studentResponse, subject) =>
    request('/api/reality-lab/evaluate', {
      method: 'POST',
      body: { title, task, student_response: studentResponse, subject },
    }),

  // ── Misconceptions ────────────────────────────────────────────────────────

  getMisconceptions: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/misconceptions${qs ? '?' + qs : ''}`)
  },

  // ── Memory Cards ──────────────────────────────────────────────────────────

  getMemoryCards:   (studentName = '') =>
    request(`/api/memory/cards?student_name=${encodeURIComponent(studentName)}`),
  reviewMemoryCard: (cardId) =>
    request('/api/memory/review', { method: 'POST', body: { id: cardId } }),

  // ── Notifications ─────────────────────────────────────────────────────────

  getNotifications: (role = 'all', studentName = '') =>
    request(`/api/notifications?role=${role}&student_name=${encodeURIComponent(studentName)}`),
  markNotificationRead: (id) =>
    request(`/api/notifications/${id}/read`, { method: 'PUT' }),

  // ── Opportunities ─────────────────────────────────────────────────────────

  getOpportunities: (params = {}) => {
    const qs = new URLSearchParams(params).toString()
    return request(`/api/opportunities${qs ? '?' + qs : ''}`)
  },

  // ── Action Center ─────────────────────────────────────────────────────────

  getActionCenterItems: () => request('/api/action-center'),

  updateActionCenterStatus: (itemId, status) =>
    request(`/api/action-center/${itemId}`, { method: 'PUT', body: { status } }),
}
