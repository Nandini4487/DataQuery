import LoadingState from '../common/LoadingState'
import ErrorMessage from '../common/ErrorMessage'
import EmptyState from '../common/EmptyState'

export default function ResultTable({ table, loading, error }) {
  // ── 1. LOADING STATE ──
  if (loading) {
    return <LoadingState message="Computing results with Pandas engine…" />
  }

  // ── 2. ERROR STATE ──
  if (error) {
    return <ErrorMessage title="Failed to Display Result Table" message={error} />
  }

  // ── 3. EMPTY STATE ──
  const rows = Array.isArray(table) ? table : table?.rows
  const columns = table?.columns || (rows && rows.length > 0 ? Object.keys(rows[0]) : [])

  if (!rows || rows.length === 0) {
    return (
      <EmptyState
        icon={
          <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 10h16M4 14h16M4 18h16" />
          </svg>
        }
        title="No Result Table Yet"
        description="Ask a question above to execute a plan and view computed tabular results."
      />
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
