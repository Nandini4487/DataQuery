// Base URL from VITE_API_URL env var; defaults to localhost:8000 for local dev.
// Never put API keys here — this file is bundled and sent to the browser.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Friendly error messages for every API error code.
 * Ensures the UI never displays raw JSON, exception traces, or cryptic codes.
 */
export const ERROR_MESSAGES = {
  rate_limited: (retryAfter) =>
    retryAfter != null && retryAfter > 0
      ? `Too many requests. Please wait ${retryAfter} second${retryAfter === 1 ? '' : 's'} and try again.`
      : 'Too many requests. Please wait a moment and try again.',
  documents_required:
    'This question requires reference documents, but none have been uploaded yet. Upload a PDF or TXT document above to proceed.',
  unsupported_question:
    'This question cannot be answered from the current dataset and documents. Please rephrase or ask a different question.',
  invalid_plan:
    'Could not formulate a safe data analysis plan for this question. Please rephrase or specify column names.',
  provider_unavailable:
    'The AI service is temporarily unavailable. Please try again in a moment.',
  embedding_unavailable:
    'The document search and embedding service is temporarily unavailable. Please try again shortly.',
  dataset_not_found:
    'The requested dataset was not found or has expired. Please upload your CSV again.',
  document_not_found:
    'The requested reference document was not found.',
  invalid_request:
    'Invalid request parameter. Please check your inputs and try again.',
  file_too_large:
    'The uploaded file exceeds the 10 MB maximum size limit.',
  internal_error:
    'An unexpected server error occurred. Please try again later.',
  network_error:
    'Could not reach the server. Is backend running?',
}

/**
 * Maps an API error code or status code to a user-friendly message.
 */
export function getFriendlyErrorMessage(errorCode, fallbackMessage, retryAfter) {
  if (errorCode === 'rate_limited') {
    return ERROR_MESSAGES.rate_limited(retryAfter)
  }
  if (errorCode && ERROR_MESSAGES[errorCode]) {
    return ERROR_MESSAGES[errorCode]
  }
  if (typeof fallbackMessage === 'string' && fallbackMessage.trim().length > 0) {
    // If fallback is already a clean string and not JSON
    if (!fallbackMessage.startsWith('{') && !fallbackMessage.startsWith('[')) {
      return fallbackMessage
    }
  }
  return 'An error occurred while processing your request.'
}

/**
 * Thin fetch wrapper: adds Content-Type when appropriate, base URL, Retry-After parsing,
 * and a consistent error shape { ok, status, data, error, message, retryAfter }.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  const isFormData = options.body instanceof FormData
  const headers = isFormData
    ? { ...options.headers }
    : { 'Content-Type': 'application/json', ...options.headers }

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    })

    // Parse Retry-After header if present (seconds integer)
    const retryHeader = res.headers.get('retry-after') || res.headers.get('Retry-After')
    let retryAfter = null
    if (retryHeader) {
      const parsed = parseInt(retryHeader, 10)
      if (!Number.isNaN(parsed) && parsed >= 0) {
        retryAfter = parsed
      }
    }

    let data
    try {
      data = await res.json()
    } catch {
      data = {
        error: res.ok ? 'invalid_response' : (res.status === 429 ? 'rate_limited' : 'request_failed'),
        message: res.statusText || 'Unable to parse server response.',
      }
    }

    if (!res.ok) {
      const errorType =
        data?.error ||
        (res.status === 429
          ? 'rate_limited'
          : res.status === 404
          ? 'not_found'
          : res.status === 413
          ? 'file_too_large'
          : 'request_failed')

      let rawMsg = data?.message
      if (!rawMsg) {
        if (Array.isArray(data?.detail)) {
          rawMsg = data.detail.map((d) => (typeof d === 'object' ? d.msg || JSON.stringify(d) : String(d))).join(', ')
        } else if (typeof data?.detail === 'string') {
          rawMsg = data.detail
        }
      }

      const message = getFriendlyErrorMessage(errorType, rawMsg, retryAfter)

      return {
        ok: false,
        status: res.status,
        error: errorType,
        message,
        retryAfter,
        data,
      }
    }

    return {
      ok: true,
      status: res.status,
      data,
      retryAfter,
    }
  } catch {
    const message = ERROR_MESSAGES.network_error
    return {
      ok: false,
      status: 0,
      error: 'network_error',
      message,
      retryAfter: null,
      data: { error: 'network_error', message },
    }
  }
}

/** GET /api/health */
export async function healthCheck() {
  return request('/api/health')
}

/** POST /api/datasets - upload a CSV file */
export async function uploadDataset(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request('/api/datasets', {
    method: 'POST',
    body: formData,
  })
}

/** GET /api/datasets/{id}/profile */
export async function getProfile(datasetId) {
  return request(`/api/datasets/${datasetId}/profile`)
}

/** GET /api/datasets/{id}/preview */
export async function getPreview(datasetId) {
  return request(`/api/datasets/${datasetId}/preview`)
}

/** DELETE /api/datasets/{id} */
export async function deleteDataset(datasetId) {
  return request(`/api/datasets/${datasetId}`, {
    method: 'DELETE',
  })
}

/**
 * POST /api/datasets/{id}/documents - upload and index a reference document (PDF or TXT)
 */
export async function uploadDocument(datasetId, file) {
  const formData = new FormData()
  formData.append('file', file)
  return request(`/api/datasets/${datasetId}/documents`, {
    method: 'POST',
    body: formData,
  })
}

/**
 * GET /api/datasets/{id}/documents - list indexed reference documents
 */
export async function listDocuments(datasetId) {
  return request(`/api/datasets/${datasetId}/documents`)
}

/**
 * DELETE /api/datasets/{id}/documents/{docId} - delete reference document and its indexed vectors
 */
export async function deleteDocument(datasetId, docId) {
  return request(`/api/datasets/${datasetId}/documents/${docId}`, {
    method: 'DELETE',
  })
}

/**
 * POST /api/datasets/{id}/ask - ask a question against a dataset.
 */
export async function askQuestion(datasetId, question) {
  return request(`/api/datasets/${datasetId}/ask`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  })
}
