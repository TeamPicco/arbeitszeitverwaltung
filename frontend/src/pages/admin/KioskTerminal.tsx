import { useState, useEffect, useRef } from 'react'
import { useAuthStore } from '../../store/auth'
import { pinLookup, stempelEvent, stempelStatus } from '../../api/stempel'
import { Fingerprint, LogIn, LogOut, Coffee, Ban } from 'lucide-react'

type MitarbeiterInfo = { id: number; vorname: string; nachname: string }
type Status = { eingestempelt: boolean; pause_aktiv: boolean }

export function KioskTerminal() {
  const betriebId = useAuthStore((s) => s.betriebId)!
  const [pin, setPin] = useState('')
  const [mitarbeiter, setMitarbeiter] = useState<MitarbeiterInfo | null>(null)
  const [status, setStatus] = useState<Status | null>(null)
  const [message, setMessage] = useState<{ text: string; ok: boolean } | null>(null)
  const [loading, setLoading] = useState(false)
  const resetTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Time display
  const [time, setTime] = useState(new Date())
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(id)
  }, [])

  const resetKiosk = () => {
    setPin('')
    setMitarbeiter(null)
    setStatus(null)
    setMessage(null)
    inputRef.current?.focus()
  }

  const scheduleReset = (ms = 5000) => {
    if (resetTimer.current) clearTimeout(resetTimer.current)
    resetTimer.current = setTimeout(resetKiosk, ms)
  }

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!pin.trim()) return
    setLoading(true)
    try {
      const ma = await pinLookup(betriebId, pin.trim())
      const st = await stempelStatus(ma.id)
      setMitarbeiter(ma)
      setStatus(st)
      scheduleReset(30_000)
    } catch {
      setMessage({ text: 'PIN nicht gefunden.', ok: false })
      scheduleReset(3000)
    } finally {
      setLoading(false)
    }
  }

  const doAction = async (action: string) => {
    if (!mitarbeiter) return
    setLoading(true)
    try {
      await stempelEvent({ mitarbeiter_id: mitarbeiter.id, action })
      const newStatus = await stempelStatus(mitarbeiter.id)
      setStatus(newStatus)
      const labels: Record<string, string> = {
        clock_in: 'Eingestempelt',
        clock_out: 'Ausgestempelt',
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

  const timeStr = time.toLocaleTimeString('de', { hour: '2-digit', minute: '2-digit' })
  const dateStr = time.toLocaleDateString('de', { weekday: 'long', day: 'numeric', month: 'long' })

  return (
    <div
      className="min-h-screen flex flex-col items-center justify-center p-8"
      style={{ background: '#080808' }}
      onClick={() => inputRef.current?.focus()}
    >
      {/* Clock */}
      <div className="text-center mb-12">
        <p className="text-7xl font-bold font-mono tracking-tight" style={{ color: '#F97316' }}>
          {timeStr}
        </p>
        <p className="text-lg mt-2 capitalize" style={{ color: 'var(--text-muted)' }}>
          {dateStr}
        </p>
      </div>

      {/* Idle — PIN entry */}
      {!mitarbeiter && !message && (
        <form onSubmit={handlePinSubmit} className="flex flex-col items-center gap-6">
          <div className="flex flex-col items-center gap-2">
            <Fingerprint size={40} style={{ color: 'var(--text-muted)' }} />
            <p className="text-lg" style={{ color: 'var(--text-muted)' }}>
              PIN eingeben zum Stempeln
            </p>
          </div>
          <input
            ref={inputRef}
            type="password"
            inputMode="numeric"
            maxLength={8}
            value={pin}
            autoFocus
            onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))}
            className="text-center text-4xl font-mono w-48 py-3 rounded-xl tracking-widest"
            style={{
              background: 'var(--surface)',
              border: '2px solid var(--border)',
              color: 'var(--text)',
              outline: 'none',
            }}
            onFocus={(e) => (e.target.style.borderColor = '#F97316')}
            onBlur={(e) => (e.target.style.borderColor = 'var(--border)')}
          />
          <button
            type="submit"
            disabled={loading || pin.length < 4}
            className="px-8 py-3 rounded-xl font-semibold text-white disabled:opacity-40 cursor-pointer"
            style={{ background: '#F97316' }}
          >
            {loading ? '…' : 'Weiter'}
          </button>
        </form>
      )}

      {/* Feedback message */}
      {message && !mitarbeiter && (
        <div
          className="text-center px-10 py-6 rounded-2xl"
          style={{
            background: message.ok ? '#052e16' : '#1c0a0a',
            border: `1px solid ${message.ok ? '#166534' : '#7f1d1d'}`,
          }}
        >
          <p className="text-2xl font-bold" style={{ color: message.ok ? '#4ade80' : '#f87171' }}>
            {message.text}
          </p>
        </div>
      )}

      {/* Mitarbeiter identified — action buttons */}
      {mitarbeiter && status && (
        <div className="flex flex-col items-center gap-6">
          <div className="text-center">
            <p className="text-3xl font-bold">
              {mitarbeiter.vorname} {mitarbeiter.nachname}
            </p>
            <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
              {status.eingestempelt
                ? status.pause_aktiv
                  ? 'Pause aktiv'
                  : 'Eingestempelt'
                : 'Ausgestempelt'}
            </p>
          </div>

          {message && (
            <div
              className="px-6 py-3 rounded-xl text-center"
              style={{
                background: message.ok ? '#052e16' : '#1c0a0a',
                border: `1px solid ${message.ok ? '#166534' : '#7f1d1d'}`,
              }}
            >
              <p className="font-semibold" style={{ color: message.ok ? '#4ade80' : '#f87171' }}>
                {message.text}
              </p>
            </div>
          )}

          <div className="flex gap-4 flex-wrap justify-center">
            {!status.eingestempelt && (
              <KioskButton
                icon={<LogIn size={24} />}
                label="Einloggen"
                color="#22c55e"
                onClick={() => doAction('clock_in')}
                disabled={loading}
              />
            )}
            {status.eingestempelt && !status.pause_aktiv && (
              <>
                <KioskButton
                  icon={<Coffee size={24} />}
                  label="Pause"
                  color="#F97316"
                  onClick={() => doAction('break_start')}
                  disabled={loading}
                />
                <KioskButton
                  icon={<LogOut size={24} />}
                  label="Ausloggen"
                  color="#ef4444"
                  onClick={() => doAction('clock_out')}
                  disabled={loading}
                />
              </>
            )}
            {status.eingestempelt && status.pause_aktiv && (
              <KioskButton
                icon={<Ban size={24} />}
                label="Pause beenden"
                color="#F97316"
                onClick={() => doAction('break_end')}
                disabled={loading}
              />
            )}
          </div>

          <button
            onClick={resetKiosk}
            className="text-sm mt-4 cursor-pointer"
            style={{ color: 'var(--text-muted)' }}
          >
            Abbrechen
          </button>
        </div>
      )}
    </div>
  )
}

function KioskButton({
  icon,
  label,
  color,
  onClick,
  disabled,
}: {
  icon: React.ReactNode
  label: string
  color: string
  onClick: () => void
  disabled?: boolean
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="flex flex-col items-center gap-2 px-8 py-5 rounded-2xl font-semibold text-white transition-opacity disabled:opacity-40 cursor-pointer hover:opacity-90"
      style={{ background: color, minWidth: 140 }}
    >
      {icon}
      {label}
    </button>
  )
}
