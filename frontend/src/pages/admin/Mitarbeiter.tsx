import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe, mitarbeiterAnlegen, mitarbeiterAktualisieren } from '../../api/mitarbeiter'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Spinner } from '../../components/Spinner'
import { UserPlus, Pencil, UserX } from 'lucide-react'

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

  const { data: mitarbeiter, isLoading } = useQuery<Mitarbeiter[]>({
    queryKey: ['mitarbeiter'],
    queryFn: () => mitarbeiterListe(true),
  })

  const handleDeactivate = async (id: number) => {
    await mitarbeiterAktualisieren(id, { aktiv: false })
    qc.invalidateQueries({ queryKey: ['mitarbeiter'] })
  }

  if (isLoading)
    return <div className="flex justify-center h-40 items-center"><Spinner /></div>

  return (
    <div className="max-w-4xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Mitarbeiter</h1>
        <Button onClick={() => { setEditing(null); setShowForm(true) }}>
          <UserPlus size={15} /> Hinzufügen
        </Button>
      </div>

      {(showForm || editing) && (
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
      )}

      <div className="flex flex-col gap-2">
        {(mitarbeiter ?? []).map((ma) => (
          <div
            key={ma.id}
            className="flex items-center justify-between px-4 py-3 rounded-xl"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
          >
            <div>
              <p className="font-medium">{ma.vorname} {ma.nachname}</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {ma.position ?? 'Keine Position'} · {ma.email ?? '–'}
              </p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                className="h-8 px-3 text-xs"
                onClick={() => { setEditing(ma); setShowForm(false) }}
              >
                <Pencil size={13} />
              </Button>
              <Button
                variant="danger"
                className="h-8 px-3 text-xs"
                onClick={() => handleDeactivate(ma.id)}
              >
                <UserX size={13} />
              </Button>
            </div>
          </div>
        ))}
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
    <Card className="mb-4">
      <h2 className="font-semibold mb-4">{initial ? 'Bearbeiten' : 'Neuer Mitarbeiter'}</h2>
      <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-3">
        <Input label="Vorname" value={form.vorname} onChange={f('vorname')} required />
        <Input label="Nachname" value={form.nachname} onChange={f('nachname')} required />
        <Input label="Position" value={form.position} onChange={f('position')} />
        <Input label="E-Mail" type="email" value={form.email} onChange={f('email')} />
        <Input label="Stundenlohn (€)" type="number" step="0.01" value={form.stundenlohn} onChange={f('stundenlohn')} />
        <Input label="Soll-Stunden/Monat" type="number" step="0.5" value={form.monatliche_soll_stunden} onChange={f('monatliche_soll_stunden')} />
        <div className="col-span-2 flex gap-2 justify-end mt-2">
          <Button variant="secondary" type="button" onClick={onCancel}>Abbrechen</Button>
          <Button type="submit" loading={loading}>Speichern</Button>
        </div>
      </form>
    </Card>
  )
}
