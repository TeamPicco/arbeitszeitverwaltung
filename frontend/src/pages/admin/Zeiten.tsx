import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { zeitenMonat, azkMonat } from '../../api/zeiten'
import { api } from '../../api/client'
import { Spinner } from '../../components/Spinner'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { PageHeader } from '../../components/PageHeader'
import { Clock, TrendingUp, TrendingDown, Minus, Trash2, Plus } from 'lucide-react'

type MA = { id: number; vorname: string; nachname: string }
type Eintrag = {
  id: number
  datum: string
  start_zeit?: string
  ende_zeit?: string
  pause_minuten?: number
  arbeitsstunden?: number
  quelle?: string
  ist_krank?: boolean
}

const now = new Date()
const MONATE = Array.from({ length: 12 }, (_, i) =>
  new Date(2000, i).toLocaleString('de', { month: 'long' })
)

export function AdminZeiten() {
  const qc = useQueryClient()
  const [selectedMaId, setSelectedMaId] = useState<number | null>(null)
  const [monat, setMonat] = useState(now.getMonth() + 1)
  const [jahr, setJahr] = useState(now.getFullYear())
  const [showManuell, setShowManuell] = useState(false)

  const { data: mitarbeiter } = useQuery<MA[]>({
    queryKey: ['mitarbeiter'],
    queryFn: () => mitarbeiterListe(true),
  })

  const { data: zeiten, isLoading: zeitenLoading } = useQuery({
    queryKey: ['zeiten', selectedMaId, monat, jahr],
    queryFn: () => zeitenMonat(selectedMaId!, monat, jahr),
    enabled: !!selectedMaId,
  })

  const { data: azk } = useQuery({
    queryKey: ['azk', selectedMaId, monat, jahr],
    queryFn: () => azkMonat(selectedMaId!, monat, jahr),
    enabled: !!selectedMaId,
  })

  const handleDelete = async (id: number) => {
    await api.delete(`/zeiten/${id}`)
    qc.invalidateQueries({ queryKey: ['zeiten', selectedMaId, monat, jahr] })
    qc.invalidateQueries({ queryKey: ['azk', selectedMaId, monat, jahr] })
  }

  const gesamtStunden = ((zeiten ?? []) as Eintrag[])
    .reduce((s, e) => s + (e.arbeitsstunden ?? 0), 0)
    .toFixed(2)

  const saldo = azk?.saldo ?? 0

  const selectStyle = {
    background: 'var(--surface)',
    border: '1px solid var(--border)',
    color: 'var(--text)',
  }

  const selectedMa = (mitarbeiter ?? []).find((m) => m.id === selectedMaId)

  return (
    <div>
      <PageHeader
        title="Zeiterfassung"
        sub={selectedMa ? `${selectedMa.vorname} ${selectedMa.nachname} · ${MONATE[monat - 1]} ${jahr}` : 'Mitarbeiter und Monat auswählen'}
        action={
          selectedMaId ? (
            <Button variant="secondary" onClick={() => setShowManuell(!showManuell)}>
              <Plus size={15} /> Manueller Eintrag
            </Button>
          ) : undefined
        }
      />

      {/* Filter row */}
      <div className="flex gap-3 mb-6 flex-wrap items-center">
        <select
          className="px-3.5 py-2.5 rounded-lg text-sm"
          style={selectStyle}
          value={selectedMaId ?? ''}
          onChange={(e) => setSelectedMaId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">— Mitarbeiter wählen —</option>
          {(mitarbeiter ?? []).map((ma) => (
            <option key={ma.id} value={ma.id}>{ma.nachname}, {ma.vorname}</option>
          ))}
        </select>

        <select
          className="px-3.5 py-2.5 rounded-lg text-sm"
          style={selectStyle}
          value={monat}
          onChange={(e) => setMonat(Number(e.target.value))}
        >
          {MONATE.map((m, i) => (
            <option key={i + 1} value={i + 1}>{m}</option>
          ))}
        </select>

        <select
          className="px-3.5 py-2.5 rounded-lg text-sm"
          style={selectStyle}
          value={jahr}
          onChange={(e) => setJahr(Number(e.target.value))}
        >
          {[2024, 2025, 2026, 2027].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {/* Empty state */}
      {!selectedMaId && (
        <div className="flex flex-col items-center py-24 gap-3 rounded-xl"
          style={{ border: '1px dashed var(--border)' }}>
          <Clock size={40} style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
          <p style={{ color: 'var(--text-muted)' }}>Mitarbeiter auswählen, um Zeiten anzuzeigen</p>
        </div>
      )}

      {selectedMaId && zeitenLoading && (
        <div className="flex justify-center h-20 items-center"><Spinner /></div>
      )}

      {selectedMaId && !zeitenLoading && (
        <>
          {/* AZK Cards */}
          {azk && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-6">
              {[
                { label: 'Ist-Stunden', value: `${gesamtStunden} h` },
                { label: 'Soll-Stunden', value: `${azk.soll_stunden?.toFixed(2) ?? '—'} h` },
                {
                  label: 'Saldo',
                  value: `${saldo >= 0 ? '+' : ''}${saldo.toFixed(2)} h`,
                  color: saldo >= 0 ? 'var(--success)' : 'var(--danger)',
                  icon: saldo > 0 ? <TrendingUp size={15} /> : saldo < 0 ? <TrendingDown size={15} /> : <Minus size={15} />,
                },
                { label: 'Einträge', value: String((zeiten ?? []).length) },
              ].map((item) => (
                <Card key={item.label} padding="p-4">
                  <p className="text-xs uppercase tracking-wider mb-1.5" style={{ color: 'var(--text-muted)' }}>
                    {item.label}
                  </p>
                  <p className="text-xl font-bold flex items-center gap-1"
                    style={{ color: item.color ?? 'var(--text)' }}>
                    {item.icon}{item.value}
                  </p>
                </Card>
              ))}
            </div>
          )}

          {/* Manueller Eintrag Form */}
          {showManuell && selectedMaId && (
            <ManuellForm
              mitarbeiterId={selectedMaId}
              monat={monat}
              jahr={jahr}
              onSaved={() => {
                qc.invalidateQueries({ queryKey: ['zeiten', selectedMaId, monat, jahr] })
                qc.invalidateQueries({ queryKey: ['azk', selectedMaId, monat, jahr] })
                setShowManuell(false)
              }}
              onCancel={() => setShowManuell(false)}
            />
          )}

          {/* Table */}
          <div
            className="rounded-xl overflow-hidden"
            style={{ border: '1px solid var(--border)' }}
          >
            <table className="w-full">
              <thead>
                <tr style={{ background: '#FFFFFF', borderBottom: '1px solid var(--border)' }}>
                  {['Datum', 'Start', 'Ende', 'Pause', 'Stunden', 'Quelle', ''].map((h) => (
                    <th
                      key={h}
                      className="text-left px-4 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {((zeiten ?? []) as Eintrag[]).map((e, idx) => (
                  <tr
                    key={e.id}
                    className="hover:bg-[#F5F5F5] transition-colors"
                    style={{
                      borderTop: '1px solid var(--border)',
                      background: idx % 2 === 0 ? 'var(--surface)' : '#F2F2F2',
                    }}
                  >
                    <td className="px-4 py-3 font-medium">{e.datum}</td>
                    <td className="px-4 py-3 font-mono text-sm">{e.start_zeit ?? '—'}</td>
                    <td className="px-4 py-3 font-mono text-sm">{e.ende_zeit ?? '—'}</td>
                    <td className="px-4 py-3 text-sm" style={{ color: 'var(--text-muted)' }}>
                      {e.pause_minuten ? `${e.pause_minuten} min` : '—'}
                    </td>
                    <td className="px-4 py-3 font-semibold">
                      {e.arbeitsstunden?.toFixed(2) ?? '—'} h
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className="text-xs px-2 py-0.5 rounded-full"
                        style={{
                          background: 'var(--surface2)',
                          color: 'var(--text-muted)',
                          border: '1px solid var(--border)',
                        }}
                      >
                        {e.quelle ?? '—'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleDelete(e.id)}
                        className="p-1.5 rounded-lg hover:bg-red-900/20 transition-colors cursor-pointer"
                        style={{ color: '#777' }}
                        title="Löschen"
                      >
                        <Trash2 size={14} />
                      </button>
                    </td>
                  </tr>
                ))}
                {(!zeiten || zeiten.length === 0) && (
                  <tr>
                    <td colSpan={7} className="py-12 text-center text-sm"
                      style={{ color: 'var(--text-muted)', background: 'var(--surface)' }}>
                      Keine Zeiteinträge für diesen Zeitraum gefunden.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}

function ManuellForm({
  mitarbeiterId,
  monat,
  jahr,
  onSaved,
  onCancel,
}: {
  mitarbeiterId: number
  monat: number
  jahr: number
  onSaved: () => void
  onCancel: () => void
}) {
  const lastDay = new Date(jahr, monat, 0).getDate()
  const defaultDate = `${jahr}-${String(monat).padStart(2,'0')}-01`
  const [form, setForm] = useState({
    datum: defaultDate,
    start_zeit: '09:00',
    ende_zeit: '17:00',
    pause_minuten: '30',
    kommentar: '',
  })
  const [loading, setLoading] = useState(false)

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  const handleSubmit = async (ev: React.FormEvent) => {
    ev.preventDefault()
    setLoading(true)
    try {
      await api.post('/zeiten/manuell', {
        mitarbeiter_id: mitarbeiterId,
        datum: form.datum,
        start_zeit: form.start_zeit,
        ende_zeit: form.ende_zeit,
        pause_minuten: Number(form.pause_minuten) || 0,
        kommentar: form.kommentar || undefined,
      })
      onSaved()
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card className="mb-5">
      <h3 className="font-semibold mb-4">Manuellen Eintrag hinzufügen</h3>
      <form onSubmit={handleSubmit}>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-4">
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Datum</label>
            <input
              type="date"
              value={form.datum}
              min={`${jahr}-${String(monat).padStart(2,'0')}-01`}
              max={`${jahr}-${String(monat).padStart(2,'0')}-${String(lastDay).padStart(2,'0')}`}
              onChange={f('datum')}
              required
              className="px-3.5 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Start</label>
            <input type="time" value={form.start_zeit} onChange={f('start_zeit')} required
              className="px-3.5 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Ende</label>
            <input type="time" value={form.ende_zeit} onChange={f('ende_zeit')} required
              className="px-3.5 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          </div>
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium">Pause (Min)</label>
            <input type="number" value={form.pause_minuten} onChange={f('pause_minuten')} min="0"
              className="px-3.5 py-2.5 rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }} />
          </div>
        </div>
        <div className="flex gap-2">
          <Button type="submit" loading={loading}>Eintrag speichern</Button>
          <Button type="button" variant="secondary" onClick={onCancel}>Abbrechen</Button>
        </div>
      </form>
    </Card>
  )
}
