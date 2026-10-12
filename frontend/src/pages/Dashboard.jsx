import { useState, useEffect } from 'react'
import { healthCheck, deleteDataset, askQuestion } from '../services/api'
import FileUploader from '../components/upload/FileUploader'
import DatasetSummary from '../components/dataset/DatasetSummary'
import DataPreviewTable from '../components/dataset/DataPreviewTable'
import QuestionInput from '../components/chat/QuestionInput'
import ChatMessage from '../components/chat/ChatMessage'

export default function Dashboard() {
  const [healthStatus, setHealthStatus] = useState('loading') // 'loading' | 'ok' | 'error'
  const [currentDataset, setCurrentDataset] = useState(null)
  const [isDeleting, setIsDeleting] = useState(false)

  // In-memory chat messages state for current dataset (no persistence)
  const [messages, setMessages] = useState([])
  const [isAsking, setIsAsking] = useState(false)

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
    setMessages([])
    setIsAsking(false)
  }

  const handleReset = () => {
    setCurrentDataset(null)
    setMessages([])
    setIsAsking(false)
  }

  const handleDelete = async () => {
    if (!currentDataset?.dataset_id) return
    setIsDeleting(true)
    await deleteDataset(currentDataset.dataset_id)
    setIsDeleting(false)
    handleReset()
  }

  const handleAskQuestion = async (questionText) => {
    if (!currentDataset?.dataset_id || isAsking) return

    const messageId = `msg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

    const pendingMessage = {
      id: messageId,
      question: questionText,
      loading: true,
      answer: null,
      error: null,
      timestamp: nowTime,
    }

    setMessages((prev) => [...prev, pendingMessage])
    setIsAsking(true)

    const res = await askQuestion(currentDataset.dataset_id, questionText)
    setIsAsking(false)

    setMessages((prev) =>
      prev.map((msg) => {
        if (msg.id !== messageId) return msg
        if (res.ok) {
          return {
            ...msg,
            loading: false,
            answer: res.data,
            error: null,
          }
        }
        return {
          ...msg,
          loading: false,
          answer: null,
          error: {
            error: res.error,
            message: res.message,
          },
        }
      })
    )
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
              Deterministic Analytics & Query Engine
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
                disabled={isDeleting || isAsking}
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
            isAsking={isAsking}
            onAsk={handleAskQuestion}
          />
        </section>

        {/* 5. Chat History & Computed Answers */}
        <section aria-labelledby="chat-heading" className="flex flex-col gap-4">
          <div className="flex items-center justify-between">
            <h2
              id="chat-heading"
              className="text-base font-bold flex items-center gap-2"
              style={{ color: 'var(--color-text-primary)' }}
            >
              <span
                className="flex h-5 w-5 items-center justify-center rounded-full text-xs text-white"
                style={{ backgroundColor: 'var(--color-primary)' }}
              >
                5
              </span>
              Conversation & Answers
            </h2>
            {messages.length > 0 && (
              <span className="text-xs text-slate-400">
                {messages.length} {messages.length === 1 ? 'query' : 'queries'} answered
              </span>
            )}
          </div>

          {messages.length === 0 ? (
            <div
              className="rounded-xl border border-dashed p-8 text-center"
              style={{
                backgroundColor: 'var(--color-surface)',
                borderColor: 'var(--color-border)',
                borderRadius: 'var(--radius-card)',
              }}
            >
              <p className="text-sm font-medium" style={{ color: 'var(--color-text-primary)' }}>
                No questions asked yet.
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
                {currentDataset
                  ? 'Type a question above or click a suggestion to start analyzing your data.'
                  : 'Upload a CSV dataset above to start querying.'}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-6">
              {messages.map((msg) => (
                <ChatMessage key={msg.id} message={msg} />
              ))}
            </div>
          )}
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
        DataQuery AI • Deterministic Analytics Workspace
      </footer>
    </div>
  )
}
