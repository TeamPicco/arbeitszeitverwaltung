import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  accent?: boolean
  padding?: string
}

export function Card({ children, className = '', accent, padding = 'p-6' }: CardProps) {
  return (
    <div
      className={`rounded-xl ${padding} ${className}`}
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
  icon,
  trend,
}: {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
  trend?: 'up' | 'down' | 'neutral'
}) {
  return (
    <div
      className="rounded-xl p-5"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderLeft: '3px solid var(--accent)',
      }}
    >
      <div className="flex items-start justify-between">
        <p
          className="text-xs font-semibold uppercase tracking-widest"
          style={{ color: 'var(--text-muted)' }}
        >
          {label}
        </p>
        {icon && (
          <span style={{ color: 'var(--accent)', opacity: 0.6 }}>{icon}</span>
        )}
      </div>
      <p className="text-3xl font-bold mt-2" style={{ color: 'var(--accent)' }}>
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
          {sub}
        </p>
      )}
    </div>
  )
}

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-4 pb-3"
      style={{ borderBottom: '1px solid var(--border)' }}>
      <h2 className="text-base font-semibold">{title}</h2>
      {action}
    </div>
  )
}
