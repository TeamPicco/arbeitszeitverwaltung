import { type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import {
  LayoutDashboard, Users, Clock, CalendarDays, FileText,
  DollarSign, Settings, LogOut, Timer, CalendarRange, Building2, Shield,
} from 'lucide-react'

const ICON = 18

interface NavItem { to: string; icon: ReactNode; label: string }

const ADMIN_NAV: NavItem[] = [
  { to: '/admin',               icon: <LayoutDashboard size={ICON} />, label: 'Übersicht' },
  { to: '/admin/mitarbeiter',   icon: <Users size={ICON} />,           label: 'Mitarbeiter' },
  { to: '/admin/dienstplan',    icon: <CalendarRange size={ICON} />,   label: 'Dienstplan' },
  { to: '/admin/zeiten',        icon: <Clock size={ICON} />,           label: 'Zeiterfassung' },
  { to: '/admin/urlaub',        icon: <CalendarDays size={ICON} />,    label: 'Urlaub' },
  { to: '/admin/lohn',          icon: <DollarSign size={ICON} />,      label: 'Lohn' },
  { to: '/admin/dokumente',     icon: <FileText size={ICON} />,        label: 'Dokumente' },
  { to: '/admin/premium',       icon: <Shield size={ICON} />,          label: 'Premium' },
  { to: '/admin/kiosk',         icon: <Timer size={ICON} />,           label: 'Kiosk' },
]

const ADMIN_BOTTOM_NAV: NavItem[] = [
  { to: '/admin/einstellungen', icon: <Settings size={ICON} />, label: 'Einstellungen' },
]

const MITARBEITER_NAV: NavItem[] = [
  { to: '/dashboard',              icon: <LayoutDashboard size={ICON} />, label: 'Übersicht' },
  { to: '/dashboard/zeiten',       icon: <Clock size={ICON} />,           label: 'Meine Zeiten' },
  { to: '/dashboard/urlaub',       icon: <CalendarDays size={ICON} />,    label: 'Urlaub' },
  { to: '/dashboard/dienstplan',   icon: <CalendarRange size={ICON} />,   label: 'Mein Dienstplan' },
]

const navClass = (isActive: boolean) =>
  `flex items-center gap-3 px-3.5 py-2.5 mx-2 rounded-lg font-medium transition-all ${
    isActive
      ? 'bg-[rgba(249,115,22,0.12)] text-[#ededf0]'
      : 'text-[#7a7a90] hover:text-[#c0c0d0] hover:bg-white/5'
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
          style={({ isActive }) => isActive ? { fontSize: 15 } : { fontSize: 15 }}
        >
          {({ isActive }) => (
            <>
              <span
                className="shrink-0"
                style={{ color: isActive ? 'var(--accent)' : undefined }}
              >
                {item.icon}
              </span>
              <span>{item.label}</span>
              {isActive && (
                <span
                  className="ml-auto w-1.5 h-1.5 rounded-full shrink-0"
                  style={{ background: 'var(--accent)' }}
                />
              )}
            </>
          )}
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
      <div className="px-5 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
        <img
          src="/complio-logo.png"
          alt="Complio"
          style={{ height: '30px', width: 'auto', objectFit: 'contain' }}
        />
      </div>

      {/* Betrieb */}
      {betriebName && (
        <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2.5 px-1">
            <div
              className="w-7 h-7 rounded-md flex items-center justify-center shrink-0"
              style={{ background: 'var(--surface2)', border: '1px solid var(--border)' }}
            >
              <Building2 size={14} style={{ color: 'var(--text-muted)' }} />
            </div>
            <span className="text-sm font-medium truncate" style={{ color: 'var(--text-muted)' }}>
              {betriebName}
            </span>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto py-3 flex flex-col gap-0.5">
        {isAdmin ? (
          <>
            <p className="text-xs font-semibold uppercase tracking-widest px-5 pt-2 pb-2.5"
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
          className="flex items-center gap-3 font-medium mx-2 px-3.5 py-2.5 rounded-lg w-[calc(100%-16px)] transition-all cursor-pointer hover:bg-red-950/25 hover:text-red-400"
          style={{ color: 'var(--text-muted)', fontSize: 15 }}
        >
          <LogOut size={ICON} />
          <span>Abmelden</span>
        </button>
      </div>
    </aside>
  )
}
