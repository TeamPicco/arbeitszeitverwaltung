import { type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import {
  LayoutDashboard,
  Users,
  Clock,
  CalendarDays,
  FileText,
  DollarSign,
  Settings,
  LogOut,
  Timer,
} from 'lucide-react'

interface NavItem {
  to: string
  icon: ReactNode
  label: string
  adminOnly?: boolean
}

const NAV: NavItem[] = [
  { to: '/admin', icon: <LayoutDashboard size={16} />, label: 'Übersicht', adminOnly: true },
  { to: '/admin/mitarbeiter', icon: <Users size={16} />, label: 'Mitarbeiter', adminOnly: true },
  { to: '/admin/zeiten', icon: <Clock size={16} />, label: 'Zeiterfassung', adminOnly: true },
  { to: '/admin/urlaub', icon: <CalendarDays size={16} />, label: 'Urlaub', adminOnly: true },
  { to: '/admin/lohn', icon: <DollarSign size={16} />, label: 'Lohn', adminOnly: true },
  { to: '/admin/dokumente', icon: <FileText size={16} />, label: 'Dokumente', adminOnly: true },
  { to: '/admin/kiosk', icon: <Timer size={16} />, label: 'Kiosk', adminOnly: true },
  { to: '/admin/einstellungen', icon: <Settings size={16} />, label: 'Einstellungen', adminOnly: true },
]

const MITARBEITER_NAV: NavItem[] = [
  { to: '/dashboard', icon: <LayoutDashboard size={16} />, label: 'Übersicht' },
  { to: '/dashboard/zeiten', icon: <Clock size={16} />, label: 'Meine Zeiten' },
  { to: '/dashboard/urlaub', icon: <CalendarDays size={16} />, label: 'Urlaub' },
]

export function Sidebar({ isAdmin }: { isAdmin: boolean }) {
  const navigate = useNavigate()
  const { betriebName, logout } = useAuthStore()
  const items = isAdmin ? NAV : MITARBEITER_NAV

  return (
    <aside
      className="flex flex-col w-56 shrink-0 h-screen sticky top-0"
      style={{
        background: '#0d0d0d',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Logo */}
      <div className="px-5 py-5 border-b" style={{ borderColor: 'var(--border)' }}>
        <span className="text-lg font-bold tracking-tight">
          comp<span style={{ color: 'var(--accent)' }}>lio</span>
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/admin' || item.to === '/dashboard'}
            className={({ isActive }) =>
              `flex items-center gap-3 px-4 py-2.5 mx-2 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'text-[#F97316] bg-orange-500/10 border-l-2 border-[#F97316] -ml-0.5 pl-3.5'
                  : 'text-[#888] hover:text-[#e8e8e8] hover:bg-[#1a1a1a]'
              }`
            }
          >
            {item.icon}
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t" style={{ borderColor: 'var(--border)' }}>
        {betriebName && (
          <p className="text-xs mb-3 truncate" style={{ color: 'var(--text-muted)' }}>
            {betriebName}
          </p>
        )}
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="flex items-center gap-2 text-sm w-full px-2 py-1.5 rounded-lg hover:bg-[#1a1a1a] transition-colors cursor-pointer"
          style={{ color: 'var(--text-muted)' }}
        >
          <LogOut size={14} />
          Abmelden
        </button>
      </div>
    </aside>
  )
}
