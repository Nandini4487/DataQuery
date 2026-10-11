import { useState, useEffect } from 'react'
import { getPreview } from '../../services/api'

export default function DataPreviewTable({ datasetId, initialPreview }) {
  const [preview, setPreview] = useState(initialPreview ?? null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!datasetId) {
      setPreview(null)
      setError('')
      return
    }

    let isMounted = true
    setLoading(true)
    setError('')

    getPreview(datasetId).then(({ ok, data }) => {
      if (!isMounted) return
      setLoading(false)
      if (ok) {
        setPreview(data)
      } else {
        setError(data?.message || data?.error || 'Failed to load dataset preview.')
      }
    })

    return () => {
      isMounted = false
    }
  }, [datasetId])

  // ── 1. EMPTY STATE ──
  if (!datasetId) {
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </div>
        <h4 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          No Preview Data
        </h4>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Upload a dataset above to preview the first 100 rows.
        </p>
      </div>
    )
  }

  // ── 2. LOADING STATE ──
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
          Loading table preview…
        </p>
      </div>
    )
  }

  // ── 3. ERROR STATE ──
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
          Error Loading Preview
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {error}
        </p>
      </div>
    )
  }

  // ── 4. SUCCESS STATE ──
  if (!preview || !preview.rows || preview.rows.length === 0) {
    return (
      <div
        className="w-full rounded-xl border p-6 text-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          The dataset appears to be empty.
        </p>
      </div>
    )
  }

  const columns = preview.columns || Object.keys(preview.rows[0] || {})
  const rowCount = preview.rows.length
  const totalCount = preview.total_rows ?? rowCount

  return (
    <div
      className="w-full rounded-xl border p-5 flex flex-col gap-3"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      {/* Header bar */}
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-base" style={{ color: 'var(--color-text-primary)' }}>
            Data Preview
          </h4>
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Showing {rowCount} of {totalCount} rows (capped at 100)
          </p>
        </div>
        <span
          className="px-2.5 py-1 text-xs font-medium rounded-full bg-slate-100"
          style={{ color: 'var(--color-text-secondary)' }}
        >
          {columns.length} columns
        </span>
      </div>

      {/* Fixed-header scrollable table container */}
      <div
        className="overflow-auto max-h-[420px] rounded-lg border"
        style={{ borderColor: 'var(--color-border)' }}
      >
        <table className="w-full text-left border-collapse text-sm">
          <thead
            className="sticky top-0 z-10 text-xs font-semibold uppercase tracking-wider shadow-sm"
            style={{
              backgroundColor: '#F8FAFC',
              color: 'var(--color-text-primary)',
            }}
          >
            <tr className="border-b" style={{ borderColor: 'var(--color-border)' }}>
              <th className="py-2.5 px-3 w-12 text-center text-slate-400 font-mono text-xs">#</th>
              {columns.map((col) => (
                <th key={col} className="py-2.5 px-4 font-semibold whitespace-nowrap">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {preview.rows.map((row, idx) => (
              <tr
                key={idx}
                className="hover:bg-slate-50/70 transition-colors"
                style={{ color: 'var(--color-text-primary)' }}
              >
                <td className="py-2.5 px-3 text-center text-slate-400 font-mono text-xs select-none">
                  {idx + 1}
                </td>
                {columns.map((col) => {
                  const val = row[col]
                  const isNull = val === null || val === undefined
                  return (
                    <td key={col} className="py-2.5 px-4 whitespace-nowrap text-xs">
                      {isNull ? (
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
