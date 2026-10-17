import { useState } from 'react'

/**
 * SourceCitation Component
 *
 * Renders an individual document citation with source badge, filename,
 * page number (or chunk index for text files), and snippet as safe plain text.
 * Snippet is collapsible/expandable so long passages do not disrupt card layout.
 *
 * CRITICAL SECURITY RULE: Uses normal React text rendering only; never dangerouslySetInnerHTML.
 */
export default function SourceCitation({ citation, index }) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (!citation) return null

  const { filename, page_number, chunk_index, snippet } = citation

  const locationLabel =
    page_number != null
      ? `Page ${page_number}`
      : chunk_index != null
      ? `Chunk ${chunk_index + 1}`
      : 'Reference'

  const cleanSnippet = typeof snippet === 'string' ? snippet.trim() : ''
  const isLong = cleanSnippet.length > 160
  const displayedSnippet = isLong && !isExpanded
    ? `${cleanSnippet.slice(0, 160)}…`
    : cleanSnippet

  return (
    <div
      className="p-3 rounded-lg border text-xs flex flex-col gap-2 transition-colors"
      style={{
        backgroundColor: 'var(--color-background)',
        borderColor: 'var(--color-border)',
      }}
    >
      {/* Header with Source Index, Filename, and Page/Chunk Badge */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-2xs font-bold text-white shadow-2xs"
            style={{ backgroundColor: 'var(--color-primary)' }}
            title={`Source [${(index ?? 0) + 1}]`}
          >
            {(index ?? 0) + 1}
          </span>
          {/* Normal React text rendering only */}
          <span
            className="font-semibold truncate max-w-xs"
            style={{ color: 'var(--color-text-primary)' }}
            title={filename}
          >
            {filename || 'Document'}
          </span>
        </div>

        <span
          className="inline-flex items-center px-2 py-0.5 rounded text-2xs font-mono font-medium border shadow-2xs"
          style={{
            backgroundColor: 'var(--color-surface)',
            borderColor: 'var(--color-border)',
            color: 'var(--color-text-secondary)',
          }}
        >
          {locationLabel}
        </span>
      </div>

      {/* Snippet rendered strictly as normal React text */}
      {cleanSnippet && (
        <div className="flex flex-col gap-1">
          <p
            className="text-xs leading-relaxed italic text-slate-700 bg-white/70 p-2.5 rounded border border-slate-200/60"
            style={{ color: 'var(--color-text-primary)' }}
          >
            “{displayedSnippet}”
          </p>
          {isLong && (
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="self-start text-2xs font-medium text-blue-600 hover:text-blue-800 hover:underline cursor-pointer focus:ring-2 focus:ring-blue-500 focus:outline-hidden rounded px-1 py-0.5"
              aria-label={isExpanded ? `Show less from source ${filename}` : `Show more from source ${filename}`}
            >
              {isExpanded ? 'Show less' : 'Show full passage'}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
