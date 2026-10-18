import { useState, useRef, useEffect } from 'react'
import { uploadDocument } from '../../services/api'

/**
 * DocumentUploader Component
 *
 * Allows uploading reference documents (.pdf or .txt) attached to the current dataset.
 * Includes drag-and-drop, convenient client-side size/type checks, indexing progress state,
 * and error/success messaging adhering to SPEC design tokens and accessibility guidelines.
 */
export default function DocumentUploader({ datasetId, onUploadSuccess, disabled }) {
  const [status, setStatus] = useState('idle') // 'idle' | 'dragging' | 'loading' | 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [retrySeconds, setRetrySeconds] = useState(0)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (retrySeconds <= 0) return
    const timer = setInterval(() => {
      setRetrySeconds((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [retrySeconds])

  const isBlocked = disabled || status === 'loading' || retrySeconds > 0

  const handleFile = async (file) => {
    if (!file || !datasetId || isBlocked) return

    const name = file.name.toLowerCase()
    const isPdf = name.endsWith('.pdf')
    const isTxt = name.endsWith('.txt')

    // 1. Client-side convenience validation (server is final authority)
    if (!isPdf && !isTxt) {
      setStatus('error')
      setErrorMessage('Unsupported file type. Please upload a .pdf or .txt document.')
      return
    }

    const MAX_SIZE = 10 * 1024 * 1024 // 10 MB
    if (file.size > MAX_SIZE) {
      setStatus('error')
      setErrorMessage(`File exceeds the 10 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`)
      return
    }

    setStatus('loading')
    setErrorMessage('')
    setSuccessMessage('')

    const res = await uploadDocument(datasetId, file)
    if (res.ok) {
      setStatus('success')
      const count = res.data?.chunk_count ?? 0
      setSuccessMessage(`Document "${file.name}" indexed successfully (${count} chunk${count === 1 ? '' : 's'}).`)
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      if (onUploadSuccess) {
        onUploadSuccess(res.data)
      }
    } else {
      setStatus('error')
      if (res.status === 429 || res.error === 'rate_limited') {
        const secs = res.retryAfter != null ? res.retryAfter : 5
        setRetrySeconds(secs)
      }
      const msg = res.message || res.data?.message || res.data?.error || 'Failed to upload document.'
      setErrorMessage(msg)
    }
  }

  const onDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (!isBlocked) {
      setStatus('dragging')
    }
  }

  const onDragLeave = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (status === 'dragging') {
      setStatus('idle')
    }
  }

  const onDrop = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (isBlocked) return
    const files = e.dataTransfer?.files
    if (files && files.length > 0) {
      handleFile(files[0])
    } else {
      setStatus('idle')
    }
  }

  const onFileInputChange = (e) => {
    const files = e.target?.files
    if (files && files.length > 0) {
      handleFile(files[0])
    }
  }

  const triggerBrowse = () => {
    if (!isBlocked && fileInputRef.current) {
      fileInputRef.current.click()
    }
  }

  const handleKeyDown = (e) => {
    if ((e.key === 'Enter' || e.key === ' ') && !isBlocked) {
      e.preventDefault()
      triggerBrowse()
    }
  }

  return (
    <div
      className="w-full rounded-xl border p-5 transition-colors"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: status === 'dragging' ? 'var(--color-primary)' : 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt"
        className="hidden"
        onChange={onFileInputChange}
        disabled={isBlocked}
        aria-label="Upload reference document (.pdf or .txt)"
      />

      {/* Accessible live status region */}
      <div className="sr-only" aria-live="polite">
        {status === 'loading' && 'Indexing document. Please wait.'}
        {status === 'success' && successMessage}
        {status === 'error' && errorMessage}
      </div>

      <div
        role="button"
        tabIndex={isBlocked ? -1 : 0}
        onClick={triggerBrowse}
        onKeyDown={handleKeyDown}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        aria-disabled={isBlocked}
        className={`flex flex-col items-center justify-center p-6 border-2 border-dashed rounded-lg transition-all focus:outline-hidden focus:ring-2 focus:ring-blue-500 ${
          isBlocked ? 'cursor-not-allowed opacity-60' : 'cursor-pointer hover:border-blue-400 hover:bg-slate-50/60'
        }`}
        style={{
          borderColor: status === 'dragging' ? 'var(--color-primary)' : 'var(--color-border)',
          backgroundColor: status === 'dragging' ? '#EFF6FF' : 'transparent',
        }}
      >
        {/* Loading State */}
        {status === 'loading' ? (
          <div className="flex flex-col items-center gap-3 py-2 text-center max-w-md">
            <svg
              className="h-8 w-8 animate-spin"
              style={{ color: 'var(--color-primary)' }}
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                Extracting and indexing document…
              </p>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--color-text-secondary)' }}>
                Chunking text and storing vectors for retrieval. Note: the first document upload can take a little longer while the embedding model initializes.
              </p>
            </div>
          </div>
        ) : (
          /* Idle / Ready State */
          <div className="flex flex-col items-center gap-2 text-center">
            <div
              className="h-10 w-10 rounded-full flex items-center justify-center text-blue-600 bg-blue-50"
              style={{ backgroundColor: '#EFF6FF', color: 'var(--color-primary)' }}
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth="2"
                  d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
                />
              </svg>
            </div>
            <div>
              <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                {status === 'dragging' ? 'Drop document here' : 'Click or drag & drop reference document'}
              </p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                Supports <span className="font-semibold">.pdf</span> (text-based) and <span className="font-semibold">.txt</span> up to 10 MB
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Success Banner */}
      {status === 'success' && successMessage && (
        <div
          className="mt-3.5 p-3 rounded-lg border text-xs flex items-center justify-between gap-2"
          style={{
            backgroundColor: '#ECFDF5',
            borderColor: '#A7F3D0',
            color: 'var(--color-success)',
          }}
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                clipRule="evenodd"
              />
            </svg>
            <span>{successMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setSuccessMessage('')}
            className="text-emerald-700 hover:text-emerald-900 font-bold px-1.5 py-0.5 rounded text-xs cursor-pointer focus:ring-2 focus:ring-emerald-500 focus:outline-hidden"
            aria-label="Dismiss success message"
          >
            ✕
          </button>
        </div>
      )}

      {/* Error Banner */}
      {status === 'error' && errorMessage && (
        <div
          className="mt-3.5 p-3 rounded-lg border text-xs flex items-center justify-between gap-2"
          style={{
            backgroundColor: '#FEF2F2',
            borderColor: '#FECACA',
            color: 'var(--color-error)',
          }}
        >
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                clipRule="evenodd"
              />
            </svg>
            <span>{errorMessage}</span>
          </div>
          <button
            type="button"
            onClick={() => setErrorMessage('')}
            className="text-rose-700 hover:text-rose-900 font-bold px-1.5 py-0.5 rounded text-xs cursor-pointer focus:ring-2 focus:ring-rose-500 focus:outline-hidden"
            aria-label="Dismiss error message"
          >
            ✕
          </button>
        </div>
      )}
    </div>
  )
}
