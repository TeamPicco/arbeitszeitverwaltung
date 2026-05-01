import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import {
  dienstplanWoche,
  dienstplanEintragSetzen,
  dienstplanEintragLoeschen,
  dienstplanWuenscheListe,
  dienstplanWunschEntscheiden,
  dienstplanEmailVersenden,
  type DienstplanEintrag,
  type DienstplanWunsch,
} from '../../api/dienstplan'
import { Button } from '../../components/Button'
import { Spinner } from '../../components/Spinner'
import { ChevronLeft, ChevronRight, Info, Mail, CheckCircle, XCircle } from 'lucide-react'

type MA = { id: number; vorname: string; nachname: string; position?: string }

type Schichttyp = 'arbeit' | 'urlaub' | 'frei' | null

const SCHICHT_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  arbeit:  { label: 'Arbeit',  bg: 'rgba(249,115,22,0.15)', text: '#F97316', border: 'rgba(249,115,22,0.4)' },
  urlaub:  { label: 'Urlaub',  bg: 'rgba(59,130,246,0.15)', text: '#60a5fa', border: 'rgba(59,130,246,0.4)' },
  frei:    { label: 'Frei',    bg: 'rgba(100,116,139,0.15)', text: '#94a3b8', border: 'rgba(100,116,139,0.4)' },
}

const DAYS_DE = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const MONTHS_DE = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']

function getMondayOfWeek(d: Date): Date {
  const day = d.getDay()
  const diff = day === 0 ? -6 : 1 - day
  const monday = new Date(d)
  monday.setDate(d.getDate() + diff)
  monday.setHours(0, 0, 0, 0)
  return monday
}

function isoDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function formatWeek(monday: Date): string {
  const sunday = new Date(monday)
  sunday.setDate(monday.getDate() + 6)
  return `${monday.getDate()}. ${MONTHS_DE[monday.getMonth()]} – ${sunday.getDate()}. ${MONTHS_DE[sunday.getMonth()]} ${sunday.getFullYear()}`
}

function isToday(d: Date): boolean {
  const today = new Date()
  return isoDate(d) === isoDate(today)
}

const WUNSCH_STATUS: Record<string, { label: string; color: string }> = {
  offen:      { label: 'Offen',      color: '#F97316' },
  ausstehend: { label: 'Ausstehend', color: '#F97316' },
  genehmigt:  { label: 'Genehmigt',  color: '#22c55e' },
  abgelehnt:  { label: 'Abgelehnt',  color: '#ef4444' },
}

