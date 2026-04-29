import { useQuery, useQueryClient } from '@tanstack/react-query'
import { urlaubListe, urlaubEntscheiden } from '../../api/urlaub'
import { Spinner } from '../../components/Spinner'
import { CheckCircle, XCircle } from 'lucide-react'

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  ausstehend: { label: 'Ausstehend', color: '#F97316' },
  genehmigt: { label: 'Genehmigt', color: '#22c55e' },
  abgelehnt: { label: 'Abgelehnt', color: '#ef4444' },
}

export function AdminUrlaub() {
  const qc = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ['urlaub-alle'],
    queryFn: () => urlaubListe(),
  })

  const decide = async (id: number, status: 'genehmigt' | 'abgelehnt') => {
    await urlaubEntscheiden(id, status)
    qc.invalidateQueries({ queryKey: ['urlaub-alle'] })
  }

  if (isLoading)
    return <div className="flex justify-center h-40 items-center"><Spinner /></div>

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">Urlaubsanträge</h1>

      <div className="flex flex-col gap-2">
        {((data ?? []) as Record<string, unknown>[]).map((a) => {
          const ma = a.mitarbeiter as Record<string, string> | undefined
          const s = STATUS_LABEL[a.status as string] ?? { label: a.status as string, color: '#888' }
          return (
            <div
              key={a.id as number}
              className="flex items-center justify-between px-4 py-3 rounded-xl"
              style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
            >
              <div>
                <p className="font-medium text-sm">
                  {ma ? `${ma.vorname} ${ma.nachname}` : `MA ${a.mitarbeiter_id}`}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  {a.datum_von as string} – {a.datum_bis as string} · {String(a.anzahl_tage)} Tage
                </p>
                {typeof a.kommentar === 'string' && a.kommentar && (
                  <p className="text-xs mt-1 italic" style={{ color: 'var(--text-muted)' }}>
                    {a.kommentar}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <span
                  className="text-xs font-medium px-2 py-1 rounded-full"
                  style={{ color: s.color, background: s.color + '20' }}
                >
                  {s.label}
                </span>
                {a.status === 'ausstehend' && (
                  <div className="flex gap-2">
                    <button
                      onClick={() => decide(a.id as number, 'genehmigt')}
                      className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-green-900/20 text-green-400 hover:bg-green-900/40 transition-colors cursor-pointer"
                    >
                      <CheckCircle size={13} /> OK
                    </button>
                    <button
                      onClick={() => decide(a.id as number, 'abgelehnt')}
                      className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-red-900/20 text-red-400 hover:bg-red-900/40 transition-colors cursor-pointer"
                    >
                      <XCircle size={13} /> Ablehnen
                    </button>
                  </div>
                )}
              </div>
            </div>
          )
        })}
        {(!data || data.length === 0) && (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Keine Urlaubsanträge vorhanden.
          </p>
        )}
      </div>
    </div>
  )
}
