import { useState, useEffect } from 'react'
import { healthCheck, deleteDataset } from './services/api'
import FileUploader from './components/upload/FileUploader'
import DatasetSummary from './components/dataset/DatasetSummary'
import DataPreviewTable from './components/dataset/DataPreviewTable'
import './index.css'

export default function App() {
  const [healthStatus, setHealthStatus] = useState('loading') // 'loading' | 'ok' | 'error'
  const [currentDataset, setCurrentDataset] = useState(null) // DatasetMeta object or null
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    healthCheck().then(({ ok, data }) => {
      if (ok && data?.status === 'ok') {
        setHealthStatus('ok')
      } else {
        setHealthStatus('error')
      }
    })
  }, [])

  const handleUploadSuccess = (meta) => {
    setCurrentDataset(meta)
  }

  const handleReset = () => {
    setCurrentDataset(null)
  }

  const handleDelete = async () => {
    if (!currentDataset?.dataset_id) return
    setIsDeleting(true)
    await deleteDataset(currentDataset.dataset_id)
    setIsDeleting(false)
    setCurrentDataset(null)
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ backgroundColor: 'var(--color-background)' }}
    >
      {/* ── Top Navigation Bar ── */}
      <nav
        className="w-full border-b px-6 py-3.5 flex items-center justify-between"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
        }}
      >
        <div className="flex items-center gap-2.5">
          <div
            className="flex h-8 w-8 items-center justify-center rounded-lg text-white font-bold text-sm shadow-xs"
            style={{ backgroundColor: 'var(--color-primary)' }}
          >
            DQ
          </div>
          <div>
            <h1
              className="text-base font-bold tracking-tight leading-none"
              style={{ color: 'var(--color-text-primary)' }}
            >
              DataQuery AI
            </h1>
            <p
              className="text-xs leading-none mt-0.5"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Full-Stack AI Data Analyst
            </p>
          </div>
        </div>

        {/* ── Corner Health Indicator ── */}
        <div
          className="flex items-center gap-2 px-2.5 py-1 rounded-full text-xs font-medium border"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-background)',
          }}
        >
          {healthStatus === 'loading' && (
            <>
              <span className="h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <span style={{ color: 'var(--color-text-secondary)' }}>Connecting…</span>
            </>
          )}
          {healthStatus === 'ok' && (
            <>
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span style={{ color: 'var(--color-text-primary)' }}>Backend Online</span>
            </>
          )}
          {healthStatus === 'error' && (
            <>
              <span className="h-2 w-2 rounded-full bg-rose-500" />
              <span style={{ color: 'var(--color-error)' }}>Backend Offline</span>
            </>
          )}
        </div>
      </nav>

      {/* ── Main Dashboard Content ── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8 flex flex-col gap-6">
        {/* Upload Section */}
        <section aria-labelledby="upload-heading">
          <div className="flex items-center justify-between mb-2">
            <h2
              id="upload-heading"
              className="text-lg font-bold"
              style={{ color: 'var(--color-text-primary)' }}
            >
              1. Upload Dataset
            </h2>
            {currentDataset && (
              <button
                type="button"
                onClick={handleDelete}
                disabled={isDeleting}
                className="text-xs font-medium text-rose-600 hover:text-rose-700 hover:underline cursor-pointer disabled:opacity-50"
              >
                {isDeleting ? 'Deleting…' : 'Delete Dataset & Reset'}
              </button>
            )}
          </div>
          <FileUploader
            onUploadSuccess={handleUploadSuccess}
            currentDataset={currentDataset}
            onReset={handleReset}
          />
        </section>

        {/* Dataset Summary Section */}
        <section aria-labelledby="summary-heading">
          <h2
            id="summary-heading"
            className="text-lg font-bold mb-2"
            style={{ color: 'var(--color-text-primary)' }}
          >
            2. Dataset Summary & Schema
          </h2>
          <DatasetSummary datasetId={currentDataset?.dataset_id} />
        </section>

        {/* Data Preview Section */}
        <section aria-labelledby="preview-heading">
          <h2
            id="preview-heading"
            className="text-lg font-bold mb-2"
            style={{ color: 'var(--color-text-primary)' }}
          >
            3. Data Preview
          </h2>
          <DataPreviewTable datasetId={currentDataset?.dataset_id} />
        </section>
      </main>

      {/* ── Footer ── */}
      <footer
        className="w-full border-t py-4 text-center text-xs"
        style={{
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-secondary)',
        }}
      >
        DataQuery AI • Phase 1 CSV Analysis Workspace
      </footer>
    </div>
  )
}
