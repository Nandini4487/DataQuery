// Base URL from VITE_API_URL env var; defaults to localhost:8000 for local dev.
// Never put API keys here — this file is bundled and sent to the browser.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Thin fetch wrapper: adds Content-Type when appropriate, base URL, and a consistent
 * error shape { error, message } matching the backend's error schema.
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
    let data
    try {
      data = await res.json()
    } catch {
      data = {
        error: res.ok ? 'invalid_response' : 'request_failed',
        message: res.statusText || 'Unable to parse server response.',
      }
    }

    if (!res.ok) {
      return { ok: false, status: res.status, data }
    }
    return { ok: true, status: res.status, data }
  } catch {
    return {
      ok: false,
      status: 0,
      data: { error: 'network_error', message: 'Could not reach the server. Is backend running?' },
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
  const res = await request(`/api/datasets/${datasetId}/documents`, {
    method: 'POST',
    body: formData,
  })

  if (!res.ok) {
    const errorType = res.data?.error || 'upload_failed'
    let message = res.data?.message
    if (!message) {
      if (Array.isArray(res.data?.detail)) {
        message = res.data.detail.map((d) => d.msg || d).join(', ')
      } else if (typeof res.data?.detail === 'string') {
        message = res.data.detail
      } else {
        message = 'Failed to upload document.'
      }
    }
    return {
      ok: false,
      status: res.status,
      error: errorType,
      message,
      data: res.data,
    }
  }

  return {
    ok: true,
    status: res.status,
    data: res.data,
  }
}

/**
 * GET /api/datasets/{id}/documents - list indexed reference documents
 */
export async function listDocuments(datasetId) {
  const res = await request(`/api/datasets/${datasetId}/documents`)
  if (!res.ok) {
    const errorType = res.data?.error || 'fetch_failed'
    const message = res.data?.message || 'Failed to list documents.'
    return {
      ok: false,
      status: res.status,
      error: errorType,
      message,
      data: res.data,
    }
  }
  return {
    ok: true,
    status: res.status,
    data: res.data,
  }
}

/**
 * DELETE /api/datasets/{id}/documents/{docId} - delete reference document and its indexed vectors
 */
export async function deleteDocument(datasetId, docId) {
  const res = await request(`/api/datasets/${datasetId}/documents/${docId}`, {
    method: 'DELETE',
  })
  if (!res.ok) {
    const errorType = res.data?.error || 'delete_failed'
    const message = res.data?.message || 'Failed to delete document.'
    return {
      ok: false,
      status: res.status,
      error: errorType,
      message,
      data: res.data,
    }
  }
  return {
    ok: true,
    status: res.status,
    data: res.data,
  }
}

/**
 * POST /api/datasets/{id}/ask - ask a question against a dataset.
 * Handles specific error codes (unsupported_question, invalid_plan, provider_unavailable)
 * and returns the error message for display.
 */
export async function askQuestion(datasetId, question) {
  const res = await request(`/api/datasets/${datasetId}/ask`, {
    method: 'POST',
    body: JSON.stringify({ question }),
  })

  if (!res.ok) {
    const errorType = res.data?.error || 'unknown_error'
    let message = res.data?.message

    if (!message) {
      if (Array.isArray(res.data?.detail)) {
        message = res.data.detail.map((d) => d.msg || d).join(', ')
      } else if (typeof res.data?.detail === 'string') {
        message = res.data.detail
      } else {
        message = 'An error occurred while analyzing your question.'
      }
    }

    return {
      ok: false,
      status: res.status,
      error: errorType,
      message,
      data: res.data,
    }
  }

  return {
    ok: true,
    status: res.status,
    data: res.data,
  }
}
