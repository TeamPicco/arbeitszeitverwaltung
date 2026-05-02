import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { kioskStatus, kioskAction } from '../api/stempel'
import { useAuthStore } from '../store/auth'
import { Button } from '../components/Button'
import { Input } from '../components/Input'
import { Clock, LogIn, LogOut, Coffee, Ban, Fingerprint } from 'lucide-react'

type Tab = 'stempeluhr' | 'login'

export function LoginPage() {
  const [tab, setTab] = useState<Tab>('stempeluhr')

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{ background: 'var(--bg)' }}>
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <img src="/complio-logo.png" alt="Complio" style={{ height: '56px', width: 'auto', objectFit: 'contain' }} />
        </div>

        {/* Tab switcher */}
        <div
          className="flex gap-1 p-1 rounded-xl mb-5"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          {([['stempeluhr', 'Stempeluhr'], ['login', 'Admin Login']] as [Tab, string][]).map(([t, label]) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className="flex-1 py-2 rounded-lg text-sm font-medium transition-all cursor-pointer flex items-center justify-center gap-2"
              style={
                tab === t
                  ? { background: 'var(--accent)', color: '#fff' }
                  : { color: 'var(--text-muted)' }
              }
            >
              {t === 'stempeluhr' ? <Clock size={14} /> : <LogIn size={14} />}
              {label}
            </button>
          ))}
        </div>

        {tab === 'stempeluhr' ? <KioskTab /> : <LoginTab />}
      </div>
    </div>
  )
}

function LoginTab() {
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
    <form
      onSubmit={handleSubmit}
      className="rounded-2xl p-8 flex flex-col gap-4"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <h1 className="text-lg font-semibold mb-2">Anmelden</h1>
      <Input
        label="Betriebsnummer"
        placeholder="z.B. 1001"
        value={form.betriebsnummer}
        onChange={(e) => setForm({ ...form, betriebsnummer: e.target.value })}
        required
        autoFocus
      />
      <Input
        label="Benutzername"
        placeholder="username"
        value={form.username}
        onChange={(e) => setForm({ ...form, username: e.target.value })}
        required
      />
      <Input
        label="Passwort"
        type="password"
        placeholder="••••••••"
        value={form.password}
        onChange={(e) => setForm({ ...form, password: e.target.value })}
        required
      />
      {error && (
        <p className="text-sm text-red-400 bg-red-900/10 rounded-lg px-3 py-2 border border-red-900/30">
          {error}
        </p>
      )}
      <Button type="submit" loading={loading} className="w-full mt-2">
        Anmelden
      </Button>
    </form>
  )
}

type KioskMa = { id: number; vorname: string; nachname: string }
type KioskStatusData = { eingestempelt: boolean; pause_aktiv: boolean }

