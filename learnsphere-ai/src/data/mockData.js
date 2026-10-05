/**
 * mockData.js — INTENTIONALLY EMPTY
 *
 * All fake student data, fake evaluations, fake plagiarism records, and fake
 * subject scores have been removed. This is a production education platform;
 * displaying fabricated academic data is not acceptable.
 *
 * If you need fixtures for automated tests, place them in:
 *   tests/fixtures/  (backend)
 *   src/__tests__/fixtures/  (frontend)
 * and import them only in test files.
 *
 * Any component that previously imported from this file now receives an empty
 * array and must show a proper empty state (e.g. "No evaluations yet").
 */

// All exports are empty so existing imports don't throw.
export const classTrend           = []
export const studentTrend         = []
export const subjectPerformance   = []
export const studentSubjectPerformance = []
export const recentEvaluationsTeacher  = []
export const recentEvaluationsStudent  = []
export const studentsNeedingSupport    = []
export const allStudents               = []
export const plagiarismMatches         = []
export const weakTopics                = []
export const evalQuestions             = []
export const academicMemory            = []
export const nextSteps                 = []

// Study techniques are UI constants (method labels), not academic data.
// Safe to keep here.
export const studyTechniques = [
  { id: 'feynman',      name: 'Feynman Technique',       desc: 'Explain it simply' },
  { id: 'pomodoro',     name: 'Pomodoro Focus',           desc: '25-min deep work' },
  { id: 'spaced',       name: 'Spaced Repetition',        desc: 'Review at intervals' },
  { id: 'active-recall',name: 'Active Recall',            desc: 'Test yourself' },
  { id: 'mindmap',      name: 'Mind Mapping',             desc: 'Visual connections' },
  { id: 'interleaving', name: 'Interleaved Practice',     desc: 'Mix subjects' },
]
