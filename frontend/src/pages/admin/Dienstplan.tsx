import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { PageHeader } from '../../components/PageHeader'
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
import { ChevronLeft, ChevronRight, Info, Mail, CheckCircle, XCircle, Printer, X, Trash2 } from 'lucide-react'

type MA = { id: number; vorname: string; nachname: string; position?: string }

const SCHICHT_CONFIG: Record<string, { label: string; bg: string; text: string; border: string }> = {
  arbeit:    { label: 'Arbeit',    bg: 'rgba(249,115,22,0.15)', text: '#F97316', border: 'rgba(249,115,22,0.4)' },
  urlaub:    { label: 'Urlaub',    bg: 'rgba(59,130,246,0.15)', text: '#60a5fa', border: 'rgba(59,130,246,0.4)' },
  krank:     { label: 'Krank',     bg: 'rgba(239,68,68,0.15)',  text: '#f87171', border: 'rgba(239,68,68,0.4)' },
  frei:      { label: 'Frei',      bg: 'rgba(100,116,139,0.15)', text: '#94a3b8', border: 'rgba(100,116,139,0.4)' },
  unbezahlt: { label: 'Unbezahlt', bg: 'rgba(168,85,247,0.15)', text: '#c084fc', border: 'rgba(168,85,247,0.4)' },
}

const SCHICHT_TYPEN = ['arbeit', 'urlaub', 'krank', 'frei', 'unbezahlt'] as const
type Schichttyp = typeof SCHICHT_TYPEN[number]

