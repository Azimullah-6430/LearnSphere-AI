import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

function cssVar(name) {
  if (typeof window === 'undefined') return '#28503f'
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div
      className="px-3 py-2 rounded-lg text-xs border"
      style={{ background: 'var(--surface)', borderColor: 'var(--border)', color: 'var(--text)' }}
    >
      <div className="font-bold mb-0.5">{label}</div>
      <div style={{ color: 'var(--text-soft)' }}>{payload[0].value}%</div>
    </div>
  )
}

export function TrendChart({ data, height = 220 }) {
  const accent = cssVar('--accent')
  const grid = cssVar('--border')
  const soft = cssVar('--text-soft')
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
        <defs>
          <linearGradient id="accentFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={accent} stopOpacity={0.25} />
            <stop offset="100%" stopColor={accent} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid vertical={false} stroke={grid} />
        <XAxis dataKey="label" tick={{ fill: soft, fontSize: 12, fontFamily: 'Manrope' }} axisLine={false} tickLine={false} dy={6} />
        <YAxis
          tick={{ fill: soft, fontSize: 12, fontFamily: 'Manrope' }}
          axisLine={false}
          tickLine={false}
          width={44}
          tickFormatter={(v) => `${v}%`}
          domain={[0, 100]}
          ticks={[0, 25, 50, 75, 100]}
        />
        <Tooltip content={<ChartTooltip />} />
        <Area type="monotone" dataKey="value" stroke={accent} strokeWidth={2.5} fill="url(#accentFill)" dot={{ r: 3, fill: accent, strokeWidth: 0 }} />
      </AreaChart>
    </ResponsiveContainer>
  )
}

export function SubjectBarChart({ data, height = 220 }) {
  const accent = cssVar('--accent')
  const grid = cssVar('--border')
  const soft = cssVar('--text-soft')
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ left: 0, right: 10, top: 10, bottom: 0 }}>
        <CartesianGrid vertical={false} stroke={grid} />
        <XAxis dataKey="label" tick={{ fill: soft, fontSize: 12, fontFamily: 'Manrope' }} axisLine={false} tickLine={false} dy={6} />
        <YAxis
          tick={{ fill: soft, fontSize: 12, fontFamily: 'Manrope' }}
          axisLine={false}
          tickLine={false}
          width={44}
          tickFormatter={(v) => `${v}%`}
          domain={[0, 100]}
          ticks={[0, 25, 50, 75, 100]}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--surface-alt)' }} />
        <Bar dataKey="value" fill={accent} radius={[6, 6, 0, 0]} maxBarSize={34} />
      </BarChart>
    </ResponsiveContainer>
  )
}
