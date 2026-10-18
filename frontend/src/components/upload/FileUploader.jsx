import { useState, useRef, useEffect } from 'react'
import { uploadDataset } from '../../services/api'

export default function FileUploader({ onUploadSuccess, currentDataset, onReset }) {
  const [status, setStatus] = useState('idle') // 'idle' | 'dragging' | 'loading' | 'success' | 'error'
  const [errorMessage, setErrorMessage] = useState('')
  const [uploadedInfo, setUploadedInfo] = useState(currentDataset ?? null)
  const [retrySeconds, setRetrySeconds] = useState(0)
  const fileInputRef = useRef(null)

  useEffect(() => {
    if (retrySeconds <= 0) return
    const timer = setInterval(() => {
      setRetrySeconds((prev) => (prev <= 1 ? 0 : prev - 1))
    }, 1000)
    return () => clearInterval(timer)
  }, [retrySeconds])

  const handleFile = async (file) => {
    if (!file || retrySeconds > 0) return

    // 1. Client-side extension validation
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setStatus('error')
      setErrorMessage('Unsupported file type. Please upload a .csv file.')
      return
    }

    // 2. Client-side size check (10 MB = 10 * 1024 * 1024 bytes)
    const MAX_SIZE = 10 * 1024 * 1024
    if (file.size > MAX_SIZE) {
      setStatus('error')
      setErrorMessage(`File exceeds the 10 MB limit (${(file.size / (1024 * 1024)).toFixed(1)} MB).`)
      return
    }

    setStatus('loading')
    setErrorMessage('')

    const res = await uploadDataset(file)
    if (res.ok) {
      setStatus('success')
      setUploadedInfo(res.data)
      if (onUploadSuccess) {
        onUploadSuccess(res.data)
      }
    } else {
      setStatus('error')
      if (res.status === 429 || res.error === 'rate_limited') {
        const secs = res.retryAfter != null ? res.retryAfter : 5
        setRetrySeconds(secs)
      }
      const msg = res.message || res.data?.message || res.data?.error || 'Failed to upload dataset.'
      setErrorMessage(msg)
    }
  }

  const onDragOver = (e) => {
    e.preventDefault()
    e.stopPropagation()
    if (status !== 'loading') {
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
    if (status === 'loading') return
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

  const handleReset = () => {
    setStatus('idle')
    setErrorMessage('')
    setUploadedInfo(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
    if (onReset) {
      onReset()
    }
  }

  return (
    <div
      className="w-full rounded-xl border p-6 transition-colors"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: status === 'dragging' ? 'var(--color-primary)' : 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={onFileInputChange}
        data-testid="file-input"
      />

      {/* ── 1. LOADING STATE ── */}
      {status === 'loading' && (
        <div className="flex flex-col items-center justify-center py-8 text-center">
          <svg
            className="h-10 w-10 animate-spin mb-3"
            style={{ color: 'var(--color-primary)' }}
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-label="Loading"
          >
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
          <h3 className="text-base font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Parsing and Validating CSV…
          </h3>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Checking encoding, inspecting rows, and profiling schema.
          </p>
        </div>
      )}

      {/* ── 2. SUCCESS STATE ── */}
      {status === 'success' && uploadedInfo && (
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 py-2">
          <div className="flex items-center gap-3">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-lg"
              style={{ backgroundColor: '#DCFCE7', color: 'var(--color-success)' }}
            >
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h4 className="font-semibold text-base" style={{ color: 'var(--color-text-primary)' }}>
                  {uploadedInfo.filename}
                </h4>
                <span
                  className="px-2 py-0.5 text-xs font-medium rounded-full"
                  style={{ backgroundColor: '#DCFCE7', color: 'var(--color-success)' }}
                >
                  Ready
                </span>
              </div>
              <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-secondary)' }}>
                {uploadedInfo.row_count !== undefined ? `${uploadedInfo.row_count} rows • ` : ''}
                {(uploadedInfo.file_size_bytes / 1024).toFixed(1)} KB • ID: {uploadedInfo.dataset_id?.slice(0, 8)}…
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="text-xs font-medium px-3 py-1.5 rounded-lg border transition-colors hover:bg-slate-50 cursor-pointer"
            style={{
              borderColor: 'var(--color-border)',
              color: 'var(--color-text-secondary)',
            }}
          >
            Upload Different CSV
          </button>
        </div>
      )}

      {/* ── 3. ERROR STATE ── */}
      {status === 'error' && (
        <div className="flex flex-col items-center justify-center py-6 text-center">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-full mb-2"
            style={{ backgroundColor: '#FEE2E2', color: 'var(--color-error)' }}
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </div>
          <h4 className="font-semibold text-base" style={{ color: 'var(--color-error)' }}>
            Upload Failed
          </h4>
          <p className="text-sm mt-1 max-w-md" style={{ color: 'var(--color-text-secondary)' }}>
            {errorMessage}
          </p>
          <div className="flex gap-2 mt-4">
            <button
              type="button"
              disabled={retrySeconds > 0}
              onClick={() => fileInputRef.current?.click()}
              className="text-xs font-semibold px-4 py-2 rounded-lg text-white transition-opacity hover:opacity-90 cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ backgroundColor: 'var(--color-primary)' }}
            >
              {retrySeconds > 0 ? `Wait ${retrySeconds}s` : 'Try Again'}
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="text-xs font-medium px-4 py-2 rounded-lg border transition-colors hover:bg-slate-50 cursor-pointer"
              style={{ borderColor: 'var(--color-border)', color: 'var(--color-text-secondary)' }}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* ── 4. EMPTY / IDLE / DRAGGING STATE ── */}
      {(status === 'idle' || status === 'dragging') && (
        <div
          onDragOver={onDragOver}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          onClick={() => {
            if (retrySeconds <= 0) fileInputRef.current?.click()
          }}
          className={`flex flex-col items-center justify-center py-10 px-4 rounded-lg border-2 border-dashed transition-colors ${
            retrySeconds > 0 ? 'cursor-not-allowed opacity-60' : 'cursor-pointer'
          }`}
          style={{
            borderColor: status === 'dragging' ? 'var(--color-primary)' : 'var(--color-border)',
            backgroundColor: status === 'dragging' ? '#EFF6FF' : '#FAFAFA',
          }}
          data-testid="dropzone"
        >
          <div
            className="flex h-12 w-12 items-center justify-center rounded-full mb-3"
            style={{ backgroundColor: '#EFF6FF', color: 'var(--color-primary)' }}
          >
            <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
              />
            </svg>
          </div>
          <p className="text-sm font-semibold" style={{ color: 'var(--color-text-primary)' }}>
            Drag & drop your CSV here, or <span style={{ color: 'var(--color-primary)' }}>browse</span>
          </p>
          <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
            Supports comma-separated .csv files up to 10 MB
          </p>
        </div>
      )}
    </div>
  )
}
