import { useState, useEffect } from 'react'
import { healthCheck, deleteDataset } from '../services/api'
import FileUploader from '../components/upload/FileUploader'
import DatasetSummary from '../components/dataset/DatasetSummary'
import DataPreviewTable from '../components/dataset/DataPreviewTable'
import QuestionInput from '../components/chat/QuestionInput'
import ResultTable from '../components/results/ResultTable'
import ChartRenderer from '../components/results/ChartRenderer'

export default function Dashboard() {
  const [healthStatus, setHealthStatus] = useState('loading') // 'loading' | 'ok' | 'error'
  const [currentDataset, setCurrentDataset] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // Query Result State
  const [queryResult, setQueryResult] = useState(null) // AnswerResponse object
  const [activeQuestion, setActiveQuestion] = useState('')

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
    setQueryResult(null)
    setActiveQuestion('')
  }

  const handleReset = () => {
    setCurrentDataset(null)
    setQueryResult(null)
    setActiveQuestion('')
  }

  const handleDelete = async () => {
    if (!currentDataset?.dataset_id) return
    setIsDeleting(true)
    await deleteDataset(currentDataset.dataset_id)
    setIsDeleting(false)
    handleReset()
  }

  const handleAnswerReceived = (answerResponse, questionText) => {
    setQueryResult(answerResponse)
    setActiveQuestion(questionText)
  }

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ backgroundColor: 'var(--color-background)' }}
    >
      {/* ── Top Navigation Bar with Health Indicator in Corner ── */}
      <nav
        className="w-full border-b px-6 py-3.5 flex items-center justify-between sticky top-0 z-20 backdrop-blur-md bg-white/95"
        style={{
          borderColor: 'var(--color-border)',
        }}
      >
        <div className="flex items-center gap-3">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg text-white font-bold text-sm shadow-xs"
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
              className="text-xs leading-none mt-1"
              style={{ color: 'var(--color-text-secondary)' }}
            >
              Deterministic Analytics & Query Engine • Phase 1
            </p>
          </div>
        </div>

        {/* ── Corner Health Indicator ── */}
        <div
          className="flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border shadow-2xs"
          style={{
            borderColor: 'var(--color-border)',
            backgroundColor: 'var(--color-surface)',
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

      {/* ── Main Workspace Canvas ── */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-4 py-8 flex flex-col gap-8">
        {/* 1. Upload Section */}
        <section aria-labelledby="upload-heading">
          <div className="flex items-center justify-between mb-2">
            <h2
              id="upload-heading"
              className="text-base font-bold flex items-center gap-2"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
                style={{ backgroundColor: 'var(--color-primary)' }}
              >
                1
              </span>
              Dataset Upload
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

        {/* 2. Dataset Summary Section */}
        <section aria-labelledby="summary-heading">
          <h2
            id="summary-heading"
            className="text-base font-bold flex items-center gap-2 mb-2"
            style={{ color: 'var(--color-text-primary)' }}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              2
            </span>
            Dataset Summary & Schema
          </h2>
          <DatasetSummary datasetId={currentDataset?.dataset_id} />
        </section>

        {/* 3. Data Preview Section */}
        <section aria-labelledby="preview-heading">
          <h2
            id="preview-heading"
            className="text-base font-bold flex items-center gap-2 mb-2"
            style={{ color: 'var(--color-text-primary)' }}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              3
            </span>
            Data Preview
          </h2>
          <DataPreviewTable datasetId={currentDataset?.dataset_id} />
        </section>

        {/* 4. Natural Language Question Input */}
        <section aria-labelledby="ask-heading">
          <h2
            id="ask-heading"
            className="text-base font-bold flex items-center gap-2 mb-2"
            style={{ color: 'var(--color-text-primary)' }}
          >
            <span
              className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              4
            </span>
            Query & Analysis
          </h2>
          <QuestionInput
            datasetId={currentDataset?.dataset_id}
            disabled={!currentDataset}
            onAnswerReceived={handleAnswerReceived}
          />
        </section>

        {/* 5. Results Section (Answer, Table & Chart) */}
        {queryResult && (
          <section aria-labelledby="results-heading" className="flex flex-col gap-5">
            <h2
              id="results-heading"
              className="text-base font-bold flex items-center gap-2"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
                style={{ backgroundColor: 'var(--color-primary)' }}
              >
                5
              </span>
              Computed Results
            </h2>

            {/* Answer banner */}
            <div
              className="p-4 rounded-xl border flex items-start gap-3"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-card)',
              }}
            >
              <div
                className="flex h-8 w-8 items-center justify-center rounded-lg shrink-0 mt-0.5"
                style={{ backgroundColor: '#EFF6FF', color: 'var(--color-primary)' }}
              >
                💡
              </div>
              <div>
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                  Query: &ldquo;{activeQuestion}&rdquo;
                </p>
                <p className="text-sm font-medium mt-1" style={{ color: 'var(--color-text-primary)' }}>
                  {queryResult.answer_text}
                </p>
              </div>
            </div>

            {/* Two-column layout for Table and Chart */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
              <ResultTable table={queryResult.table} />
              <ChartRenderer chartSpec={queryResult.chart_spec} />
            </div>
          </section>
        )}
      </main>

      {/* ── Footer ── */}
      <footer
        className="w-full border-t py-4 text-center text-xs"
        style={{
          borderColor: 'var(--color-border)',
          color: 'var(--color-text-secondary)',
        }}
      >
        DataQuery AI • Phase 1 Deterministic Analytics Workspace
      </footer>
    </div>
  )
}