const DAYS_DE = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
const DAYS_FULL = ['Montag', 'Dienstag', 'Mittwoch', 'Donnerstag', 'Freitag', 'Samstag', 'Sonntag']
const MONTHS_DE = ['Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun', 'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
const MONTHS_FULL = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember']

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

function formatDateFull(d: Date): string {
  return `${DAYS_FULL[d.getDay() === 0 ? 6 : d.getDay() - 1]}, ${d.getDate()}. ${MONTHS_FULL[d.getMonth()]} ${d.getFullYear()}`
}

type DialogState = { ma: MA; day: Date; eintrag: DienstplanEintrag | undefined }

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
  const [dialog, setDialog] = useState<DialogState | null>(null)

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

  const handleCellClick = (ma: MA, day: Date) => {
    setDialog({ ma, day, eintrag: getEintrag(ma.id, day) })
  }

  const handleSave = async (data: {
    schichttyp: string
    start_zeit?: string
    end_zeit?: string
    pause_minuten?: number
  }) => {
    if (!dialog) return
    setSaving(`${dialog.ma.id}-${isoDate(dialog.day)}`)
    try {
      await dienstplanEintragSetzen({
        mitarbeiter_id: dialog.ma.id,
        datum: isoDate(dialog.day),
        ...data,
      })
      qc.invalidateQueries({ queryKey: ['dienstplan', isoDate(monday)] })
      setDialog(null)
    } finally {
      setSaving(null)
    }
  }

  const handleDelete = async () => {
    if (!dialog?.eintrag?.id) return
    setSaving(`${dialog.ma.id}-${isoDate(dialog.day)}`)
    try {
      await dienstplanEintragLoeschen(dialog.eintrag.id)
      qc.invalidateQueries({ queryKey: ['dienstplan', isoDate(monday)] })
      setDialog(null)
    } finally {
      setSaving(null)
    }
  }

  const isLoading = maLoading || dpLoading

  const handlePrint = () => {
    const DAYS = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
    const LABELS: Record<string, string> = { arbeit: 'Arbeit', urlaub: 'Urlaub', krank: 'Krank', frei: 'Frei', unbezahlt: 'Unbez.' }
    const COLORS: Record<string, string> = { arbeit: '#f97316', urlaub: '#3b82f6', krank: '#ef4444', frei: '#64748b', unbezahlt: '#a855f7' }

    const dayHeaders = weekDays.map((day, i) =>
      `<th style="padding:10px 6px;text-align:center;font-size:11px;color:#666;font-weight:600;">
        ${DAYS[i]}<br><span style="font-size:14px;font-weight:700;color:#111;">${day.getDate()}.${day.getMonth() + 1}.</span>
      </th>`
    ).join('')

    const rows = (mitarbeiter ?? []).map((ma) => {
      const cells = weekDays.map((day) => {
        const e = getEintrag(ma.id, day)
        const typ = e?.schichttyp
        const col = typ ? COLORS[typ] : null
        const cell = typ
          ? `<span style="padding:3px 10px;border-radius:5px;background:${col}22;color:${col};border:1px solid ${col}55;font-size:11px;">${LABELS[typ] ?? typ}</span>`
          : `<span style="color:#bbb;font-size:11px;">—</span>`
        const zeit = e?.start_zeit ? `<div style="font-size:10px;color:#888;margin-top:2px;">${e.start_zeit.slice(0,5)}${e.end_zeit ? ` – ${e.end_zeit.slice(0,5)}` : ''}</div>` : ''
        return `<td style="padding:8px 6px;text-align:center;">${cell}${zeit}</td>`
      }).join('')
      return `<tr style="border-bottom:1px solid #e5e7eb;">
        <td style="padding:8px 12px;font-size:13px;font-weight:500;">${ma.vorname} ${ma.nachname}${ma.position ? `<div style="font-size:10px;color:#888;">${ma.position}</div>` : ''}</td>
        ${cells}
      </tr>`
    }).join('')

    const logoSrc = `${window.location.origin}/complio-logo.png`
    const heute = new Date().toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })

    const html = `<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Dienstplan ${formatWeek(monday)}</title>
<style>
  body{font-family:Arial,sans-serif;margin:0;padding:28px;background:#fff;color:#111;}
  table{width:100%;border-collapse:collapse;}
  @media print{body{padding:14px;}button{display:none;}}
</style>
</head><body>
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:20px;padding-bottom:14px;border-bottom:3px solid #f97316;">
  <div style="background:#000;padding:8px 16px;border-radius:8px;">
    <img src="${logoSrc}" style="height:32px;display:block;" alt="Complio">
  </div>
  <div style="text-align:right;">
    <div style="font-size:18px;font-weight:700;">Dienstplan</div>
    <div style="font-size:13px;color:#666;margin-top:2px;">${formatWeek(monday)}</div>
  </div>
</div>
<table>
  <thead><tr style="border-bottom:2px solid #e5e7eb;background:#f9f9f9;">
    <th style="padding:10px 12px;text-align:left;font-size:11px;color:#666;font-weight:600;">Mitarbeiter</th>
    ${dayHeaders}
  </tr></thead>
  <tbody>${rows}</tbody>
</table>
<div style="margin-top:36px;padding:14px 18px;border:1.5px solid #f97316;border-radius:8px;background:#fff8f3;">
  <p style="font-size:11px;color:#333;margin:0;line-height:1.7;">
    <strong style="color:#f97316;">⚠ Wichtiger Hinweis:</strong>&nbsp;
    Dieser Dienstplan gilt vorbehaltlich kurzfristiger Änderungen durch Krankheit, höhere Gewalt oder sonstige
    unvorhergesehene Ereignisse. Die angegebenen Endzeiten können je nach wirtschaftlicher Auslastung und
    betrieblichen Erfordernissen variieren. Änderungen werden so früh wie möglich kommuniziert.
  </p>
</div>
<p style="font-size:10px;color:#aaa;text-align:center;margin-top:20px;">
  Erstellt am ${heute} · Steakhouse Piccolo · Complio HR-Software
</p>
<div style="text-align:center;margin-top:12px;">
  <button onclick="window.print()" style="background:#f97316;color:#fff;border:none;padding:10px 28px;border-radius:6px;font-size:13px;cursor:pointer;">
    Drucken / Als PDF speichern
  </button>
</div>
</body></html>`

    const win = window.open('', '_blank')
    if (win) {
      win.document.write(html)
      win.document.close()
      win.focus()
    }
  }

  return (
    <div>
      <PageHeader
        title="Dienstplan"
        sub="Wöchentliche Schichtplanung — Zelle anklicken zum Bearbeiten"
        action={
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={handlePrint}>
              <Printer size={14} /> PDF
            </Button>
            <Button variant="secondary" onClick={sendEmail} loading={emailSending}>
              <Mail size={14} /> Per E-Mail senden
            </Button>
            <div className="flex items-center gap-1">
              <button
                onClick={prevWeek}
                className="p-1.5 rounded-lg hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                <ChevronLeft size={16} />
              </button>
              <button
                onClick={thisWeek}
                className="px-3 py-1.5 rounded-lg text-sm font-medium hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                style={{ border: '1px solid var(--border)', color: 'var(--text)', minWidth: 200, textAlign: 'center' }}
              >
                {formatWeek(monday)}
              </button>
              <button
                onClick={nextWeek}
                className="p-1.5 rounded-lg hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                style={{ border: '1px solid var(--border)', color: 'var(--text)' }}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        }
      />

      {emailResult && (
        <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>{emailResult}</p>
      )}

      {/* Legend */}
      <div className="flex items-center gap-4 mb-5 flex-wrap">
        {Object.entries(SCHICHT_CONFIG).map(([k, v]) => (
          <div key={k} className="flex items-center gap-2">
            <div className="w-3 h-3 rounded-sm" style={{ background: v.bg, border: `1px solid ${v.border}` }} />
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{v.label}</span>
          </div>
        ))}
        <div className="flex items-center gap-1 ml-2" style={{ color: 'var(--text-muted)' }}>
          <Info size={12} />
          <span className="text-xs">Zelle anklicken zum Bearbeiten</span>
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
                            className="w-full rounded-lg py-1.5 px-1 text-xs font-medium transition-all cursor-pointer hover:opacity-80"
                            style={{
                              minWidth: 70,
                              background: cfg ? cfg.bg : 'transparent',
                              color: cfg ? cfg.text : 'var(--text-muted)',
                              border: cfg ? `1px solid ${cfg.border}` : '1px dashed var(--border)',
                              opacity: isSaving ? 0.5 : 1,
                            }}
                          >
                            {isSaving ? '…' : cfg ? (
                              <>
                                <div>{cfg.label}</div>
                                {eintrag?.start_zeit && (
                                  <div className="text-xs mt-0.5 opacity-80">
                                    {eintrag.start_zeit.slice(0, 5)}{eintrag.end_zeit ? `–${eintrag.end_zeit.slice(0, 5)}` : ''}
                                  </div>
                                )}
                              </>
                            ) : '—'}
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
          <div className="flex items-center gap-2 py-3" style={{ color: 'var(--text-muted)' }}>
            <Spinner size={14} /> <span className="text-sm">Lade Wünsche …</span>
          </div>
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

      {/* Schicht-Dialog */}
      {dialog && (
        <SchichtDialog
          ma={dialog.ma}
          day={dialog.day}
          eintrag={dialog.eintrag}
          saving={saving === `${dialog.ma.id}-${isoDate(dialog.day)}`}
          onSave={handleSave}
          onDelete={handleDelete}
          onClose={() => setDialog(null)}
        />
      )}
    </div>
  )
}

