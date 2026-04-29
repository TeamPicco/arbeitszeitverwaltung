import { useQuery, useQueryClient } from '@tanstack/react-query'
import { dashboardStats } from '../../api/admin'
import { urlaubListe, urlaubEntscheiden } from '../../api/urlaub'
import { MetricCard } from '../../components/Card'
import { Spinner } from '../../components/Spinner'
import { useAuthStore } from '../../store/auth'
import { CheckCircle, XCircle } from 'lucide-react'

export function AdminDashboard() {
  const betriebName = useAuthStore((s) => s.betriebName)
  const qc = useQueryClient()

  const { data: stats, isLoading } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: dashboardStats,
    refetchInterval: 30_000,
  })

  const { data: offeneAntraege } = useQuery({
    queryKey: ['urlaub-offen'],
    queryFn: () => urlaubListe('ausstehend'),
  })

  const decide = async (id: number, status: 'genehmigt' | 'abgelehnt') => {
    await urlaubEntscheiden(id, status)
    qc.invalidateQueries({ queryKey: ['urlaub-offen'] })
    qc.invalidateQueries({ queryKey: ['admin-stats'] })
  }

  if (isLoading)
    return (
      <div className="flex items-center justify-center h-40">
        <Spinner />
      </div>
    )

  return (
    <div className="max-w-5xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold">Dashboard</h1>
        {betriebName && (
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            {betriebName}
          </p>
        )}
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        <MetricCard
          label="Mitarbeiter aktiv"
          value={stats?.anzahl_mitarbeiter ?? '—'}
        />
        <MetricCard
          label="Aktuell eingestempelt"
          value={stats?.aktuell_eingestempelt ?? '—'}
          sub="heute"
        />
        <MetricCard
          label="Offene Urlaubsanträge"
          value={stats?.offene_urlaubsantraege ?? '—'}
        />
      </div>

      {/* Offene Urlaubsanträge */}
      {offeneAntraege && offeneAntraege.length > 0 && (
        <section>
          <h2
            className="text-base font-semibold mb-3 pb-2"
            style={{ borderBottom: '1px solid var(--border)' }}
          >
            Offene Urlaubsanträge
          </h2>
          <div className="flex flex-col gap-2">
            {(offeneAntraege as Record<string, unknown>[]).map((a) => {
              const ma = a.mitarbeiter as Record<string, string> | undefined
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
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => decide(a.id as number, 'genehmigt')}
                      className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-green-900/20 text-green-400 hover:bg-green-900/40 transition-colors cursor-pointer"
                    >
                      <CheckCircle size={13} /> Genehmigen
                    </button>
                    <button
                      onClick={() => decide(a.id as number, 'abgelehnt')}
                      className="flex items-center gap-1 text-xs px-3 py-1.5 rounded-lg bg-red-900/20 text-red-400 hover:bg-red-900/40 transition-colors cursor-pointer"
                    >
                      <XCircle size={13} /> Ablehnen
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        </section>
      )}
    </div>
  )
}
