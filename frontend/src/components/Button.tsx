import { type ReactNode, type ButtonHTMLAttributes } from 'react'
import { Spinner } from './Spinner'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  loading?: boolean
  children: ReactNode
}

const styles = {
  primary:
    'bg-[#F97316] hover:bg-[#ea6a0a] text-white font-semibold',
  secondary:
    'bg-[#1a1a1a] hover:bg-[#222] text-[#e8e8e8] border border-[#1f1f1f]',
  danger:
    'bg-transparent hover:bg-red-900/20 text-red-400 border border-red-900/50',
  ghost:
    'bg-transparent hover:bg-[#1a1a1a] text-[#888]',
}

export function Button({
  variant = 'primary',
  loading,
  children,
  className = '',
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg text-sm transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
    >
      {loading && <Spinner size={14} />}
      {children}
    </button>
  )
}
