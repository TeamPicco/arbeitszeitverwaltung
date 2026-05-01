import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { Spinner } from '../../components/Spinner'
import { PageHeader } from '../../components/PageHeader'
import { SelectInput } from '../../components/Input'
import { Upload, Trash2, ExternalLink, FileText, X } from 'lucide-react'

type MA = { id: number; vorname: string; nachname: string }
type Dokument = {
  id: number
  name: string
  typ?: string
  status?: string
  gueltig_bis?: string
  file_url?: string
  created_at?: string
}

export function AdminDokumente() {
  const [selectedMaId, setSelectedMaId] = useState<number | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const qc = useQueryClient()

  const { data: mitarbeiter } = useQuery<MA[]>({
    queryKey: ['mitarbeiter'],
    queryFn: () => mitarbeiterListe(true),
  })

  const { data: dokumente, isLoading } = useQuery<Dokument[]>({
    queryKey: ['dokumente', selectedMaId],
    queryFn: () =>
      api.get(`/dokumente/mitarbeiter/${selectedMaId}`).then((r) => r.data),
    enabled: !!selectedMaId,
  })

  const handleDelete = async (id: number) => {
    if (!confirm('Dokument wirklich löschen?')) return
    await api.delete(`/dokumente/${id}`)
    qc.invalidateQueries({ queryKey: ['dokumente', selectedMaId] })
  }

  const selectedMa = (mitarbeiter ?? []).find((m) => m.id === selectedMaId)

  return (
    <div>
      <PageHeader
        title="Dokumente"
        sub="Mitarbeiterdokumente verwalten und hochladen"
        action={
          selectedMaId ? (
            <Button onClick={() => setShowUpload((v) => !v)}>
              <Upload size={14} /> Dokument hochladen
            </Button>
          ) : undefined
        }
      />

      {/* Mitarbeiter auswählen */}
      <div className="mb-6" style={{ maxWidth: 320 }}>
        <SelectInput
          label="Mitarbeiter"
          value={selectedMaId ?? ''}
          onChange={(e) => {
            setSelectedMaId(e.target.value ? Number(e.target.value) : null)
            setShowUpload(false)
          }}
        >
          <option value="">— Mitarbeiter wählen —</option>
          {(mitarbeiter ?? []).map((ma) => (
            <option key={ma.id} value={ma.id}>
              {ma.nachname}, {ma.vorname}
            </option>
          ))}
        </SelectInput>
      </div>

      {/* Upload Panel */}
      {showUpload && selectedMaId && (
        <UploadPanel
          mitarbeiterId={selectedMaId}
          onUploaded={() => {
            qc.invalidateQueries({ queryKey: ['dokumente', selectedMaId] })
            setShowUpload(false)
          }}
          onClose={() => setShowUpload(false)}
        />
      )}

      {/* Empty state */}
      {!selectedMaId && (
        <div
          className="flex flex-col items-center justify-center py-20 rounded-xl gap-3"
          style={{ border: '1px dashed var(--border)' }}
        >
          <FileText size={36} style={{ color: 'var(--text-subtle)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            Mitarbeiter auswählen, um Dokumente anzuzeigen
          </p>
        </div>
      )}

      {selectedMaId && isLoading && (
        <div className="flex justify-center h-20 items-center"><Spinner /></div>
      )}

      {selectedMaId && !isLoading && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)' }}
        >
          {/* Table header */}
          <div
            className="px-5 py-3"
            style={{ background: '#0d0d0d', borderBottom: '1px solid var(--border)' }}
          >
            <p className="text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
              {selectedMa ? `${selectedMa.vorname} ${selectedMa.nachname}` : ''} · {dokumente?.length ?? 0} Dokument{dokumente?.length !== 1 ? 'e' : ''}
            </p>
          </div>

          {!dokumente || dokumente.length === 0 ? (
            <div className="flex flex-col items-center py-12 gap-2">
              <FileText size={28} style={{ color: 'var(--text-subtle)' }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Noch keine Dokumente für diesen Mitarbeiter.
              </p>
              <Button
                variant="secondary"
                className="mt-2"
                onClick={() => setShowUpload(true)}
              >
                <Upload size={14} /> Erstes Dokument hochladen
              </Button>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface)' }}>
                  {['Name', 'Typ', 'Status', 'Gültig bis', 'Hochgeladen', ''].map((h) => (
                    <th
                      key={h}
                      className="text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {dokumente.map((d, idx) => (
                  <tr
                    key={d.id}
                    className="hover:bg-[#141414] transition-colors"
                    style={{
                      borderTop: idx > 0 ? '1px solid var(--border)' : undefined,
                      background: idx % 2 === 0 ? 'var(--surface)' : '#0f0f0f',
                    }}
                  >
                    <td className="px-5 py-3.5 font-medium text-sm">{d.name}</td>
                    <td className="px-5 py-3.5 text-sm" style={{ color: 'var(--text-muted)' }}>
                      {d.typ ?? '–'}
                    </td>
                    <td className="px-5 py-3.5">
                      <span
                        className="text-xs px-2 py-0.5 rounded-full font-medium"
                        style={{
                          background: d.status === 'aktiv' ? 'rgba(74,222,128,0.12)' : 'rgba(248,113,113,0.12)',
                          color: d.status === 'aktiv' ? '#4ade80' : '#f87171',
                        }}
                      >
                        {d.status ?? '–'}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-sm" style={{ color: 'var(--text-muted)' }}>
                      {d.gueltig_bis ?? '–'}
                    </td>
                    <td className="px-5 py-3.5 text-sm" style={{ color: 'var(--text-muted)' }}>
                      {d.created_at?.slice(0, 10) ?? '–'}
                    </td>
                    <td className="px-5 py-3.5">
                      <div className="flex items-center gap-1.5 justify-end">
                        {d.file_url && (
                          <a
                            href={d.file_url}
                            target="_blank"
                            rel="noreferrer"
                            className="p-1.5 rounded-md hover:bg-[#1a1a1a] transition-colors"
                            style={{ color: 'var(--accent)' }}
                            title="Öffnen"
                          >
                            <ExternalLink size={14} />
                          </a>
                        )}
                        <button
                          onClick={() => handleDelete(d.id)}
                          className="p-1.5 rounded-md hover:bg-red-900/20 transition-colors cursor-pointer"
                          style={{ color: '#ef4444' }}
                          title="Löschen"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

function UploadPanel({
  mitarbeiterId,
  onUploaded,
  onClose,
}: {
  mitarbeiterId: number
  onUploaded: () => void
  onClose: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')
  const [typ, setTyp] = useState('sonstig')
  const [gueltigBis, setGueltigBis] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [error, setError] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setName(f.name.replace(/\.[^.]+$/, ''))
    setError('')
  }

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) { setError('Bitte eine Datei auswählen.'); return }
    setLoading(true)
    setError('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('name', name || file.name)
      fd.append('typ', typ)
      if (gueltigBis) fd.append('gueltig_bis', gueltigBis)
      await api.post(`/dokumente/mitarbeiter/${mitarbeiterId}`, fd)
      onUploaded()
    } catch {
      setError('Upload fehlgeschlagen. Bitte erneut versuchen.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="rounded-xl mb-6 p-5"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-[15px]">Dokument hochladen</h3>
        <button onClick={onClose} className="p-1 rounded hover:bg-white/5 cursor-pointer" style={{ color: 'var(--text-muted)' }}>
          <X size={16} />
        </button>
      </div>

      <form onSubmit={handleUpload}>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-4">
          {/* File picker */}
          <div className="flex flex-col gap-1.5 sm:col-span-2 lg:col-span-1">
            <label className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Datei *</label>
            <input ref={fileRef} type="file" className="hidden" onChange={handleFileChange} />
            <button
              type="button"
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-2 px-3 py-2 rounded-md text-sm font-medium transition-colors cursor-pointer text-left"
              style={{
                background: 'var(--surface2)',
                border: '1px solid var(--border)',
                color: file ? 'var(--text)' : 'var(--text-muted)',
              }}
            >
              <Upload size={14} className="shrink-0" />
              <span className="truncate">{file ? file.name : 'Datei wählen …'}</span>
            </button>
          </div>

          {/* Name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Dokumentname *</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="z.B. Arbeitsvertrag 2026"
              required
              className="px-3 py-2 rounded-md text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            />
          </div>

          {/* Typ */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Dokumenttyp</label>
            <select
              value={typ}
              onChange={(e) => setTyp(e.target.value)}
              className="px-3 py-2 rounded-md text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            >
              <option value="sonstig">Sonstig</option>
              <option value="arbeitsvertrag">Arbeitsvertrag</option>
              <option value="zeugnis">Zeugnis</option>
              <option value="bescheinigung">Bescheinigung</option>
              <option value="krankmeldung">Krankmeldung</option>
              <option value="lohnabrechnung">Lohnabrechnung</option>
            </select>
          </div>

          {/* Gültig bis */}
          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>Gültig bis (optional)</label>
            <input
              type="date"
              value={gueltigBis}
              onChange={(e) => setGueltigBis(e.target.value)}
              className="px-3 py-2 rounded-md text-sm outline-none focus:ring-1 focus:ring-[#F97316]"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)', color: 'var(--text)' }}
            />
          </div>
        </div>

        {error && (
          <p className="text-xs mb-3" style={{ color: 'var(--danger)' }}>{error}</p>
        )}

        <div className="flex gap-2">
          <Button type="submit" loading={loading}>
            <Upload size={14} /> Hochladen
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>Abbrechen</Button>
        </div>
      </form>
    </div>
  )
}
