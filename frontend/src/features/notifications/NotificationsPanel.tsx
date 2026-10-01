// Provides the dashboard preview and full notification list

import { useId, useState } from 'react'
import { LuArrowRight } from 'react-icons/lu'
import { Link } from 'react-router'
import { formatDate, formatTime } from '../../lib/format'
import { useNotifications } from './NotificationsProvider'
import './notifications.css'

export function NotificationsPanel({ preview = false }: { preview?: boolean }) {
  const titleId = useId()
  const [unreadOnly, setUnreadOnly] = useState(false)
  const { notifications, unreadCount, markRead, markAllRead } =
    useNotifications()

  const shown = preview
    ? notifications.slice(0, 3)
    : notifications.filter((item) => !unreadOnly || !item.read)

  return (
    <section
      className={`notifications-panel glass${preview ? ' notifications-panel--preview' : ''}`}
      aria-labelledby={titleId}
    >
      <div className="notifications-toolbar">
        <h2 id={titleId}>
          {preview ? 'Recent notifications' : 'Queue notifications'}
        </h2>

        <span className="badge badge-primary" role="status" aria-atomic="true">
          {unreadCount} unread
        </span>

        {!preview && (
          <button
            type="button"
            className="btn btn-ghost btn-pill"
            disabled={unreadCount === 0}
            onClick={markAllRead}
          >
            Mark all as read
          </button>
        )}
      </div>

      {!preview && (
        <div
          className="notifications-toolbar"
          role="group"
          aria-label="Filter notifications"
        >
          <button
            type="button"
            className="btn btn-ghost btn-pill notifications-filter"
            aria-pressed={!unreadOnly}
            onClick={() => setUnreadOnly(false)}
          >
            All
          </button>
          <button
            type="button"
            className="btn btn-ghost btn-pill notifications-filter"
            aria-pressed={unreadOnly}
            onClick={() => setUnreadOnly(true)}
          >
            Unread
          </button>
        </div>
      )}

      {shown.length === 0 ? (
        <p className="notifications-muted">
          {unreadOnly ? 'You have no unread notifications.' : 'No notifications yet.'}
        </p>
      ) : (
        <ol className="notifications-list">
          {shown.map((item) => (
            <li
              key={item.id}
              className="notification"
              data-unread={!item.read}
            >
              <div className="notifications-toolbar">
                <span className="badge badge-neutral">
                  {item.category === 'queue' ? 'Queue update' : 'Status change'}
                </span>
                <span className="notifications-muted">
                  {item.read ? 'Read' : 'Unread'}
                </span>
              </div>

              <h3>{item.title}</h3>
              <p>{item.message}</p>

              <time
                className="notifications-muted"
                dateTime={new Date(item.at).toISOString()}
              >
                {formatDate(item.at)} · {formatTime(item.at)}
              </time>

              <div className="notifications-toolbar">
                <Link to="/queue" onClick={() => markRead(item.id)}>
                  View queue
                  <span className="visually-hidden">: {item.title}</span>
                </Link>

                {!preview && (
                  <button
                    type="button"
                    className="btn btn-ghost btn-pill"
                    disabled={item.read}
                    aria-label={`Mark "${item.title}" as read`}
                    onClick={() => markRead(item.id)}
                  >
                    Mark as read
                  </button>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}

      {preview && (
        <Link to="/notifications" className="notifications-link">
          View all notifications <LuArrowRight aria-hidden="true" />
        </Link>
      )}
    </section>
  )
}