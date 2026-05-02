import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe, mitarbeiterAnlegen, mitarbeiterAktualisieren } from '../../api/mitarbeiter'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input, SelectInput } from '../../components/Input'
import { Spinner } from '../../components/Spinner'
import { PageHeader } from '../../components/PageHeader'
import { UserPlus, Pencil, UserX, Mail, Clock, Briefcase, Search, UserCheck, Upload, AlertCircle, CheckCircle2, X } from 'lucide-react'

type Mitarbeiter = {
  id: number
  vorname: string
  nachname: string
  position?: string
  bereich?: string
  beschaeftigungsart?: string
  email?: string
  monatliche_brutto_verguetung?: number
  monatliche_soll_stunden?: number
  aktiv: boolean
}

export function AdminMitarbeiter() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
  const [showImport, setShowImport] = useState(false)
  const [editing, setEditing] = useState<Mitarbeiter | null>(null)
  const [search, setSearch] = useState('')

  const { data: mitarbeiter, isLoading } = useQuery<Mitarbeiter[]>({
    queryKey: ['mitarbeiter'],
    queryFn: () => mitarbeiterListe(true),
  })

  const filtered = (mitarbeiter ?? []).filter((ma) => {
    const q = search.toLowerCase()
    return (
      !q ||
      ma.vorname.toLowerCase().includes(q) ||
      ma.nachname.toLowerCase().includes(q) ||
      (ma.position ?? '').toLowerCase().includes(q) ||
      (ma.email ?? '').toLowerCase().includes(q)
    )
  })

  const handleDeactivate = async (ma: Mitarbeiter) => {
    if (!confirm(`${ma.vorname} ${ma.nachname} wirklich deaktivieren?`)) return
    await mitarbeiterAktualisieren(ma.id, { aktiv: false })
    qc.invalidateQueries({ queryKey: ['mitarbeiter'] })
  }

  const handleEdit = (ma: Mitarbeiter) => {
    setEditing(ma)
    setShowForm(false)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleNew = () => {
    setEditing(null)
    setShowForm(true)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  if (isLoading)
    return <div className="flex justify-center h-40 items-center"><Spinner /></div>

  return (
    <div>
      <PageHeader
        title="Mitarbeiter"
        sub={`${(mitarbeiter ?? []).length} aktive Mitarbeiter`}
        action={
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => { setShowImport((v) => !v); setShowForm(false); setEditing(null) }}>
              <Upload size={14} /> CSV importieren
            </Button>
            <Button onClick={handleNew}>
              <UserPlus size={15} /> Neu anlegen
            </Button>
          </div>
        }
      />

      {/* CSV Import */}
      {showImport && (
        <div className="mb-6">
          <CsvImport
            onImported={() => { qc.invalidateQueries({ queryKey: ['mitarbeiter'] }); setShowImport(false) }}
            onCancel={() => setShowImport(false)}
          />
        </div>
      )}

      {/* Form */}
      {(showForm || editing) && (
        <div className="mb-6">
          <MitarbeiterForm
            initial={editing}
            onSave={async (data) => {
              if (editing) {
                await mitarbeiterAktualisieren(editing.id, data)
              } else {
                await mitarbeiterAnlegen(data)
              }
              qc.invalidateQueries({ queryKey: ['mitarbeiter'] })
              setShowForm(false)
              setEditing(null)
            }}
            onCancel={() => { setShowForm(false); setEditing(null) }}
          />
        </div>
      )}

      {/* Search */}
      <div className="relative mb-4">
        <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
        <input
          type="text"
          placeholder="Suchen nach Name, Position, E-Mail …"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-10 pr-4 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', maxWidth: 400 }}
        />
      </div>

      {/* List */}
      <div
        className="rounded-xl overflow-hidden"
        style={{ border: '1px solid var(--border)' }}
      >
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center py-16 gap-3">
            <UserCheck size={40} style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
            <p style={{ color: 'var(--text-muted)' }}>
              {search ? 'Keine Ergebnisse gefunden.' : 'Noch keine Mitarbeiter angelegt.'}
            </p>
          </div>
        ) : (
          filtered.map((ma, idx) => (
            <div
              key={ma.id}
              className="flex items-center justify-between px-6 py-5 transition-colors hover:bg-[#F5F5F5]"
              style={{
                borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                background: idx % 2 === 0 ? 'var(--surface)' : '#F5F5F5',
              }}
            >
              <div className="flex items-center gap-5">
                {/* Avatar */}
                <div
                  className="w-12 h-12 rounded-2xl flex items-center justify-center text-base font-bold shrink-0"
                  style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
                >
                  {ma.vorname[0]}{ma.nachname[0]}
                </div>

                {/* Info */}
                <div>
                  <p className="font-semibold text-[16px]">{ma.vorname} {ma.nachname}</p>
                  <div className="flex items-center gap-4 mt-1 flex-wrap">
                    {ma.position && (
                      <span className="flex items-center gap-1.5 text-sm" style={{ color: 'var(--text-muted)' }}>
                        <Briefcase size={13} /> {ma.position}
                      </span>
                    )}
                    {ma.email && (
                      <span className="flex items-center gap-1.5 text-sm" style={{ color: 'var(--text-muted)' }}>
                        <Mail size={13} /> {ma.email}
                      </span>
                    )}
                    {ma.monatliche_soll_stunden && (
                      <span className="flex items-center gap-1.5 text-sm" style={{ color: 'var(--text-muted)' }}>
                        <Clock size={13} /> {ma.monatliche_soll_stunden} h/Monat
                      </span>
                    )}
                    {ma.beschaeftigungsart && (
                      <span className="text-xs px-2 py-0.5 rounded-full" style={{ background: 'var(--surface2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
                        {ma.beschaeftigungsart}
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex gap-2 shrink-0">
                <Button
                  variant="secondary"
                  className="h-9 px-3"
                  onClick={() => handleEdit(ma)}
                >
                  <Pencil size={14} /> Bearbeiten
                </Button>
                <Button
                  variant="danger"
                  className="h-9 px-3"
                  onClick={() => handleDeactivate(ma)}
                >
                  <UserX size={14} />
                </Button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

function MitarbeiterForm({
  initial,
  onSave,
  onCancel,
}: {
  initial: Mitarbeiter | null
  onSave: (d: Record<string, unknown>) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState({
    vorname: initial?.vorname ?? '',
    nachname: initial?.nachname ?? '',
    position: initial?.position ?? '',
    bereich: initial?.bereich ?? '',
    email: initial?.email ?? '',
    beschaeftigungsart: initial?.beschaeftigungsart ?? '',
    monatliche_brutto_verguetung: String(initial?.monatliche_brutto_verguetung ?? ''),
    monatliche_soll_stunden: String(initial?.monatliche_soll_stunden ?? ''),
  })
  const [loading, setLoading] = useState(false)

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    await onSave({
      ...form,
      monatliche_brutto_verguetung: form.monatliche_brutto_verguetung
        ? Number(form.monatliche_brutto_verguetung)
        : undefined,
      monatliche_soll_stunden: form.monatliche_soll_stunden
        ? Number(form.monatliche_soll_stunden)
        : undefined,
      beschaeftigungsart: form.beschaeftigungsart || undefined,
    })
    setLoading(false)
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-5">
        <h2 className="font-semibold text-[15px]">
          {initial ? `${initial.vorname} ${initial.nachname} bearbeiten` : 'Neuen Mitarbeiter anlegen'}
        </h2>
        <button onClick={onCancel} className="p-1 rounded hover:bg-white/5 cursor-pointer transition-colors" style={{ color: 'var(--text-muted)' }}>
          <X size={16} />
        </button>
      </div>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-5">
          <Input label="Vorname *" value={form.vorname} onChange={f('vorname')} required autoFocus={!initial} />
          <Input label="Nachname *" value={form.nachname} onChange={f('nachname')} required />
          <Input label="Position / Rolle" value={form.position} onChange={f('position')} placeholder="z.B. Kellner, Koch …" />
          <Input label="Bereich" value={form.bereich} onChange={f('bereich')} placeholder="z.B. Küche, Service …" />
          <Input label="E-Mail" type="email" value={form.email} onChange={f('email')} />
          <SelectInput
            label="Beschäftigungsart"
            value={form.beschaeftigungsart}
            onChange={(e) => setForm((p) => ({ ...p, beschaeftigungsart: e.target.value }))}
          >
            <option value="">— Bitte wählen —</option>
            <option value="Vollzeit">Vollzeit</option>
            <option value="Teilzeit">Teilzeit</option>
            <option value="Minijob">Minijob</option>
            <option value="Aushilfe">Aushilfe</option>
            <option value="Ausbildung">Ausbildung</option>
          </SelectInput>
          <Input label="Monatsbrutto (€)" type="number" step="0.01" min="0" value={form.monatliche_brutto_verguetung} onChange={f('monatliche_brutto_verguetung')} placeholder="0.00" />
          <Input label="Soll-Stunden / Monat" type="number" step="0.5" min="0" value={form.monatliche_soll_stunden} onChange={f('monatliche_soll_stunden')} placeholder="160" />
        </div>
        <div className="flex gap-2 justify-end pt-2" style={{ borderTop: '1px solid var(--border)' }}>
          <Button variant="secondary" type="button" onClick={onCancel}>Abbrechen</Button>
          <Button type="submit" loading={loading}>
            {initial ? 'Änderungen speichern' : 'Mitarbeiter anlegen'}
          </Button>
        </div>
      </form>
    </Card>
  )
}

type CsvRow = { vorname: string; nachname: string; position?: string; email?: string; monatliche_soll_stunden?: string; monatliche_brutto_verguetung?: string; beschaeftigungsart?: string }

function CsvImport({ onImported, onCancel }: { onImported: () => void; onCancel: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [rows, setRows] = useState<CsvRow[]>([])
  const [errors, setErrors] = useState<string[]>([])
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(0)

  const parseCsv = (text: string) => {
    const lines = text.split('\n').map((l) => l.trim()).filter(Boolean)
    if (lines.length < 2) { setErrors(['CSV hat keine Datenzeilen.']); return }
    const header = lines[0].split(';').map((h) => h.trim().toLowerCase())
    const parsed: CsvRow[] = []
    const errs: string[] = []
    for (let i = 1; i < lines.length; i++) {
      const cols = lines[i].split(';').map((c) => c.trim())
      const row: Record<string, string> = {}
      header.forEach((h, j) => { row[h] = cols[j] ?? '' })
      if (!row['vorname'] || !row['nachname']) {
        errs.push(`Zeile ${i + 1}: Vorname und Nachname sind Pflichtfelder.`)
        continue
      }
      parsed.push(row as CsvRow)
    }
    setRows(parsed)
    setErrors(errs)
  }

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    const reader = new FileReader()
    reader.onload = (ev) => parseCsv(ev.target?.result as string)
    reader.readAsText(f, 'UTF-8')
  }

  const handleImport = async () => {
    setLoading(true)
    let count = 0
    for (const row of rows) {
      try {
        await mitarbeiterAnlegen({
          vorname: row.vorname,
          nachname: row.nachname,
          position: row.position || undefined,
          email: row.email || undefined,
          beschaeftigungsart: row.beschaeftigungsart || undefined,
          monatliche_soll_stunden: row.monatliche_soll_stunden ? Number(row.monatliche_soll_stunden) : undefined,
          monatliche_brutto_verguetung: row.monatliche_brutto_verguetung ? Number(row.monatliche_brutto_verguetung) : undefined,
        })
        count++
      } catch { /* ignore single failures */ }
    }
    setDone(count)
    setLoading(false)
    if (count > 0) setTimeout(onImported, 1200)
  }

  return (
    <Card>
      <div className="flex items-center justify-between mb-4">
        <h2 className="font-semibold text-[15px]">Mitarbeiter per CSV importieren</h2>
        <button onClick={onCancel} className="p-1 rounded hover:bg-white/5 cursor-pointer transition-colors" style={{ color: 'var(--text-muted)' }}>
          <X size={16} />
        </button>
      </div>

      <div className="mb-4 p-3 rounded-lg text-xs" style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}>
        <p className="font-semibold mb-1" style={{ color: 'var(--text-muted)' }}>CSV-Format (Semikolon-getrennt, erste Zeile = Kopfzeile):</p>
        <code className="block" style={{ color: 'var(--accent)' }}>
          vorname;nachname;position;email;beschaeftigungsart;monatliche_soll_stunden;monatliche_brutto_verguetung
        </code>
        <p className="mt-1.5" style={{ color: 'var(--text-muted)' }}>Pflichtfelder: <strong>vorname</strong>, <strong>nachname</strong></p>
      </div>

      <input ref={fileRef} type="file" accept=".csv,.txt" className="hidden" onChange={handleFile} />

      {rows.length === 0 ? (
        <button
          onClick={() => fileRef.current?.click()}
          className="flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors cursor-pointer"
          style={{ background: 'var(--surface2)', border: '1px dashed var(--border)', color: 'var(--text-muted)' }}
        >
          <Upload size={14} /> CSV-Datei auswählen
        </button>
      ) : (
        <>
          {errors.length > 0 && (
            <div className="mb-3 p-3 rounded-lg" style={{ background: 'var(--danger-dim)', border: '1px solid rgba(248,113,113,0.2)' }}>
              {errors.map((e, i) => (
                <p key={i} className="text-xs flex items-center gap-1.5" style={{ color: 'var(--danger)' }}>
                  <AlertCircle size={12} /> {e}
                </p>
              ))}
            </div>
          )}

          <div className="rounded-lg overflow-hidden mb-4" style={{ border: '1px solid var(--border)' }}>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: 'var(--surface2)', borderBottom: '1px solid var(--border)' }}>
                  {['Vorname', 'Nachname', 'Position', 'E-Mail', 'Beschäftigung', 'Stunden/Mo'].map((h) => (
                    <th key={h} className="text-left px-3 py-2 font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.slice(0, 10).map((r, i) => (
                  <tr key={i} style={{ borderTop: '1px solid var(--border)', background: i % 2 === 0 ? 'var(--surface)' : '#F2F2F2' }}>
                    <td className="px-3 py-2 font-medium">{r.vorname}</td>
                    <td className="px-3 py-2 font-medium">{r.nachname}</td>
                    <td className="px-3 py-2" style={{ color: 'var(--text-muted)' }}>{r.position || '—'}</td>
                    <td className="px-3 py-2" style={{ color: 'var(--text-muted)' }}>{r.email || '—'}</td>
                    <td className="px-3 py-2" style={{ color: 'var(--text-muted)' }}>{r.beschaeftigungsart || '—'}</td>
                    <td className="px-3 py-2" style={{ color: 'var(--text-muted)' }}>{r.monatliche_soll_stunden || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {rows.length > 10 && (
              <p className="px-3 py-2 text-xs" style={{ color: 'var(--text-muted)', borderTop: '1px solid var(--border)' }}>
                … und {rows.length - 10} weitere Zeilen
              </p>
            )}
          </div>

          {done > 0 ? (
            <div className="flex items-center gap-2 text-sm" style={{ color: 'var(--success)' }}>
              <CheckCircle2 size={16} /> {done} Mitarbeiter erfolgreich importiert
            </div>
          ) : (
            <div className="flex gap-2">
              <Button onClick={handleImport} loading={loading}>
                {rows.length} Mitarbeiter importieren
              </Button>
              <Button variant="secondary" onClick={() => { setRows([]); setErrors([]) }}>
                Andere Datei
              </Button>
              <Button variant="ghost" onClick={onCancel}>Abbrechen</Button>
            </div>
          )}
        </>
      )}
    </Card>
  )
}
