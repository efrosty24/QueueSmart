import { PageHeader } from '../../components/PageHeader'
import { NotificationsPanel } from './NotificationsPanel'

export function NotificationsPage() {
  return (
    <>
      <PageHeader
        title="Notifications"
        description="Queue updates and status changes, newest first."
      />
      <NotificationsPanel />
    </>
  )
}