import { type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import {
  LayoutDashboard, Users, Clock, CalendarDays, FileText,
  DollarSign, Settings, LogOut, Timer, CalendarRange, Building2,
} from 'lucide-react'

interface NavItem { to: string; icon: ReactNode; label: string }

const ADMIN_NAV: NavItem[] = [
  { to: '/admin',               icon: <LayoutDashboard size={16} />, label: 'Übersicht' },
  { to: '/admin/mitarbeiter',   icon: <Users size={16} />,           label: 'Mitarbeiter' },
  { to: '/admin/dienstplan',    icon: <CalendarRange size={16} />,   label: 'Dienstplan' },
  { to: '/admin/zeiten',        icon: <Clock size={16} />,           label: 'Zeiterfassung' },
  { to: '/admin/urlaub',        icon: <CalendarDays size={16} />,    label: 'Urlaub' },
  { to: '/admin/lohn',          icon: <DollarSign size={16} />,      label: 'Lohn' },
  { to: '/admin/dokumente',     icon: <FileText size={16} />,        label: 'Dokumente' },
  { to: '/admin/kiosk',         icon: <Timer size={16} />,           label: 'Kiosk' },
]

const ADMIN_BOTTOM_NAV: NavItem[] = [
  { to: '/admin/einstellungen', icon: <Settings size={16} />, label: 'Einstellungen' },
]

const MITARBEITER_NAV: NavItem[] = [
  { to: '/dashboard',              icon: <LayoutDashboard size={16} />, label: 'Übersicht' },
  { to: '/dashboard/zeiten',       icon: <Clock size={16} />,           label: 'Meine Zeiten' },
  { to: '/dashboard/urlaub',       icon: <CalendarDays size={16} />,    label: 'Urlaub' },
  { to: '/dashboard/dienstplan',   icon: <CalendarRange size={16} />,   label: 'Mein Dienstplan' },
]

const navClass = (isActive: boolean) =>
  `flex items-center gap-2.5 px-3 py-2 mx-2 rounded-md text-sm font-medium transition-all ${
    isActive
      ? 'bg-white/8 text-[#ededf0]'
      : 'text-[#6c6c80] hover:text-[#b0b0c0] hover:bg-white/4'
  }`

function NavGroup({ items }: { items: NavItem[] }) {
  return (
    <>
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.to === '/admin' || item.to === '/dashboard'}
          className={({ isActive }) => navClass(isActive)}
        >
          {item.icon}
          <span>{item.label}</span>
        </NavLink>
      ))}
    </>
  )
}

export function Sidebar({ isAdmin }: { isAdmin: boolean }) {
  const navigate = useNavigate()
  const { betriebName, logout } = useAuthStore()

  return (
    <aside
      className="flex flex-col shrink-0 h-screen sticky top-0"
      style={{ width: 'var(--sidebar-w)', background: '#09090e', borderRight: '1px solid var(--border)' }}
    >
      {/* Logo */}
      <div className="px-4 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
        <img
          src="/complio-logo.png"
          alt="Complio"
          style={{ height: '26px', width: 'auto', objectFit: 'contain' }}
        />
      </div>

      {/* Betrieb */}
      {betriebName && (
        <div className="px-4 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <Building2 size={13} style={{ color: 'var(--text-muted)' }} />
            <span className="text-xs font-medium truncate" style={{ color: 'var(--text-muted)' }}>
              {betriebName}
            </span>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-2 flex flex-col gap-0.5">
        {isAdmin ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-widest px-5 pt-3 pb-2"
              style={{ color: 'var(--text-subtle)' }}>
              Admin
            </p>
            <NavGroup items={ADMIN_NAV} />
          </>
        ) : (
          <NavGroup items={MITARBEITER_NAV} />
        )}
      </nav>

      {/* Bottom */}
      <div className="py-2" style={{ borderTop: '1px solid var(--border)' }}>
        {isAdmin && (
          <div className="flex flex-col gap-0.5 mb-0.5">
            <NavGroup items={ADMIN_BOTTOM_NAV} />
          </div>
        )}
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="flex items-center gap-2.5 text-sm font-medium mx-2 px-3 py-2 rounded-md w-[calc(100%-16px)] transition-all cursor-pointer hover:bg-red-950/20 hover:text-red-400"
          style={{ color: 'var(--text-muted)' }}
        >
          <LogOut size={16} />
          <span>Abmelden</span>
        </button>
      </div>
    </aside>
  )
}
