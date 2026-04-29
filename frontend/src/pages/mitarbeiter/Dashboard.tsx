import { useQuery } from '@tanstack/react-query'
import { stempelStatus } from '../../api/stempel'
import { urlaubMitarbeiter, urlaubSaldo } from '../../api/urlaub'
import { useAuthStore } from '../../store/auth'
import { Card, MetricCard } from '../../components/Card'
import { Spinner } from '../../components/Spinner'
import { Clock, CalendarDays } from 'lucide-react'

export function MitarbeiterDashboard() {
  const { mitarbeiterId } = useAuthStore()
  const now = new Date()
  const jahr = now.getFullYear()

  const { data: status } = useQuery({
    queryKey: ['stempel-status', mitarbeiterId],
    queryFn: () => stempelStatus(mitarbeiterId!),
    enabled: !!mitarbeiterId,
    refetchInterval: 30_000,
  })

  const { data: saldo } = useQuery({
    queryKey: ['urlaub-saldo', mitarbeiterId, jahr],
    queryFn: () => urlaubSaldo(mitarbeiterId!, jahr),
    enabled: !!mitarbeiterId,
  })

  const { data: antraege } = useQuery({
    queryKey: ['urlaub-liste', mitarbeiterId],
    queryFn: () => urlaubMitarbeiter(mitarbeiterId!),
    enabled: !!mitarbeiterId,
  })

  return (
    <div className="max-w-3xl">
      <h1 className="text-2xl font-bold mb-6">Mein Bereich</h1>

      {/* Status */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
        <Card accent className="flex items-center gap-4">
          <Clock size={28} style={{ color: 'var(--accent)' }} />
          <div>
            <p className="text-xs uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              Status heute
            </p>
            {status ? (
              <p className="font-semibold">
                {status.eingestempelt
                  ? status.pause_aktiv
                    ? 'Pause'
                    : 'Eingestempelt'
                  : 'Ausgestempelt'}
              </p>
            ) : (
              <Spinner size={16} />
            )}
          </div>
        </Card>

        <MetricCard
          label={`Resturlaub ${jahr}`}
          value={saldo?.rest_tage !== undefined ? `${saldo.rest_tage} Tage` : '—'}
          sub={`Genommen: ${saldo?.genommene_tage ?? '—'} / Anspruch: ${saldo?.anspruch_tage ?? '—'}`}
        />
      </div>

      {/* Letzte Anträge */}
      <section>
        <h2
          className="text-base font-semibold mb-3 pb-2"
          style={{ borderBottom: '1px solid var(--border)' }}
        >
          Meine Urlaubsanträge
        </h2>
        {!antraege ? (
          <Spinner />
        ) : antraege.length === 0 ? (
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Keine Anträge vorhanden.
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {(antraege as Record<string, unknown>[]).slice(0, 5).map((a) => (
              <div
                key={a.id as number}
                className="flex items-center justify-between px-4 py-3 rounded-xl"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <div className="flex items-center gap-3">
                  <CalendarDays size={15} style={{ color: 'var(--text-muted)' }} />
                  <div>
                    <p className="text-sm font-medium">
                      {a.datum_von as string} – {a.datum_bis as string}
                    </p>
                    <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                      {String(a.anzahl_tage)} Tage
                    </p>
                  </div>
                </div>
                <StatusBadge status={a.status as string} />
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string }> = {
    ausstehend: { label: 'Ausstehend', color: '#F97316' },
    genehmigt: { label: 'Genehmigt', color: '#22c55e' },
    abgelehnt: { label: 'Abgelehnt', color: '#ef4444' },
  }
  const s = map[status] ?? { label: status, color: '#888' }
  return (
    <span
      className="text-xs font-medium px-2 py-1 rounded-full"
      style={{ color: s.color, background: s.color + '20' }}
    >
      {s.label}
    </span>
  )
}
