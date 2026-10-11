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
