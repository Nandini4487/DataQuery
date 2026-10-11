export default function ResultTable({ table, loading, error }) {
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
          Computing results with Pandas engine…
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
          Failed to Display Result Table
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {error}
        </p>
      </div>
    )
  }

  // ── 3. EMPTY STATE ──
  const rows = Array.isArray(table) ? table : table?.rows
  const columns = table?.columns || (rows && rows.length > 0 ? Object.keys(rows[0]) : [])

  if (!rows || rows.length === 0) {
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
        </div>
        <h4 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          No Result Table Yet
        </h4>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Ask a question above to execute a plan and view computed tabular results.
        </p>
      </div>
    )
  }

  // ── 4. SUCCESS STATE ──
  return (
    <div
      className="w-full rounded-xl border p-5 flex flex-col gap-3"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <h4 className="font-semibold text-base" style={{ color: 'var(--color-text-primary)' }}>
            Result Table
          </h4>
          <span
            className="text-[11px] font-medium px-2 py-0.5 rounded-full"
            style={{ backgroundColor: '#DCFCE7', color: 'var(--color-success)' }}
          >
            Deterministic Computation
          </span>
        </div>
        <span className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
          {rows.length} {rows.length === 1 ? 'row' : 'rows'}
        </span>
      </div>

      <div
        className="overflow-auto max-h-[360px] rounded-lg border"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <table className="w-full text-left border-collapse text-sm">
          <thead
            className="sticky top-0 z-10 text-xs font-semibold uppercase tracking-wider"
            style={{
              backgroundColor: '#F8FAFC',
              color: 'var(--color-text-primary)',
            }}
          >
            <tr className="border-b" style={{ borderColor: 'var(--color-border)' }}>
              <th className="py-2.5 px-3 w-10 text-center text-slate-400 font-mono text-xs">#</th>
              {columns.map((col) => (
                <th key={col} className="py-2.5 px-4 font-semibold whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {rows.map((row, idx) => (
              <tr key={idx} className="hover:bg-slate-50/70 transition-colors">
                <td className="py-2.5 px-3 text-center text-slate-400 font-mono text-xs">
                  {idx + 1}
                </td>
                {columns.map((col) => {
                  const val = row[col]
                  return (
                    <td key={col} className="py-2.5 px-4 whitespace-nowrap text-xs font-medium">
                      {val === null || val === undefined ? (
                        <span className="italic text-slate-400">null</span>
                      ) : typeof val === 'number' ? (
                        val.toLocaleString()
                      ) : (
                        String(val)
                      )}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
