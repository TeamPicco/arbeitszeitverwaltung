import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe, mitarbeiterAnlegen, mitarbeiterAktualisieren } from '../../api/mitarbeiter'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Spinner } from '../../components/Spinner'
import { UserPlus, Pencil, UserX, Mail, Clock, Briefcase, Search, UserCheck } from 'lucide-react'

type Mitarbeiter = {
  id: number
  vorname: string
  nachname: string
  position?: string
  email?: string
  stundenlohn?: number
  monatliche_soll_stunden?: number
  aktiv: boolean
}

export function AdminMitarbeiter() {
  const qc = useQueryClient()
  const [showForm, setShowForm] = useState(false)
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
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold tracking-tight">Mitarbeiter</h1>
          <p className="text-base mt-1.5" style={{ color: 'var(--text-muted)' }}>
            {(mitarbeiter ?? []).length} aktive Mitarbeiter
          </p>
        </div>
        <Button onClick={handleNew}>
          <UserPlus size={16} /> Neu anlegen
        </Button>
      </div>

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
              className="flex items-center justify-between px-6 py-5 transition-colors hover:bg-[#141414]"
              style={{
                borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                background: idx % 2 === 0 ? 'var(--surface)' : '#0d0d0d',
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
    email: initial?.email ?? '',
    stundenlohn: String(initial?.stundenlohn ?? ''),
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
      stundenlohn: form.stundenlohn ? Number(form.stundenlohn) : undefined,
      monatliche_soll_stunden: form.monatliche_soll_stunden
        ? Number(form.monatliche_soll_stunden)
        : undefined,
    })
    setLoading(false)
  }

  return (
    <Card>
      <h2 className="font-semibold text-base mb-5">
        {initial ? `${initial.vorname} ${initial.nachname} bearbeiten` : 'Neuen Mitarbeiter anlegen'}
      </h2>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-5">
          <Input label="Vorname" value={form.vorname} onChange={f('vorname')} required autoFocus={!initial} />
          <Input label="Nachname" value={form.nachname} onChange={f('nachname')} required />
          <Input label="Position / Rolle" value={form.position} onChange={f('position')} placeholder="z.B. Kellner, Koch …" />
          <Input label="E-Mail" type="email" value={form.email} onChange={f('email')} />
          <Input label="Stundenlohn (€)" type="number" step="0.01" min="0" value={form.stundenlohn} onChange={f('stundenlohn')} placeholder="0.00" />
          <Input label="Soll-Stunden / Monat" type="number" step="0.5" min="0" value={form.monatliche_soll_stunden} onChange={f('monatliche_soll_stunden')} placeholder="160" />
        </div>
        <div className="flex gap-2 justify-end">
          <Button variant="secondary" type="button" onClick={onCancel}>Abbrechen</Button>
          <Button type="submit" loading={loading}>
            {initial ? 'Änderungen speichern' : 'Mitarbeiter anlegen'}
          </Button>
        </div>
      </form>
    </Card>
  )
}
