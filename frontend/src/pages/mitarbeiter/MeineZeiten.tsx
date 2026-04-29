import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { zeitenMonat } from '../../api/zeiten'
import { useAuthStore } from '../../store/auth'
import { Spinner } from '../../components/Spinner'

type Eintrag = {
  id: number
  datum: string
  start_zeit?: string
  ende_zeit?: string
  pause_minuten?: number
  arbeitsstunden?: number
  quelle?: string
}

const now = new Date()

export function MeineZeiten() {
  const { mitarbeiterId } = useAuthStore()
  const [monat, setMonat] = useState(now.getMonth() + 1)
  const [jahr, setJahr] = useState(now.getFullYear())

  const { data, isLoading } = useQuery({
    queryKey: ['meine-zeiten', mitarbeiterId, monat, jahr],
    queryFn: () => zeitenMonat(mitarbeiterId!, monat, jahr),
    enabled: !!mitarbeiterId,
  })

  const total = ((data ?? []) as Eintrag[])
    .reduce((s, e) => s + (e.arbeitsstunden ?? 0), 0)
    .toFixed(2)

  return (
    <div className="max-w-3xl">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h1 className="text-2xl font-bold">Meine Zeiten</h1>
        <div className="flex gap-2">
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
            {[2024, 2025, 2026].map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>

      {isLoading ? (
        <div className="flex justify-center h-20 items-center"><Spinner /></div>
      ) : (
        <>
          <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
            Gesamt: <span className="font-semibold" style={{ color: 'var(--accent)' }}>{total} h</span>
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {['Datum', 'Start', 'Ende', 'Pause', 'Stunden'].map((h) => (
                    <th
                      key={h}
                      className="text-left py-2 pr-4 font-semibold text-xs uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {((data ?? []) as Eintrag[]).map((e) => (
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
                  </tr>
                ))}
                {(!data || data.length === 0) && (
                  <tr>
                    <td colSpan={5} className="py-6 text-center text-sm" style={{ color: 'var(--text-muted)' }}>
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
