export function Card({ children, className = '', style }) {
  return (
    <div
      className={`bg-[var(--surface)] border border-[var(--border)] rounded-md p-[22px] ${className}`}
      style={style}
    >
      {children}
    </div>
  )
}

export function CardHeader({ title, subtitle, action }) {
  return (
    <div className="flex items-center justify-between mb-[18px] gap-3">
      <div>
        <div className="text-[15px] font-bold">{title}</div>
        {subtitle && <div className="text-[12.5px] text-[var(--text-faint)] mt-0.5">{subtitle}</div>}
      </div>
      {action}
    </div>
  )
}

const badgeStyles = {
  success: 'bg-[var(--success-soft)] text-[var(--success)]',
  warning: 'bg-[var(--warning-soft)] text-[var(--warning)]',
  error: 'bg-[var(--error-soft)] text-[var(--error)]',
  neutral: 'bg-[var(--surface-alt)] text-[var(--text-soft)]',
  gold: 'bg-[var(--gold-soft)] text-[var(--gold)]',
}

export function Badge({ children, tone = 'neutral' }) {
  return (
    <span className={`inline-flex items-center gap-1.5 px-[9px] py-[3px] rounded-full text-[11.5px] font-semibold ${badgeStyles[tone]}`}>
      {children}
    </span>
  )
}

const btnStyles = {
  primary: 'bg-[var(--accent)] text-[#F7F8F4] hover:bg-[var(--accent-dim)] hover:-translate-y-px',
  secondary: 'bg-[var(--surface)] text-[var(--text)] border border-[var(--border-strong)] hover:bg-[var(--surface-alt)]',
  ghost: 'bg-transparent text-[var(--text-soft)] hover:text-[var(--text)] hover:bg-[var(--surface-alt)]',
}

export function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  const pad = size === 'sm' ? 'px-[13px] py-[7px] text-[12.5px] rounded-[7px]' : 'px-[18px] py-[10px] text-[13.5px] rounded-[9px]'
  return (
    <button
      className={`inline-flex items-center justify-center gap-2 font-semibold whitespace-nowrap transition-all duration-150 ${pad} ${btnStyles[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  )
}

export function StatCard({ label, value, delta, deltaTone }) {
  const toneClass = deltaTone === 'up' ? 'text-[var(--success)]' : deltaTone === 'down' ? 'text-[var(--error)]' : 'text-[var(--text-faint)]'
  return (
    <div className="bg-[var(--surface)] border border-[var(--border)] rounded-md px-5 py-[18px]">
      <div className="text-xs text-[var(--text-faint)] font-semibold mb-2.5">{label}</div>
      <div className="text-[26px] font-extrabold tracking-tight">{value}</div>
      {delta && <div className={`text-xs font-semibold mt-1.5 ${toneClass}`}>{delta}</div>}
    </div>
  )
}

export function PageHead({ title, subtitle, action }) {
  return (
    <div className="flex items-end justify-between mb-6 flex-wrap gap-3">
      <div>
        <h1 className="text-[22px] font-bold mb-1">{title}</h1>
        {subtitle && <p className="text-[13.5px] text-[var(--text-soft)]">{subtitle}</p>}
      </div>
      {action}
    </div>
  )
}

export function RowItem({ title, subtitle, right }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-[var(--border)] last:border-0 last:pb-0 first:pt-0">
      <div>
        <div className="text-[13.5px] font-semibold">{title}</div>
        {subtitle && <div className="text-xs text-[var(--text-faint)] mt-0.5">{subtitle}</div>}
      </div>
      {right}
    </div>
  )
}

export function SearchBox({ placeholder = 'Search...' }) {
  return (
    <div className="flex items-center gap-2 border border-[var(--border-strong)] rounded-lg px-3 py-2 bg-[var(--surface)] min-w-[230px]">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" className="text-[var(--text-faint)] shrink-0">
        <circle cx="11" cy="11" r="7" />
        <path d="m21 21-4.3-4.3" />
      </svg>
      <input placeholder={placeholder} className="border-none outline-none bg-transparent text-[13px] w-full text-[var(--text)]" />
    </div>
  )
}
