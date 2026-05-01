import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { login } from '../api/auth'
import { useAuthStore } from '../store/auth'
import { Button } from '../components/Button'
import { Input } from '../components/Input'

export function LoginPage() {
  const navigate = useNavigate()
  const setAuth = useAuthStore((s) => s.setAuth)

  const [form, setForm] = useState({
    betriebsnummer: '',
    username: '',
    password: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const data = await login(form)
      setAuth({ ...data, token: data.access_token })
      if (data.role === 'admin' || data.role === 'superadmin') {
        navigate('/admin')
      } else {
        navigate('/dashboard')
      }
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Login fehlgeschlagen.'
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4"
      style={{ background: 'var(--bg)' }}>
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex justify-center mb-8">
          <img
            src="/complio-logo.png"
            alt="Complio"
            style={{ height: '56px', width: 'auto', objectFit: 'contain' }}
          />
        </div>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl p-8 flex flex-col gap-4"
          style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
        >
          <h1 className="text-lg font-semibold mb-2">Anmelden</h1>

          <Input
            label="Betriebsnummer"
            placeholder="z.B. 1001"
            value={form.betriebsnummer}
            onChange={(e) => setForm({ ...form, betriebsnummer: e.target.value })}
            required
            autoFocus
          />
          <Input
            label="Benutzername"
            placeholder="username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <Input
            label="Passwort"
            type="password"
            placeholder="••••••••"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
          />

          {error && (
            <p className="text-sm text-red-400 bg-red-900/10 rounded-lg px-3 py-2 border border-red-900/30">
              {error}
            </p>
          )}

          <Button type="submit" loading={loading} className="w-full mt-2">
            Anmelden
          </Button>
        </form>
      </div>
    </div>
  )
}
