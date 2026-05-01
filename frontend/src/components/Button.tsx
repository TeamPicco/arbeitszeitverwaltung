import { type ReactNode, type ButtonHTMLAttributes } from 'react'
import { Spinner } from './Spinner'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  loading?: boolean
  children: ReactNode
}

const styles = {
  primary:   'bg-[#F97316] hover:bg-[#ea6a0a] text-white font-semibold',
  secondary: 'bg-[#17171f] hover:bg-[#1c1c26] text-[#ededf0] border border-[#1f1f2e] hover:border-[#2d2d42]',
  danger:    'bg-transparent hover:bg-red-950/30 text-red-400 border border-red-900/30 hover:border-red-800/50',
  ghost:     'bg-transparent hover:bg-white/5 text-[#6c6c80] hover:text-[#ededf0]',
}

export function Button({
  variant = 'primary', loading, children, className = '', disabled, ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 px-3.5 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
    >
      {loading && <Spinner size={13} />}
      {children}
    </button>
  )
}
