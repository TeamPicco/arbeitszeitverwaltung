import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { zeitenMonat, azkMonat } from '../../api/zeiten'
import { Spinner } from '../../components/Spinner'
import { Card } from '../../components/Card'

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

export function AdminZeiten() {
  const [selectedMaId, setSelectedMaId] = useState<number | null>(null)
  const [monat, setMonat] = useState(now.getMonth() + 1)
  const [jahr, setJahr] = useState(now.getFullYear())

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

  const gesamtStunden = ((zeiten ?? []) as Eintrag[])
    .reduce((s, e) => s + (e.arbeitsstunden ?? 0), 0)
    .toFixed(2)

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">Zeiterfassung</h1>

      {/* Filter */}
      <div className="flex gap-3 mb-6 flex-wrap">
        <select
          className="px-3 py-2 rounded-lg text-sm"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          value={selectedMaId ?? ''}
          onChange={(e) => setSelectedMaId(e.target.value ? Number(e.target.value) : null)}
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
          onChange={(e) => setMonat(Number(e.target.value))}
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
          onChange={(e) => setJahr(Number(e.target.value))}
        >
          {[2024, 2025, 2026].map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {!selectedMaId && (
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Mitarbeiter auswählen, um Zeiten anzuzeigen.
        </p>
      )}

      {selectedMaId && zeitenLoading && (
        <div className="flex justify-center h-20 items-center"><Spinner /></div>
      )}

      {selectedMaId && !zeitenLoading && (
        <>
          {/* AZK Summary */}
          {azk && (
            <Card className="mb-4">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-sm">
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Ist-Stunden</p>
                  <p className="font-semibold">{gesamtStunden} h</p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Soll-Stunden</p>
                  <p className="font-semibold">{azk.soll_stunden?.toFixed(2) ?? '—'} h</p>
                </div>
                <div>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Saldo</p>
                  <p className={`font-semibold ${(azk.saldo ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {(azk.saldo ?? 0) >= 0 ? '+' : ''}{azk.saldo?.toFixed(2) ?? '—'} h
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Table */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Datum', 'Start', 'Ende', 'Pause', 'Stunden', 'Quelle'].map((h) => (
                    <th key={h} className="text-left py-2 pr-4 font-semibold text-xs uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}>
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {((zeiten ?? []) as Eintrag[]).map((e) => (
                  <tr
                    key={e.id}
                    style={{ borderBottom: '1px solid var(--border)' }}
                    className="hover:bg-[#111] transition-colors"
                  >
                    <td className="py-2 pr-4">{e.datum}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{e.start_zeit ?? '–'}</td>
                    <td className="py-2 pr-4 font-mono text-xs">{e.ende_zeit ?? '–'}</td>
                    <td className="py-2 pr-4">{e.pause_minuten ?? 0} min</td>
                    <td className="py-2 pr-4">{e.arbeitsstunden?.toFixed(2) ?? '–'} h</td>
                    <td className="py-2 pr-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {e.quelle ?? '–'}
                    </td>
                  </tr>
                ))}
                {(!zeiten || zeiten.length === 0) && (
                  <tr>
                    <td colSpan={6} className="py-6 text-center text-sm"
                      style={{ color: 'var(--text-muted)' }}>
                      Keine Einträge für diesen Zeitraum.
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
