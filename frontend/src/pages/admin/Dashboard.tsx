import { useQuery, useQueryClient } from '@tanstack/react-query'
import { dashboardStats } from '../../api/admin'
import { urlaubListe, urlaubEntscheiden } from '../../api/urlaub'
import { MetricCard, SectionHeader } from '../../components/Card'
import { Spinner } from '../../components/Spinner'
import { useAuthStore } from '../../store/auth'
import { CheckCircle, XCircle, Users, Clock, CalendarDays, TrendingUp } from 'lucide-react'

const MONTHS_DE = ['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember']
const DAYS_DE = ['Sonntag','Montag','Dienstag','Mittwoch','Donnerstag','Freitag','Samstag']

export function AdminDashboard() {
  const betriebName = useAuthStore((s) => s.betriebName)
  const qc = useQueryClient()
  const now = new Date()

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

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <p className="text-xs font-medium mb-1.5" style={{ color: 'var(--text-muted)' }}>
          {DAYS_DE[now.getDay()]}, {now.getDate()}. {MONTHS_DE[now.getMonth()]} {now.getFullYear()}
        </p>
        <h1 className="font-bold tracking-tight" style={{ fontSize: '1.75rem', lineHeight: 1.2 }}>
          Guten {now.getHours() < 12 ? 'Morgen' : now.getHours() < 18 ? 'Tag' : 'Abend'}
          {betriebName ? `, ${betriebName}` : ''}
        </h1>
        <p className="text-sm mt-1.5" style={{ color: 'var(--text-muted)' }}>
          Tagesaktuelle Übersicht
        </p>
      </div>

      {/* Metrics */}
      {isLoading ? (
        <div className="flex items-center justify-center h-28">
          <Spinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-6">
          <MetricCard
            label="Mitarbeiter aktiv"
            value={stats?.anzahl_mitarbeiter ?? '—'}
            icon={<Users size={14} />}
            sub="Im System angelegt"
          />
          <MetricCard
            label="Eingestempelt"
            value={stats?.aktuell_eingestempelt ?? '—'}
            icon={<Clock size={14} />}
            sub="Aktuell im Dienst"
          />
          <MetricCard
            label="Offene Anträge"
            value={stats?.offene_urlaubsantraege ?? '—'}
            icon={<CalendarDays size={14} />}
            sub="Urlaubsanträge offen"
          />
        </div>
      )}

      {/* Offene Urlaubsanträge */}
      <div
        className="rounded-lg overflow-hidden"
        style={{ border: '1px solid var(--border)', background: 'var(--surface)' }}
      >
        <div className="px-5 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <SectionHeader
            title="Offene Urlaubsanträge"
            action={
              offeneAntraege && offeneAntraege.length > 0 ? (
                <span
                  className="text-xs font-semibold px-2 py-0.5 rounded-full"
                  style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
                >
                  {offeneAntraege.length} offen
                </span>
              ) : null
            }
          />
        </div>

        <div className="px-5 py-4">
          {!offeneAntraege ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : offeneAntraege.length === 0 ? (
            <div className="flex flex-col items-center py-8 gap-2">
              <CalendarDays size={24} style={{ color: 'var(--text-subtle)' }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Keine offenen Urlaubsanträge
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {(offeneAntraege as Record<string, unknown>[]).map((a) => {
                const ma = a.mitarbeiter as Record<string, string> | undefined
                return (
                  <div
                    key={a.id as number}
                    className="flex items-center justify-between px-4 py-3 rounded-lg"
                    style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
                        style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
                      >
                        {ma ? ma.vorname[0] : '?'}
                      </div>
                      <div>
                        <p className="text-sm font-medium">
                          {ma ? `${ma.vorname} ${ma.nachname}` : `Mitarbeiter ${a.mitarbeiter_id}`}
                        </p>
                        <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                          {a.datum_von as string} – {a.datum_bis as string}
                          <span
                            className="ml-2 px-1.5 py-0.5 rounded text-xs"
                            style={{ background: 'var(--surface3)', color: 'var(--text-muted)' }}
                          >
                            {String(a.anzahl_tage)} Tage
                          </span>
                        </p>
                        {typeof a.kommentar === 'string' && a.kommentar && (
                          <p className="text-xs mt-0.5 italic" style={{ color: 'var(--text-muted)' }}>
                            „{a.kommentar}"
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => decide(a.id as number, 'genehmigt')}
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md font-medium transition-all cursor-pointer"
                        style={{ background: 'var(--success-dim)', color: 'var(--success)' }}
                      >
                        <CheckCircle size={13} /> Genehmigen
                      </button>
                      <button
                        onClick={() => decide(a.id as number, 'abgelehnt')}
                        className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md font-medium transition-all cursor-pointer"
                        style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}
                      >
                        <XCircle size={13} /> Ablehnen
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      <div className="mt-3 flex items-center gap-1.5" style={{ color: 'var(--text-subtle)' }}>
        <TrendingUp size={12} />
        <p className="text-xs">Aktualisierung alle 30 Sekunden</p>
      </div>
    </div>
  )
}
