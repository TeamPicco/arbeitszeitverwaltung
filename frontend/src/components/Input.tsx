import { type InputHTMLAttributes, type SelectHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', ...rest }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium" style={{ color: 'var(--text)' }}>
          {label}
        </label>
      )}
      <input
        ref={ref}
        {...rest}
        className={`w-full px-3.5 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316] transition ${className}`}
        style={{
          background: 'var(--surface2)',
          border: `1px solid ${error ? 'var(--danger)' : 'var(--border)'}`,
          color: 'var(--text)',
        }}
      />
      {error && <p className="text-xs" style={{ color: 'var(--danger)' }}>{error}</p>}
    </div>
  )
)
Input.displayName = 'Input'

interface SelectInputProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
}

export function SelectInput({ label, error, className = '', children, ...rest }: SelectInputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label className="text-sm font-medium" style={{ color: 'var(--text)' }}>
          {label}
        </label>
      )}
      <select
        className={`w-full px-3.5 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316] transition ${className}`}
        style={{
          background: 'var(--surface2)',
          border: `1px solid ${error ? 'var(--danger)' : 'var(--border)'}`,
          color: 'var(--text)',
        }}
        {...rest}
      >
        {children}
      </select>
      {error && <p className="text-xs" style={{ color: 'var(--danger)' }}>{error}</p>}
    </div>
  )
}
