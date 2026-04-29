import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { api } from '../../api/client'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Spinner } from '../../components/Spinner'
import { Download } from 'lucide-react'

type MA = { id: number; vorname: string; nachname: string }

const now = new Date()

export function AdminLohn() {
  const [selectedMaId, setSelectedMaId] = useState<number | null>(null)
  const [monat, setMonat] = useState(now.getMonth() + 1)
  const [jahr, setJahr] = useState(now.getFullYear())
  const [berechnung, setBerechnung] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const qc = useQueryClient()

  const { data: mitarbeiter } = useQuery<MA[]>({
    queryKey: ['mitarbeiter'],
    queryFn: () => mitarbeiterListe(true),
  })

  const { data: abrechnungen } = useQuery({
    queryKey: ['lohn-liste', selectedMaId],
    queryFn: () =>
      api.get(`/lohn/liste/${selectedMaId}`).then((r) => r.data),
    enabled: !!selectedMaId,
  })

  const berechnen = async () => {
    if (!selectedMaId) return
    setLoading(true)
    setError('')
    setBerechnung(null)
    try {
      const res = await api.post('/lohn/berechnen', {
        mitarbeiter_id: selectedMaId,
        monat,
        jahr,
      })
      setBerechnung(res.data)
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Fehler beim Berechnen.'
      )
    } finally {
      setLoading(false)
    }
  }

  const speichern = async () => {
    if (!selectedMaId) return
    setSaving(true)
    try {
      await api.post('/lohn/speichern', {
        mitarbeiter_id: selectedMaId,
        monat,
        jahr,
      })
      qc.invalidateQueries({ queryKey: ['lohn-liste', selectedMaId] })
      setBerechnung(null)
    } catch (err: unknown) {
      setError(
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
          'Fehler beim Speichern.'
      )
    } finally {
      setSaving(false)
    }
  }

  const downloadPdf = async () => {
    if (!selectedMaId) return
    const res = await api.get(`/lohn/pdf/${selectedMaId}`, {
      params: { monat, jahr },
      responseType: 'blob',
    })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `lohnabrechnung_${selectedMaId}_${jahr}_${String(monat).padStart(2, '0')}.pdf`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">Lohn</h1>

      {/* Filter */}
      <div className="flex gap-3 mb-6 flex-wrap items-end">
        <select
          className="px-3 py-2 rounded-lg text-sm"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          value={selectedMaId ?? ''}
          onChange={(e) => {
            setSelectedMaId(e.target.value ? Number(e.target.value) : null)
            setBerechnung(null)
          }}
        >
          <option value="">Mitarbeiter wählen …</option>
          {(mitarbeiter ?? []).map((ma) => (
            <option key={ma.id} value={ma.id}>
              {ma.nachname} {ma.vorname}
            </option>
          ))}
        </select>

        <select
          className="px-3 py-2 rounded-lg text-sm"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          value={monat}
          onChange={(e) => { setMonat(Number(e.target.value)); setBerechnung(null) }}
        >
          {Array.from({ length: 12 }, (_, i) => (
            <option key={i + 1} value={i + 1}>
              {new Date(2000, i).toLocaleString('de', { month: 'long' })}
            </option>
          ))}
        </select>

        <select
          className="px-3 py-2 rounded-lg text-sm"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          value={jahr}
          onChange={(e) => { setJahr(Number(e.target.value)); setBerechnung(null) }}
        >
          {[2024, 2025, 2026].map((y) => <option key={y} value={y}>{y}</option>)}
        </select>

        <Button onClick={berechnen} loading={loading} disabled={!selectedMaId}>
          Berechnen
        </Button>

        {berechnung && (
          <>
            <Button onClick={speichern} loading={saving} variant="secondary">
              Speichern
            </Button>
            <Button onClick={downloadPdf} variant="secondary">
              <Download size={14} /> PDF
            </Button>
          </>
        )}
      </div>

      {error && (
        <p className="text-sm text-red-400 mb-4">{error}</p>
      )}

      {/* Berechnungsergebnis */}
      {berechnung && (
        <Card className="mb-6">
          <h2 className="font-semibold mb-4">
            Abrechnung {new Date(2000, monat - 1).toLocaleString('de', { month: 'long' })} {jahr}
          </h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
            {Object.entries(berechnung).map(([k, v]) => (
              <div key={k}>
                <p className="text-xs uppercase tracking-wider mb-1" style={{ color: 'var(--text-muted)' }}>
                  {k.replace(/_/g, ' ')}
                </p>
                <p className="font-semibold">{String(v ?? '—')}</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Abrechnungshistorie */}
      {selectedMaId && (
        <section>
          <h2 className="text-base font-semibold mb-3 pb-2"
            style={{ borderBottom: '1px solid var(--border)' }}>
            Gespeicherte Abrechnungen
          </h2>
          {!abrechnungen ? (
            <Spinner />
          ) : abrechnungen.length === 0 ? (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Keine gespeicherten Abrechnungen.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Monat', 'Jahr', 'Stunden', 'Brutto', 'Erstellt'].map((h) => (
                      <th key={h} className="text-left py-2 pr-4 text-xs uppercase tracking-wider font-semibold"
                        style={{ color: 'var(--text-muted)' }}>
                        {h}
                      </th>
                    ))}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {(abrechnungen as Record<string, unknown>[]).map((a) => (
                    <tr key={a.id as number} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td className="py-2 pr-4">
                        {new Date(2000, (a.monat as number) - 1).toLocaleString('de', { month: 'long' })}
                      </td>
                      <td className="py-2 pr-4">{String(a.jahr)}</td>
                      <td className="py-2 pr-4">{String(a.stunden ?? '—')} h</td>
                      <td className="py-2 pr-4">{String(a.brutto ?? '—')} €</td>
                      <td className="py-2 pr-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                        {String(a.erstellt_am ?? '').slice(0, 10)}
                      </td>
                      <td className="py-2">
                        <button
                          onClick={() => {
                            setMonat(a.monat as number)
                            setJahr(a.jahr as number)
                            downloadPdf()
                          }}
                          className="text-xs px-2 py-1 rounded hover:bg-[#1a1a1a] transition-colors cursor-pointer"
                          style={{ color: 'var(--accent)' }}
                        >
                          PDF
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </div>
  )
}
