import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { urlaubMitarbeiter, urlaubSaldo, urlaubBeantragen } from '../../api/urlaub'
import { useAuthStore } from '../../store/auth'
import { Card, MetricCard } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Spinner } from '../../components/Spinner'

const STATUS_MAP: Record<string, { label: string; color: string }> = {
  ausstehend: { label: 'Ausstehend', color: '#F97316' },
  genehmigt: { label: 'Genehmigt', color: '#22c55e' },
  abgelehnt: { label: 'Abgelehnt', color: '#ef4444' },
}

export function MeinUrlaub() {
  const { mitarbeiterId } = useAuthStore()
  const qc = useQueryClient()
  const jahr = new Date().getFullYear()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ datum_von: '', datum_bis: '', kommentar: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const { data: saldo } = useQuery({
    queryKey: ['urlaub-saldo', mitarbeiterId, jahr],
    queryFn: () => urlaubSaldo(mitarbeiterId!, jahr),
    enabled: !!mitarbeiterId,
  })

  const { data: antraege, isLoading } = useQuery({
    queryKey: ['urlaub-liste', mitarbeiterId],
    queryFn: () => urlaubMitarbeiter(mitarbeiterId!),
    enabled: !!mitarbeiterId,
  })

  const berechneArbeitstage = (von: string, bis: string): number => {
    if (!von || !bis) return 0
    const start = new Date(von)
    const end = new Date(bis)
    let count = 0
    const d = new Date(start)
    while (d <= end) {
      if (d.getDay() !== 0 && d.getDay() !== 6) count++
      d.setDate(d.getDate() + 1)
    }
    return count
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    const anzahl_tage = berechneArbeitstage(form.datum_von, form.datum_bis)
    if (anzahl_tage <= 0) {
      setError('Ungültige Datumsauswahl.')
      return
    }
    setLoading(true)
    try {
      await urlaubBeantragen({
        mitarbeiter_id: mitarbeiterId!,
        datum_von: form.datum_von,
        datum_bis: form.datum_bis,
        anzahl_tage,
        kommentar: form.kommentar || undefined,
      })
      qc.invalidateQueries({ queryKey: ['urlaub-liste', mitarbeiterId] })
      qc.invalidateQueries({ queryKey: ['urlaub-saldo', mitarbeiterId, jahr] })
      setForm({ datum_von: '', datum_bis: '', kommentar: '' })
      setShowForm(false)
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Fehler beim Antrag.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Mein Urlaub</h1>
        <Button onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Abbrechen' : '+ Antrag stellen'}
        </Button>
      </div>

      {saldo && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <MetricCard label="Anspruch" value={`${saldo.anspruch_tage ?? '—'} T`} />
          <MetricCard label="Genommen" value={`${saldo.genommene_tage ?? '—'} T`} />
          <MetricCard label="Rest" value={`${saldo.rest_tage ?? '—'} T`} sub={`${jahr}`} />
        </div>
      )}

      {showForm && (
        <Card className="mb-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-3">
            <h2 className="font-semibold mb-2">Urlaubsantrag stellen</h2>
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
            {form.datum_von && form.datum_bis && (
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {berechneArbeitstage(form.datum_von, form.datum_bis)} Arbeitstage
              </p>
            )}
            <Input
              label="Kommentar (optional)"
              value={form.kommentar}
              onChange={(e) => setForm((p) => ({ ...p, kommentar: e.target.value }))}
            />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button type="submit" loading={loading}>Antrag einreichen</Button>
          </form>
        </Card>
      )}

      {isLoading ? (
        <Spinner />
      ) : (
        <div className="flex flex-col gap-2">
          {((antraege ?? []) as Record<string, unknown>[]).map((a) => {
            const s = STATUS_MAP[a.status as string] ?? { label: a.status as string, color: '#888' }
            return (
              <div
                key={a.id as number}
                className="flex items-center justify-between px-4 py-3 rounded-xl"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <div>
                  <p className="text-sm font-medium">
                    {a.datum_von as string} – {a.datum_bis as string}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                    {String(a.anzahl_tage)} Tage
                    {a.kommentar ? ` · ${a.kommentar as string}` : ''}
                  </p>
                </div>
                <span
                  className="text-xs font-medium px-2 py-1 rounded-full"
                  style={{ color: s.color, background: s.color + '20' }}
                >
                  {s.label}
                </span>
              </div>
            )
          })}
          {(!antraege || antraege.length === 0) && (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Noch keine Urlaubsanträge.
            </p>
          )}
        </div>
      )}
    </div>
  )
}