function SchichtDialog({
  ma,
  day,
  eintrag,
  saving,
  onSave,
  onDelete,
  onClose,
}: {
  ma: MA
  day: Date
  eintrag: DienstplanEintrag | undefined
  saving: boolean
  onSave: (data: { schichttyp: string; start_zeit?: string; end_zeit?: string; pause_minuten?: number }) => Promise<void>
  onDelete: () => Promise<void>
  onClose: () => void
}) {
  const [typ, setTyp] = useState<Schichttyp>((eintrag?.schichttyp as Schichttyp) ?? 'arbeit')
  const [start, setStart] = useState(eintrag?.start_zeit?.slice(0, 5) ?? '09:00')
  const [ende, setEnde] = useState(eintrag?.end_zeit?.slice(0, 5) ?? '17:00')
  const [pause, setPause] = useState(String(eintrag?.pause_minuten ?? 30))

  const needsZeiten = typ === 'arbeit' || typ === 'unbezahlt'
  const cfg = SCHICHT_CONFIG[typ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSave({
      schichttyp: typ,
      start_zeit: needsZeiten ? start : undefined,
      end_zeit: needsZeiten ? ende : undefined,
      pause_minuten: needsZeiten ? (Number(pause) || 0) : undefined,
    })
  }

  const inputStyle = { background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: 'rgba(0,0,0,0.7)' }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div className="w-full max-w-md rounded-2xl p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
        <div className="flex items-start justify-between mb-5">
          <div>
            <h2 className="font-semibold text-base">Dienst bearbeiten</h2>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {ma.vorname} {ma.nachname} · {formatDateFull(day)}
            </p>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg hover:bg-[#1a1a1a] transition-colors cursor-pointer" style={{ color: 'var(--text-muted)' }}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Schichttyp</label>
            <div className="flex gap-2 flex-wrap">
              {SCHICHT_TYPEN.map((t) => {
                const c = SCHICHT_CONFIG[t]
                const active = typ === t
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => setTyp(t)}
                    className="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all cursor-pointer"
                    style={{
                      background: active ? c.bg : 'var(--surface2)',
                      color: active ? c.text : 'var(--text-muted)',
                      border: active ? `1px solid ${c.border}` : '1px solid var(--border)',
                    }}
                  >
                    {c.label}
                  </button>
                )
              })}
            </div>
          </div>

          {needsZeiten && (
            <div className="grid grid-cols-3 gap-3">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Start</label>
                <input type="time" value={start} onChange={(e) => setStart(e.target.value)}
                  className="px-3 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]" style={inputStyle} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Ende</label>
                <input type="time" value={ende} onChange={(e) => setEnde(e.target.value)}
                  className="px-3 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]" style={inputStyle} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium">Pause (Min)</label>
                <input type="number" value={pause} onChange={(e) => setPause(e.target.value)} min="0"
                  className="px-3 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]" style={inputStyle} />
              </div>
            </div>
          )}

          {!needsZeiten && (
            <div className="text-sm px-4 py-3 rounded-lg" style={{ background: cfg.bg, color: cfg.text, border: `1px solid ${cfg.border}` }}>
              {typ === 'urlaub' && 'Urlaubstag — Arbeitszeit wird nicht erfasst.'}
              {typ === 'krank' && 'Krankheitstag — Lohnfortzahlung nach BUrlG.'}
              {typ === 'frei' && 'Freier Tag — kein Arbeitseinsatz geplant.'}
            </div>
          )}

          <div className="flex gap-2 mt-1">
            <button
              type="submit"
              disabled={saving}
              className="flex-1 py-2.5 rounded-xl font-semibold text-white text-sm transition-opacity disabled:opacity-50 cursor-pointer"
              style={{ background: cfg.text }}
            >
              {saving ? '…' : eintrag ? 'Änderungen speichern' : 'Eintrag erstellen'}
            </button>
            {eintrag && (
              <button
                type="button"
                onClick={onDelete}
                disabled={saving}
                className="p-2.5 rounded-xl transition-colors cursor-pointer hover:bg-red-900/20"
                style={{ border: '1px solid var(--border)', color: '#ef4444' }}
                title="Eintrag löschen"
              >
                <Trash2 size={16} />
              </button>
            )}
          </div>
        </form>
      </div>
    </div>
  )
}
