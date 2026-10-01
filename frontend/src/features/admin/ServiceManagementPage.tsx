import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { AppHeader } from '../../components/AppHeader'
import { ConfirmDialog } from '../../components/ConfirmDialog'
import { useAuth } from '../auth/AuthProvider'
import {
  createService,
  deleteService,
  fetchServices,
  updateService,
  type Service,
  type ServiceInput,
} from './adminApi'
import { ServiceFormDialog } from './ServiceFormDialog'
import './admin.css'

// Lets admins create new services and edit the details of existing ones.
export function ServiceManagementPage() {
  const { user, signOut } = useAuth()
  const navigate = useNavigate()
  const [services, setServices] = useState<Service[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [editingService, setEditingService] = useState<Service | null>(null)
  const [deletingService, setDeletingService] = useState<Service | null>(null)
  const [isDeleting, setIsDeleting] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchServices()
      .then((data) => {
        if (!cancelled) setServices(data)
      })
      .catch(() => {
        if (!cancelled) setError('Could not load services. Try refreshing the page.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const handleSignOut = () => {
    signOut()
    navigate('/login', { replace: true })
  }

  const handleCreate = async (input: ServiceInput) => {
    const created = await createService(input)
    setServices((current) => (current ? [...current, created] : [created]))
    setIsCreating(false)
  }

  const handleUpdate = async (input: ServiceInput) => {
    if (!editingService) return
    const updated = await updateService(editingService.id, input)
    setServices((current) => current?.map((service) => (service.id === updated.id ? updated : service)) ?? current)
    setEditingService(null)
  }

  const handleDelete = async () => {
    if (!deletingService) return
    setIsDeleting(true)
    try {
      await deleteService(deletingService.id)
      setServices((current) => current?.filter((service) => service.id !== deletingService.id) ?? current)
      setDeletingService(null)
    } catch {
      setError(`Could not delete ${deletingService.name}. Try again.`)
    } finally {
      setIsDeleting(false)
    }
  }

  // RequireAdmin guarantees a signed-in admin.
  if (!user) return null

  return (
    <div className="admin-page">
      <AppHeader
        actions={
          <>
            <Link to="/admin" className="btn btn-ghost">
              Back to dashboard
            </Link>
            <button type="button" className="btn btn-ghost" onClick={handleSignOut}>
              Sign out
            </button>
          </>
        }
      />

      <main className="admin-page__main">
        <section className="admin-intro glass" aria-labelledby="services-title">
          <div className="admin-intro__row">
            <div>
              <p className="admin-intro__eyebrow">Admin dashboard</p>
              <h1 id="services-title">Manage services</h1>
              <p className="admin-intro__note">Create new services or edit the ones patients can join.</p>
            </div>
            <button type="button" className="btn btn-primary" onClick={() => setIsCreating(true)}>
              Add service
            </button>
          </div>
        </section>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        <section className="service-list" aria-label="Services">
          {services === null && !error && <p className="service-list__loading">Loading services…</p>}
          {services?.map((service) => (
            <article key={service.id} className="service-card glass">
              <div className="service-card__info">
                <h2 className="service-card__name">{service.name}</h2>
                <span className={`priority-badge priority-badge--${service.priority}`}>{service.priority}</span>
              </div>
              <p className="service-card__description">{service.description}</p>
              <p className="service-card__duration">~{service.expectedDurationMinutes} min</p>
              <div className="service-card__actions">
                <button type="button" className="btn btn-ghost" onClick={() => setEditingService(service)}>
                  Edit
                </button>
                <button type="button" className="btn btn-danger" onClick={() => setDeletingService(service)}>
                  Delete
                </button>
              </div>
            </article>
          ))}
        </section>
      </main>

      {isCreating && <ServiceFormDialog service={null} onClose={() => setIsCreating(false)} onSubmit={handleCreate} />}
      {editingService && (
        <ServiceFormDialog service={editingService} onClose={() => setEditingService(null)} onSubmit={handleUpdate} />
      )}
      {deletingService && (
        <ConfirmDialog
          title="Delete service?"
          message={`"${deletingService.name}" will be removed and patients will no longer be able to join its queue. This can't be undone.`}
          confirmLabel="Delete"
          pending={isDeleting}
          onConfirm={handleDelete}
          onCancel={() => setDeletingService(null)}
        />
      )}
    </div>
  )
}
