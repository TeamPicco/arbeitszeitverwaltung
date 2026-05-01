import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  accent?: boolean
  padding?: string
}

export function Card({ children, className = '', padding = 'p-6' }: CardProps) {
  return (
    <div
      className={`rounded-lg ${padding} ${className}`}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
    >
      {children}
    </div>
  )
}

export function MetricCard({
  label, value, sub, icon,
}: {
  label: string
  value: string | number
  sub?: string
  icon?: ReactNode
}) {
  return (
    <div
      className="rounded-lg p-5"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          {label}
        </p>
        {icon && (
          <span
            className="flex items-center justify-center w-7 h-7 rounded-md"
            style={{ background: 'var(--accent-dim2)', color: 'var(--accent)' }}
          >
            {icon}
          </span>
        )}
      </div>
      <p className="text-3xl font-bold tracking-tight" style={{ color: 'var(--text)' }}>
        {value}
      </p>
      {sub && (
        <p className="text-xs mt-2" style={{ color: 'var(--text-muted)' }}>
          {sub}
        </p>
      )}
    </div>
  )
}

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-5">
      <h2 className="text-sm font-semibold" style={{ color: 'var(--text)' }}>{title}</h2>
      {action}
    </div>
  )
}
