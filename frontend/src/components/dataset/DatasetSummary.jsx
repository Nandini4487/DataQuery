import { useState, useEffect } from 'react'
import { getProfile } from '../../services/api'

export default function DatasetSummary({ datasetId, initialProfile }) {
  const [profile, setProfile] = useState(initialProfile ?? null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!datasetId) {
      setProfile(null)
      setError('')
      return
    }

    let isMounted = true
    setLoading(true)
    setError('')

    getProfile(datasetId).then(({ ok, data }) => {
      if (!isMounted) return
      setLoading(false)
      if (ok) {
        setProfile(data)
      } else {
        setError(data?.message || data?.error || 'Failed to load dataset profile.')
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
        </div>
        <h4 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
          No Dataset Selected
        </h4>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Upload a CSV above to inspect its columns, types, and statistics.
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
          Profiling dataset metrics…
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
          Error Loading Profile
        </p>
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {error}
        </p>
      </div>
    )
  }

  // ── 4. SUCCESS STATE ──
  if (!profile) return null

  const numericEntries = Object.entries(profile.numeric_summary || {})

  return (
    <div className="flex flex-col gap-5 w-full">
      {/* ── Summary Cards ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Total Rows Card */}
        <div
          className="p-4 rounded-xl border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)',
            borderRadius: 'var(--radius-card)',
          }}
        >
          <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
            Total Rows
          </p>
          <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-text-primary)' }}>
            {profile.row_count?.toLocaleString()}
          </p>
        </div>

        {/* Total Columns Card */}
        <div
          className="p-4 rounded-xl border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)',
            borderRadius: 'var(--radius-card)',
          }}
        >
          <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
            Total Columns
          </p>
          <p className="text-2xl font-bold mt-1" style={{ color: 'var(--color-text-primary)' }}>
            {profile.col_count?.toLocaleString()}
          </p>
        </div>

        {/* Duplicate Rows Card */}
        <div
          className="p-4 rounded-xl border"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)',
            borderRadius: 'var(--radius-card)',
          }}
        >
          <p className="text-xs font-medium uppercase tracking-wider" style={{ color: 'var(--color-text-secondary)' }}>
            Duplicate Rows
          </p>
          <p className="text-2xl font-bold mt-1" style={{ color: profile.duplicate_rows > 0 ? 'var(--color-warning)' : 'var(--color-text-primary)' }}>
            {profile.duplicate_rows?.toLocaleString()}
          </p>
        </div>
      </div>

      {/* ── Column Metadata & Schema Badges ── */}
      <div
        className="rounded-xl border p-5"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
          Columns & Inferred Types
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {profile.columns?.map((col) => {
            const dtype = profile.dtypes?.[col] || 'unknown'
            const isNumeric = dtype.includes('int') || dtype.includes('float')
            const missing = profile.missing_values?.[col] ?? 0

            return (
              <div
                key={col}
                className="flex items-center justify-between p-3 rounded-lg border bg-slate-50/50"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <div className="flex flex-col min-w-0 pr-2">
                  <span className="text-sm font-semibold truncate" style={{ color: 'var(--color-text-primary)' }}>
                    {col}
                  </span>
                  <div className="flex items-center gap-1.5 mt-1">
                    {/* Missing value indicator */}
                    {missing === 0 ? (
                      <span className="text-xs text-emerald-600 font-medium">0 missing</span>
                    ) : (
                      <span className="text-xs text-amber-600 font-medium">{missing} missing</span>
                    )}
                  </div>
                </div>

                {/* Dtype badge */}
                <span
                  className="px-2 py-0.5 text-xs font-mono font-medium rounded-md shrink-0"
                  style={{
                    backgroundColor: isNumeric ? '#DBEAFE' : '#F3E8FF',
                    color: isNumeric ? 'var(--color-primary)' : '#7E22CE',
                  }}
                >
                  {dtype}
                </span>
              </div>
            )
          })}
        </div>
      </div>

      {/* ── Numeric Summaries (if any exist) ── */}
      {numericEntries.length > 0 && (
        <div
          className="rounded-xl border p-5"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)',
            borderRadius: 'var(--radius-card)',
          }}
        >
          <h4 className="text-sm font-semibold mb-3" style={{ color: 'var(--color-text-primary)' }}>
            Numeric Column Summary
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {numericEntries.map(([col, stats]) => (
              <div
                key={col}
                className="p-3 rounded-lg border bg-slate-50/50 flex flex-col gap-1 text-xs"
                style={{ borderColor: 'var(--color-border)' }}
              >
                <span className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
                  {col}
                </span>
                <div className="flex justify-between text-slate-500 pt-1">
                  <span>Min: <strong className="text-slate-800">{stats.min?.toLocaleString() ?? 'N/A'}</strong></span>
                  <span>Mean: <strong className="text-slate-800">{typeof stats.mean === 'number' ? stats.mean.toLocaleString(undefined, { maximumFractionDigits: 2 }) : 'N/A'}</strong></span>
                  <span>Max: <strong className="text-slate-800">{stats.max?.toLocaleString() ?? 'N/A'}</strong></span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
