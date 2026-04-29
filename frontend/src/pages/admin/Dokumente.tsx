import { useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { mitarbeiterListe } from '../../api/mitarbeiter'
import { api } from '../../api/client'
import { Button } from '../../components/Button'
import { Spinner } from '../../components/Spinner'
import { Upload, Trash2, ExternalLink } from 'lucide-react'

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
    await api.delete(`/dokumente/${id}`)
    qc.invalidateQueries({ queryKey: ['dokumente', selectedMaId] })
  }

  return (
    <div className="max-w-4xl">
      <h1 className="text-2xl font-bold mb-6">Dokumente</h1>

      <div className="flex gap-3 mb-6 flex-wrap items-end">
        <select
          className="px-3 py-2 rounded-lg text-sm"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)' }}
          value={selectedMaId ?? ''}
          onChange={(e) => setSelectedMaId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Mitarbeiter wählen …</option>
          {(mitarbeiter ?? []).map((ma) => (
            <option key={ma.id} value={ma.id}>
              {ma.nachname} {ma.vorname}
            </option>
          ))}
        </select>

        {selectedMaId && (
          <UploadButton
            mitarbeiterId={selectedMaId}
            onUploaded={() => qc.invalidateQueries({ queryKey: ['dokumente', selectedMaId] })}
          />
        )}
      </div>

      {!selectedMaId && (
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
          Mitarbeiter auswählen, um Dokumente anzuzeigen.
        </p>
      )}

      {selectedMaId && isLoading && (
        <div className="flex justify-center h-20 items-center"><Spinner /></div>
      )}

      {selectedMaId && !isLoading && (
        <>
          {(!dokumente || dokumente.length === 0) ? (
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Keine Dokumente vorhanden.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Name', 'Typ', 'Status', 'Gültig bis', 'Hochgeladen', ''].map((h) => (
                      <th key={h} className="text-left py-2 pr-4 text-xs uppercase tracking-wider font-semibold"
                        style={{ color: 'var(--text-muted)' }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {dokumente.map((d) => (
                    <tr key={d.id} style={{ borderBottom: '1px solid var(--border)' }}>
                      <td className="py-2 pr-4 font-medium">{d.name}</td>
                      <td className="py-2 pr-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                        {d.typ ?? '–'}
                      </td>
                      <td className="py-2 pr-4">
                        <span
                          className="text-xs px-2 py-0.5 rounded-full"
                          style={{
                            background: d.status === 'aktiv' ? '#052e16' : '#1c0a0a',
                            color: d.status === 'aktiv' ? '#4ade80' : '#f87171',
                          }}
                        >
                          {d.status ?? '–'}
                        </span>
                      </td>
                      <td className="py-2 pr-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                        {d.gueltig_bis ?? '–'}
                      </td>
                      <td className="py-2 pr-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                        {d.created_at?.slice(0, 10) ?? '–'}
                      </td>
                      <td className="py-2">
                        <div className="flex gap-2">
                          {d.file_url && (
                            <a
                              href={d.file_url}
                              target="_blank"
                              rel="noreferrer"
                              className="p-1.5 rounded hover:bg-[#1a1a1a] transition-colors"
                              style={{ color: 'var(--accent)' }}
                            >
                              <ExternalLink size={13} />
                            </a>
                          )}
                          <button
                            onClick={() => handleDelete(d.id)}
                            className="p-1.5 rounded hover:bg-red-900/20 transition-colors cursor-pointer"
                            style={{ color: '#ef4444' }}
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function UploadButton({
  mitarbeiterId,
  onUploaded,
}: {
  mitarbeiterId: number
  onUploaded: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [loading, setLoading] = useState(false)
  const [name, setName] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [file, setFile] = useState<File | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (!f) return
    setFile(f)
    setName(f.name.replace(/\.[^.]+$/, ''))
    setShowForm(true)
  }

  const handleUpload = async () => {
    if (!file) return
    setLoading(true)
    const fd = new FormData()
    fd.append('file', file)
    fd.append('name', name || file.name)
    fd.append('typ', 'sonstig')
    await api.post(`/dokumente/mitarbeiter/${mitarbeiterId}`, fd)
    onUploaded()
    setFile(null)
    setName('')
    setShowForm(false)
    setLoading(false)
  }

  return (
    <>
      <input
        ref={fileRef}
        type="file"
        className="hidden"
        onChange={handleFileChange}
      />
      {!showForm && (
        <Button onClick={() => fileRef.current?.click()} variant="secondary">
          <Upload size={14} /> Hochladen
        </Button>
      )}
      {showForm && (
        <div className="flex items-center gap-2">
          <input
            className="px-3 py-2 rounded-lg text-sm"
            style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text)', width: 180 }}
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Dokumentname"
          />
          <Button onClick={handleUpload} loading={loading}>
            Speichern
          </Button>
          <Button variant="secondary" onClick={() => { setShowForm(false); setFile(null) }}>
            Abbruch
          </Button>
        </div>
      )}
    </>
  )
}
