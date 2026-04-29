import { type ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { useAuthStore } from '../store/auth'

export function Layout({ children }: { children: ReactNode }) {
  const role = useAuthStore((s) => s.role)
  const isAdmin = role === 'admin' || role === 'superadmin'

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar isAdmin={isAdmin} />
      <main
        className="flex-1 overflow-y-auto"
        style={{ background: 'var(--bg)', padding: '44px 52px' }}
      >
        {children}
      </main>
    </div>
  )
}
