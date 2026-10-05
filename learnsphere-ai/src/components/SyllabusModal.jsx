import { useState } from 'react'
import { UploadCloud, FileText, Sparkles, X, CheckCircle, BookOpen } from 'lucide-react'
import { api } from '../services/api.js'
import { useApp } from '../context/AppContext.jsx'

export default function SyllabusModal({ isOpen, onClose }) {
  const { user, profile, setSyllabusData } = useApp()
  const [file, setFile] = useState(null)
  const [pastedText, setPastedText] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  if (!isOpen) return null

  const handleUploadAndAnalyze = async (e) => {
    e.preventDefault()
    if (!file && !pastedText.trim()) {
      setError('Please select a syllabus PDF/image or paste syllabus text.')
      return
    }

    setLoading(true)
    setError('')
    try {
      const activeProfile = { ...user, ...profile }
      const formData = new FormData()
      if (file) formData.append('syllabus_file', file)
      if (pastedText) formData.append('text', pastedText)
      
      formData.append('level', activeProfile.level || 'college')
      formData.append('semester', activeProfile.semester || '5')
      formData.append('classLevel', activeProfile.grade_level || activeProfile.classLevel || '12')
      formData.append('stream', activeProfile.stream || '')
      formData.append('domain', activeProfile.domain || '')

      const res = await api.analyzeSyllabus(formData)
      if (res && res.success && res.analysis) {
        setResult(res.analysis)
        // Update in-memory context; server has already persisted the full record
        if (setSyllabusData) setSyllabusData(res.analysis)
      } else {
        setError(res?.error || 'Failed to analyze syllabus. Please try again.')
      }
    } catch (err) {
      setError('Error analyzing syllabus document.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[var(--surface)] border border-[var(--border-strong)] rounded-2xl w-full max-w-[560px] p-6 shadow-2xl overflow-y-auto max-h-[90vh]">
        <div className="flex items-center justify-between pb-4 border-b border-[var(--border)]">
          <div className="flex items-center gap-2.5">
            <div className="w-9 h-9 rounded-xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center">
              <BookOpen size={20} />
            </div>
            <div>
              <h3 className="font-bold text-base">Upload & Analyze Curriculum & Syllabus</h3>
              <p className="text-xs text-[var(--text-soft)]">Extract subjects, units, learning outcomes & evaluation guidelines via Gemini AI</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 text-[var(--text-soft)] hover:text-[var(--text)] rounded-lg">
            <X size={18} />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-[var(--warning-soft)] border border-[var(--warning)] text-xs font-semibold text-[var(--warning)] rounded-lg">
            {error}
          </div>
        )}

        {!result ? (
          <form onSubmit={handleUploadAndAnalyze} className="mt-5 space-y-4">
            <div>
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-2">Option A: Upload Curriculum / Syllabus Document (PDF / Image)</label>
              <label className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-[var(--border-strong)] rounded-xl bg-[var(--surface-alt)] hover:border-[var(--accent)] transition-colors cursor-pointer text-center">
                <UploadCloud size={28} className="text-[var(--accent)] mb-2" />
                <span className="text-xs font-bold text-[var(--text)]">{file ? file.name : 'Click to select PDF, PNG or JPG'}</span>
                <span className="text-[11px] text-[var(--text-faint)] mt-1">Official curriculum regulation or course syllabus blueprint</span>
                <input 
                  type="file" 
                  accept=".pdf,.png,.jpg,.jpeg" 
                  className="hidden" 
                  onChange={(e) => e.target.files[0] && setFile(e.target.files[0])} 
                />
              </label>
            </div>

            <div>
              <label className="block text-xs font-semibold text-[var(--text-soft)] mb-1.5">Option B: Paste Curriculum / Syllabus Text & Topics</label>
              <textarea
                rows={3}
                placeholder="Paste course subjects, units, learning outcomes, or curriculum guidelines here..."
                value={pastedText}
                onChange={(e) => setPastedText(e.target.value)}
                className="w-full p-3 rounded-lg border border-[var(--border-strong)] bg-[var(--surface)] text-xs focus:outline-none focus:border-[var(--accent)] resize-none"
              />
            </div>

            <div className="pt-2 flex justify-end gap-2.5">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 text-xs font-semibold rounded-lg border border-[var(--border)] hover:bg-[var(--surface-alt)]"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)] flex items-center gap-2"
              >
                <Sparkles size={15} />
                {loading ? 'Analyzing with Gemini AI...' : 'Analyze Syllabus'}
              </button>
            </div>
          </form>
        ) : (
          <div className="mt-5 space-y-4">
            <div className="p-3 bg-[var(--accent-soft)] rounded-xl flex items-center gap-2 text-xs font-bold text-[var(--accent)]">
              <CheckCircle size={18} />
              <span>Syllabus analyzed successfully! Extracted topics loaded into your profile.</span>
            </div>

            <div className="bg-[var(--surface-alt)] p-4 rounded-xl text-xs space-y-3">
              <div>
                <span className="font-bold text-[var(--text)] uppercase tracking-wider block mb-1">Extracted Course Title</span>
                <div className="font-semibold text-sm text-[var(--accent)]">{result.course_title}</div>
              </div>

              <div>
                <span className="font-bold text-[var(--text)] uppercase tracking-wider block mb-1">Extracted Subjects</span>
                <div className="flex flex-wrap gap-1.5">
                  {(result.extracted_subjects || []).map((s, i) => (
                    <span key={i} className="px-2.5 py-1 bg-[var(--surface)] border border-[var(--border)] rounded-md font-semibold text-[11px]">
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              <div>
                <span className="font-bold text-[var(--text)] uppercase tracking-wider block mb-1">Key Topics & Concepts</span>
                <ul className="list-disc pl-4 space-y-0.5 text-[var(--text-soft)]">
                  {(result.key_topics || []).slice(0, 4).map((t, i) => (
                    <li key={i}>{t}</li>
                  ))}
                </ul>
              </div>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => { setResult(null); onClose(); }}
                className="px-5 py-2 text-xs font-semibold rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-dim)]"
              >
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
