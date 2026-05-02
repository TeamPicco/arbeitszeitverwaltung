import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  leadsListe, leadsStats, leadAnlegen, leadAktualisieren, leadLoeschen,
  type Lead,
} from '../../api/leads'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Skeleton } from '../../components/Skeleton'
import { Building2, Phone, Mail, Globe, Search, Plus, Pencil, Trash2, X } from 'lucide-react'

const STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  neu:          { label: 'Neu',         color: '#2563EB', bg: 'rgba(37,99,235,0.10)' },
  kontaktiert:  { label: 'Kontaktiert', color: '#D97706', bg: 'rgba(217,119,6,0.10)' },
  interessiert: { label: 'Interessiert',color: '#9333EA', bg: 'rgba(147,51,234,0.10)' },
  abschluss:    { label: 'Abschluss',   color: '#16A34A', bg: 'rgba(22,163,74,0.10)'  },
}

function AnimatedCounter({ value }: { value: number }) {
  const [display, setDisplay] = useState(0)

  useEffect(() => {
    if (value === 0) { setDisplay(0); return }
    let current = 0
    const step = Math.ceil(value / 25)
    const timer = setInterval(() => {
      current = Math.min(current + step, value)
      setDisplay(current)
      if (current >= value) clearInterval(timer)
    }, 30)
    return () => clearInterval(timer)
  }, [value])

  return <>{display}</>
}

function KpiTile({
  label, value, color,
}: { label: string; value: number; color: string }) {
  return (
    <div
      style={{
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderLeft: `4px solid ${color}`,
        borderRadius: 12,
        padding: '18px 20px',
        minWidth: 0,
      }}
    >
      <p style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {label}
      </p>
      <p style={{ fontSize: 32, fontWeight: 800, color: 'var(--text)', lineHeight: 1 }}>
        <AnimatedCounter value={value} />
      </p>
    </div>
  )
}

const EMPTY_FORM = { firmenname: '', ort: '', branche: '', telefon: '', email: '', website: '', notizen: '' }

