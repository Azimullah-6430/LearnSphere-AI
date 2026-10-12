import React from 'react'
import { AlertTriangle, BookOpen, UploadCloud, CheckCircle2, ShieldAlert, ArrowRight, RefreshCw, Loader2, AlertOctagon, XCircle } from 'lucide-react'
import { Badge, Button } from './ui/Primitives.jsx'

/**
 * CurriculumReviewNotice
 * 
 * Strict UI gate displayed across:
 * 1. Personal Trainer
 * 2. Reality Lab
 * 3. Knowledge Challenge
 * 
 * Implements dedicated UI states for:
 * - NOT_UPLOADED: Prompt user to upload syllabus
 * - PROCESSING: Display processing/parsing progress
 * - EXTRACTION_FAILED: Display extraction error and retry CTA
 * - NEEDS_REVIEW: Display validation issues/mismatch review CTA
 */
export default function CurriculumReviewNotice({ 
  curriculum, 
  featureName = 'Learning Feature', 
  onOpenSyllabusModal 
}) {
  const status = (curriculum?.curriculumStatus || curriculum?.status || 'NOT_UPLOADED').toUpperCase()
  const reason = curriculum?.reason || curriculum?.mismatch_reason || 'Curriculum validation requires review before activation.'
  const sem = curriculum?.semester ? `Semester ${curriculum.semester}` : ''
  const program = curriculum?.degree || curriculum?.program || ''
  const department = curriculum?.department || ''

  // ── 1. NOT_UPLOADED STATE ──────────────────────────────────────────────────
  if (status === 'NOT_UPLOADED' || status === 'NOT_AVAILABLE' || status === 'UNCONFIGURED') {
    return (
      <div className="p-8 sm:p-12 max-w-2xl mx-auto text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-18 h-18 rounded-3xl bg-[var(--accent-soft)] text-[var(--accent)] flex items-center justify-center mx-auto shadow-xs border border-[var(--accent)]/20">
          <UploadCloud size={38} strokeWidth={1.8} />
        </div>

        <div>
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20 mb-3">
            <BookOpen size={14} /> Official Syllabus Grounding Required
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            Upload Your Official Syllabus to Unlock Courses
          </h2>
          <p className="text-sm sm:text-base text-[var(--text-soft)] mt-2.5 max-w-lg mx-auto leading-relaxed">
            <strong>{featureName}</strong> uses your official syllabus to ground curriculum topics, generate accredited exam drills, and prevent unverified AI outputs.
          </p>
        </div>

        {/* Academic Context Card */}
        <div className="p-5 rounded-2xl border border-[var(--border)] bg-[var(--surface)] text-left space-y-2.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[var(--text-soft)] uppercase tracking-wider text-xs">Target Academic Profile</span>
            <Badge tone="neutral">NO ACTIVE SYLLABUS</Badge>
          </div>
          <div className="text-sm font-semibold text-[var(--text)]">
            {program && <span>{program} · </span>}
            {department && <span>{department} · </span>}
            {sem ? <span className="text-[var(--accent)] font-bold">{sem}</span> : <span>Academic Profile Active</span>}
          </div>
          <div className="pt-2.5 border-t border-[var(--border)] text-xs text-[var(--text-soft)] leading-relaxed">
            Upload a PDF or document of your official course syllabus. Course modules and topics are automatically extracted and verified.
          </div>
        </div>

        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            onClick={onOpenSyllabusModal}
            className="w-full sm:w-auto shadow-sm"
          >
            <UploadCloud size={18} /> Upload Official Syllabus
          </Button>
        </div>

        <p className="text-xs text-[var(--text-faint)]">
          Upload your syllabus to unlock tailored questions, practice scenarios, and tutor coaching.
        </p>
      </div>
    )
  }

  // ── 2. PROCESSING STATE ───────────────────────────────────────────────────
  if (status === 'PROCESSING' || status === 'ANALYZING' || status === 'PARSING') {
    return (
      <div className="p-8 sm:p-12 max-w-2xl mx-auto text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-18 h-18 rounded-3xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mx-auto shadow-xs border border-indigo-500/20">
          <Loader2 size={38} className="animate-spin text-indigo-600 dark:text-indigo-400" />
        </div>

        <div>
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border border-indigo-500/20 mb-3">
            <RefreshCw size={14} className="animate-spin" /> Verifying Curriculum
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            Analyzing Your Syllabus Document
          </h2>
          <p className="text-sm sm:text-base text-[var(--text-soft)] mt-2.5 max-w-lg mx-auto leading-relaxed">
            Extracting course units, credit tables, and verifying curriculum completeness…
          </p>
        </div>

        <div className="w-full max-w-md mx-auto bg-[var(--surface-alt)] h-2.5 rounded-full overflow-hidden border border-[var(--border)]">
          <div className="h-full bg-indigo-500 rounded-full animate-pulse w-3/4 transition-all duration-1000" />
        </div>

        <p className="text-xs text-[var(--text-faint)]">
          This usually takes a few seconds. The learning modules will activate automatically upon completion.
        </p>
      </div>
    )
  }

  // ── 3. EXTRACTION_FAILED STATE ─────────────────────────────────────────────
  if (status === 'EXTRACTION_FAILED' || status === 'FAILED' || status === 'ERROR') {
    return (
      <div className="p-8 sm:p-12 max-w-2xl mx-auto text-center space-y-6 animate-in fade-in duration-300">
        <div className="w-18 h-18 rounded-3xl bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center mx-auto shadow-xs border border-rose-500/20">
          <AlertOctagon size={38} />
        </div>

        <div>
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/20 mb-3">
            <XCircle size={14} /> Extraction Error
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight">
            Syllabus Subject Extraction Failed
          </h2>
          <p className="text-sm sm:text-base text-[var(--text-soft)] mt-2.5 max-w-lg mx-auto leading-relaxed">
            We could not parse structured academic subjects from the uploaded document.
          </p>
        </div>

        <div className="p-5 rounded-2xl border border-rose-500/30 bg-rose-500/5 text-left text-xs md:text-sm space-y-2.5 shadow-xs">
          <div className="flex items-center justify-between">
            <span className="font-bold text-rose-700 dark:text-rose-300 uppercase tracking-wider text-xs">Failure Diagnostics</span>
            <Badge tone="error">FAILED</Badge>
          </div>
          <div className="text-[var(--text)] font-medium leading-relaxed">
            ⚠️ {reason}
          </div>
          <div className="pt-2.5 border-t border-rose-500/20 text-xs text-[var(--text-soft)]">
            Tips: Ensure your document contains clear printed text (avoid blurry mobile snapshots or password-protected files).
          </div>
        </div>

        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            size="lg"
            variant="danger"
            onClick={onOpenSyllabusModal}
            className="w-full sm:w-auto shadow-sm"
          >
            <UploadCloud size={18} /> Retry / Upload Clear Syllabus
          </Button>
        </div>
      </div>
    )
  }

  // ── 4. NEEDS_REVIEW / MISMATCH STATE ───────────────────────────────────────
  return (
    <div className="p-8 sm:p-12 max-w-2xl mx-auto text-center space-y-6 animate-in fade-in duration-300">
      <div className="w-18 h-18 rounded-3xl bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center mx-auto shadow-xs border border-amber-500/20">
        <ShieldAlert size={38} />
      </div>

      <div>
        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-300 border border-amber-500/20 mb-3">
          <AlertTriangle size={14} /> Verification Required
        </div>
        <h2 className="text-2xl sm:text-3xl font-extrabold text-[var(--text)] tracking-tight">
          {featureName} Locked: Verification Required
        </h2>
        <p className="text-sm sm:text-base text-[var(--text-soft)] mt-2.5 max-w-lg mx-auto leading-relaxed">
          The uploaded syllabus could not be fully reconciled with your active academic semester profile.
        </p>
      </div>

      <div className="p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5 text-left text-xs md:text-sm space-y-2.5 shadow-xs">
        <div className="flex items-center justify-between">
          <span className="font-bold text-[var(--text-soft)] uppercase tracking-wider text-xs">Academic Context</span>
          <Badge tone="warning">{status}</Badge>
        </div>
        <div className="text-sm font-semibold text-[var(--text)]">
          {program && <span>{program} · </span>}
          {department && <span>{department} · </span>}
          {sem ? <span className="text-[var(--accent)] font-bold">{sem}</span> : <span>Semester Profile Active</span>}
        </div>
        <div className="pt-2.5 border-t border-amber-500/20 text-xs md:text-sm text-[var(--text)] font-medium leading-relaxed">
          ⚠️ <strong>Issue Detected:</strong> {reason}
        </div>
      </div>

      <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
        <Button
          size="lg"
          onClick={onOpenSyllabusModal}
          className="w-full sm:w-auto shadow-sm"
        >
          <UploadCloud size={18} /> Review or Replace Syllabus
        </Button>
      </div>

      <p className="text-xs text-[var(--text-faint)]">
        Once confirmed, <strong>Personal Trainer</strong>, <strong>Reality Lab</strong>, and <strong>Knowledge Challenge</strong> will activate.
      </p>
    </div>
  )
}
