import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  accent?: boolean
}

export function Card({ children, className = '', accent }: CardProps) {
  return (
    <div
      className={`rounded-xl p-5 ${className}`}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        ...(accent ? { borderLeft: '3px solid var(--accent)' } : {}),
      }}
    >
      {children}
    </div>
  )
}

export function MetricCard({
  label,
  value,
  sub,
}: {
  label: string
  value: string | number
  sub?: string
}) {
  return (
    <Card accent>
      <p
        className="text-xs font-semibold uppercase tracking-widest mb-1"
        style={{ color: 'var(--text-muted)' }}
      >
        {label}
      </p>
      <p className="text-3xl font-bold" style={{ color: 'var(--accent)' }}>
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
          {sub}
        </p>
      )}
    </Card>
  )
}