export function AdminLeads() {
  const qc = useQueryClient()
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Lead | null>(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['leads-stats'],
    queryFn: leadsStats,
  })

  const { data: leads, isLoading } = useQuery({
    queryKey: ['leads', filterStatus, search],
    queryFn: () => leadsListe(filterStatus || undefined, search || undefined),
  })

  const openNew = () => {
    setEditing(null)
    setForm(EMPTY_FORM)
    setShowForm(true)
  }

  const openEdit = (lead: Lead) => {
    setEditing(lead)
    setForm({
      firmenname: lead.firmenname ?? '',
      ort: lead.ort ?? '',
      branche: lead.branche ?? '',
      telefon: lead.telefon ?? '',
      email: lead.email ?? '',
      website: lead.website ?? '',
      notizen: lead.notizen ?? '',
    })
    setShowForm(true)
  }

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.firmenname.trim()) { toast.error('Firmenname ist pflicht.'); return }
    setSaving(true)
    try {
      if (editing) {
        await leadAktualisieren(editing.id, form)
        toast.success('Lead aktualisiert')
      } else {
        await leadAnlegen(form)
        toast.success('Lead angelegt')
      }
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['leads-stats'] })
      setShowForm(false)
    } catch {
      toast.error('Fehler beim Speichern')
    } finally {
      setSaving(false)
    }
  }

  const handleStatusChange = async (lead: Lead, newStatus: string) => {
    try {
      await leadAktualisieren(lead.id, { status: newStatus as Lead['status'] })
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['leads-stats'] })
    } catch {
      toast.error('Statusänderung fehlgeschlagen')
    }
  }

  const handleDelete = async (id: number) => {
    if (!window.confirm('Lead wirklich löschen?')) return
    try {
      await leadLoeschen(id)
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['leads-stats'] })
      toast.success('Lead gelöscht')
    } catch {
      toast.error('Fehler beim Löschen')
    }
  }

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  return (
    <div className="max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[22px] font-bold tracking-tight">Leads</h1>
          <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Vertriebskontakte verwalten
          </p>
        </div>
        <Button onClick={openNew}>
          <Plus size={15} /> Neuer Lead
        </Button>
      </div>

      {/* KPI-Kacheln */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mb-6">
        {statsLoading ? (
          Array.from({ length: 5 }).map((_, i) => (
            <div key={i} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '18px 20px' }}>
              <Skeleton height={11} width="60%" className="mb-3" />
              <Skeleton height={28} width="40%" />
            </div>
          ))
        ) : (
          <>
            <KpiTile label="Gesamt"       value={stats?.gesamt       ?? 0} color="var(--accent)" />
            <KpiTile label="Neu"          value={stats?.neu          ?? 0} color="#2563EB" />
            <KpiTile label="Kontaktiert"  value={stats?.kontaktiert  ?? 0} color="#D97706" />
            <KpiTile label="Interessiert" value={stats?.interessiert ?? 0} color="#9333EA" />
            <KpiTile label="Abschluss"    value={stats?.abschluss    ?? 0} color="#16A34A" />
          </>
        )}
      </div>

      {/* Filter-Leiste */}
      <div className="flex flex-wrap gap-3 mb-5 items-center">
        <div className="relative flex-1 min-w-[200px]">
          <Search size={14} style={{ position: 'absolute', left: 11, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-subtle)' }} />
          <input
            type="text"
            placeholder="Suche nach Firma, Ort, Branche …"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{
              width: '100%', paddingLeft: 32, paddingRight: 12, paddingTop: 8, paddingBottom: 8,
              fontSize: 14, borderRadius: 8, border: '1px solid var(--border)',
              background: 'var(--surface)', color: 'var(--text)', outline: 'none',
            }}
            onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(255,107,0,0.12)' }}
            onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
          />
        </div>
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value)}
          style={{
            padding: '8px 28px 8px 12px', fontSize: 14, borderRadius: 8,
            border: '1px solid var(--border)', background: 'var(--surface)',
            color: 'var(--text)', cursor: 'pointer',
          }}
        >
          <option value="">Alle Status</option>
          {Object.entries(STATUS_CONFIG).map(([k, v]) => (
            <option key={k} value={k}>{v.label}</option>
          ))}
        </select>
      </div>

      {/* Formular */}
      {showForm && (
        <div
          className="rounded-xl p-6 mb-6"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-semibold">{editing ? 'Lead bearbeiten' : 'Neuer Lead'}</h2>
            <button
              onClick={() => setShowForm(false)}
              style={{ color: 'var(--text-muted)', background: 'none', border: 'none', cursor: 'pointer', padding: 4 }}
            >
              <X size={17} />
            </button>
          </div>
          <form onSubmit={handleSave} className="flex flex-col gap-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Input label="Firmenname *" value={form.firmenname} onChange={f('firmenname')} required />
              <Input label="Ort" value={form.ort} onChange={f('ort')} />
              <Input label="Branche" value={form.branche} onChange={f('branche')} />
              <Input label="Telefon" value={form.telefon} onChange={f('telefon')} />
              <Input label="E-Mail" type="email" value={form.email} onChange={f('email')} />
              <Input label="Website" value={form.website} onChange={f('website')} />
            </div>
            <div className="flex flex-col gap-1.5">
              <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>Notizen</label>
              <textarea
                value={form.notizen}
                onChange={f('notizen')}
                rows={3}
                style={{
                  width: '100%', padding: '10px 12px', fontSize: 14, borderRadius: 8,
                  border: '1px solid var(--border)', background: 'var(--surface2)',
                  color: 'var(--text)', resize: 'vertical', outline: 'none', fontFamily: 'inherit',
                }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#FF6B00'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(255,107,0,0.12)' }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.boxShadow = 'none' }}
              />
            </div>
            <div className="flex gap-3">
              <Button type="submit" loading={saving}>{editing ? 'Speichern' : 'Anlegen'}</Button>
              <Button type="button" variant="ghost" onClick={() => setShowForm(false)}>Abbrechen</Button>
            </div>
          </form>
        </div>
      )}

      {/* Liste */}
      {isLoading ? (
        <div className="flex flex-col gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, padding: '16px 20px' }}>
              <div className="flex justify-between mb-2">
                <Skeleton height={16} width="30%" />
                <Skeleton height={22} width="80px" rounded />
              </div>
              <Skeleton height={12} width="50%" />
            </div>
          ))}
        </div>
      ) : !leads || leads.length === 0 ? (
        <div
          className="flex flex-col items-center justify-center py-16 rounded-xl"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <Building2 size={36} style={{ color: 'var(--text-subtle)', marginBottom: 12 }} />
          <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>
            {search || filterStatus ? 'Keine Treffer für diese Filter.' : 'Noch keine Leads angelegt.'}
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {leads.map((lead) => {
            const s = STATUS_CONFIG[lead.status] ?? STATUS_CONFIG.neu
            return (
              <div
                key={lead.id}
                style={{
                  background: 'var(--surface)',
                  border: '1px solid var(--border)',
                  borderRadius: 12,
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 14,
                }}
              >
                {/* Icon */}
                <div style={{
                  width: 38, height: 38, borderRadius: 9, background: 'var(--surface2)',
                  border: '1px solid var(--border)', display: 'flex', alignItems: 'center',
                  justifyContent: 'center', flexShrink: 0,
                }}>
                  <Building2 size={17} style={{ color: 'var(--accent)' }} />
                </div>

                {/* Content */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="flex items-center justify-between gap-2 flex-wrap">
                    <span style={{ fontWeight: 600, fontSize: 15 }}>{lead.firmenname}</span>
                    <div className="flex items-center gap-2">
                      <select
                        value={lead.status}
                        onChange={(e) => handleStatusChange(lead, e.target.value)}
                        style={{
                          fontSize: 12, fontWeight: 600, padding: '3px 22px 3px 8px',
                          borderRadius: 20, border: 'none', cursor: 'pointer',
                          background: s.bg, color: s.color,
                        }}
                      >
                        {Object.entries(STATUS_CONFIG).map(([k, v]) => (
                          <option key={k} value={k}>{v.label}</option>
                        ))}
                      </select>
                      <button
                        onClick={() => openEdit(lead)}
                        style={{ padding: 5, borderRadius: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--surface2)'; e.currentTarget.style.color = 'var(--text)' }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--text-muted)' }}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => handleDelete(lead.id)}
                        style={{ padding: 5, borderRadius: 6, background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
                        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(220,38,38,0.08)'; e.currentTarget.style.color = '#DC2626' }}
                        onMouseLeave={(e) => { e.currentTarget.style.background = 'none'; e.currentTarget.style.color = 'var(--text-muted)' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>

                  <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5">
                    {lead.ort && (
                      <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>{lead.ort}</span>
                    )}
                    {lead.branche && (
                      <span style={{ fontSize: 13, color: 'var(--text-subtle)' }}>{lead.branche}</span>
                    )}
                    {lead.telefon && (
                      <a href={`tel:${lead.telefon}`} style={{ fontSize: 13, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                        <Phone size={11} /> {lead.telefon}
                      </a>
                    )}
                    {lead.email && (
                      <a href={`mailto:${lead.email}`} style={{ fontSize: 13, color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                        <Mail size={11} /> {lead.email}
                      </a>
                    )}
                    {lead.website && (
                      <a href={lead.website} target="_blank" rel="noreferrer" style={{ fontSize: 13, color: 'var(--info)', display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none' }}>
                        <Globe size={11} /> Website
                      </a>
                    )}
                  </div>
                  {lead.notizen && (
                    <p style={{ fontSize: 13, color: 'var(--text-muted)', marginTop: 6, fontStyle: 'italic' }}>
                      {lead.notizen}
                    </p>
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
