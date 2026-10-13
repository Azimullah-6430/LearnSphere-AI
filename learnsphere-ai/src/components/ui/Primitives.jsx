export function Card({ children, className = '', style, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-4 sm:p-5 md:p-6 shadow-[var(--shadow-xs)] hover:shadow-[var(--shadow-sm)] transition-all duration-200 ${className}`}
      style={style}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-start justify-between mb-4 sm:mb-5 gap-3">
      <div className="min-w-0 flex-1">
        <h3 className="text-lg sm:text-xl md:text-2xl font-bold text-[var(--text)] tracking-tight leading-snug">{title}</h3>
        {subtitle && <p className="text-xs sm:text-sm md:text-base text-[var(--text-soft)] mt-1 font-normal leading-relaxed">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}

const badgeStyles = {
  success: 'bg-[var(--success-soft)] text-[var(--success)] border border-[var(--success)]/20',
  warning: 'bg-[var(--warning-soft)] text-[var(--warning)] border border-[var(--warning)]/20',
  error: 'bg-[var(--error-soft)] text-[var(--error)] border border-[var(--error)]/20',
  neutral: 'bg-[var(--surface-alt)] text-[var(--text-soft)] border border-[var(--border)]',
  gold: 'bg-[var(--gold-soft)] text-[var(--gold)] border border-[var(--gold)]/20',
  accent: 'bg-[var(--accent-soft)] text-[var(--accent)] border border-[var(--accent)]/20 font-bold',
}

export function Badge({ children, tone = 'neutral', className = '' }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs sm:text-[13px] font-semibold leading-normal ${badgeStyles[tone] || badgeStyles.neutral} ${className}`}>
      {children}
    </span>
  )
}

const btnStyles = {
  primary: 'bg-[var(--accent)] text-white hover:bg-[var(--accent-hover)] shadow-sm hover:shadow active:scale-[0.99]',
  secondary: 'bg-[var(--surface)] text-[var(--text)] border border-[var(--border-strong)] hover:bg-[var(--surface-alt)] hover:border-[var(--text-soft)] active:scale-[0.99]',
  ghost: 'bg-transparent text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)] active:scale-[0.99]',
  danger: 'bg-[var(--error)] text-white hover:opacity-90 shadow-sm active:scale-[0.99]',
}

export function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  const pad =
    size === 'sm'
      ? 'px-3.5 py-1.5 text-xs sm:text-sm rounded-lg min-h-[34px]'
      : size === 'lg'
      ? 'px-6 py-3 text-sm sm:text-base rounded-xl font-bold min-h-[46px]'
      : 'px-4 py-2 text-xs sm:text-sm rounded-xl font-semibold min-h-[38px]'

  return (
    <button
      className={`inline-flex items-center justify-center gap-1.5 font-semibold whitespace-nowrap transition-all duration-150 cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed ${pad} ${btnStyles[variant] || btnStyles.primary} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function StatCard({ label, value, delta, deltaTone, icon: Icon }) {
  const toneClass = deltaTone === 'up' ? 'text-[var(--success)]' : deltaTone === 'down' ? 'text-[var(--error)]' : 'text-[var(--text-faint)]'
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-2xl p-5 sm:p-6 shadow-[var(--shadow-xs)] hover:border-[var(--border-strong)] hover:shadow-[var(--shadow-sm)] transition-all duration-200 min-w-0">
      <div className="flex items-center justify-between mb-2.5 gap-1.5">
        <span className="text-xs sm:text-[13px] font-bold tracking-wider uppercase text-[var(--text-soft)] truncate">{label}</span>
        {Icon && <Icon size={18} className="text-[var(--text-faint)] shrink-0" />}
      </div>
      <div className="text-2xl sm:text-3xl md:text-[34px] font-extrabold tracking-tight text-[var(--text)] leading-none truncate">{value}</div>
      {delta && <div className={`text-xs sm:text-[13px] font-semibold mt-2.5 flex items-center gap-1.5 ${toneClass}`}>{delta}</div>}
    </div>
  )
}

export function PageHead({ title, subtitle, action }) {
  return (
    <div className="flex items-start md:items-end justify-between mb-6 md:mb-7 flex-wrap gap-3 pb-3.5 border-b border-[var(--border)]/70">
      <div className="max-w-3xl">
        <h1 className="text-2xl sm:text-3xl md:text-[30px] font-extrabold tracking-tight text-[var(--text)] leading-tight mb-1.5">{title}</h1>
        {subtitle && <p className="text-sm sm:text-base text-[var(--text-soft)] leading-relaxed">{subtitle}</p>}
      </div>
      {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
    </div>
  )
}

export function RowItem({ title, subtitle, right, icon: Icon }) {
  return (
    <div className="flex items-center justify-between py-4 border-b border-[var(--border)] last:border-0 last:pb-0 first:pt-0 gap-4">
      <div className="flex items-center gap-3.5 min-w-0">
        {Icon && (
          <div className="w-10 h-10 rounded-xl bg-[var(--surface-alt)] border border-[var(--border)] flex items-center justify-center shrink-0 text-[var(--text-soft)]">
            <Icon size={18} />
          </div>
        )}
        <div className="min-w-0">
          <div className="text-sm md:text-base font-semibold text-[var(--text)] truncate">{title}</div>
          {subtitle && <div className="text-xs md:text-sm text-[var(--text-soft)] mt-0.5 truncate">{subtitle}</div>}
        </div>
      </div>
      {right && <div className="shrink-0">{right}</div>}
    </div>
  )
}

export function SearchBox({ placeholder = 'Search...', value, onChange, className = '' }) {
  return (
    <div className={`flex items-center gap-2.5 border border-[var(--border-strong)] focus-within:border-[var(--accent)] focus-within:ring-2 focus-within:ring-[var(--accent-soft)] rounded-xl px-3.5 py-2.5 bg-[var(--surface)] transition-all w-full sm:w-auto sm:min-w-[240px] ${className}`}>
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-[var(--text-faint)] shrink-0">
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="border-none outline-none bg-transparent text-sm w-full text-[var(--text)] placeholder:text-[var(--text-faint)]"
      />
    </div>
  )
}
