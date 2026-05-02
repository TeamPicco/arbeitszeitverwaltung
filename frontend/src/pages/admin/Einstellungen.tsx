import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { betriebInfo } from '../../api/admin'
import { changePassword } from '../../api/auth'
import { Card } from '../../components/Card'
import { Button } from '../../components/Button'
import { Input } from '../../components/Input'
import { Spinner } from '../../components/Spinner'
import { api } from '../../api/client'

export function AdminEinstellungen() {
  const qc = useQueryClient()
  const { data: betrieb, isLoading } = useQuery({
    queryKey: ['betrieb'],
    queryFn: betriebInfo,
  })

  if (isLoading)
    return <div className="flex justify-center h-40 items-center"><Spinner /></div>

  return (
    <div className="max-w-2xl flex flex-col gap-6">
      <h1 className="text-2xl font-bold">Einstellungen</h1>

      <BetriebCard betrieb={betrieb} onSaved={() => qc.invalidateQueries({ queryKey: ['betrieb'] })} />
      <PasswordCard />
    </div>
  )
}

function BetriebCard({
  betrieb,
  onSaved,
}: {
  betrieb: Record<string, unknown> | undefined
  onSaved: () => void
}) {
  const [form, setForm] = useState({
    name: (betrieb?.name as string) ?? '',
    adresse: (betrieb?.adresse as string) ?? '',
    telefon: (betrieb?.telefon as string) ?? '',
    email: (betrieb?.email as string) ?? '',
  })
  const [loading, setLoading] = useState(false)

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.patch('/admin/betrieb', form)
      onSaved()
      toast.success('Betriebsdaten gespeichert')
    } catch {
      toast.error('Fehler beim Speichern')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <h2 className="font-semibold mb-4">Betrieb</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <Input label="Betriebsname" value={form.name} onChange={f('name')} />
        <Input label="Adresse" value={form.adresse} onChange={f('adresse')} />
        <Input label="Telefon" value={form.telefon} onChange={f('telefon')} />
        <Input label="E-Mail" type="email" value={form.email} onChange={f('email')} />
        <div className="mt-1">
          <Button type="submit" loading={loading}>Speichern</Button>
        </div>
      </form>
    </Card>
  )
}

function PasswordCard() {
  const [form, setForm] = useState({ old_password: '', new_password: '', confirm: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const f = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((p) => ({ ...p, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (form.new_password !== form.confirm) {
      setError('Passwörter stimmen nicht überein.')
      return
    }
    setLoading(true)
    try {
      await changePassword({ old_password: form.old_password, new_password: form.new_password })
      toast.success('Passwort erfolgreich geändert')
      setForm({ old_password: '', new_password: '', confirm: '' })
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Fehler beim Ändern.'
      toast.error(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <Card>
      <h2 className="font-semibold mb-4">Passwort ändern</h2>
      <form onSubmit={handleSubmit} className="flex flex-col gap-3">
        <Input
          label="Aktuelles Passwort"
          type="password"
          value={form.old_password}
          onChange={f('old_password')}
          required
        />
        <Input
          label="Neues Passwort"
          type="password"
          value={form.new_password}
          onChange={f('new_password')}
          required
        />
        <Input
          label="Wiederholen"
          type="password"
          value={form.confirm}
          onChange={f('confirm')}
          required
          error={error}
        />
        <div className="mt-1">
          <Button type="submit" loading={loading}>Ändern</Button>
        </div>
      </form>
    </Card>
  )
}
