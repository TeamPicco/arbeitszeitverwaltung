import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  padding?: string
}

export function Card({ children, className = '', padding = 'p-6' }: CardProps) {
  return (
    <div
      className={`rounded-xl ${padding} ${className}`}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-card)',
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
      className="rounded-xl p-5"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-card)',
        borderLeft: '4px solid var(--accent)',
      }}
    >
      <div className="flex items-center justify-between mb-3">
        <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          {label}
        </p>
        {icon && (
          <span
            className="flex items-center justify-center w-8 h-8 rounded-lg"
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
      <h2 className="font-semibold" style={{ fontSize: 15, color: 'var(--text)' }}>{title}</h2>
      {action}
    </div>
  )
}
