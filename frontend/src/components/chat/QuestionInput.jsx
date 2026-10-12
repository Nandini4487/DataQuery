import { useState } from 'react'
import { askQuestion } from '../../services/api'

export default function QuestionInput({ datasetId, onAsk, onAnswerReceived, disabled, isAsking }) {
  const [question, setQuestion] = useState('')
  const [internalLoading, setInternalLoading] = useState(false)
  const [error, setError] = useState('')
  const [lastSubmitted, setLastSubmitted] = useState('')

  const loading = isAsking || internalLoading

  const handleSubmit = async (e) => {
    if (e) e.preventDefault()
    const trimmed = question.trim()
    if (!trimmed || !datasetId || loading || disabled) return

    setError('')

    // If parent handles the asking flow (e.g. Dashboard managing chat messages)
    if (onAsk) {
      setLastSubmitted(trimmed)
      setQuestion('')
      onAsk(trimmed)
      return
    }

    // Fallback: internal handling
    setInternalLoading(true)
    const res = await askQuestion(datasetId, trimmed)
    setInternalLoading(false)

    if (res.ok) {
      setLastSubmitted(trimmed)
      setQuestion('')
      if (onAnswerReceived) {
        onAnswerReceived(res.data, trimmed)
      }
    } else {
      setError(res.message || res.data?.message || res.data?.error || 'Failed to analyze question.')
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const suggestedQuestions = [
    'What is the total revenue?',
    'Highest revenue product?',
    'Total count of rows?',
  ]

  const handleSuggestionClick = (sq) => {
    if (disabled || loading) return
    setQuestion(sq)
  }

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
        <div>
          <h4 className="font-semibold text-base" style={{ color: 'var(--color-text-primary)' }}>
            Ask a Question
          </h4>
          <p className="text-xs" style={{ color: 'var(--color-text-secondary)' }}>
            Ask in natural language. Powered by deterministic calculations and grounded explanations.
          </p>
        </div>
        {lastSubmitted && (
          <span
            className="text-xs px-2.5 py-1 rounded-full font-medium"
            style={{ backgroundColor: '#DCFCE7', color: 'var(--color-success)' }}
          >
            Last asked: &ldquo;{lastSubmitted.length > 30 ? lastSubmitted.slice(0, 30) + '…' : lastSubmitted}&rdquo;
          </span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <div className="relative">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || loading}
            rows={3}
            placeholder={
              disabled
                ? 'Upload a CSV dataset above to start asking questions…'
                : loading
                ? 'Analyzing query with data engine… please wait'
                : 'e.g. What is the total revenue? Press Enter to ask…'
            }
            className="w-full resize-none rounded-lg border p-3 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-slate-50 disabled:text-slate-400"
            style={{
              borderColor: error ? 'var(--color-error)' : 'var(--color-border)',
              borderRadius: 'var(--radius-input)',
              color: 'var(--color-text-primary)',
            }}
          />

          {loading && (
            <div className="absolute inset-0 bg-white/70 backdrop-blur-2xs flex items-center justify-center rounded-lg">
              <div className="flex items-center gap-2 text-xs font-medium" style={{ color: 'var(--color-primary)' }}>
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Executing query plan with data engine…
              </div>
            </div>
          )}
        </div>

        {/* Suggested question chips */}
        {!disabled && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Suggestions:</span>
            {suggestedQuestions.map((sq) => (
              <button
                key={sq}
                type="button"
                disabled={loading}
                onClick={() => handleSuggestionClick(sq)}
                className="text-xs px-2.5 py-1 rounded-md border bg-slate-50 hover:bg-slate-100 disabled:opacity-50 transition-colors text-slate-600 cursor-pointer disabled:cursor-not-allowed"
                style={{ borderColor: 'var(--color-border)' }}
              >
                {sq}
              </button>
            ))}
          </div>
        )}

        {/* Error State */}
        {error && (
          <div
            className="p-3 rounded-lg border text-xs flex items-start gap-2"
            style={{
              backgroundColor: '#FEF2F2',
              borderColor: '#FECACA',
              color: 'var(--color-error)',
            }}
          >
            <svg className="h-4 w-4 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div className="flex-1">
              <p className="font-semibold">Query Failed</p>
              <p className="mt-0.5">{error}</p>
            </div>
            <button
              type="button"
              onClick={() => setError('')}
              className="text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              ✕
            </button>
          </div>
        )}

        {/* Submit Actions */}
        <div className="flex items-center justify-between pt-1">
          <span className="text-xs text-slate-400">
            {disabled ? 'No dataset active' : 'Shift+Enter for newline'}
          </span>
          <button
            type="submit"
            disabled={disabled || loading || !question.trim()}
            className="flex items-center gap-2 px-5 py-2 text-sm font-semibold rounded-lg text-white shadow-xs transition-opacity hover:opacity-90 disabled:opacity-40 cursor-pointer disabled:cursor-not-allowed"
            style={{ backgroundColor: 'var(--color-primary)' }}
          >
            {loading ? (
              <>
                <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                Analyzing…
              </>
            ) : (
              <>
                <span>Submit Query</span>
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M14 5l7 7m0 0l-7 7m7-7H3" />
                </svg>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  )
}
