import React, { type ReactNode, type ButtonHTMLAttributes } from 'react'
import { Spinner } from './Spinner'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  loading?: boolean
  children: ReactNode
}

const styles: Record<string, React.CSSProperties> = {
  primary:   { background: '#FF6B00', color: '#FFFFFF', border: '1.5px solid #FF6B00' },
  secondary: { background: 'transparent', color: '#FF6B00', border: '1.5px solid #FF6B00' },
  danger:    { background: 'transparent', color: '#DC2626', border: '1.5px solid rgba(220,38,38,0.4)' },
  ghost:     { background: 'transparent', color: 'var(--text-muted)', border: '1.5px solid var(--border)' },
}
const hoverStyles: Record<string, React.CSSProperties> = {
  primary:   { background: '#FF8C33', transform: 'translateY(-1px)', boxShadow: '0 4px 16px rgba(255,107,0,0.3)' },
  secondary: { background: 'rgba(255,107,0,0.06)' },
  danger:    { background: 'rgba(220,38,38,0.08)' },
  ghost:     { background: 'var(--surface2)', color: 'var(--text)' },
}

export function Button({
  variant = 'primary', loading, children, className = '', disabled, style, ...rest
}: ButtonProps) {
  const [hovered, setHovered] = React.useState(false)
  const base: React.CSSProperties = {
    display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7,
    padding: '9px 18px', borderRadius: 8,
    fontSize: 14, fontWeight: 600, fontFamily: 'inherit',
    cursor: disabled || loading ? 'not-allowed' : 'pointer',
    opacity: disabled || loading ? 0.45 : 1,
    transition: 'all 0.15s ease',
    ...styles[variant],
    ...(hovered && !disabled && !loading ? hoverStyles[variant] : {}),
    ...style,
  }
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      style={base}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {loading && <Spinner size={13} />}
      {children}
    </button>
  )
}
