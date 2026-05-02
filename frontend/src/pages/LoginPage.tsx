import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { kioskStatus, kioskAction } from '../api/stempel'
import { useAuthStore } from '../store/auth'
import { Clock, LogIn, LogOut, Coffee, Ban, Fingerprint } from 'lucide-react'

type Tab = 'stempeluhr' | 'login'

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
  const [tab, setTab] = useState<Tab>('stempeluhr')

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

        {/* Tab switcher */}
        <div
          style={{
            display: 'flex',
            gap: '4px',
            padding: '4px',
            borderRadius: '12px',
            background: 'rgba(14,14,20,0.9)',
            border: '1px solid rgba(255,255,255,0.07)',
            marginBottom: '8px',
          }}
        >
          {([['stempeluhr', 'Stempeluhr'], ['login', 'Admin Login']] as [Tab, string][]).map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                flex: 1,
                padding: '8px 12px',
                borderRadius: '8px',
                fontSize: '13px',
                fontWeight: 500,
                cursor: 'pointer',
                border: 'none',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '6px',
                transition: 'background 0.15s, color 0.15s',
                background: tab === t ? '#F97316' : 'transparent',
                color: tab === t ? '#fff' : '#6c6c80',
              }}
            >
              {t === 'stempeluhr' ? <Clock size={13} /> : <LogIn size={13} />}
              {label}
            </button>
          ))}
        </div>

        {/* Card */}
        <div
          className="rounded-2xl"
          style={{
            background: 'rgba(14,14,20,0.9)',
            border: '1px solid rgba(255,255,255,0.07)',
            boxShadow: '0 0 0 1px rgba(255,255,255,0.02), 0 24px 48px rgba(0,0,0,0.5)',
            backdropFilter: 'blur(16px)',
            padding: '32px',
          }}
        >
          {tab === 'login' ? <LoginForm /> : <KioskForm />}
        </div>

        {/* Footer */}
        <p className="text-center mt-6" style={{ fontSize: '12px', color: '#3d3d52' }}>
          © 2026 Complio · HR-Software für Gastronomie
        </p>
      </div>
    </div>
  )
}

function LoginForm() {
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
    <>
      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '18px', fontWeight: 600, color: '#ededf0', marginBottom: '4px' }}>Anmelden</h1>
        <p style={{ fontSize: '13px', color: '#6c6c80' }}>Gib deine Betriebsdaten ein um fortzufahren</p>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <LoginField label="Betriebsnummer" placeholder="z. B. 1001" value={form.betriebsnummer}
          onChange={(v) => setForm({ ...form, betriebsnummer: v })} autoFocus />
        <LoginField label="Benutzername" placeholder="username" value={form.username}
          onChange={(v) => setForm({ ...form, username: v })} />
        <LoginField label="Passwort" type="password" placeholder="••••••••" value={form.password}
          onChange={(v) => setForm({ ...form, password: v })} />

        {error && (
          <div style={{
            background: 'rgba(248,113,113,0.08)', border: '1px solid rgba(248,113,113,0.2)',
            borderRadius: '8px', padding: '10px 14px', fontSize: '13px', color: '#f87171',
          }}>
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={loading}
          style={{
            marginTop: '4px', width: '100%', padding: '11px', borderRadius: '9px', border: 'none',
            background: loading ? '#7c3a0a' : '#F97316', color: '#fff', fontSize: '14px', fontWeight: 600,
            cursor: loading ? 'not-allowed' : 'pointer', transition: 'background 0.15s, opacity 0.15s',
            opacity: loading ? 0.7 : 1, letterSpacing: '0.01em',
          }}
        >
          {loading ? 'Wird angemeldet…' : 'Anmelden'}
        </button>
      </form>
    </>
  )
}

type KioskMa = { id: number; vorname: string; nachname: string }
type KioskStatusData = { eingestempelt: boolean; pause_aktiv: boolean }

