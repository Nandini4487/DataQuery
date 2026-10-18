import ResultTable from '../results/ResultTable'
import ChartRenderer from '../results/ChartRenderer'
import SourceCitation from '../sources/SourceCitation'

/**
 * ChatMessage Component
 *
 * Displays a conversation turn:
 * - A user question bubble
 * - An answer card with loading, error, empty, and success states
 * - Route badge: "Data engine" (structured), "Documents" (document), or "Data + documents" (combined)
 * - "Computed by data engine" badge (only when computed_by_engine is true)
 * - Fallback note when AI explanation was unavailable
 * - ResultTable and ChartRenderer components ONLY when table/chart actually exist
 * - Collapsible "Sources & Citations" panel when citations exist
 * - Friendly inline error messages for documents_required, unsupported_question, embedding_unavailable, provider_unavailable, invalid_plan
 */
export default function ChatMessage({ message, question: qProp, answer: aProp, error: errProp, loading: loadProp }) {
  const question = message?.question ?? qProp ?? ''
  const answer = message?.answer ?? aProp ?? null
  const error = message?.error ?? errProp ?? null
  const loading = message?.loading ?? loadProp ?? false
  const timestamp = message?.timestamp ?? null

  const isFallback = Boolean(answer?.explanation_is_fallback)
  const isComputedByEngine = Boolean(answer?.computed_by_engine)

  const route = answer?.route
  const routeLabel =
    route === 'structured'
      ? 'Data engine'
      : route === 'document'
      ? 'Documents'
      : route === 'combined'
      ? 'Data + documents'
      : null

  const hasTable = Boolean(answer?.table && Array.isArray(answer.table.rows) && answer.table.rows.length > 0)
  const hasChart = Boolean(answer?.chart_spec && answer.chart_spec.type && answer.chart_spec.type !== 'none')
  const hasCitations = Boolean(answer?.citations && Array.isArray(answer.citations) && answer.citations.length > 0)

  // Configure friendly error display
  const getErrorInfo = (err) => {
    const code = err?.error || 'error'
    const rawMsg = typeof err === 'string' ? err : err?.message || ''

    switch (code) {
      case 'documents_required':
        return {
          title: 'Reference Document Required',
          message: rawMsg || 'Please upload a reference document (.pdf or .txt) above before asking questions about documents or policies.',
          tip: 'Use the Reference Documents uploader above to attach your documentation.',
          bg: '#FFFBEB',
          border: '#FDE68A',
          textColor: '#92400E',
          icon: '📄',
        }
      case 'unsupported_question':
        return {
          title: 'Question Unsupported',
          message: rawMsg || 'This question cannot be answered from the current dataset columns or documents.',
          tip: 'Try rephrasing your question to target available columns or uploaded reference materials.',
          bg: '#FFFBEB',
          border: '#FDE68A',
          textColor: '#92400E',
          icon: 'ℹ️',
        }
      case 'embedding_unavailable':
        return {
          title: 'Embedding Service Unavailable',
          message: rawMsg || 'The document embedding engine is temporarily unavailable. Please try again shortly.',
          tip: 'Check that backend vector services are operational.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⏳',
        }
      case 'provider_unavailable':
        return {
          title: 'AI Service Temporarily Unavailable',
          message: rawMsg || 'The AI service is temporarily unreachable. Please try again in a moment.',
          tip: 'The backend will automatically retry on transient connection interruptions.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⏳',
        }
      case 'invalid_plan':
        return {
          title: 'Query Plan Notice',
          message: rawMsg || 'Unable to formulate a safe deterministic execution plan for this question.',
          tip: 'Try asking for specific aggregates (sums, averages, counts) or filters.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⚠️',
        }
      case 'rate_limited':
        return {
          title: 'Rate Limit Reached',
          message: rawMsg || 'Too many requests. Please wait a moment and try again.',
          tip: 'Please pause before submitting another question to avoid exhausting server rate limits.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⏱️',
        }
      case 'dataset_not_found':
        return {
          title: 'Dataset Not Found',
          message: rawMsg || 'The dataset was not found or has expired. Please upload your CSV again.',
          tip: 'Datasets are ephemeral. Upload a new CSV above to continue.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '📁',
        }
      case 'document_not_found':
        return {
          title: 'Document Not Found',
          message: rawMsg || 'The referenced document was not found.',
          tip: 'Please upload the document again.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '📄',
        }
      case 'invalid_request':
        return {
          title: 'Invalid Request',
          message: rawMsg || 'Invalid request parameter. Please verify your query.',
          tip: 'Ensure the question is not empty or overly long.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⚠️',
        }
      case 'file_too_large':
        return {
          title: 'File Too Large',
          message: rawMsg || 'The file exceeds the maximum 10 MB limit.',
          tip: 'Please upload files under 10 MB.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '📁',
        }
      case 'network_error':
        return {
          title: 'Connection Error',
          message: rawMsg || 'Could not reach the server. Is backend running?',
          tip: 'Check that the FastAPI server is running on port 8000.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '🔌',
        }
      case 'internal_error':
        return {
          title: 'Server Error',
          message: rawMsg || 'An unexpected server error occurred.',
          tip: 'Please try again in a few moments.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⚠️',
        }
      default:
        return {
          title: 'Query Notice',
          message: rawMsg || 'Unable to complete this query.',
          tip: 'Check your dataset schema and question phrasing.',
          bg: '#FEF2F2',
          border: '#FECACA',
          textColor: '#991B1B',
          icon: '⚠️',
        }
    }
  }

  const errInfo = error ? getErrorInfo(error) : null

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
                    Analyzing query with DataQuery engine…
                  </span>
                  <span className="text-2xs text-slate-400">
                    Routing, retrieving evidence, and executing computations
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

          {/* ── B. Friendly Inline Error State ── */}
          {!loading && error && errInfo && (
            <div className="flex flex-col gap-2">
              <div
                className="p-3.5 rounded-lg border text-xs flex items-start gap-3"
                style={{
                  backgroundColor: errInfo.bg,
                  borderColor: errInfo.border,
                }}
              >
                <span className="text-base leading-none">{errInfo.icon}</span>
                <div className="flex-1 flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span
                      className="font-semibold"
                      style={{ color: errInfo.textColor }}
                    >
                      {errInfo.title}
                    </span>
                    <span
                      className="px-1.5 py-0.5 rounded text-2xs uppercase font-mono font-medium"
                      style={{
                        backgroundColor: 'rgba(0,0,0,0.05)',
                        color: errInfo.textColor,
                      }}
                    >
                      {error.error || 'notice'}
                    </span>
                  </div>
                  <p
                    className="leading-relaxed"
                    style={{ color: errInfo.textColor }}
                  >
                    {errInfo.message}
                  </p>
                </div>
              </div>
              {errInfo.tip && (
                <p className="text-2xs text-slate-400 px-1">
                  Tip: {errInfo.tip}
                </p>
              )}
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
                {/* Route badge: "Data engine", "Documents", or "Data + documents" */}
                {routeLabel && (
                  <span
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold shadow-2xs border"
                    style={{
                      backgroundColor:
                        route === 'document'
                          ? '#EFF6FF'
                          : route === 'combined'
                          ? '#F5F3FF'
                          : '#F1F5F9',
                      color:
                        route === 'document'
                          ? '#1D4ED8'
                          : route === 'combined'
                          ? '#6D28D9'
                          : '#334155',
                      borderColor:
                        route === 'document'
                          ? '#BFDBFE'
                          : route === 'combined'
                          ? '#DDD6FE'
                          : '#CBD5E1',
                    }}
                  >
                    <span className="text-2xs">
                      {route === 'document' ? '📄' : route === 'combined' ? '📊+📄' : '📊'}
                    </span>
                    {routeLabel}
                  </span>
                )}

                {/* Show "Computed by data engine" ONLY when computed_by_engine is true */}
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

                {/* Fallback explanation note */}
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

              {/* Plain-English Answer Text (rendered safely as plain text) */}
              {answer.answer_text && (
                <div
                  className="text-sm leading-relaxed font-normal whitespace-pre-wrap"
                  style={{ color: 'var(--color-text-primary)' }}
                >
                  {answer.answer_text}
                </div>
              )}

              {/* Data Table & Visualization ONLY when they actually exist */}
              {(hasTable || hasChart) && (
                <div className="flex flex-col gap-4 pt-1">
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 items-start">
                    {hasTable && (
                      <div className="w-full">
                        <ResultTable table={answer.table} />
                      </div>
                    )}
                    {hasChart && (
                      <div className="w-full">
                        <ChartRenderer chartSpec={answer.chart_spec} />
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Empty Data Rows indicator if table exists but has 0 rows */}
              {answer.table && Array.isArray(answer.table.rows) && answer.table.rows.length === 0 && (
                <div
                  className="p-3 rounded-lg border text-xs text-center text-slate-500"
                  style={{ borderColor: 'var(--color-border)', backgroundColor: 'var(--color-background)' }}
                >
                  The query executed successfully but 0 rows matched the condition.
                </div>
              )}

              {/* Sources & Citations Panel (Hidden when there are no citations) */}
              {hasCitations && (
                <div
                  className="mt-2 pt-3 border-t flex flex-col gap-2.5"
                  style={{ borderColor: 'var(--color-border)' }}
                >
                  <div className="flex items-center gap-1.5 font-semibold text-xs text-slate-700">
                    <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth="2"
                        d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                      />
                    </svg>
                    <span>Reference Sources & Citations ({answer.citations.length})</span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5">
                    {answer.citations.map((cit, idx) => (
                      <SourceCitation
                        key={`${cit.document_id || idx}-${cit.chunk_index ?? idx}-${idx}`}
                        citation={cit}
                        index={idx}
                      />
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
