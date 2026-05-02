import { type InputHTMLAttributes, type SelectHTMLAttributes, forwardRef } from 'react'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, error, className = '', style, ...rest }, ref) => (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
          {label}
        </label>
      )}
      <input
        ref={ref}
        {...rest}
        style={{
          width: '100%',
          padding: '10px 14px',
          borderRadius: 8,
          fontSize: 14,
          fontFamily: 'inherit',
          outline: 'none',
          background: 'var(--surface)',
          border: `1.5px solid ${error ? 'var(--danger)' : 'var(--border)'}`,
          color: 'var(--text)',
          transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
          ...style,
        }}
        onFocus={(e) => {
          e.currentTarget.style.borderColor = '#FF6B00'
          e.currentTarget.style.boxShadow = '0 0 0 3px rgba(255,107,0,0.12)'
          rest.onFocus?.(e)
        }}
        onBlur={(e) => {
          e.currentTarget.style.borderColor = error ? 'var(--danger)' : 'var(--border)'
          e.currentTarget.style.boxShadow = 'none'
          rest.onBlur?.(e)
        }}
      />
      {error && <p style={{ fontSize: 12, color: 'var(--danger)' }}>{error}</p>}
    </div>
  )
)
Input.displayName = 'Input'

interface SelectInputProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
}

export function SelectInput({ label, error, className = '', children, style, ...rest }: SelectInputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
          {label}
        </label>
      )}
      <select
        style={{
          width: '100%',
          padding: '10px 14px',
          borderRadius: 8,
          fontSize: 14,
          fontFamily: 'inherit',
          outline: 'none',
          background: 'var(--surface)',
          border: `1.5px solid ${error ? 'var(--danger)' : 'var(--border)'}`,
          color: 'var(--text)',
          ...style,
        }}
        {...rest}
      >
        {children}
      </select>
      {error && <p style={{ fontSize: 12, color: 'var(--danger)' }}>{error}</p>}
    </div>
  )
}
