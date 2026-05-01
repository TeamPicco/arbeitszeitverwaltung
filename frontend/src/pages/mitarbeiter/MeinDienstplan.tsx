import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  dienstplanMonat,
  dienstplanWunschEinreichen,
  type DienstplanEintrag,
} from '../../api/dienstplan'
import { useAuthStore } from '../../store/auth'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Spinner } from '../../components/Spinner'
import { CalendarDays, Send, CheckCircle } from 'lucide-react'

const SCHICHT_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  arbeit:  { label: 'Arbeit',  color: '#F97316', bg: 'rgba(249,115,22,0.12)' },
  urlaub:  { label: 'Urlaub',  color: '#60a5fa', bg: 'rgba(59,130,246,0.12)' },
  frei:    { label: 'Frei',    color: '#94a3b8', bg: 'rgba(100,116,139,0.12)' },
}

const DAYS_SHORT = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const MONTHS_DE = [
  'Januar','Februar','März','April','Mai','Juni',
  'Juli','August','September','Oktober','November','Dezember',
]

function MonthGrid({ eintraege, monat, jahr }: { eintraege: DienstplanEintrag[]; monat: number; jahr: number }) {
  const firstDay = new Date(jahr, monat - 1, 1)
  const lastDay = new Date(jahr, monat, 0)
  // Offset: Mo=0 … So=6
  const startOffset = (firstDay.getDay() + 6) % 7

  const cells: (DienstplanEintrag | null)[] = []
  for (let i = 0; i < startOffset; i++) cells.push(null)
  for (let d = 1; d <= lastDay.getDate(); d++) {
    const iso = `${jahr}-${String(monat).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push(eintraege.find((e) => e.datum === iso) ?? { datum: iso } as DienstplanEintrag)
  }

  return (
    <div>
      <div className="grid grid-cols-7 mb-2">
        {DAYS_SHORT.map((d) => (
          <div key={d} className="text-center text-xs font-semibold py-1" style={{ color: 'var(--text-muted)' }}>
            {d}
          </div>
        ))}
      </div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((cell, idx) => {
          if (!cell) return <div key={idx} />
          const day = parseInt(cell.datum.slice(8, 10), 10)
          const cfg = cell.schichttyp ? SCHICHT_CONFIG[cell.schichttyp] : null
          return (
            <div
              key={cell.datum}
              className="rounded-lg text-center py-1.5 text-sm font-medium"
              style={cfg ? { background: cfg.bg, color: cfg.color } : { color: 'var(--text-muted)' }}
            >
              <div>{day}</div>
              {cfg && <div className="text-xs">{cfg.label}</div>}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function MeinDienstplan() {
  const { mitarbeiterId } = useAuthStore()
  const qc = useQueryClient()
  const now = new Date()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ datum_von: '', datum_bis: '', wunsch_text: '' })
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState('')

  const thisMonat = now.getMonth() + 1
  const thisJahr = now.getFullYear()
  const nextMonat = thisMonat === 12 ? 1 : thisMonat + 1
  const nextJahr = thisMonat === 12 ? thisJahr + 1 : thisJahr

  const { data: thisPlan, isLoading: l1 } = useQuery<DienstplanEintrag[]>({
    queryKey: ['dienstplan-monat', thisMonat, thisJahr, mitarbeiterId],
    queryFn: () => dienstplanMonat(thisJahr, thisMonat),
    enabled: !!mitarbeiterId,
  })

  const { data: nextPlan, isLoading: l2 } = useQuery<DienstplanEintrag[]>({
    queryKey: ['dienstplan-monat', nextMonat, nextJahr, mitarbeiterId],
    queryFn: () => dienstplanMonat(nextJahr, nextMonat),
    enabled: !!mitarbeiterId,
  })

  const myThis = (thisPlan ?? []).filter((e) => e.mitarbeiter_id === mitarbeiterId)
  const myNext = (nextPlan ?? []).filter((e) => e.mitarbeiter_id === mitarbeiterId)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.datum_von || !form.datum_bis) {
      setError('Bitte Zeitraum angeben.')
      return
    }
    setLoading(true)
    try {
      await dienstplanWunschEinreichen({
        datum_von: form.datum_von,
        datum_bis: form.datum_bis,
        wunsch_text: form.wunsch_text || undefined,
      })
      qc.invalidateQueries({ queryKey: ['dienstplan-wunsch'] })
      setSuccess(true)
      setShowForm(false)
      setForm({ datum_von: '', datum_bis: '', wunsch_text: '' })
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Fehler beim Einreichen.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Mein Dienstplan</h1>
        <Button onClick={() => { setShowForm((v) => !v); setSuccess(false) }}>
          <Send size={14} /> {showForm ? 'Abbrechen' : 'Wunsch einreichen'}
        </Button>
      </div>

      {success && (
        <div
          className="flex items-center gap-2 px-4 py-3 rounded-xl mb-6 text-sm font-medium"
          style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e', border: '1px solid rgba(34,197,94,0.3)' }}
        >
          <CheckCircle size={16} /> Ihr Wunsch wurde eingereicht und wird geprüft.
        </div>
      )}

      {showForm && (
        <Card className="mb-6">
          <h2 className="font-semibold mb-4">Dienstplanwunsch einreichen</h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="Von"
                type="date"
                value={form.datum_von}
                onChange={(e) => setForm((p) => ({ ...p, datum_von: e.target.value }))}
                required
              />
              <Input
                label="Bis"
                type="date"
                value={form.datum_bis}
                onChange={(e) => setForm((p) => ({ ...p, datum_bis: e.target.value }))}
                required
              />
            </div>
            <Input
              label="Begründung / Wunsch (optional)"
              value={form.wunsch_text}
              onChange={(e) => setForm((p) => ({ ...p, wunsch_text: e.target.value }))}
              placeholder="z.B. Urlaub, Arzttermin, bevorzugte Schicht …"
            />
            {error && <p className="text-sm" style={{ color: '#ef4444' }}>{error}</p>}
            <Button type="submit" loading={loading}>Wunsch einreichen</Button>
          </form>
        </Card>
      )}

      {/* Aktueller Monat */}
      <Card className="mb-4">
        <div className="flex items-center gap-2 mb-4">
          <CalendarDays size={18} style={{ color: 'var(--accent)' }} />
          <h2 className="font-semibold">{MONTHS_DE[thisMonat - 1]} {thisJahr}</h2>
        </div>
        {l1 ? <Spinner /> : myThis.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Noch kein Dienstplan veröffentlicht.</p>
        ) : (
          <MonthGrid eintraege={myThis} monat={thisMonat} jahr={thisJahr} />
        )}
      </Card>

      {/* Nächster Monat */}
      <Card>
        <div className="flex items-center gap-2 mb-4">
          <CalendarDays size={18} style={{ color: 'var(--text-muted)' }} />
          <h2 className="font-semibold">{MONTHS_DE[nextMonat - 1]} {nextJahr}</h2>
        </div>
        {l2 ? <Spinner /> : myNext.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Noch kein Dienstplan veröffentlicht.</p>
        ) : (
          <MonthGrid eintraege={myNext} monat={nextMonat} jahr={nextJahr} />
        )}
      </Card>
    </div>
  )
}
