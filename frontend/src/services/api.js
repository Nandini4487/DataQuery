// Base URL from VITE_API_URL env var; defaults to localhost:8000 for local dev.
// Never put API keys here — this file is bundled and sent to the browser.
const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

/**
 * Thin fetch wrapper: adds Content-Type, base URL, and a consistent
 * error shape { error, message } matching the backend's error schema.
 */
async function request(path, options = {}) {
  const url = `${BASE_URL}${path}`
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    })
    const data = await res.json()
    if (!res.ok) {
      return { ok: false, status: res.status, data }
    }
    return { ok: true, status: res.status, data }
  } catch (err) {
    return {
      ok: false,
      status: 0,
      data: { error: 'network_error', message: 'Could not reach the server.' },
    }
  }
}

/** GET /api/health */
export async function healthCheck() {
  return request('/api/health')
}
