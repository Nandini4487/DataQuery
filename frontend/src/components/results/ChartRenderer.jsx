import {
  ResponsiveContainer,
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from 'recharts'

export default function ChartRenderer({ chartSpec, loading, error }) {
  // ── 1. LOADING STATE ──
  if (loading) {
    return (
      <div
        className="w-full rounded-xl border p-8 text-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <svg
          className="h-8 w-8 animate-spin mx-auto mb-3"
          style={{ color: 'var(--color-primary)' }}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Generating visualization…
        </p>
      </div>
    )
  }

  // ── 2. ERROR STATE ──
  if (error) {
    return (
      <div
        className="w-full rounded-xl border p-6 text-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <p className="text-sm font-semibold" style={{ color: 'var(--color-error)' }}>
          Chart Generation Error
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {error}
        </p>
      </div>
    )
  }

  // ── 3. EMPTY STATE ──
  if (!chartSpec || !chartSpec.type || chartSpec.type === 'empty' || !chartSpec.data || chartSpec.data.length === 0) {
    return (
      <div
        className="w-full rounded-xl border p-8 text-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <div
          className="mx-auto flex h-10 w-10 items-center justify-center rounded-full mb-3"
          style={{ backgroundColor: '#F1F5F9', color: 'var(--color-text-secondary)' }}
        >
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
          </svg>
        </div>
        <h4 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          No Chart Available
        </h4>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Charts are automatically inferred when results contain metrics or groupings.
        </p>
      </div>
    )
  }

  const { type, x, y, data } = chartSpec

  // Accessibility text summary for screen readers & high-contrast access
  const accessibleSummary =
    type === 'scalar'
      ? `Single metric: ${y} is ${data[0]?.[y] ?? 'N/A'}`
      : `${type.toUpperCase()} chart of ${y} by ${x}. Data points: ${data
          .map((d) => `${d[x]}: ${d[y]}`)
          .join(', ')}`

  return (
    <div
      className="w-full rounded-xl border p-5 flex flex-col gap-4"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-base" style={{ color: 'var(--color-text-primary)' }}>
            Visualization
          </h4>
          <p className="text-xs capitalize" style={{ color: 'var(--color-text-secondary)' }}>
            {type} chart • Inferred from query structure
          </p>
        </div>
        <span
          className="text-xs px-2.5 py-0.5 rounded-full font-medium"
          style={{ backgroundColor: '#EFF6FF', color: 'var(--color-primary)' }}
        >
          {type.toUpperCase()}
        </span>
      </div>

      {/* ── 4A. SCALAR CHART (Single Metric Card) ── */}
      {type === 'scalar' && (
        <div className="flex flex-col items-center justify-center p-8 bg-slate-50/60 rounded-lg border text-center"
             style={{ borderColor: 'var(--color-border)' }}>
          <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            {y || 'Computed Total'}
          </span>
          <span className="text-4xl font-extrabold mt-2" style={{ color: 'var(--color-primary)' }}>
            {typeof data[0]?.[y] === 'number'
              ? data[0][y].toLocaleString()
              : String(data[0]?.[y] ?? '0')}
          </span>
          <span className="text-xs text-slate-400 mt-2">
            Deterministic calculation from active dataset
          </span>
        </div>
      )}

      {/* ── 4B. BAR CHART (Grouped Aggregation) ── */}
      {type === 'bar' && (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 10, right: 15, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <XAxis dataKey={x} tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
              <YAxis tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderColor: '#E2E8F0',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)',
                }}
              />
              <Bar dataKey={y} fill="#2563EB" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── 4C. LINE CHART (Time Series) ── */}
      {type === 'line' && (
        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 10, right: 15, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E2E8F0" />
              <XAxis dataKey={x} tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
              <YAxis tickLine={false} tick={{ fontSize: 12, fill: '#64748B' }} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#FFFFFF',
                  borderColor: '#E2E8F0',
                  borderRadius: '8px',
                }}
              />
              <Line
                type="monotone"
                dataKey={y}
                stroke="#2563EB"
                strokeWidth={2.5}
                dot={{ r: 4, fill: '#2563EB' }}
                activeDot={{ r: 6 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* ── Text alternative for accessibility (SPEC §2.6) ── */}
      <div
        className="pt-2 border-t text-[11px] text-slate-500 flex items-center justify-between"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <span className="truncate pr-2">
          <strong>Accessible data summary:</strong> {accessibleSummary}
        </span>
      </div>
    </div>
  )
}
