import React from 'react'
import { AlertTriangle, BookOpen, UploadCloud, CheckCircle2, ShieldAlert, ArrowRight, RefreshCw, Loader2, AlertOctagon, XCircle } from 'lucide-react'
import { Badge, Button } from './ui/Primitives.jsx'

/**
 * CurriculumReviewNotice
 * 
 * Strict UI gate displayed across:
 * 1. Personal Trainer
 * 2. Reality Lab
 * 3. Knowledge Transfer
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
      <div className="p-8 max-w-[640px] mx-auto text-center space-y-5 animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-2xl bg-[var(--accent)]/10 border border-[var(--accent)]/25 text-[var(--accent)] flex items-center justify-center mx-auto text-2xl shadow-inner">
          <UploadCloud size={34} />
        </div>

        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-[var(--accent)]/10 text-[var(--accent)] border border-[var(--accent)]/20 mb-2.5">
            <BookOpen size={13} /> Syllabus Required · NOT_UPLOADED
          </div>
          <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight">
            Upload Your Syllabus to Unlock Subjects
          </h2>
          <p className="text-sm text-[var(--text-soft)] mt-2 max-w-[500px] mx-auto leading-relaxed">
            <strong>{featureName}</strong> uses your official syllabus to generate accredited curriculum subjects, study strategies, and exam scenarios.
          </p>
        </div>

        {/* Info card */}
        <div className="p-4 rounded-xl border border-[var(--border)] bg-[var(--surface-alt)] text-left text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold text-[var(--text)] uppercase tracking-wider text-[10.5px]">Target Academic Context</span>
            <Badge tone="default">NO SYLLABUS</Badge>
          </div>
          <div className="text-[var(--text-soft)]">
            {program && <span>{program} · </span>}
            {department && <span>{department} · </span>}
            {sem ? <span className="font-semibold text-[var(--text)]">{sem}</span> : <span>Semester Profile Active</span>}
          </div>
          <div className="pt-2 border-t border-[var(--border)] text-[var(--text-faint)] leading-relaxed">
            💡 Upload a PDF or text document of your syllabus. Subjects and units will be automatically extracted and validated.
          </div>
        </div>

        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            onClick={onOpenSyllabusModal}
            className="w-full sm:w-auto px-7 py-3 bg-[var(--accent)] text-white text-xs font-bold rounded-xl hover:bg-[var(--accent-dim)] inline-flex items-center justify-center gap-2 shadow-lg hover:shadow-xl transition-all"
          >
            <UploadCloud size={16} /> Upload Official Syllabus
          </Button>
        </div>

        <p className="text-[11px] text-[var(--text-faint)]">
          Zero mock or generic subjects will be shown until your accredited syllabus is uploaded and verified.
        </p>
      </div>
    )
  }

  // ── 2. PROCESSING STATE ───────────────────────────────────────────────────
  if (status === 'PROCESSING' || status === 'ANALYZING' || status === 'PARSING') {
    return (
      <div className="p-8 max-w-[640px] mx-auto text-center space-y-5 animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/25 text-indigo-500 flex items-center justify-center mx-auto text-2xl shadow-inner">
          <Loader2 size={34} className="animate-spin text-indigo-500" />
        </div>

        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/25 mb-2.5">
            <RefreshCw size={13} className="animate-spin" /> Processing · PROCESSING
          </div>
          <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight">
            Analyzing Your Syllabus Document
          </h2>
          <p className="text-sm text-[var(--text-soft)] mt-2 max-w-[500px] mx-auto leading-relaxed">
            Our AI parser is extracting course codes, theory units, labs, and performing anti-hallucination verification...
          </p>
        </div>

        {/* Progress bar animation */}
        <div className="w-full max-w-[400px] mx-auto bg-[var(--surface-alt)] h-2 rounded-full overflow-hidden border border-[var(--border)]">
          <div className="h-full bg-indigo-500 rounded-full animate-pulse w-3/4 transition-all duration-1000" />
        </div>

        <p className="text-[11.5px] text-[var(--text-faint)]">
          This usually takes 3–8 seconds. Your learning agents will automatically activate upon completion.
        </p>
      </div>
    )
  }

  // ── 3. EXTRACTION_FAILED STATE ─────────────────────────────────────────────
  if (status === 'EXTRACTION_FAILED' || status === 'FAILED' || status === 'ERROR') {
    return (
      <div className="p-8 max-w-[640px] mx-auto text-center space-y-5 animate-in fade-in duration-300">
        <div className="w-16 h-16 rounded-2xl bg-rose-500/10 border border-rose-500/25 text-rose-500 flex items-center justify-center mx-auto text-2xl shadow-inner">
          <AlertOctagon size={34} />
        </div>

        <div>
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/25 mb-2.5">
            <XCircle size={13} /> Extraction Error · EXTRACTION_FAILED
          </div>
          <h2 className="text-2xl font-extrabold text-[var(--text)] tracking-tight">
            Syllabus Subject Extraction Failed
          </h2>
          <p className="text-sm text-[var(--text-soft)] mt-2 max-w-[520px] mx-auto leading-relaxed">
            We were unable to extract structured academic subjects or course tables from the uploaded file.
          </p>
        </div>

        <div className="p-4 rounded-xl border border-rose-500/30 bg-rose-500/5 text-left text-xs space-y-2">
          <div className="flex items-center justify-between">
            <span className="font-bold text-rose-600 dark:text-rose-400 uppercase tracking-wider text-[10.5px]">Failure Diagnostic</span>
            <Badge tone="error">FAILED</Badge>
          </div>
          <div className="text-[var(--text)] font-medium leading-relaxed">
            ⚠️ {reason}
          </div>
          <div className="pt-2 border-t border-rose-500/20 text-[var(--text-faint)]">
            Tips: Ensure your PDF contains clear text or standard syllabus tables (not blurry photos or password-protected documents).
          </div>
        </div>

        <div className="pt-2 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Button
            onClick={onOpenSyllabusModal}
            className="w-full sm:w-auto px-7 py-3 bg-rose-600 text-white text-xs font-bold rounded-xl hover:bg-rose-700 inline-flex items-center justify-center gap-2 shadow-lg"
          >
            <UploadCloud size={16} /> Retry / Upload Clear Syllabus
          </Button>
        </div>
      </div>
    )
  }

  // ── 4. NEEDS_REVIEW / MISMATCH STATE ───────────────────────────────────────
  return (
    <div className="p-8 max-w-[680px] mx-auto text-center space-y-5 animate-in fade-in duration-300">
      <div className="w-16 h-16 rounded-2xl bg-amber-500/10 border border-amber-500/20 text-amber-500 flex items-center justify-center mx-auto text-2xl shadow-inner">
        <ShieldAlert size={34} />
      </div>

      <div>
        <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/25 mb-2.5">
          <AlertTriangle size={13} /> Validation Requires Review · NEEDS_REVIEW
        </div>
        <h2 className="text-xl font-extrabold text-[var(--text)] tracking-tight">
          {featureName} Locked: Verification Required
        </h2>
        <p className="text-sm text-[var(--text-soft)] mt-1.5 max-w-[540px] mx-auto leading-relaxed">
          The uploaded syllabus could not be fully verified against your active semester profile.
        </p>
      </div>

      {/* Diagnosis Card */}
      <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 text-left text-xs space-y-2">
        <div className="flex items-center justify-between">
          <span className="font-bold text-[var(--text)] uppercase tracking-wider text-[10.5px]">Academic Context</span>
          <Badge tone="warning">{status}</Badge>
        </div>
        <div className="text-[var(--text-soft)]">
          {program && <span>{program} · </span>}
          {department && <span>{department} · </span>}
          {sem ? <span className="font-semibold text-[var(--text)]">{sem}</span> : <span>Semester Profile Active</span>}
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
        Once validated or manually confirmed, <strong>Personal Trainer</strong>, <strong>Reality Lab</strong>, and <strong>Knowledge Transfer</strong> will unlock with verified subjects.
      </p>
    </div>
  )
}
