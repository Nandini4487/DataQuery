import { useState, useEffect } from 'react'
import { healthCheck } from './services/api'
import './index.css'

/**
 * App root — Phase 0 only.
 * Calls healthCheck() on mount and shows loading / ok / error states
 * using the design tokens from SPEC §2.2.
 */
export default function App() {
  const [status, setStatus] = useState('loading') // 'loading' | 'ok' | 'error'
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    healthCheck().then(({ ok, data }) => {
      if (ok && data?.status === 'ok') {
        setStatus('ok')
      } else {
        setStatus('error')
        setErrorMsg(data?.message ?? 'Backend did not return status ok.')
      }
    })
  }, [])

  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 px-4"
         style={{ backgroundColor: 'var(--color-background)' }}>

      {/* ── Header ─────────────────────────────────────────────────── */}
      <header className="text-center">
        <h1 className="text-3xl font-bold tracking-tight"
            style={{ color: 'var(--color-text-primary)' }}>
          DataQuery AI
        </h1>
        <p className="mt-2 text-sm"
           style={{ color: 'var(--color-text-secondary)' }}>
          Full-Stack AI Data Analyst
        </p>
      </header>

      {/* ── Status card ────────────────────────────────────────────── */}
      <div className="w-full max-w-sm rounded-xl border p-6 shadow-sm"
           style={{
             backgroundColor: 'var(--color-surface)',
             borderColor: 'var(--color-border)',
             borderRadius: 'var(--radius-card)',
           }}>

        {status === 'loading' && (
          <div className="flex items-center gap-3">
            {/* Spinner */}
            <svg className="h-5 w-5 animate-spin"
                 style={{ color: 'var(--color-primary)' }}
                 xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
                 aria-label="Loading">
              <circle className="opacity-25" cx="12" cy="12" r="10"
                      stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor"
                    d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <span style={{ color: 'var(--color-text-secondary)' }}>
              Connecting to backend…
            </span>
          </div>
        )}

        {status === 'ok' && (
          <div className="flex items-center gap-3">
            <span className="text-xl" role="img" aria-label="OK">✅</span>
            <div>
              <p className="font-semibold" style={{ color: 'var(--color-success)' }}>
                Backend is healthy
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                GET /api/health → 200 OK
              </p>
            </div>
          </div>
        )}

        {status === 'error' && (
          <div className="flex items-start gap-3">
            <span className="text-xl" role="img" aria-label="Error">❌</span>
            <div>
              <p className="font-semibold" style={{ color: 'var(--color-error)' }}>
                Backend unreachable
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                {errorMsg}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                Make sure uvicorn is running on the configured{' '}
                <code className="font-mono">VITE_API_URL</code>.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
