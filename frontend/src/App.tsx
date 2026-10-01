import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { AppShell } from './components/AppShell'
import { AuthProvider, useAuth } from './features/auth/AuthProvider'
import { LoginPage } from './features/auth/LoginPage'
import { RegisterPage } from './features/auth/RegisterPage'
import { RedirectIfSignedIn, RequireAuth } from './features/auth/RouteGuards'
import { DashboardPage } from './features/dashboard/DashboardPage'
import { HistoryPage } from './features/history/HistoryPage'
import { JoinQueuePage } from './features/join/JoinQueuePage'
import { QueueStatusPage } from './features/queue/QueueStatusPage'
import { ThemeProvider } from './theme/ThemeProvider'
import { NotificationsPage } from './features/notifications/NotificationsPage'
import { NotificationsProvider } from './features/notifications/NotificationsProvider'
import { QueueProvider } from './features/queue/QueueProvider'

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
              <Route element={<SignedInLayout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/join-queue" element={<JoinQueuePage />} />
                <Route path="/queue" element={<QueueStatusPage />} />
                <Route path="/history" element={<HistoryPage />} />
                <Route path="/notifications" element={<NotificationsPage />} />
              </Route>
            </Route>

            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  )
}

function SignedInLayout() {
  const { user } = useAuth()

  if (!user) return null

  return (
    <QueueProvider key={`${user.role}:${user.email}`}>
      <NotificationsProvider>
        <AppShell />
      </NotificationsProvider>
    </QueueProvider>
  )
}