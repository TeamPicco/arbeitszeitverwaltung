import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { urlaubListe, urlaubEntscheiden } from '../../api/urlaub'
import { Spinner } from '../../components/Spinner'
import { PageHeader } from '../../components/PageHeader'
import { CheckCircle, XCircle, CalendarDays, Filter } from 'lucide-react'

type StatusFilter = 'alle' | 'ausstehend' | 'genehmigt' | 'abgelehnt'

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  ausstehend: { label: 'Ausstehend', color: '#F97316', bg: 'rgba(249,115,22,0.12)' },
  genehmigt:  { label: 'Genehmigt',  color: '#22c55e', bg: 'rgba(34,197,94,0.12)' },
  abgelehnt:  { label: 'Abgelehnt',  color: '#ef4444', bg: 'rgba(239,68,68,0.12)' },
}

export function AdminUrlaub() {
  const qc = useQueryClient()
  const [filter, setFilter] = useState<StatusFilter>('alle')

  const { data, isLoading } = useQuery({
    queryKey: ['urlaub-alle', filter],
    queryFn: () => urlaubListe(filter === 'alle' ? undefined : filter),
  })

  const decide = async (id: number, status: 'genehmigt' | 'abgelehnt') => {
    await urlaubEntscheiden(id, status)
    qc.invalidateQueries({ queryKey: ['urlaub-alle'] })
    qc.invalidateQueries({ queryKey: ['urlaub-offen'] })
    qc.invalidateQueries({ queryKey: ['admin-stats'] })
  }

  const items = (data ?? []) as Record<string, unknown>[]

  return (
    <div>
      <PageHeader
        title="Urlaubsanträge"
        sub={`${items.length} ${filter === 'alle' ? 'Anträge gesamt' : `Anträge (${STATUS_CONFIG[filter]?.label ?? filter})`}`}
        action={
          <div className="flex items-center gap-1 p-1 rounded-lg" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
            <Filter size={13} className="ml-2" style={{ color: 'var(--text-muted)' }} />
            {(['alle', 'ausstehend', 'genehmigt', 'abgelehnt'] as StatusFilter[]).map((s) => (
              <button
                key={s}
                onClick={() => setFilter(s)}
                className="px-3 py-1.5 rounded-md text-sm font-medium transition-all cursor-pointer capitalize"
                style={
                  filter === s
                    ? { background: 'var(--accent)', color: '#fff' }
                    : { color: 'var(--text-muted)' }
                }
              >
                {s === 'alle' ? 'Alle' : STATUS_CONFIG[s]?.label ?? s}
              </button>
            ))}
          </div>
        }
      />

      {isLoading ? (
        <div className="flex justify-center h-40 items-center"><Spinner /></div>
      ) : items.length === 0 ? (
        <div className="flex flex-col items-center py-24 gap-3 rounded-xl"
          style={{ border: '1px dashed var(--border)' }}>
          <CalendarDays size={40} style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
          <p style={{ color: 'var(--text-muted)' }}>Keine Urlaubsanträge vorhanden</p>
        </div>
      ) : (
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)' }}
        >
          {items.map((a, idx) => {
            const ma = a.mitarbeiter as Record<string, string> | undefined
            const s = STATUS_CONFIG[a.status as string] ?? { label: a.status as string, color: '#888', bg: '#1a1a1a' }
            return (
              <div
                key={a.id as number}
                className="flex items-center justify-between px-5 py-4 transition-colors hover:bg-[#141414]"
                style={{
                  borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                  background: idx % 2 === 0 ? 'var(--surface)' : '#0f0f0f',
                }}
              >
                <div className="flex items-center gap-4">
                  {/* Avatar */}
                  <div
                    className="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                    style={{ background: 'var(--surface2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
                  >
                    {ma ? ma.vorname[0] : '?'}
                  </div>

                  <div>
                    <p className="font-semibold">
                      {ma ? `${ma.vorname} ${ma.nachname}` : `Mitarbeiter ${a.mitarbeiter_id}`}
                    </p>
                    <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                      <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
                        {a.datum_von as string} – {a.datum_bis as string}
                      </span>
                      <span
                        className="text-xs px-2 py-0.5 rounded-full"
                        style={{ background: 'var(--surface2)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
                      >
                        {String(a.anzahl_tage)} Tage
                      </span>
                    </div>
                    {typeof a.kommentar === 'string' && a.kommentar && (
                      <p className="text-sm mt-1 italic" style={{ color: 'var(--text-muted)' }}>
                        „{a.kommentar}"
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3 shrink-0">
                  <span
                    className="text-xs font-semibold px-3 py-1.5 rounded-full"
                    style={{ color: s.color, background: s.bg }}
                  >
                    {s.label}
                  </span>
                  {a.status === 'ausstehend' && (
                    <div className="flex gap-2">
                      <button
                        onClick={() => decide(a.id as number, 'genehmigt')}
                        className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer"
                        style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e' }}
                      >
                        <CheckCircle size={14} /> Genehmigen
                      </button>
                      <button
                        onClick={() => decide(a.id as number, 'abgelehnt')}
                        className="flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-lg font-medium transition-all cursor-pointer"
                        style={{ background: 'rgba(239,68,68,0.12)', color: '#ef4444' }}
                      >
                        <XCircle size={14} /> Ablehnen
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
