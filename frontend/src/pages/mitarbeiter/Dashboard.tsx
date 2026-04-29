import { useQuery } from '@tanstack/react-query'
import { stempelStatus } from '../../api/stempel'
import { urlaubMitarbeiter, urlaubSaldo } from '../../api/urlaub'
import { zeitenMonat } from '../../api/zeiten'
import { useAuthStore } from '../../store/auth'
import { Card, MetricCard } from '../../components/Card'
import { Spinner } from '../../components/Spinner'
import { Clock, CalendarDays, CheckCircle, XCircle, Hourglass, TrendingUp } from 'lucide-react'

const MONTHS_DE = ['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
const DAYS_DE = ['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag']

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; color: string; bg: string; icon: React.ReactNode }> = {
    ausstehend: { label: 'Ausstehend', color: '#F97316', bg: 'rgba(249,115,22,0.12)', icon: <Hourglass size={12} /> },
    genehmigt:  { label: 'Genehmigt',  color: '#22c55e', bg: 'rgba(34,197,94,0.12)',  icon: <CheckCircle size={12} /> },
    abgelehnt:  { label: 'Abgelehnt',  color: '#ef4444', bg: 'rgba(239,68,68,0.12)',  icon: <XCircle size={12} /> },
  }
  const s = map[status] ?? { label: status, color: '#888', bg: '#1a1a1a', icon: null }
  return (
    <span
      className="inline-flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full"
      style={{ color: s.color, background: s.bg }}
    >
      {s.icon} {s.label}
    </span>
  )
}

export function MitarbeiterDashboard() {
  const { mitarbeiterId } = useAuthStore()
  const now = new Date()
  const jahr = now.getFullYear()
  const monat = now.getMonth() + 1

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

  const { data: zeiten } = useQuery({
    queryKey: ['zeiten', mitarbeiterId, monat, jahr],
    queryFn: () => zeitenMonat(mitarbeiterId!, monat, jahr),
    enabled: !!mitarbeiterId,
  })

  const gesamtStunden = ((zeiten ?? []) as { arbeitsstunden?: number }[])
    .reduce((s, e) => s + (e.arbeitsstunden ?? 0), 0)
    .toFixed(1)

  const statusText = status?.eingestempelt
    ? status.pause_aktiv ? 'Pause' : 'Eingestempelt'
    : 'Ausgestempelt'
  const statusColor = status?.eingestempelt
    ? status.pause_aktiv ? '#f59e0b' : '#22c55e'
    : 'var(--text-muted)'

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-sm mb-1" style={{ color: 'var(--text-muted)' }}>
          {DAYS_DE[now.getDay()]}, {now.getDate()}. {MONTHS_DE[now.getMonth()]} {now.getFullYear()}
        </p>
        <h1 className="text-3xl font-bold">Mein Bereich</h1>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
        {/* Status */}
        <div
          className="rounded-xl p-5"
          style={{
            background: 'var(--surface)',
            border: '1px solid var(--border)',
            borderLeft: '3px solid var(--accent)',
          }}
        >
          <div className="flex items-center gap-3 mb-2">
            <Clock size={18} style={{ color: statusColor }} />
            <p className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              Status heute
            </p>
          </div>
          <p className="text-2xl font-bold" style={{ color: statusColor }}>
            {status ? statusText : <Spinner size={20} />}
          </p>
        </div>

        <MetricCard
          label={`Resturlaub ${jahr}`}
          value={saldo?.rest_tage !== undefined ? `${saldo.rest_tage} T` : '—'}
          icon={<CalendarDays size={18} />}
          sub={saldo ? `Genommen: ${saldo.genommene_tage} · Anspruch: ${saldo.anspruch_tage}` : undefined}
        />

        <MetricCard
          label={`Stunden ${MONTHS_DE[monat - 1]}`}
          value={`${gesamtStunden} h`}
          icon={<TrendingUp size={18} />}
          sub="Gearbeitete Stunden diesen Monat"
        />
      </div>

      {/* Urlaubsanträge */}
      <Card>
        <div className="flex items-center justify-between mb-4 pb-3"
          style={{ borderBottom: '1px solid var(--border)' }}>
          <h2 className="font-semibold">Meine Urlaubsanträge</h2>
          {antraege && antraege.length > 0 && (
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {antraege.length} Anträge
            </span>
          )}
        </div>

        {!antraege ? (
          <div className="flex justify-center py-6"><Spinner /></div>
        ) : antraege.length === 0 ? (
          <div className="flex flex-col items-center py-10 gap-2">
            <CalendarDays size={32} style={{ color: 'var(--text-muted)', opacity: 0.3 }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Noch keine Urlaubsanträge gestellt</p>
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {(antraege as Record<string, unknown>[]).map((a) => (
              <div
                key={a.id as number}
                className="flex items-center justify-between px-4 py-3.5 rounded-xl"
                style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
              >
                <div className="flex items-center gap-3">
                  <CalendarDays size={16} style={{ color: 'var(--text-muted)' }} />
                  <div>
                    <p className="font-medium">
                      {a.datum_von as string} – {a.datum_bis as string}
                    </p>
                    <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {String(a.anzahl_tage)} Tage
                      {typeof a.kommentar === 'string' && a.kommentar ? ` · „${a.kommentar}"` : ''}
                    </p>
                  </div>
                </div>
                <StatusBadge status={a.status as string} />
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
