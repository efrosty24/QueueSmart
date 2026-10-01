import assert from 'node:assert/strict'
import { after, test } from 'node:test'
import { createServer } from 'vite'
import { createElement } from 'react'
import { renderToStaticMarkup } from 'react-dom/server'

// Load the actual TypeScript modules through the project's existing Vite dependency.
const server = await createServer({ configFile: false, server: { middlewareMode: true }, appType: 'custom' })
after(() => server.close())
const storage = new Map()
globalThis.sessionStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
}
globalThis.window = new EventTarget()
const { readQueueSession, joinService, leaveService, queueVisits, startDemo } =
  await server.ssrLoadModule('/src/features/queue/queueSession.ts')
const { deriveQueueState } = await server.ssrLoadModule('/src/features/queue/queueStatus.ts')
const joinedAt = Date.parse('2026-09-30T12:00:00Z')

test('new student has no queue; closed and unknown services cannot be joined', () => {
  const email = 'empty@example.test'
  assert.equal(readQueueSession(email).entry, null)
  assert.match(joinService(email, 'lab-work', joinedAt), /closed/)
  assert.match(joinService(email, 'unknown', joinedAt), /closed/)
  assert.equal(readQueueSession(email).entry, null)
})

test('join uses the selected service and correct estimate; duplicate joins preserve the ticket', () => {
  const email = 'join@example.test'
  assert.equal(joinService(email, 'flu-shot', joinedAt), undefined)
  const entry = readQueueSession(email).entry
  const queue = deriveQueueState(joinedAt, joinedAt, entry)
  assert.equal(queue.service.id, 'flu-shot')
  assert.equal(queue.position, 3)
  assert.equal(queue.estimatedWaitMinutes, 10)
  assert.match(joinService(email, 'sick-visit', joinedAt), /already have/)
  assert.equal(readQueueSession(email).entry.id, entry.id)
  assert.equal(deriveQueueState(joinedAt, joinedAt + 15_000, entry).status, 'almost-ready')
})

test('leave removes the active queue, records its outcome once, and allows another service', () => {
  const email = 'leave@example.test'
  joinService(email, 'sick-visit', joinedAt)
  assert.equal(leaveService(email, joinedAt + 10_000), true)
  assert.equal(readQueueSession(email).entry, null)
  assert.equal(leaveService(email, joinedAt + 11_000), false)
  const visits = queueVisits(email, joinedAt + 11_000)
  assert.equal(visits.length, 1)
  assert.equal(visits[0].outcome, 'left')
  assert.equal(visits[0].serviceId, 'sick-visit')
  assert.equal(joinService(email, 'prescription-refill', joinedAt + 12_000), undefined)
})

test('completed visits persist when a new queue is joined and cannot be marked left', () => {
  const email = 'served@example.test'
  joinService(email, 'prescription-refill', joinedAt)
  const entry = readQueueSession(email).entry
  assert.equal(deriveQueueState(joinedAt, joinedAt, entry).estimatedWaitMinutes, 0)
  assert.equal(deriveQueueState(joinedAt, joinedAt + 15_000, entry).status, 'served')
  assert.equal(leaveService(email, joinedAt + 15_000), false)
  assert.equal(queueVisits(email, joinedAt + 15_000)[0].outcome, 'served')
  joinService(email, 'flu-shot', joinedAt + 16_000)
  assert.equal(queueVisits(email, joinedAt + 16_000).length, 1)
  assert.equal(queueVisits(email, joinedAt + 70_000).length, 2)
  assert.equal(new Set(queueVisits(email, joinedAt + 70_000).map((visit) => visit.id)).size, 2)
})

test('queue sessions are isolated by student and restore valid saved state', () => {
  assert.equal(readQueueSession('other@example.test').entry, null)
  const saved = storage.get('queuesmart-queue-v2:join@example.test')
  storage.set('queuesmart-queue-v2:restored@example.test', saved)
  assert.equal(readQueueSession('restored@example.test').entry.serviceId, 'flu-shot')
  storage.set('queuesmart-queue-v2:broken@example.test', '{bad json')
  assert.equal(readQueueSession('broken@example.test').entry, null)
  storage.set('queuesmart-queue-v2:invalid@example.test', JSON.stringify({ entry: { serviceId: 'missing' }, visits: [] }))
  assert.equal(readQueueSession('invalid@example.test').entry, null)
})

test('mock demo remains available and preserves the priority-delay timeline', () => {
  const email = 'demo@example.test'
  startDemo(email)
  const entry = readQueueSession(email).entry
  const queue = deriveQueueState(entry.joinedAt, entry.joinedAt + 30_000, entry)
  assert.equal(queue.updates[0].kind, 'delayed')
  assert.equal(queue.position, 5)
})

test('merged providers handle empty, joined, left and served queues consistently', async () => {
  const { AuthProvider } = await server.ssrLoadModule('/src/features/auth/AuthProvider.tsx')
  const { QueueProvider, useQueue } = await server.ssrLoadModule('/src/features/queue/QueueProvider.tsx')
  const { NotificationsProvider, useNotifications } =
    await server.ssrLoadModule('/src/features/notifications/NotificationsProvider.tsx')
  const email = 'notifications@example.test'
  globalThis.localStorage = {
    getItem: (key) => key === 'queuesmart-session' ? JSON.stringify({ email, role: 'patient' }) : null,
  }

  function snapshot() {
    let result
    function Probe() {
      const { queue } = useQueue()
      const { notifications, unreadCount } = useNotifications()
      result = { queue, notifications, unreadCount }
      return null
    }
    renderToStaticMarkup(createElement(AuthProvider, null,
      createElement(QueueProvider, null, createElement(NotificationsProvider, null, createElement(Probe)))))
    return result
  }

  assert.equal(snapshot().queue, null)
  assert.equal(snapshot().unreadCount, 0)
  const now = Date.now()
  joinService(email, 'flu-shot', now)
  const joined = snapshot()
  assert.equal(joined.queue.service.id, 'flu-shot')
  assert.equal(joined.unreadCount, 1)
  assert.match(joined.notifications[0].message, /Flu Shot/)
  leaveService(email, now + 1)
  assert.equal(snapshot().queue, null)
  assert.deepEqual(snapshot().notifications, [])
  joinService(email, 'sick-visit', now - 150_000)
  const served = snapshot()
  assert.equal(served.queue.status, 'served')
  assert.equal(served.notifications[0].title, 'Served')
  assert.match(served.notifications[0].message, /Sick Visit/)
})