function KioskTab() {
  const [betriebsnummer, setBetriebsnummer] = useState('')
  const [pin, setPin] = useState('')
  const [mitarbeiter, setMitarbeiter] = useState<KioskMa | null>(null)
  const [stempelStatus, setStempelStatus] = useState<KioskStatusData | null>(null)
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
    setStempelStatus(null)
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
      setStempelStatus(res.status)
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
      setStempelStatus(res.status)
      const labels: Record<string, string> = {
        clock_in: 'Eingestempelt!',
        clock_out: 'Ausgestempelt!',
        break_start: 'Pause gestartet',
        break_end: 'Pause beendet',
      }
      setMessage({ text: labels[action] ?? 'Gebucht', ok: true })
      scheduleReset(4000)
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Fehler beim Stempeln.'
      setMessage({ text: detail, ok: false })
      scheduleReset(4000)
    } finally {
      setLoading(false)
    }
  }

  const timeStr = time.toLocaleTimeString('de', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  return (
    <div
      className="rounded-2xl p-6 flex flex-col items-center gap-5"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      {/* Clock */}
      <div className="text-center">
        <p className="text-4xl font-bold font-mono tracking-tight" style={{ color: 'var(--accent)' }}>
          {timeStr}
        </p>
        <p className="text-xs mt-1 capitalize" style={{ color: 'var(--text-muted)' }}>
          {time.toLocaleDateString('de', { weekday: 'long', day: 'numeric', month: 'long' })}
        </p>
      </div>

      {/* PIN form */}
      {!mitarbeiter && (
        <form onSubmit={handlePinSubmit} className="w-full flex flex-col gap-3">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Betriebsnummer</label>
            <input
              type="text"
              placeholder="z.B. 1001"
              value={betriebsnummer}
              onChange={(e) => setBetriebsnummer(e.target.value)}
              className="w-full px-3.5 py-2.5 rounded-xl text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium flex items-center gap-2">
              <Fingerprint size={14} style={{ color: 'var(--text-muted)' }} /> PIN eingeben
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
              className="w-full text-center text-2xl font-mono px-3.5 py-3 rounded-xl tracking-widest outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            />
          </div>
          {message && (
            <p
              className="text-sm text-center px-3 py-2 rounded-lg"
              style={{
                background: message.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                color: message.ok ? '#22c55e' : '#f87171',
                border: `1px solid ${message.ok ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
              }}
            >
              {message.text}
            </p>
          )}
          <button
            type="submit"
            disabled={loading || !betriebsnummer || pin.length < 4}
            className="w-full py-3 rounded-xl font-semibold text-white disabled:opacity-40 cursor-pointer transition-opacity"
            style={{ background: 'var(--accent)' }}
          >
            {loading ? '…' : 'Stempeln'}
          </button>
        </form>
      )}

      {/* Identified employee */}
      {mitarbeiter && stempelStatus && (
        <div className="w-full flex flex-col items-center gap-4">
          <div className="text-center">
            <p className="text-xl font-bold">{mitarbeiter.vorname} {mitarbeiter.nachname}</p>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              {stempelStatus.eingestempelt
                ? stempelStatus.pause_aktiv ? 'Pause aktiv' : 'Eingestempelt'
                : 'Ausgestempelt'}
            </p>
          </div>

          {message && (
            <p
              className="text-sm text-center w-full px-3 py-2 rounded-lg"
              style={{
                background: message.ok ? 'rgba(34,197,94,0.1)' : 'rgba(239,68,68,0.1)',
                color: message.ok ? '#22c55e' : '#f87171',
                border: `1px solid ${message.ok ? 'rgba(34,197,94,0.3)' : 'rgba(239,68,68,0.3)'}`,
              }}
            >
              {message.text}
            </p>
          )}

          <div className="flex gap-2 flex-wrap justify-center w-full">
            {!stempelStatus.eingestempelt && (
              <KioskBtn icon={<LogIn size={18} />} label="KOMMEN" color="#22c55e" onClick={() => doAction('clock_in')} disabled={loading} />
            )}
            {stempelStatus.eingestempelt && !stempelStatus.pause_aktiv && (
              <>
                <KioskBtn icon={<Coffee size={18} />} label="PAUSE START" color="#F97316" onClick={() => doAction('break_start')} disabled={loading} />
                <KioskBtn icon={<LogOut size={18} />} label="GEHEN" color="#ef4444" onClick={() => doAction('clock_out')} disabled={loading} />
              </>
            )}
            {stempelStatus.eingestempelt && stempelStatus.pause_aktiv && (
              <KioskBtn icon={<Ban size={18} />} label="PAUSE ENDE" color="#F97316" onClick={() => doAction('break_end')} disabled={loading} />
            )}
          </div>

          <button
            onClick={resetKiosk}
            className="text-xs cursor-pointer"
            style={{ color: 'var(--text-muted)' }}
          >
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
      className="flex flex-col items-center gap-1.5 px-5 py-3 rounded-xl font-bold text-white text-xs transition-opacity disabled:opacity-40 cursor-pointer hover:opacity-90"
      style={{ background: color, minWidth: 100 }}
    >
      {icon}
      {label}
    </button>
  )
}
