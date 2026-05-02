import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import { login } from '../api/auth'
import { kioskStatus, kioskAction } from '../api/stempel'
import { Fingerprint } from 'lucide-react'

// ── Kiosk Tab ──────────────────────────────────────────────────────────────
function KioskForm() {
  const [betrieb, setBetrieb] = useState('')
  const [pin, setPin] = useState('')
  const [stempelData, setStempelData] = useState<null | {
    mitarbeiter: { id: number; vorname: string; nachname: string }
    status: { eingestempelt: boolean; pause_aktiv: boolean }
  }>(null)
  const [loading, setLoading] = useState(false)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState('')
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
    setStempelData(null)
    setMessage(null)
    setError('')
    pinRef.current?.focus()
  }

  const scheduleReset = (ms = 5000) => {
    if (resetTimer.current) clearTimeout(resetTimer.current)
    resetTimer.current = setTimeout(resetKiosk, ms)
  }

  const handleIdentify = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const res = await kioskStatus(betrieb, pin)
      setStempelData(res)
      scheduleReset(30_000)
    } catch {
      setError('PIN oder Betriebsnummer ungültig.')
      setPin('')
      scheduleReset(3000)
    } finally {
      setLoading(false)
    }
  }

  const handleAction = async (action: string) => {
    if (!stempelData) return
    setActionLoading(true)
    try {
      const res = await kioskAction(betrieb, pin, action)
      setStempelData((prev) => prev ? { ...prev, status: res.status } : null)
      const labels: Record<string, string> = {
        clock_in: 'Eingestempelt!', clock_out: 'Ausgestempelt!',
        break_start: 'Pause gestartet', break_end: 'Pause beendet',
      }
      setMessage({ text: labels[action] ?? 'Gebucht', ok: true })
      scheduleReset(4000)
    } catch {
      setMessage({ text: 'Fehler beim Stempeln.', ok: false })
      scheduleReset(4000)
    } finally {
      setActionLoading(false)
    }
  }

  const timeStr = time.toLocaleTimeString('de', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
      {/* Clock */}
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: 36, fontWeight: 700, fontFamily: 'monospace', color: '#FF6B00', letterSpacing: '-0.02em' }}>
          {timeStr}
        </p>
        <p style={{ fontSize: 12, color: '#9A9A9A', marginTop: 4, textTransform: 'capitalize' }}>
          {time.toLocaleDateString('de', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </div>

      {!stempelData ? (
        <form onSubmit={handleIdentify} style={{ width: '100%', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={labelStyle}>Betriebsnummer</label>
            <input
              value={betrieb}
              onChange={(e) => setBetrieb(e.target.value)}
              placeholder="z. B. 1001"
              required
              style={inputStyle()}
              onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00' }}
              onBlur={(e) => { e.currentTarget.style.borderColor = '#E5E5E5' }}
            />
          </div>
          <div>
            <label style={{ ...labelStyle, display: 'flex', alignItems: 'center', gap: 6 }}>
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
              style={{ ...inputStyle(), fontSize: 22, fontFamily: 'monospace', letterSpacing: '0.2em', textAlign: 'center' }}
              onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00' }}
              onBlur={(e) => { e.currentTarget.style.borderColor = '#E5E5E5' }}
            />
          </div>
          {error && (
            <p style={{ color: '#DC2626', fontSize: 13, padding: '10px 14px', background: 'rgba(220,38,38,0.08)', borderRadius: 8 }}>
              {error}
            </p>
          )}
          <button
            type="submit"
            disabled={loading || !betrieb || pin.length < 4}
            style={{ ...btnStyle('#FF6B00'), opacity: (loading || !betrieb || pin.length < 4) ? 0.4 : 1 }}
          >
            {loading ? '…' : 'Identifizieren'}
          </button>
        </form>
      ) : (
        <div style={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{
              width: 64, height: 64, borderRadius: '50%',
              background: 'rgba(255,107,0,0.1)', border: '2px solid rgba(255,107,0,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px', fontSize: 24, fontWeight: 700, color: '#FF6B00',
            }}>
              {stempelData.mitarbeiter.vorname[0]}
            </div>
            <p style={{ fontSize: 20, fontWeight: 700, color: '#2D2D2D' }}>
              {stempelData.mitarbeiter.vorname} {stempelData.mitarbeiter.nachname}
            </p>
            <p style={{
              fontSize: 13, marginTop: 4,
              color: stempelData.status.eingestempelt
                ? stempelData.status.pause_aktiv ? '#D97706' : '#16A34A'
                : '#5A5A5A',
              fontWeight: 600,
            }}>
              {stempelData.status.eingestempelt
                ? stempelData.status.pause_aktiv ? 'Pause aktiv' : 'Eingestempelt'
                : 'Ausgestempelt'}
            </p>
          </div>

          {message && (
            <div style={{
              background: message.ok ? 'rgba(22,163,74,0.08)' : 'rgba(220,38,38,0.08)',
              border: `1px solid ${message.ok ? 'rgba(22,163,74,0.2)' : 'rgba(220,38,38,0.2)'}`,
              borderRadius: 8, padding: '10px 14px', fontSize: 13,
              color: message.ok ? '#16A34A' : '#DC2626', textAlign: 'center', width: '100%',
            }}>
              {message.text}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center', width: '100%' }}>
            {!stempelData.status.eingestempelt && (
              <button onClick={() => handleAction('clock_in')} disabled={actionLoading} style={btnStyle('#16A34A')}>
                {actionLoading ? '...' : '✓ KOMMEN'}
              </button>
            )}
            {stempelData.status.eingestempelt && !stempelData.status.pause_aktiv && (
              <>
                <button onClick={() => handleAction('break_start')} disabled={actionLoading} style={btnStyle('#D97706')}>
                  {actionLoading ? '...' : '⏸ PAUSE'}
                </button>
                <button onClick={() => handleAction('clock_out')} disabled={actionLoading} style={btnStyle('#DC2626')}>
                  {actionLoading ? '...' : '✕ GEHEN'}
                </button>
              </>
            )}
            {stempelData.status.eingestempelt && stempelData.status.pause_aktiv && (
              <button onClick={() => handleAction('break_end')} disabled={actionLoading} style={btnStyle('#FF6B00')}>
                {actionLoading ? '...' : '▶ WEITER'}
              </button>
            )}
          </div>

          <button onClick={resetKiosk} style={{ fontSize: 12, color: '#9A9A9A', background: 'none', border: 'none', cursor: 'pointer', marginTop: 4 }}>
            Abbrechen
          </button>
        </div>
      )}
    </div>
  )
}

// ── Login Tab ──────────────────────────────────────────────────────────────
function LoginForm() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)
  const [form, setForm] = useState({ betriebsnummer: '', username: '', password: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
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
        'Ungültige Anmeldedaten. Bitte prüfe Betriebsnummer, Benutzername und Passwort.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div>
        <label style={labelStyle}>Betriebsnummer</label>
        <input
          value={form.betriebsnummer}
          onChange={(e) => setForm({ ...form, betriebsnummer: e.target.value })}
          placeholder="z. B. B-12345"
          required
          style={inputStyle()}
          onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00' }}
          onBlur={(e) => { e.currentTarget.style.borderColor = '#E5E5E5' }}
        />
      </div>
      <div>
        <label style={labelStyle}>Benutzername</label>
        <input
          value={form.username}
          onChange={(e) => setForm({ ...form, username: e.target.value })}
          placeholder="Benutzername"
          required
          style={inputStyle()}
          onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00' }}
          onBlur={(e) => { e.currentTarget.style.borderColor = '#E5E5E5' }}
        />
      </div>
      <div>
        <label style={labelStyle}>Passwort</label>
        <input
          type="password"
          value={form.password}
          onChange={(e) => setForm({ ...form, password: e.target.value })}
          placeholder="••••••••"
          required
          style={inputStyle()}
          onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00' }}
          onBlur={(e) => { e.currentTarget.style.borderColor = '#E5E5E5' }}
        />
      </div>
      {error && (
        <p style={{ color: '#DC2626', fontSize: 13, padding: '10px 14px', background: 'rgba(220,38,38,0.08)', borderRadius: 8, borderLeft: '3px solid #DC2626' }}>
          {error}
        </p>
      )}
      <button type="submit" disabled={loading} style={{ ...btnStyle('#FF6B00'), marginTop: 4 }}>
        {loading ? 'Anmelden...' : 'Anmelden'}
      </button>
    </form>
  )
}

// ── Shared styles ──────────────────────────────────────────────────────────
const labelStyle: React.CSSProperties = {
  display: 'block', fontSize: 13, fontWeight: 500, color: '#5A5A5A', marginBottom: 6,
}
const inputStyle = (): React.CSSProperties => ({
  width: '100%', padding: '11px 14px', borderRadius: 8, fontSize: 14,
  fontFamily: 'inherit', outline: 'none',
  border: '1.5px solid #E5E5E5', background: '#FFFFFF', color: '#2D2D2D',
  transition: 'border-color 0.15s ease, box-shadow 0.15s ease',
})
const btnStyle = (bg: string): React.CSSProperties => ({
  width: '100%', padding: '12px', borderRadius: 8, fontSize: 15,
  fontWeight: 600, fontFamily: 'inherit', cursor: 'pointer',
  background: bg, color: '#FFFFFF',
  border: 'none', transition: 'all 0.15s ease',
})

// ── Main LoginPage ──────────────────────────────────────────────────────────
export function LoginPage() {
  const [tab, setTab] = useState<'login' | 'kiosk'>('login')

  return (
    <div style={{
      minHeight: '100svh',
      background: '#F8F8F8',
      backgroundImage: 'radial-gradient(#E0E0E0 1px, transparent 1px)',
      backgroundSize: '24px 24px',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      padding: '24px',
    }}>
      <div style={{
        width: '100%', maxWidth: 400,
        background: '#FFFFFF',
        borderRadius: 16,
        boxShadow: '0 4px 40px rgba(0,0,0,0.10)',
        overflow: 'hidden',
      }}>
        {/* Logo header */}
        <div style={{ padding: '32px 36px 24px', textAlign: 'center', borderBottom: '1px solid #F0F0F0' }}>
          <img src="/complio-logo.png" alt="Complio" style={{ height: 44, width: 'auto', objectFit: 'contain' }} />
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', borderBottom: '1px solid #F0F0F0' }}>
          {(['login', 'kiosk'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                flex: 1, padding: '14px', fontSize: 14, fontWeight: 600,
                fontFamily: 'inherit', cursor: 'pointer', border: 'none',
                background: 'transparent',
                color: tab === t ? '#FF6B00' : '#9A9A9A',
                borderBottom: tab === t ? '2px solid #FF6B00' : '2px solid transparent',
                transition: 'all 0.15s ease',
              }}
            >
              {t === 'login' ? 'Anmelden' : '⏱ Stempeluhr'}
            </button>
          ))}
        </div>

        {/* Content */}
        <div style={{ padding: '28px 36px 32px' }}>
          {tab === 'login' ? <LoginForm /> : <KioskForm />}
        </div>
      </div>
    </div>
  )
}
