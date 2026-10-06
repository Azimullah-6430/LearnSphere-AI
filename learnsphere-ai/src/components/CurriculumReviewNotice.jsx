import React from 'react'
import { AlertTriangle, BookOpen, UploadCloud, CheckCircle2, ShieldAlert, ArrowRight, RefreshCw } from 'lucide-react'
import { Badge, Button } from './ui/Primitives.jsx'

/**
 * CurriculumReviewNotice
 * 
 * Displayed across Personal Trainer, Reality Lab, and Knowledge Transfer
 * when the curriculum is in 'NEEDS_REVIEW', 'MISMATCH', or 'UNCONFIGURED' state.
 * 
 * Prevents partial activation of an unvalidated curriculum.
 */
export default function CurriculumReviewNotice({ 
  curriculum, 
  featureName = 'Learning Agent', 
  onOpenSyllabusModal 
}) {
  const status = curriculum?.status || 'NEEDS_REVIEW'
  const reason = curriculum?.reason || 'Curriculum validation requires review before activation.'
  const sem = curriculum?.semester ? `Semester ${curriculum.semester}` : ''
  const program = curriculum?.degree || curriculum?.program || ''
  const department = curriculum?.department || ''

  return (
    <div className="p-8 max-w-[680px] mx-auto text-center space-y-5 animate-in fade-in duration-300">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500 flex items-center justify-center mx-auto text-2xl shadow-inner">
        <ShieldAlert size={34} />
      </div>

      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/25 mb-2.5">
          <AlertTriangle size={13} /> Syllabus Requires Review
        </div>
        <h2 className="text-xl font-extrabold text-[var(--text)] tracking-tight">
          {featureName} Locked: Validated Curriculum Required
        </h2>
        <p className="text-sm text-[var(--text-soft)] mt-1.5 max-w-[540px] mx-auto leading-relaxed">
          To maintain strict academic integrity, <strong>{featureName}</strong> must consume your validated semester curriculum object.
        </p>
      </div>

      {/* Diagnosis Card */}
      <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 text-left text-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-bold text-[var(--text)] uppercase tracking-wider text-[10.5px]">Academic Context</span>
          <Badge tone={status === 'VALID' ? 'success' : 'warning'}>{status}</Badge>
        </div>
        <div className="text-[var(--text-soft)]">
          {program && <span>{program} · </span>}
          {department && <span>{department} · </span>}
          {sem ? <span className="font-semibold text-[var(--text)]">{sem}</span> : <span>Semester Not Configured</span>}
        </div>
        <div className="pt-2 border-t border-amber-500/20 text-[var(--text)] font-medium leading-relaxed">
          ⚠️ <strong>Issue Detected:</strong> {reason}
        </div>
      </div>

      <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
        <Button
          onClick={onOpenSyllabusModal}
          className="w-full sm:w-auto px-6 py-2.5 bg-[var(--accent)] text-white text-xs font-bold rounded-xl hover:bg-[var(--accent-dim)] inline-flex items-center justify-center gap-2 shadow-md"
        >
          <UploadCloud size={16} /> Review / Replace Syllabus
        </Button>
      </div>

      <p className="text-[11px] text-[var(--text-faint)]">
        Once validated or manually confirmed, <strong>Personal Trainer</strong>, <strong>Reality Lab</strong>, and <strong>Knowledge Transfer</strong> will instantly activate with identical semester subjects.
      </p>
    </div>
  )
}
