export default function EmptyState({ icon, title, description }) {
  return (
    <div
      className="w-full rounded-xl border p-8 text-center"
      style={{
        backgroundColor: 'var(--color-surface)',
        borderColor: 'var(--color-border)',
        borderRadius: 'var(--radius-card)',
      }}
    >
      {icon && (
        <div
          className="mx-auto flex h-10 w-10 items-center justify-center rounded-full mb-3"
          style={{ backgroundColor: '#F1F5F9', color: 'var(--color-text-secondary)' }}
        >
          {icon}
        </div>
      )}
      <h4 className="font-semibold text-sm" style={{ color: 'var(--color-text-primary)' }}>
        {title}
      </h4>
      {description && (
        <p className="text-xs mt-1" style={{ color: 'var(--color-text-secondary)' }}>
          {description}
        </p>
      )}
    </div>
  )
}
