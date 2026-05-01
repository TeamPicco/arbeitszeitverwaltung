import { type ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import {
  LayoutDashboard, Users, Clock, CalendarDays, FileText,
  DollarSign, Settings, LogOut, Timer, CalendarRange, Building2,
} from 'lucide-react'

interface NavItem { to: string; icon: ReactNode; label: string }

const ADMIN_NAV: NavItem[] = [
  { to: '/admin',               icon: <LayoutDashboard size={22} />, label: 'Übersicht' },
  { to: '/admin/mitarbeiter',   icon: <Users size={22} />,           label: 'Mitarbeiter' },
  { to: '/admin/dienstplan',    icon: <CalendarRange size={22} />,   label: 'Dienstplan' },
  { to: '/admin/zeiten',        icon: <Clock size={22} />,           label: 'Zeiterfassung' },
  { to: '/admin/urlaub',        icon: <CalendarDays size={22} />,    label: 'Urlaub' },
  { to: '/admin/lohn',          icon: <DollarSign size={22} />,      label: 'Lohn' },
  { to: '/admin/dokumente',     icon: <FileText size={22} />,        label: 'Dokumente' },
  { to: '/admin/kiosk',         icon: <Timer size={22} />,           label: 'Kiosk' },
]

const ADMIN_BOTTOM_NAV: NavItem[] = [
  { to: '/admin/einstellungen', icon: <Settings size={22} />, label: 'Einstellungen' },
]

const MITARBEITER_NAV: NavItem[] = [
  { to: '/dashboard',              icon: <LayoutDashboard size={22} />, label: 'Übersicht' },
  { to: '/dashboard/zeiten',       icon: <Clock size={22} />,           label: 'Meine Zeiten' },
  { to: '/dashboard/urlaub',       icon: <CalendarDays size={22} />,    label: 'Urlaub' },
  { to: '/dashboard/dienstplan',   icon: <CalendarRange size={22} />,   label: 'Mein Dienstplan' },
]

const navClass = (isActive: boolean) =>
  `flex items-center gap-4 px-5 py-3.5 mx-3 rounded-xl font-medium transition-all text-base ${
    isActive
      ? 'bg-orange-500/10 text-[#F97316] border border-orange-500/20'
      : 'text-[#999] hover:text-[#f2f2f2] hover:bg-white/5 border border-transparent'
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
      style={{ width: 'var(--sidebar-w)', background: '#0a0a0a', borderRight: '1px solid var(--border)' }}
    >
      {/* Logo */}
      <div className="px-6 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
        <img
          src="/complio-logo.png"
          alt="Complio"
          style={{ height: '38px', width: 'auto', objectFit: 'contain' }}
        />
      </div>

      {/* Betrieb */}
      {betriebName && (
        <div className="px-6 py-4" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2.5">
            <Building2 size={16} style={{ color: 'var(--accent)', opacity: 0.8 }} />
            <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-muted)' }}>
              {betriebName}
            </p>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-5 overflow-y-auto flex flex-col gap-1">
        {isAdmin ? (
          <>
            <p className="text-xs font-bold uppercase tracking-widest px-7 pb-3"
              style={{ color: '#555' }}>
              Verwaltung
            </p>
            <NavGroup items={ADMIN_NAV} />
          </>
        ) : (
          <NavGroup items={MITARBEITER_NAV} />
        )}
      </nav>

      {/* Bottom */}
      <div className="py-4" style={{ borderTop: '1px solid var(--border)' }}>
        {isAdmin && <div className="mb-1"><NavGroup items={ADMIN_BOTTOM_NAV} /></div>}
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="flex items-center gap-4 text-base font-medium mx-3 px-5 py-3.5 rounded-xl hover:bg-white/5 transition-all cursor-pointer border border-transparent"
          style={{ color: 'var(--text-muted)', width: 'calc(100% - 24px)' }}
        >
          <LogOut size={22} />
          <span>Abmelden</span>
        </button>
      </div>
    </aside>
  )
}
