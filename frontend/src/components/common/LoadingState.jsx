export default function LoadingState({ message = 'Loading…' }) {
  return (
    <div
      className="w-full rounded-xl border p-8 text-center"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <svg
        className="h-8 w-8 animate-spin mx-auto mb-3"
        style={{ color: 'var(--color-primary)' }}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        aria-label="Loading"
      >
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
      </svg>
      <p className="text-sm font-medium" style={{ color: 'var(--color-text-secondary)' }}>
        {message}
      </p>
    </div>
  )
}
