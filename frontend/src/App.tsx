import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AppShell } from './components/AppShell'
import { AdminDashboardPage } from './features/admin/AdminDashboardPage'
import { QueueManagementPage } from './features/admin/QueueManagementPage'
import { ServiceManagementPage } from './features/admin/ServiceManagementPage'
import { AuthProvider } from './features/auth/AuthProvider'
import { LoginPage } from './features/auth/LoginPage'
import { RegisterPage } from './features/auth/RegisterPage'
import { RedirectIfSignedIn, RequireAdmin, RequireAuth } from './features/auth/RouteGuards'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { HistoryPage } from './features/history/HistoryPage'
import { QueueStatusPage } from './features/queue/QueueStatusPage'
import { ThemeProvider } from './theme/ThemeProvider'

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<RedirectIfSignedIn />}>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/register" element={<RegisterPage />} />
            </Route>
            <Route element={<RequireAuth />}>
              <Route element={<AppShell />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/queue" element={<QueueStatusPage />} />
                <Route path="/history" element={<HistoryPage />} />
              </Route>
            </Route>
            <Route element={<RequireAdmin />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
              <Route path="/admin/services" element={<ServiceManagementPage />} />
              <Route path="/admin/queue" element={<QueueManagementPage />} />
              <Route path="/admin/queue/:serviceId" element={<QueueManagementPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
