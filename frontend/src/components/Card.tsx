import { type ReactNode } from 'react'

interface CardProps {
  children: ReactNode
  className?: string
  accent?: boolean
  padding?: string
}

export function Card({ children, className = '', accent, padding = 'p-8' }: CardProps) {
  return (
    <div
      className={`rounded-2xl ${padding} ${className}`}
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        ...(accent ? { borderLeft: '4px solid var(--accent)' } : {}),
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
      className="rounded-2xl p-7"
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderLeft: '4px solid var(--accent)',
      }}
    >
      <div className="flex items-start justify-between mb-4">
        <p className="text-sm font-bold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          {label}
        </p>
        {icon && <span style={{ color: 'var(--accent)', opacity: 0.7 }}>{icon}</span>}
      </div>
      <p className="text-5xl font-bold" style={{ color: 'var(--accent)' }}>
        {value}
      </p>
      {sub && (
        <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>
          {sub}
        </p>
      )}
    </div>
  )
}

export function SectionHeader({ title, action }: { title: string; action?: ReactNode }) {
  return (
    <div className="flex items-center justify-between mb-6 pb-4"
      style={{ borderBottom: '1px solid var(--border)' }}>
      <h2 className="text-xl font-semibold">{title}</h2>
      {action}
    </div>
  )
}
