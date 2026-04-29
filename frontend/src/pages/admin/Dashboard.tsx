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
      <div className="mb-12">
        <p className="text-base mb-2 font-medium" style={{ color: 'var(--text-muted)' }}>
          {DAYS_DE[now.getDay()]}, {now.getDate()}. {MONTHS_DE[now.getMonth()]} {now.getFullYear()}
        </p>
        <h1 className="font-extrabold tracking-tight" style={{ fontSize: '2.8rem', lineHeight: 1.15 }}>
          Guten {now.getHours() < 12 ? 'Morgen' : now.getHours() < 18 ? 'Tag' : 'Abend'}
          {betriebName ? `, ${betriebName}` : ''}
        </h1>
        <p className="text-base mt-2.5" style={{ color: 'var(--text-muted)' }}>
          Hier ist deine tagesaktuelle Übersicht.
        </p>
      </div>

      {/* Metrics */}
      {isLoading ? (
        <div className="flex items-center justify-center h-32">
          <Spinner />
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
          <MetricCard
            label="Mitarbeiter aktiv"
            value={stats?.anzahl_mitarbeiter ?? '—'}
            icon={<Users size={20} />}
            sub="Im System angelegt"
          />
          <MetricCard
            label="Eingestempelt"
            value={stats?.aktuell_eingestempelt ?? '—'}
            icon={<Clock size={20} />}
            sub="Aktuell im Dienst"
          />
          <MetricCard
            label="Offene Anträge"
            value={stats?.offene_urlaubsantraege ?? '—'}
            icon={<CalendarDays size={20} />}
            sub="Urlaubsanträge offen"
          />
        </div>
      )}

      {/* Offene Urlaubsanträge */}
      <div
        className="rounded-xl overflow-hidden"
        style={{ border: '1px solid var(--border)' }}
      >
        <div className="px-6 py-4" style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}>
          <SectionHeader
            title="Offene Urlaubsanträge"
            action={
              offeneAntraege && offeneAntraege.length > 0 ? (
                <span
                  className="text-xs font-semibold px-2.5 py-1 rounded-full"
                  style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
                >
                  {offeneAntraege.length} ausstehend
                </span>
              ) : null
            }
          />

          {!offeneAntraege ? (
            <div className="flex justify-center py-8"><Spinner /></div>
          ) : offeneAntraege.length === 0 ? (
            <div className="flex flex-col items-center py-10 gap-3">
              <CalendarDays size={32} style={{ color: 'var(--text-muted)', opacity: 0.4 }} />
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
                    className="flex items-center justify-between px-4 py-3.5 rounded-xl"
                    style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className="w-9 h-9 rounded-full flex items-center justify-center text-sm font-bold shrink-0"
                        style={{ background: 'var(--accent-dim)', color: 'var(--accent)' }}
                      >
                        {ma ? ma.vorname[0] : '?'}
                      </div>
                      <div>
                        <p className="font-medium">
                          {ma ? `${ma.vorname} ${ma.nachname}` : `Mitarbeiter ${a.mitarbeiter_id}`}
                        </p>
                        <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
                          {a.datum_von as string} – {a.datum_bis as string}
                          <span
                            className="ml-2 px-2 py-0.5 rounded-full text-xs"
                            style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
                          >
                            {String(a.anzahl_tage)} Tage
                          </span>
                        </p>
                        {typeof a.kommentar === 'string' && a.kommentar && (
                          <p className="text-xs mt-1 italic" style={{ color: 'var(--text-muted)' }}>
                            „{a.kommentar}"
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex gap-2 shrink-0">
                      <button
                        onClick={() => decide(a.id as number, 'genehmigt')}
                        className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg font-medium transition-all cursor-pointer"
                        style={{ background: 'var(--success-dim)', color: 'var(--success)' }}
                      >
                        <CheckCircle size={15} /> Genehmigen
                      </button>
                      <button
                        onClick={() => decide(a.id as number, 'abgelehnt')}
                        className="flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg font-medium transition-all cursor-pointer"
                        style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}
                      >
                        <XCircle size={15} /> Ablehnen
                      </button>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>
      </div>

      {/* Quick Stats Footer */}
      <div className="mt-4 flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
        <TrendingUp size={14} />
        <p className="text-xs">Daten werden alle 30 Sekunden aktualisiert</p>
      </div>
    </div>
  )
}
