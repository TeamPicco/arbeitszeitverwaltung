import { type ReactNode, type ButtonHTMLAttributes } from 'react'
import { Spinner } from './Spinner'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost'
  loading?: boolean
  children: ReactNode
}

const styles = {
  primary:   'bg-[#F97316] hover:bg-[#ea6a0a] text-white font-semibold',
  secondary: 'bg-[#1a1a1a] hover:bg-[#242424] text-[#e8e8e8] border border-[#2a2a2a]',
  danger:    'bg-transparent hover:bg-red-900/20 text-red-400 border border-red-900/40',
  ghost:     'bg-transparent hover:bg-white/5 text-[#888]',
}

export function Button({
  variant = 'primary', loading, children, className = '', disabled, ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2.5 px-5 py-3 rounded-xl text-base font-medium transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${styles[variant]} ${className}`}
    >
      {loading && <Spinner size={16} />}
      {children}
    </button>
  )
}
