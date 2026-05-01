import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/auth'
import { Layout } from './components/Layout'
import { LoginPage } from './pages/LoginPage'
import { AdminDashboard } from './pages/admin/Dashboard'
import { AdminMitarbeiter } from './pages/admin/Mitarbeiter'
import { AdminZeiten } from './pages/admin/Zeiten'
import { AdminUrlaub } from './pages/admin/Urlaub'
import { AdminEinstellungen } from './pages/admin/Einstellungen'
import { AdminLohn } from './pages/admin/Lohn'
import { AdminDokumente } from './pages/admin/Dokumente'
import { AdminDienstplan } from './pages/admin/Dienstplan'
import { KioskTerminal } from './pages/admin/KioskTerminal'
import { MitarbeiterDashboard } from './pages/mitarbeiter/Dashboard'
import { MeineZeiten } from './pages/mitarbeiter/MeineZeiten'
import { MeinUrlaub } from './pages/mitarbeiter/MeinUrlaub'
import { MeinDienstplan } from './pages/mitarbeiter/MeinDienstplan'

function RequireAuth({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token)
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

function RequireAdmin({ children }: { children: React.ReactNode }) {
  const role = useAuthStore((s) => s.role)
  if (!role) return <Navigate to="/login" replace />
  if (role !== 'admin' && role !== 'superadmin') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Kiosk — full-screen, no sidebar */}
      <Route
        path="/kiosk"
        element={
          <RequireAuth>
            <KioskTerminal />
          </RequireAuth>
        }
      />

      {/* Admin */}
      <Route
        path="/admin/*"
        element={
          <RequireAuth>
            <RequireAdmin>
              <Layout>
                <Routes>
                  <Route index element={<AdminDashboard />} />
                  <Route path="mitarbeiter" element={<AdminMitarbeiter />} />
                  <Route path="dienstplan" element={<AdminDienstplan />} />
                  <Route path="zeiten" element={<AdminZeiten />} />
                  <Route path="urlaub" element={<AdminUrlaub />} />
                  <Route path="lohn" element={<AdminLohn />} />
                  <Route path="dokumente" element={<AdminDokumente />} />
                  <Route path="kiosk" element={<KioskTerminal />} />
                  <Route path="einstellungen" element={<AdminEinstellungen />} />
                </Routes>
              </Layout>
            </RequireAdmin>
          </RequireAuth>
        }
      />

      {/* Mitarbeiter */}
      <Route
        path="/dashboard/*"
        element={
          <RequireAuth>
            <Layout>
              <Routes>
                <Route index element={<MitarbeiterDashboard />} />
                <Route path="zeiten" element={<MeineZeiten />} />
                <Route path="urlaub" element={<MeinUrlaub />} />
                <Route path="dienstplan" element={<MeinDienstplan />} />
              </Routes>
            </Layout>
          </RequireAuth>
        }
      />

      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
