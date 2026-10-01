import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AdminDashboardPage } from './features/admin/AdminDashboardPage'
import { ServiceManagementPage } from './features/admin/ServiceManagementPage'
import { AuthProvider } from './features/auth/AuthProvider'
import { LoginPage } from './features/auth/LoginPage'
import { RegisterPage } from './features/auth/RegisterPage'
import { RedirectIfSignedIn, RequireAdmin, RequireAuth } from './features/auth/RouteGuards'
import { DashboardPage } from './features/dashboard/DashboardPage'
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
              <Route path="/dashboard" element={<DashboardPage />} />
            </Route>
            <Route element={<RequireAdmin />}>
              <Route path="/admin" element={<AdminDashboardPage />} />
              <Route path="/admin/services" element={<ServiceManagementPage />} />
            </Route>
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}
