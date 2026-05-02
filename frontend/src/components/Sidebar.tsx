import { type ReactNode, useState, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/auth'
import {
  LayoutDashboard, Users, Clock, CalendarDays, FileText,
  DollarSign, Settings, LogOut, Timer, CalendarRange, Building2, Shield, Sun, Moon, TrendingUp,
} from 'lucide-react'

interface NavItem { to: string; icon: ReactNode; label: string; badge?: string }

const ADMIN_NAV: NavItem[] = [
  { to: '/admin',               icon: <LayoutDashboard size={17} />, label: 'Übersicht' },
  { to: '/admin/mitarbeiter',   icon: <Users size={17} />,           label: 'Mitarbeiter' },
  { to: '/admin/dienstplan',    icon: <CalendarRange size={17} />,   label: 'Dienstplan' },
  { to: '/admin/zeiten',        icon: <Clock size={17} />,           label: 'Zeiterfassung' },
  { to: '/admin/urlaub',        icon: <CalendarDays size={17} />,    label: 'Urlaub' },
  { to: '/admin/lohn',          icon: <DollarSign size={17} />,      label: 'Lohn' },
  { to: '/admin/dokumente',     icon: <FileText size={17} />,        label: 'Dokumente' },
  { to: '/admin/premium',       icon: <Shield size={17} />,          label: 'Premium', badge: 'PRO' },
  { to: '/admin/kiosk',         icon: <Timer size={17} />,           label: 'Kiosk' },
  { to: '/admin/leads',         icon: <TrendingUp size={17} />,      label: 'Leads' },
]

const ADMIN_BOTTOM_NAV: NavItem[] = [
  { to: '/admin/einstellungen', icon: <Settings size={17} />, label: 'Einstellungen' },
]

const MITARBEITER_NAV: NavItem[] = [
  { to: '/dashboard',            icon: <LayoutDashboard size={17} />, label: 'Übersicht' },
  { to: '/dashboard/zeiten',     icon: <Clock size={17} />,           label: 'Meine Zeiten' },
  { to: '/dashboard/urlaub',     icon: <CalendarDays size={17} />,    label: 'Urlaub' },
  { to: '/dashboard/dienstplan', icon: <CalendarRange size={17} />,   label: 'Mein Dienstplan' },
]

function NavItemLink({ item }: { item: NavItem }) {
  return (
    <NavLink
      to={item.to}
      end={item.to === '/admin' || item.to === '/dashboard'}
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        padding: '9px 14px',
        margin: '1px 10px',
        borderRadius: 8,
        fontSize: 14,
        fontWeight: 500,
        textDecoration: 'none',
        borderLeft: isActive ? '3px solid #FF6B00' : '3px solid transparent',
        background: isActive ? 'rgba(255,107,0,0.09)' : 'transparent',
        color: isActive ? '#FFFFFF' : '#9A9A9A',
        transition: 'all 0.15s ease',
      })}
      className="sidebar-link"
    >
      {({ isActive }) => (
        <>
          <span style={{ color: isActive ? '#FF6B00' : '#9A9A9A', flexShrink: 0 }}>
            {item.icon}
          </span>
          <span style={{ flex: 1 }}>{item.label}</span>
          {item.badge && (
            <span style={{
              fontSize: 10,
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: 4,
              background: 'rgba(255,107,0,0.2)',
              color: '#FF6B00',
              letterSpacing: '0.05em',
            }}>
              {item.badge}
            </span>
          )}
        </>
      )}
    </NavLink>
  )
}

function NavGroup({ items }: { items: NavItem[] }) {
  return (
    <>
      {items.map((item) => (
        <NavItemLink key={item.to} item={item} />
      ))}
    </>
  )
}

function useDarkMode() {
  const [dark, setDark] = useState(() => localStorage.getItem('complio-theme') === 'dark')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('complio-theme', dark ? 'dark' : 'light')
  }, [dark])

  return [dark, () => setDark((v) => !v)] as const
}

export function Sidebar({ isAdmin }: { isAdmin: boolean }) {
  const navigate = useNavigate()
  const { betriebName, logout } = useAuthStore()
  const [isDark, toggleDark] = useDarkMode()

  return (
    <>
      <style>{`
        .sidebar-link:hover { color: #FFFFFF !important; background: rgba(255,255,255,0.06) !important; }
        .sidebar-link:hover span:first-child { color: #FFFFFF !important; }
      `}</style>
      <aside
        className="flex flex-col shrink-0 h-screen sticky top-0"
        style={{ width: 'var(--sidebar-w)', background: '#0A0A0A', borderRight: '1px solid #1A1A1A' }}
      >
        {/* Logo */}
        <div style={{ padding: '20px 20px 18px', borderBottom: '1px solid #1A1A1A' }}>
          <img
            src="/complio-logo.png"
            alt="Complio"
            style={{ height: 30, width: 'auto', objectFit: 'contain' }}
          />
        </div>

        {/* Betrieb */}
        {betriebName && (
          <div style={{ padding: '10px 20px', borderBottom: '1px solid #1A1A1A' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 26, height: 26, borderRadius: 6,
                background: '#1A1A1A', border: '1px solid #2A2A2A',
                display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
              }}>
                <Building2 size={13} color="#FF6B00" />
              </div>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#CCCCCC', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {betriebName}
              </span>
            </div>
          </div>
        )}

        {/* Nav */}
        <nav style={{ flex: 1, overflowY: 'auto', padding: '10px 0' }}>
          {isAdmin ? (
            <>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase', color: '#444', padding: '12px 24px 8px' }}>
                Verwaltung
              </p>
              <NavGroup items={ADMIN_NAV} />
            </>
          ) : (
            <NavGroup items={MITARBEITER_NAV} />
          )}
        </nav>

        {/* Bottom */}
        <div style={{ borderTop: '1px solid #1A1A1A', padding: '8px 0' }}>
          {isAdmin && (
            <div style={{ marginBottom: 4 }}>
              <NavGroup items={ADMIN_BOTTOM_NAV} />
            </div>
          )}
          {/* Dark/Light Toggle */}
          <button
            onClick={toggleDark}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 14px', margin: '1px 10px',
              borderRadius: 8, fontSize: 14, fontWeight: 500,
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: '#9A9A9A', width: 'calc(100% - 20px)',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.06)'; e.currentTarget.style.color = '#FFFFFF' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#9A9A9A' }}
          >
            {isDark ? <Sun size={17} /> : <Moon size={17} />}
            <span>{isDark ? 'Hell' : 'Dunkel'}</span>
          </button>
          <button
            onClick={() => { logout(); navigate('/login') }}
            style={{
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '9px 14px', margin: '1px 10px',
              borderRadius: 8, fontSize: 14, fontWeight: 500,
              background: 'transparent', border: 'none', cursor: 'pointer',
              color: '#9A9A9A', width: 'calc(100% - 20px)',
              transition: 'all 0.15s ease',
            }}
            onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(220,38,38,0.1)'; e.currentTarget.style.color = '#F87171' }}
            onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = '#9A9A9A' }}
          >
            <LogOut size={17} />
            <span>Abmelden</span>
          </button>
        </div>
      </aside>
    </>
  )
}
