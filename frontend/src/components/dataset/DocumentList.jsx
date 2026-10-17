import { useState } from 'react'
import { deleteDocument } from '../../services/api'

/**
 * DocumentList Component
 *
 * Lists reference documents indexed for the active dataset.
 * Displays filename, type, page count, chunk count, and status.
 * Features an empty state, per-row delete confirmation with loading/error handling,
 * and refreshes when a document is deleted.
 */
export default function DocumentList({ datasetId, documents, loading, error, onRefresh }) {
  const [confirmingId, setConfirmingId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [rowError, setRowError] = useState({}) // { [docId]: errorMessage }

  const handleDelete = async (docId) => {
    if (!datasetId || !docId || deletingId) return

    setDeletingId(docId)
    setRowError((prev) => ({ ...prev, [docId]: '' }))

    const res = await deleteDocument(datasetId, docId)
    setDeletingId(null)
    setConfirmingId(null)

    if (res.ok) {
      if (onRefresh) {
        onRefresh()
      }
    } else {
      const msg = res.message || res.data?.message || res.data?.error || 'Failed to delete document.'
      setRowError((prev) => ({ ...prev, [docId]: msg }))
    }
  }

  // 1. Loading State
  if (loading && (!documents || documents.length === 0)) {
    return (
      <div
        className="w-full rounded-xl border p-6 text-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <svg
          className="h-6 w-6 animate-spin mx-auto mb-2"
          style={{ color: 'var(--color-primary)' }}
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
        </svg>
        <p className="text-xs font-medium" style={{ color: 'var(--color-text-secondary)' }}>
          Loading reference documents…
        </p>
      </div>
    )
  }

  // 2. Global Error State
  if (error && (!documents || documents.length === 0)) {
    return (
      <div
        className="w-full rounded-xl border p-5 text-center"
        style={{
          backgroundColor: '#FEF2F2',
          borderColor: '#FECACA',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <p className="text-xs font-semibold" style={{ color: 'var(--color-error)' }}>
          Failed to load documents
        </p>
        <p className="text-2xs text-slate-500 mt-1">{error}</p>
      </div>
    )
  }

  // 3. Empty State
  if (!documents || documents.length === 0) {
    return (
      <div
        className="w-full rounded-xl border border-dashed p-6 text-center"
        style={{
          backgroundColor: 'var(--color-surface)',
          borderColor: 'var(--color-border)',
          borderRadius: 'var(--radius-card)',
        }}
      >
        <p className="text-xs font-medium" style={{ color: 'var(--color-text-primary)' }}>
          No reference documents yet
        </p>
        <p className="text-2xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          Upload PDF or TXT policy/reference documents above to ask document or combined questions.
        </p>
      </div>
    )
  }

  // 4. Document List Table / Cards
  return (
    <div
      className="w-full rounded-xl border overflow-hidden shadow-2xs"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr
              className="border-b font-semibold"
              style={{
                backgroundColor: 'var(--color-background)',
                borderColor: 'var(--color-border)',
                color: 'var(--color-text-secondary)',
              }}
            >
              <th className="py-2.5 px-4">Filename</th>
              <th className="py-2.5 px-3">Type</th>
              <th className="py-2.5 px-3">Pages</th>
              <th className="py-2.5 px-3">Chunks</th>
              <th className="py-2.5 px-3">Status</th>
              <th className="py-2.5 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y" style={{ borderColor: 'var(--color-border)' }}>
            {documents.map((doc) => {
              const isConfirming = confirmingId === doc.id
              const isDeletingThis = deletingId === doc.id
              const errorThis = rowError[doc.id]

              return (
                <tr
                  key={doc.id}
                  className="hover:bg-slate-50/50 transition-colors"
                >
                  <td className="py-3 px-4 font-medium max-w-xs truncate" style={{ color: 'var(--color-text-primary)' }}>
                    <div className="flex items-center gap-2">
                      <span className="text-sm">
                        {doc.file_type?.toLowerCase() === 'pdf' ? '📄' : '📝'}
                      </span>
                      {/* Normal React text rendering only — no dangerouslySetInnerHTML */}
                      <span title={doc.filename} className="truncate">
                        {doc.filename}
                      </span>
                    </div>
                    {errorThis && (
                      <p className="text-2xs text-rose-600 mt-1">{errorThis}</p>
                    )}
                  </td>
                  <td className="py-3 px-3 uppercase text-2xs font-semibold text-slate-500">
                    {doc.file_type}
                  </td>
                  <td className="py-3 px-3 text-slate-600">
                    {doc.page_count != null ? doc.page_count : '—'}
                  </td>
                  <td className="py-3 px-3 text-slate-600">
                    {doc.chunk_count ?? 0}
                  </td>
                  <td className="py-3 px-3">
                    <span
                      className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium"
                      style={{
                        backgroundColor: '#ECFDF5',
                        color: 'var(--color-success)',
                      }}
                    >
                      {doc.status || 'ready'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    {isConfirming ? (
                      <div className="inline-flex items-center gap-2 justify-end">
                        <span className="text-2xs text-slate-500 font-medium">Delete?</span>
                        <button
                          type="button"
                          disabled={isDeletingThis}
                          onClick={() => handleDelete(doc.id)}
                          className="px-2 py-1 text-2xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-md transition-colors cursor-pointer disabled:opacity-50 focus:ring-2 focus:ring-rose-500 focus:outline-hidden"
                          aria-label={`Confirm delete document ${doc.filename}`}
                        >
                          {isDeletingThis ? 'Deleting…' : 'Yes, Delete'}
                        </button>
                        <button
                          type="button"
                          disabled={isDeletingThis}
                          onClick={() => setConfirmingId(null)}
                          className="px-2 py-1 text-2xs font-medium border border-slate-300 hover:bg-slate-100 rounded-md transition-colors cursor-pointer disabled:opacity-50 focus:ring-2 focus:ring-slate-400 focus:outline-hidden"
                          aria-label="Cancel deletion"
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        type="button"
                        onClick={() => setConfirmingId(doc.id)}
                        className="px-2.5 py-1 text-2xs font-medium text-rose-600 hover:text-rose-700 hover:bg-rose-50 rounded-md transition-colors cursor-pointer focus:ring-2 focus:ring-rose-500 focus:outline-hidden"
                        aria-label={`Delete document ${doc.filename}`}
                      >
                        Delete
                      </button>
                    )}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
