export default function ErrorMessage({ title = 'Error', message }) {
  return (
    <div
      className="w-full rounded-xl border p-6 text-center"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      <p className="text-sm font-semibold" style={{ color: 'var(--color-error)' }}>
        {title}
      </p>
      {message && (
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {message}
        </p>
      )}
    </div>
  )
}
