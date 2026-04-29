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
  CalendarRange,
  Building2,
} from 'lucide-react'

interface NavItem {
  to: string
  icon: ReactNode
  label: string
}

const ADMIN_NAV: NavItem[] = [
  { to: '/admin',               icon: <LayoutDashboard size={18} />, label: 'Übersicht' },
  { to: '/admin/mitarbeiter',   icon: <Users size={18} />,           label: 'Mitarbeiter' },
  { to: '/admin/dienstplan',    icon: <CalendarRange size={18} />,   label: 'Dienstplan' },
  { to: '/admin/zeiten',        icon: <Clock size={18} />,           label: 'Zeiterfassung' },
  { to: '/admin/urlaub',        icon: <CalendarDays size={18} />,    label: 'Urlaub' },
  { to: '/admin/lohn',          icon: <DollarSign size={18} />,      label: 'Lohn' },
  { to: '/admin/dokumente',     icon: <FileText size={18} />,        label: 'Dokumente' },
  { to: '/admin/kiosk',         icon: <Timer size={18} />,           label: 'Kiosk' },
]

const ADMIN_BOTTOM_NAV: NavItem[] = [
  { to: '/admin/einstellungen', icon: <Settings size={18} />,        label: 'Einstellungen' },
]

const MITARBEITER_NAV: NavItem[] = [
  { to: '/dashboard',         icon: <LayoutDashboard size={18} />, label: 'Übersicht' },
  { to: '/dashboard/zeiten',  icon: <Clock size={18} />,           label: 'Meine Zeiten' },
  { to: '/dashboard/urlaub',  icon: <CalendarDays size={18} />,    label: 'Urlaub' },
]

const navClass = (isActive: boolean) =>
  `flex items-center gap-3 px-3 py-2.5 mx-2 rounded-lg text-sm font-medium transition-all ${
    isActive
      ? 'bg-orange-500/10 text-[#F97316] border border-orange-500/20'
      : 'text-[#888] hover:text-[#ebebeb] hover:bg-[#1a1a1a] border border-transparent'
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
      style={{
        width: 'var(--sidebar-w)',
        background: '#0c0c0c',
        borderRight: '1px solid var(--border)',
      }}
    >
      {/* Logo */}
      <div className="px-5 py-5" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-lg flex items-center justify-center text-white text-xs font-bold"
            style={{ background: 'var(--accent)' }}
          >
            C
          </div>
          <div>
            <p className="font-bold text-base leading-none">
              comp<span style={{ color: 'var(--accent)' }}>lio</span>
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>HR-Software</p>
          </div>
        </div>
      </div>

      {/* Betrieb */}
      {betriebName && (
        <div className="px-4 py-3" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2">
            <Building2 size={13} style={{ color: 'var(--text-muted)' }} />
            <p className="text-xs truncate font-medium" style={{ color: 'var(--text-muted)' }}>
              {betriebName}
            </p>
          </div>
        </div>
      )}

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto flex flex-col gap-0.5">
        {isAdmin ? (
          <>
            <p className="text-[10px] font-semibold uppercase tracking-widest px-5 py-2 mt-1"
              style={{ color: 'var(--text-muted)' }}>
              Verwaltung
            </p>
            <NavGroup items={ADMIN_NAV} />
          </>
        ) : (
          <NavGroup items={MITARBEITER_NAV} />
        )}
      </nav>

      {/* Bottom */}
      <div className="py-3" style={{ borderTop: '1px solid var(--border)' }}>
        {isAdmin && (
          <div className="mb-1">
            <NavGroup items={ADMIN_BOTTOM_NAV} />
          </div>
        )}
        <button
          onClick={() => { logout(); navigate('/login') }}
          className="flex items-center gap-3 text-sm w-full px-3 py-2.5 mx-2 rounded-lg hover:bg-[#1a1a1a] transition-all cursor-pointer border border-transparent"
          style={{ color: 'var(--text-muted)', width: 'calc(100% - 16px)' }}
        >
          <LogOut size={18} />
          <span>Abmelden</span>
        </button>
      </div>
    </aside>
  )
}