function KioskForm() {
  const [betriebsnummer, setBetriebsnummer] = useState('')
  const [pin, setPin] = useState('')
  const [mitarbeiter, setMitarbeiter] = useState<KioskMa | null>(null)
  const [stempelSt, setStempelSt] = useState<KioskStatusData | null>(null)
  const [loading, setLoading] = useState(false)
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null)
  const [time, setTime] = useState(new Date())
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pinRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const resetKiosk = () => {
    setPin('')
    setMitarbeiter(null)
    setStempelSt(null)
    setMessage(null)
    pinRef.current?.focus()
  }

  const scheduleReset = (ms = 5000) => {
    if (resetTimer.current) clearTimeout(resetTimer.current)
    resetTimer.current = setTimeout(resetKiosk, ms)
  }

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!betriebsnummer || !pin) return
    setLoading(true)
    setMessage(null)
    try {
      const res = await kioskStatus(betriebsnummer, pin)
      setMitarbeiter(res.mitarbeiter)
      setStempelSt(res.status)
      scheduleReset(30_000)
    } catch {
      setMessage({ text: 'PIN nicht gefunden.', ok: false })
      setPin('')
      scheduleReset(3000)
    } finally {
      setLoading(false)
    }
  }

  const doAction = async (action: string) => {
    if (!mitarbeiter) return
    setLoading(true)
    try {
      const res = await kioskAction(betriebsnummer, pin, action)
      setStempelSt(res.status)
      const labels: Record<string, string> = {
        clock_in: 'Eingestempelt!', clock_out: 'Ausgestempelt!',
        break_start: 'Pause gestartet', break_end: 'Pause beendet',
      }
      setMessage({ text: labels[action] ?? 'Gebucht', ok: true })
      scheduleReset(4000)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? 'Fehler beim Stempeln.'
      setMessage({ text: detail, ok: false })
      scheduleReset(4000)
    } finally {
      setLoading(false)
    }
  }

  const timeStr = time.toLocaleTimeString('de', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '20px' }}>
      {/* Clock */}
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: '36px', fontWeight: 700, fontFamily: 'monospace', color: '#F97316', letterSpacing: '-0.02em' }}>
          {timeStr}
        </p>
        <p style={{ fontSize: '12px', color: '#6c6c80', marginTop: '4px', textTransform: 'capitalize' }}>
          {time.toLocaleDateString('de', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </div>

      {!mitarbeiter ? (
        <form onSubmit={handlePinSubmit} style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <LoginField label="Betriebsnummer" placeholder="z. B. 1001" value={betriebsnummer}
            onChange={setBetriebsnummer} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <label style={{ fontSize: '11px', fontWeight: 600, color: '#6c6c80', letterSpacing: '0.06em', textTransform: 'uppercase', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Fingerprint size={13} /> PIN
            </label>
            <input
              ref={pinRef}
              type="password"
              inputMode="numeric"
              maxLength={8}
              placeholder="••••"
              value={pin}
              autoComplete="off"
              onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
              style={{
                background: '#0e0e16', border: '1px solid #1f1f2e', borderRadius: '8px',
                padding: '10px 14px', fontSize: '22px', fontFamily: 'monospace', letterSpacing: '0.2em',
                color: '#ededf0', outline: 'none', textAlign: 'center', width: '100%',
              }}
              onFocus={(e) => { e.currentTarget.style.borderColor = '#F97316' }}
              onBlur={(e) => { e.currentTarget.style.borderColor = '#1f1f2e' }}
            />
          </div>

          {message && (
            <div style={{
              background: message.ok ? 'rgba(34,197,94,0.08)' : 'rgba(248,113,113,0.08)',
              border: `1px solid ${message.ok ? 'rgba(34,197,94,0.2)' : 'rgba(248,113,113,0.2)'}`,
              borderRadius: '8px', padding: '10px 14px', fontSize: '13px',
              color: message.ok ? '#22c55e' : '#f87171', textAlign: 'center',
            }}>
              {message.text}
            </div>
          )}

          <button
            type="submit"
            disabled={loading || !betriebsnummer || pin.length < 4}
            style={{
              width: '100%', padding: '11px', borderRadius: '9px', border: 'none',
              background: '#F97316', color: '#fff', fontSize: '14px', fontWeight: 600,
              cursor: 'pointer', opacity: (loading || !betriebsnummer || pin.length < 4) ? 0.4 : 1,
              transition: 'opacity 0.15s',
            }}
          >
            {loading ? '…' : 'Stempeln'}
          </button>
        </form>
      ) : (
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '16px' }}>
          <div style={{ textAlign: 'center' }}>
            <p style={{ fontSize: '20px', fontWeight: 700, color: '#ededf0' }}>
              {mitarbeiter.vorname} {mitarbeiter.nachname}
            </p>
            <p style={{ fontSize: '13px', color: '#6c6c80', marginTop: '4px' }}>
              {stempelSt?.eingestempelt
                ? stempelSt.pause_aktiv ? 'Pause aktiv' : 'Eingestempelt'
                : 'Ausgestempelt'}
            </p>
          </div>

          {message && (
            <div style={{
              background: message.ok ? 'rgba(34,197,94,0.08)' : 'rgba(248,113,113,0.08)',
              border: `1px solid ${message.ok ? 'rgba(34,197,94,0.2)' : 'rgba(248,113,113,0.2)'}`,
              borderRadius: '8px', padding: '10px 14px', fontSize: '13px',
              color: message.ok ? '#22c55e' : '#f87171', textAlign: 'center', width: '100%',
            }}>
              {message.text}
            </div>
          )}

          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: 'center', width: '100%' }}>
            {!stempelSt?.eingestempelt && (
              <KioskBtn icon={<LogIn size={16} />} label="KOMMEN" color="#22c55e" onClick={() => doAction('clock_in')} disabled={loading} />
            )}
            {stempelSt?.eingestempelt && !stempelSt.pause_aktiv && (
              <>
                <KioskBtn icon={<Coffee size={16} />} label="PAUSE" color="#F97316" onClick={() => doAction('break_start')} disabled={loading} />
                <KioskBtn icon={<LogOut size={16} />} label="GEHEN" color="#ef4444" onClick={() => doAction('clock_out')} disabled={loading} />
              </>
            )}
            {stempelSt?.eingestempelt && stempelSt.pause_aktiv && (
              <KioskBtn icon={<Ban size={16} />} label="PAUSE ENDE" color="#F97316" onClick={() => doAction('break_end')} disabled={loading} />
            )}
          </div>

          <button onClick={resetKiosk} style={{ fontSize: '12px', color: '#6c6c80', background: 'none', border: 'none', cursor: 'pointer' }}>
            Abbrechen
          </button>
        </div>
      )}
    </div>
  )
}

function KioskBtn({ icon, label, color, onClick, disabled }: {
  icon: React.ReactNode; label: string; color: string; onClick: () => void; disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px',
        padding: '12px 20px', borderRadius: '10px', border: 'none',
        background: color, color: '#fff', fontSize: '11px', fontWeight: 700,
        cursor: 'pointer', opacity: disabled ? 0.4 : 1, minWidth: '90px',
        transition: 'opacity 0.15s',
      }}
    >
      {icon}
      {label}
    </button>
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
          background: '#0e0e16', border: '1px solid #1f1f2e', borderRadius: '8px',
          padding: '10px 14px', fontSize: '14px', color: '#ededf0', outline: 'none',
          transition: 'border-color 0.15s', width: '100%',
        }}
        onFocus={(e) => { e.currentTarget.style.borderColor = '#F97316' }}
        onBlur={(e) => { e.currentTarget.style.borderColor = '#1f1f2e' }}
      />
    </div>
  )
}