export function AdminDienstplan() {
  const qc = useQueryClient()
  const [monday, setMonday] = useState<Date>(() => getMondayOfWeek(new Date()))
  const [saving, setSaving] = useState<string | null>(null)
  const [emailSending, setEmailSending] = useState(false)
  const [emailResult, setEmailResult] = useState<string | null>(null)
  const [ablehnungsgrund, setAblehnungsgrund] = useState<Record<number, string>>({})

  const weekDays = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(monday)
    d.setDate(monday.getDate() + i)
    return d
  })

  const { data: mitarbeiter, isLoading: maLoading } = useQuery<MA[]>({
    queryKey: ['mitarbeiter'],
    queryFn: () => mitarbeiterListe(true),
  })

  const { data: eintraege, isLoading: dpLoading } = useQuery<DienstplanEintrag[]>({
    queryKey: ['dienstplan', isoDate(monday)],
    queryFn: () => dienstplanWoche(isoDate(monday)),
  })

  const { data: wuensche } = useQuery<DienstplanWunsch[]>({
    queryKey: ['dienstplan-wuensche'],
    queryFn: dienstplanWuenscheListe,
  })

  const offeneWuensche = (wuensche ?? []).filter((w) => w.status === 'offen' || w.status === 'ausstehend')

  const sendEmail = async () => {
    setEmailSending(true)
    setEmailResult(null)
    try {
      const res = await dienstplanEmailVersenden(monday.getMonth() + 1, monday.getFullYear()) as {
        gesendet: number; fehlgeschlagen: number; keine_email: number
      }
      setEmailResult(`Versendet: ${res.gesendet} · Fehler: ${res.fehlgeschlagen} · Keine E-Mail: ${res.keine_email}`)
    } catch {
      setEmailResult('Fehler beim Versenden.')
    } finally {
      setEmailSending(false)
    }
  }

  const entscheideWunsch = async (id: number, status: 'genehmigt' | 'abgelehnt') => {
    await dienstplanWunschEntscheiden(id, status, ablehnungsgrund[id])
    qc.invalidateQueries({ queryKey: ['dienstplan-wuensche'] })
    setAblehnungsgrund((p) => { const c = { ...p }; delete c[id]; return c })
  }

  const prevWeek = () => {
    const d = new Date(monday)
    d.setDate(d.getDate() - 7)
    setMonday(d)
  }
  const nextWeek = () => {
    const d = new Date(monday)
    d.setDate(d.getDate() + 7)
    setMonday(d)
  }
  const thisWeek = () => setMonday(getMondayOfWeek(new Date()))

  const getEintrag = (maId: number, day: Date): DienstplanEintrag | undefined =>
    (eintraege ?? []).find((e) => e.mitarbeiter_id === maId && e.datum === isoDate(day))

  const CYCLE: Schichttyp[] = ['arbeit', 'urlaub', 'frei', null]

  const handleCellClick = async (ma: MA, day: Date) => {
    const key = `${ma.id}-${isoDate(day)}`
    setSaving(key)
    const current = getEintrag(ma.id, day)
    const currentType = current?.schichttyp ?? null
    const idx = CYCLE.indexOf(currentType as Schichttyp)
    const next = CYCLE[(idx + 1) % CYCLE.length]

    try {
      if (next === null) {
        if (current?.id) {
          await dienstplanEintragLoeschen(current.id)
        }
      } else {
        await dienstplanEintragSetzen({
          mitarbeiter_id: ma.id,
          datum: isoDate(day),
          schichttyp: next,
        })
      }
      qc.invalidateQueries({ queryKey: ['dienstplan', isoDate(monday)] })
    } finally {
      setSaving(null)
    }
  }

  const isLoading = maLoading || dpLoading

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Dienstplan</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Wöchentliche Schichtplanung — Zelle anklicken zum Wechseln
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Email versenden */}
          <Button variant="secondary" onClick={sendEmail} loading={emailSending}>
            <Mail size={14} /> Dienstplan per E-Mail versenden
          </Button>

          {/* Week navigation */}
          <div className="flex items-center gap-2">
          <button
            onClick={prevWeek}
            className="p-2 rounded-lg hover:bg-[#1a1a1a] transition-colors cursor-pointer"
            style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            <ChevronLeft size={18} />
          </button>
          <button
            onClick={thisWeek}
            className="px-4 py-2 rounded-lg text-sm font-medium hover:bg-[#1a1a1a] transition-colors cursor-pointer"
            style={{ border: '1px solid var(--border)', color: 'var(--text)', minWidth: 220, textAlign: 'center' }}
          >
            {formatWeek(monday)}
          </button>
          <button
            onClick={nextWeek}
            className="p-2 rounded-lg hover:bg-[#1a1a1a] transition-colors cursor-pointer"
            style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
          >
            <ChevronRight size={18} />
          </button>
          </div>
        </div>
      </div>

      {emailResult && (
        <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{emailResult}</p>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 mb-5">
        {Object.entries(SCHICHT_CONFIG).map(([k, v]) => (
          <div key={k} className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ background: v.bg, border: `1px solid ${v.border}` }}
            />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{v.label}</span>
          </div>
        ))}
        <div className="flex items-center gap-1 ml-2" style={{ color: 'var(--text-muted)' }}>
          <Info size={12} />
          <span className="text-xs">Klicken zum Wechseln: Arbeit → Urlaub → Frei → Leer</span>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center items-center h-48">
          <Spinner />
        </div>
      ) : (
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)' }}
        >
          <div className="overflow-x-auto">
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#0d0d0d', borderBottom: '1px solid var(--border)' }}>
                  <th
                    className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider"
                    style={{ color: 'var(--text-muted)', width: 180 }}
                  >
                    Mitarbeiter
                  </th>
                  {weekDays.map((day, i) => {
                    const today = isToday(day)
                    const isWeekend = i >= 5
                    return (
                      <th
                        key={i}
                        className="px-2 py-3 text-center"
                        style={{
                          color: today ? 'var(--accent)' : isWeekend ? '#555' : 'var(--text-muted)',
                          minWidth: 90,
                        }}
                      >
                        <div className="text-xs font-semibold uppercase tracking-wider">{DAYS_DE[i]}</div>
                        <div
                          className={`text-base font-bold mt-0.5 ${today ? 'w-7 h-7 rounded-full flex items-center justify-center mx-auto' : ''}`}
                          style={today ? { background: 'var(--accent)', color: '#fff', fontSize: 13 } : {}}
                        >
                          {day.getDate()}
                        </div>
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {(mitarbeiter ?? []).length === 0 && (
                  <tr>
                    <td
                      colSpan={8}
                      className="py-12 text-center text-sm"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      Keine Mitarbeiter angelegt.
                    </td>
                  </tr>
                )}
                {(mitarbeiter ?? []).map((ma, maIdx) => (
                  <tr
                    key={ma.id}
                    style={{
                      borderTop: maIdx > 0 ? '1px solid var(--border)' : undefined,
                      background: maIdx % 2 === 0 ? 'var(--surface)' : '#0f0f0f',
                    }}
                  >
                    {/* Employee name */}
                    <td className="px-4 py-3">
                      <p className="text-sm font-medium">{ma.vorname} {ma.nachname}</p>
                      {ma.position && (
                        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                          {ma.position}
                        </p>
                      )}
                    </td>

                    {/* Day cells */}
                    {weekDays.map((day, i) => {
                      const eintrag = getEintrag(ma.id, day)
                      const typ = eintrag?.schichttyp ?? null
                      const cfg = typ ? SCHICHT_CONFIG[typ] : null
                      const key = `${ma.id}-${isoDate(day)}`
                      const isSaving = saving === key
                      const isWeekend = i >= 5

                      return (
                        <td
                          key={i}
                          className="px-2 py-2 text-center"
                          style={{
                            background: isWeekend && !typ ? 'rgba(0,0,0,0.2)' : undefined,
                          }}
                        >
                          <button
                            onClick={() => handleCellClick(ma, day)}
                            disabled={isSaving}
                            className="w-full rounded-lg py-1.5 px-1 text-xs font-medium transition-all cursor-pointer"
                            style={{
                              minWidth: 70,
                              background: cfg ? cfg.bg : 'transparent',
                              color: cfg ? cfg.text : 'var(--text-muted)',
                              border: cfg ? `1px solid ${cfg.border}` : '1px dashed var(--border)',
                              opacity: isSaving ? 0.5 : 1,
                            }}
                          >
                            {isSaving ? '…' : cfg ? cfg.label : '—'}
                          </button>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Dienstplanwünsche */}
      <div className="mt-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold">Dienstplanwünsche</h2>
          {offeneWuensche.length > 0 && (
            <span
              className="text-xs font-semibold px-2.5 py-1 rounded-full"
              style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
            >
              {offeneWuensche.length} ausstehend
            </span>
          )}
        </div>

        {!wuensche ? (
          <Spinner />
        ) : wuensche.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Keine Dienstplanwünsche vorhanden.</p>
        ) : (
          <div
            className="rounded-xl overflow-hidden"
            style={{ border: '1px solid var(--border)' }}
          >
            {wuensche.map((w, idx) => {
              const s = WUNSCH_STATUS[w.status] ?? { label: w.status, color: '#888' }
              const ma = w.mitarbeiter
              return (
                <div
                  key={w.id}
                  className="px-5 py-4"
                  style={{
                    borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                    background: idx % 2 === 0 ? 'var(--surface)' : '#0f0f0f',
                  }}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium">
                        {ma ? `${ma.vorname} ${ma.nachname}` : `MA ${w.mitarbeiter_id}`}
                      </p>
                      <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {w.datum_von} – {w.datum_bis}
                        {w.wunsch_text && ` · „${w.wunsch_text}"`}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-xs font-semibold" style={{ color: s.color }}>
                        {s.label}
                      </span>
                      {(w.status === 'ausstehend' || w.status === 'offen') && (
                        <>
                          <button
                            onClick={() => entscheideWunsch(w.id, 'genehmigt')}
                            className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg font-medium cursor-pointer transition-all"
                            style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e' }}
                          >
                            <CheckCircle size={13} /> Genehmigen
                          </button>
                          <div className="flex items-center gap-1">
                            <input
                              type="text"
                              placeholder="Begründung (optional)"
                              value={ablehnungsgrund[w.id] ?? ''}
                              onChange={(e) => setAblehnungsgrund((p) => ({ ...p, [w.id]: e.target.value }))}
                              className="text-xs px-2 py-1.5 rounded-lg"
                              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)', width: 160 }}
                            />
                            <button
                              onClick={() => entscheideWunsch(w.id, 'abgelehnt')}
                              className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg font-medium cursor-pointer transition-all"
                              style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
                            >
                              <XCircle size={13} /> Ablehnen
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
