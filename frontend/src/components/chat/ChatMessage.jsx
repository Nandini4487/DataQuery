import ResultTable from '../results/ResultTable'
import ChartRenderer from '../results/ChartRenderer'

/**
 * ChatMessage Component
 *
 * Displays a conversation turn:
 * - A user question bubble
 * - An answer card with loading, error, empty, and success states
 * - "Computed by data engine" badge
 * - Fallback note when AI explanation was unavailable
 * - ResultTable and ChartRenderer components for numerical results
 */
export default function ChatMessage({ message, question: qProp, answer: aProp, error: errProp, loading: loadProp }) {
  const question = message?.question ?? qProp ?? ''
  const answer = message?.answer ?? aProp ?? null
  const error = message?.error ?? errProp ?? null
  const loading = message?.loading ?? loadProp ?? false
  const timestamp = message?.timestamp ?? null

  const isFallback = Boolean(answer?.explanation_is_fallback)
  const isComputedByEngine = answer?.computed_by_engine ?? true

  return (
    <div className="w-full flex flex-col gap-3 py-2">
      {/* ── 1. User Question Bubble ── */}
      <div className="flex justify-end items-end gap-2">
        <div className="max-w-2xl flex flex-col items-end">
          <div
            className="px-4 py-2.5 text-white text-sm font-medium rounded-2xl rounded-tr-xs shadow-xs"
            style={{ backgroundColor: 'var(--color-primary)' }}
          >
            {question}
          </div>
          {timestamp && (
            <span className="text-2xs text-slate-400 mt-1 px-1">
              {timestamp}
            </span>
          )}
        </div>
        <div
          className="h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 shadow-2xs"
          style={{ backgroundColor: '#1E293B' }}
          title="User"
        >
          U
        </div>
      </div>

      {/* ── 2. Assistant Answer Card ── */}
      <div className="flex justify-start items-start gap-2.5">
        <div
          className="h-7 w-7 rounded-full flex items-center justify-center text-xs font-bold text-white shrink-0 shadow-2xs mt-1"
          style={{ backgroundColor: 'var(--color-primary)' }}
          title="DataQuery AI"
        >
          DQ
        </div>

        <div
          className="flex-1 max-w-4xl rounded-xl border p-4.5 shadow-2xs transition-all"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)',
            borderRadius: 'var(--radius-card)',
          }}
        >
          {/* ── A. Loading State ── */}
          {loading && (
            <div className="flex flex-col gap-3 py-4">
              <div className="flex items-center gap-3">
                <svg
                  className="h-5 w-5 animate-spin"
                  style={{ color: 'var(--color-primary)' }}
                  viewBox="0 0 24 24"
                  fill="none"
                >
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold" style={{ color: 'var(--color-text-primary)' }}>
                    Analyzing query with deterministic data engine…
                  </span>
                  <span className="text-2xs text-slate-400">
                    Routing, planning, and executing computations
                  </span>
                </div>
              </div>
              {/* Skeleton placeholders */}
              <div className="space-y-2 pt-2">
                <div className="h-3.5 bg-slate-100 rounded-md w-4/5 animate-pulse" />
                <div className="h-3.5 bg-slate-100 rounded-md w-3/5 animate-pulse" />
              </div>
            </div>
          )}

          {/* ── B. Error State (Friendly Inline Message) ── */}
          {!loading && error && (
            <div className="flex flex-col gap-2">
              <div
                className="p-3.5 rounded-lg border text-xs flex items-start gap-3"
                style={{
                  backgroundColor: error.error === 'unsupported_question' ? '#FFFBEB' : '#FEF2F2',
                  borderColor: error.error === 'unsupported_question' ? '#FDE68A' : '#FECACA',
                }}
              >
                <span className="text-base leading-none">
                  {error.error === 'unsupported_question' ? 'ℹ️' : error.error === 'provider_unavailable' ? '⏳' : '⚠️'}
                </span>
                <div className="flex-1 flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="font-semibold"
                      style={{
                        color: error.error === 'unsupported_question' ? '#92400E' : 'var(--color-error)',
                      }}
                    >
                      {error.error === 'unsupported_question'
                        ? 'Question Unsupported by Schema'
                        : error.error === 'provider_unavailable'
                        ? 'AI Service Temporarily Unavailable'
                        : error.error === 'invalid_plan'
                        ? 'Plan Validation Notice'
                        : 'Query Notice'}
                    </span>
                    <span
                      className="px-1.5 py-0.5 rounded text-2xs uppercase font-mono font-medium"
                      style={{
                        backgroundColor: error.error === 'unsupported_question' ? '#FEF3C7' : '#FEE2E2',
                        color: error.error === 'unsupported_question' ? '#B45309' : '#DC2626',
                      }}
                    >
                      {error.error || 'error'}
                    </span>
                  </div>
                  <p
                    className="leading-relaxed"
                    style={{
                      color: error.error === 'unsupported_question' ? '#78350F' : '#991B1B',
                    }}
                  >
                    {typeof error === 'string' ? error : error.message || 'Unable to complete this query.'}
                  </p>
                </div>
              </div>
              <p className="text-2xs text-slate-400 px-1">
                Tip: Try rephrasing your question to target columns present in your dataset schema.
              </p>
            </div>
          )}

          {/* ── C. Empty State ── */}
          {!loading && !error && !answer && (
            <div className="text-center py-6 text-slate-400">
              <p className="text-xs">No response available for this message.</p>
            </div>
          )}

          {/* ── D. Success State ── */}
          {!loading && !error && answer && (
            <div className="flex flex-col gap-4">
              {/* Badges and Metadata Header */}
              <div className="flex flex-wrap items-center gap-2">
                {isComputedByEngine && (
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold shadow-2xs"
                    style={{
                      backgroundColor: '#ECFDF5',
                      color: 'var(--color-success)',
                      borderColor: '#A7F3D0',
                      borderWidth: '1px',
                    }}
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                        clipRule="evenodd"
                      />
                    </svg>
                    Computed by data engine
                  </span>
                )}

                {isFallback && (
                  <span
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                    style={{
                      backgroundColor: '#FEF3C7',
                      color: 'var(--color-warning)',
                      borderColor: '#FDE68A',
                      borderWidth: '1px',
                    }}
                    title="The AI explanation model was unavailable; results were computed deterministically with a fallback explanation."
                  >
                    <svg className="w-3.5 h-3.5" viewBox="0 0 20 20" fill="currentColor">
                      <path
                        fillRule="evenodd"
                        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z"
                        clipRule="evenodd"
                      />
                    </svg>
                    AI explanation unavailable (fallback used)
                  </span>
                )}
              </div>

              {/* Plain-English Answer Text */}
              {answer.answer_text && (
                <div
                  className="text-sm leading-relaxed font-normal"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {answer.answer_text}
                </div>
              )}

              {/* Data Table & Visualization */}
              {(answer.table || answer.chart_spec) && (
                <div className="flex flex-col gap-4 pt-1">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
                    {answer.table && (
                      <div className="w-full">
                        <ResultTable table={answer.table} />
                      </div>
                    )}
                    {answer.chart_spec && (
                      <div className="w-full">
                        <ChartRenderer chartSpec={answer.chart_spec} />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Empty Data Rows indicator if table is empty */}
              {answer.table && Array.isArray(answer.table.rows) && answer.table.rows.length === 0 && (
                <div
                  className="p-3 rounded-lg border text-xs text-center text-slate-500"
                  style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-background)' }}
                >
                  The query executed successfully but 0 rows matched the condition.
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
