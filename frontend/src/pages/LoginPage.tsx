import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuthStore } from '../store/auth'

function CompLogo() {
  return (
    <svg viewBox="0 0 220 56" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ height: '40px', width: 'auto' }}>
      <path
        d="M28 6C15.85 6 6 15.85 6 28C6 40.15 15.85 50 28 50C34.6 50 40.54 47.22 44.8 42.8"
        stroke="white" strokeWidth="6.5" strokeLinecap="round" fill="none"
      />
      <polygon points="36,19 36,37 52,28" fill="#F97316" />
      <text x="60" y="38" fontFamily="Inter,system-ui,sans-serif" fontWeight="700" fontSize="30" fill="white" letterSpacing="-0.5">omplio</text>
    </svg>
  )
}

export function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [form, setForm] = useState({ betriebsnummer: '', username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(form)
      setAuth({ ...data, token: data.access_token })
      if (data.role === 'admin' || data.role === 'superadmin') {
        navigate('/admin')
      } else {
        navigate('/dashboard')
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Login fehlgeschlagen.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center px-4 relative overflow-hidden"
      style={{ background: '#05050a' }}
    >
      {/* Radial accent glow */}
      <div
        className="absolute pointer-events-none"
        style={{
          top: '50%', left: '50%',
          transform: 'translate(-50%, -60%)',
          width: '900px', height: '600px',
          background: 'radial-gradient(ellipse at center, rgba(249,115,22,0.07) 0%, transparent 65%)',
        }}
      />
      {/* Subtle grid */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
          maskImage: 'radial-gradient(ellipse 70% 60% at 50% 40%, black 0%, transparent 100%)',
        }}
      />

      <div className="relative w-full" style={{ maxWidth: '400px' }}>
        {/* Logo */}
        <div className="flex justify-center mb-10">
          <CompLogo />
        </div>

        {/* Card */}
        <div
          className="rounded-2xl"
          style={{
            background: 'rgba(14,14,20,0.9)',
            border: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '0 0 0 1px rgba(255,255,255,0.02), 0 24px 48px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(16px)',
            padding: '36px 32px',
          }}
        >
          <div className="mb-7">
            <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#ededf0', marginBottom: '4px' }}>
              Anmelden
            </h1>
            <p style={{ fontSize: '13px', color: '#6c6c80' }}>
              Gib deine Betriebsdaten ein um fortzufahren
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <LoginField
              label="Betriebsnummer"
              placeholder="z. B. 1001"
              value={form.betriebsnummer}
              onChange={(v) => setForm({ ...form, betriebsnummer: v })}
              autoFocus
            />
            <LoginField
              label="Benutzername"
              placeholder="username"
              value={form.username}
              onChange={(v) => setForm({ ...form, username: v })}
            />
            <LoginField
              label="Passwort"
              type="password"
              placeholder="••••••••"
              value={form.password}
              onChange={(v) => setForm({ ...form, password: v })}
            />

            {error && (
              <div
                style={{
                  background: 'rgba(248,113,113,0.08)',
                  border: '1px solid rgba(248,113,113,0.2)',
                  borderRadius: '8px',
                  padding: '10px 14px',
                  fontSize: '13px',
                  color: '#f87171',
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                marginTop: '4px',
                width: '100%',
                padding: '11px',
                borderRadius: '9px',
                border: 'none',
                background: loading ? '#7c3a0a' : '#F97316',
                color: '#fff',
                fontSize: '14px',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
                transition: 'background 0.15s, opacity 0.15s',
                opacity: loading ? 0.7 : 1,
                letterSpacing: '0.01em',
              }}
            >
              {loading ? 'Wird angemeldet…' : 'Anmelden'}
            </button>
          </form>
        </div>

        {/* Footer */}
        <p
          className="text-center mt-6"
          style={{ fontSize: '12px', color: '#3d3d52' }}
        >
          © 2026 Complio · HR-Software für Gastronomie
        </p>
      </div>
    </div>
  )
}

function LoginField({
  label, type = 'text', placeholder, value, onChange, autoFocus,
}: {
  label: string; type?: string; placeholder?: string;
  value: string; onChange: (v: string) => void; autoFocus?: boolean
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <label style={{ fontSize: '11px', fontWeight: 600, color: '#6c6c80', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
        {label}
      </label>
      <input
        type={type}
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus={autoFocus}
        required
        style={{
          background: '#0e0e16',
          border: '1px solid #1f1f2e',
          borderRadius: '8px',
          padding: '10px 14px',
          fontSize: '14px',
          color: '#ededf0',
          outline: 'none',
          transition: 'border-color 0.15s',
          width: '100%',
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = '#F97316' }}
        onBlur={(e) => { e.currentTarget.style.borderColor = '#1f1f2e' }}
      />
    </div>
  )
}
