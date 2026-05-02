import { useCallback, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { Spinner } from '../../components/Spinner'
import { Upload, Trash2, ExternalLink, FileText, X, FilePlus } from 'lucide-react'

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

const inp: React.CSSProperties = {
  background: 'var(--surface2)',
  border: '1px solid var(--border)',
  color: 'var(--text)',
  borderRadius: 8,
  padding: '11px 14px',
  fontSize: 15,
  outline: 'none',
  width: '100%',
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
      <div className="mb-8">
        <h1 className="font-bold mb-1" style={{ fontSize: 26 }}>Dokumente</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: 15 }}>Mitarbeiterdokumente verwalten und hochladen</p>
      </div>

      {/* Mitarbeiter + Upload-Button */}
      <div className="flex flex-wrap items-end gap-4 mb-7">
        <div className="flex flex-col gap-2" style={{ minWidth: 260 }}>
          <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
            Mitarbeiter auswählen
          </label>
          <select
            value={selectedMaId ?? ''}
            onChange={(e) => {
              setSelectedMaId(e.target.value ? Number(e.target.value) : null)
              setShowUpload(false)
            }}
            style={{ ...inp, width: 'auto' }}
          >
            <option value="">— Mitarbeiter wählen —</option>
            {(mitarbeiter ?? []).map((ma) => (
              <option key={ma.id} value={ma.id}>
                {ma.nachname}, {ma.vorname}
              </option>
            ))}
          </select>
        </div>

        {selectedMaId && (
          <Button onClick={() => setShowUpload((v) => !v)}>
            <Upload size={15} /> Dokument hochladen
          </Button>
        )}
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
          className="flex flex-col items-center justify-center py-24 rounded-2xl gap-4"
          style={{ border: '2px dashed var(--border)' }}
        >
          <div
            className="w-16 h-16 rounded-2xl flex items-center justify-center"
            style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
          >
            <FileText size={28} style={{ color: 'var(--text-muted)' }} />
          </div>
          <div className="text-center">
            <p className="font-semibold text-base">Kein Mitarbeiter gewählt</p>
            <p className="mt-1" style={{ color: 'var(--text-muted)', fontSize: 14 }}>
              Mitarbeiter auswählen, um Dokumente anzuzeigen
            </p>
          </div>
        </div>
      )}

      {selectedMaId && isLoading && (
        <div className="flex justify-center h-24 items-center"><Spinner /></div>
      )}

      {selectedMaId && !isLoading && (
        <div
          className="rounded-xl overflow-hidden"
          style={{ border: '1px solid var(--border)' }}
        >
          {/* Header */}
          <div
            className="px-6 py-4 flex items-center justify-between"
            style={{ background: 'var(--surface)', borderBottom: '1px solid var(--border)' }}
          >
            <p className="font-semibold" style={{ fontSize: 15 }}>
              {selectedMa ? `${selectedMa.vorname} ${selectedMa.nachname}` : ''}
            </p>
            <span className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {dokumente?.length ?? 0} Dokument{dokumente?.length !== 1 ? 'e' : ''}
            </span>
          </div>

          {!dokumente || dokumente.length === 0 ? (
            <div className="flex flex-col items-center py-16 gap-4">
              <FilePlus size={32} style={{ color: 'var(--text-subtle)' }} />
              <div className="text-center">
                <p className="font-medium text-base">Noch keine Dokumente</p>
                <p className="mt-1 text-sm" style={{ color: 'var(--text-muted)' }}>
                  Erstes Dokument für diesen Mitarbeiter hochladen
                </p>
              </div>
              <Button variant="secondary" onClick={() => setShowUpload(true)}>
                <Upload size={15} /> Dokument hochladen
              </Button>
            </div>
          ) : (
            <table className="w-full">
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)', background: 'var(--surface2)' }}>
                  {['Dokument', 'Typ', 'Status', 'Gültig bis', 'Hochgeladen', ''].map((h) => (
                    <th
                      key={h}
                      className="text-left px-6 py-3 text-xs font-semibold uppercase tracking-wider"
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
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div
                          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                          style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
                        >
                          <FileText size={16} style={{ color: 'var(--text-muted)' }} />
                        </div>
                        <span className="font-medium" style={{ fontSize: 14 }}>{d.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4" style={{ color: 'var(--text-muted)', fontSize: 14 }}>
                      {d.typ ?? '–'}
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className="text-xs px-2.5 py-1 rounded-full font-medium"
                        style={{
                          background: d.status === 'aktiv' ? 'rgba(74,222,128,0.12)' : 'rgba(248,113,113,0.12)',
                          color: d.status === 'aktiv' ? '#4ade80' : '#f87171',
                        }}
                      >
                        {d.status ?? '–'}
                      </span>
                    </td>
                    <td className="px-6 py-4" style={{ color: 'var(--text-muted)', fontSize: 14 }}>
                      {d.gueltig_bis ?? '–'}
                    </td>
                    <td className="px-6 py-4" style={{ color: 'var(--text-muted)', fontSize: 14 }}>
                      {d.created_at?.slice(0, 10) ?? '–'}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 justify-end">
                        {d.file_url && (
                          <a
                            href={d.file_url}
                            target="_blank"
                            rel="noreferrer"
                            className="flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium hover:bg-[#1a1a1a] transition-colors"
                            style={{ color: 'var(--accent)' }}
                          >
                            <ExternalLink size={13} />
                            Öffnen
                          </a>
                        )}
                        <button
                          onClick={() => handleDelete(d.id)}
                          className="p-2 rounded-md hover:bg-red-900/20 transition-colors cursor-pointer"
                          style={{ color: '#ef4444' }}
                          title="Löschen"
                        >
                          <Trash2 size={15} />
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
  const [dragging, setDragging] = useState(false)

  const applyFile = (f: File) => {
    setFile(f)
    setName(f.name.replace(/\.[^.]+$/, ''))
    setError('')
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) applyFile(f)
  }

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragging(false)
    const f = e.dataTransfer.files[0]
    if (f) applyFile(f)
  }, [])

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
      className="rounded-xl mb-7 p-6"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      <div className="flex items-center justify-between mb-6">
        <h3 className="font-semibold" style={{ fontSize: 17 }}>Dokument hochladen</h3>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg hover:bg-white/5 cursor-pointer"
          style={{ color: 'var(--text-muted)' }}
        >
          <X size={17} />
        </button>
      </div>

      <form onSubmit={handleUpload}>
        {/* Drop zone */}
        <input ref={fileRef} type="file" className="hidden" onChange={handleFileChange} />
        <div
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          className="flex flex-col items-center justify-center gap-2 rounded-xl mb-6 py-10 cursor-pointer transition-colors"
          style={{
            border: `2px dashed ${dragging ? 'var(--accent)' : file ? 'var(--success)' : 'var(--border-hover)'}`,
            background: dragging ? 'var(--accent-dim2)' : file ? 'rgba(74,222,128,0.04)' : 'var(--surface2)',
          }}
        >
          <Upload size={26} style={{ color: file ? 'var(--success)' : 'var(--text-muted)' }} />
          <div className="text-center">
            {file ? (
              <>
                <p className="font-medium" style={{ fontSize: 15 }}>{file.name}</p>
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  {(file.size / 1024).toFixed(0)} KB — Klicken zum Ändern
                </p>
              </>
            ) : (
              <>
                <p className="font-medium" style={{ fontSize: 15 }}>Datei hierher ziehen oder klicken</p>
                <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>PDF, Word, JPG bis 20 MB</p>
              </>
            )}
          </div>
        </div>

        {/* Fields */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mb-5">
          <div className="flex flex-col gap-2">
            <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
              Dokumentname *
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="z. B. Arbeitsvertrag 2026"
              required
              style={inp}
            />
          </div>

          <div className="flex flex-col gap-2">
            <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
              Dokumenttyp
            </label>
            <select value={typ} onChange={(e) => setTyp(e.target.value)} style={inp}>
              <option value="sonstig">Sonstig</option>
              <option value="arbeitsvertrag">Arbeitsvertrag</option>
              <option value="zeugnis">Zeugnis</option>
              <option value="bescheinigung">Bescheinigung</option>
              <option value="krankmeldung">Krankmeldung</option>
              <option value="lohnabrechnung">Lohnabrechnung</option>
            </select>
          </div>

          <div className="flex flex-col gap-2">
            <label style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-muted)' }}>
              Gültig bis <span style={{ color: 'var(--text-subtle)' }}>(optional)</span>
            </label>
            <input
              type="date"
              value={gueltigBis}
              onChange={(e) => setGueltigBis(e.target.value)}
              style={inp}
            />
          </div>
        </div>

        {error && (
          <p className="text-sm mb-4" style={{ color: 'var(--danger)' }}>{error}</p>
        )}

        <div className="flex gap-3">
          <Button type="submit" loading={loading}>
            <Upload size={15} /> Hochladen
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>Abbrechen</Button>
        </div>
      </form>
    </div>
  )
}
