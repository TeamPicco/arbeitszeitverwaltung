import { type ReactNode } from 'react'

export function PageHeader({
  title,
  sub,
  action,
}: {
  title: string
  sub?: string
  action?: ReactNode
}) {
  return (
    <div className="flex items-start justify-between mb-7 gap-4">
      <div>
        <h1 className="text-[22px] font-bold tracking-tight leading-tight" style={{ color: 'var(--text)' }}>
          {title}
        </h1>
        {sub && (
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {sub}
          </p>
        )}
      </div>
      {action && <div className="shrink-0 mt-0.5">{action}</div>}
    </div>
  )
}
