import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { AppHeader } from '../../components/AppHeader'
import { SelectField } from '../../components/SelectField'
import { TextField } from '../../components/TextField'
import { errorMessage } from '../../lib/api'
import { formatDate, formatMinutes, formatTime } from '../../lib/format'
import { useAuth } from '../auth/AuthProvider'
import { fetchServices, type Service } from './adminApi'
import { downloadReport, fetchReport, type ExportFormat, type Report, type ReportFilters } from './reportsApi'
import './admin.css'
import './reports.css'

// Long tables show this many rows until the admin asks for the rest. Exports always include every row.
const PREVIEW_ROWS = 10

// YYYY-MM-DD in local time, the format <input type="date"> uses.
function localDate(date: Date) {
  const pad = (value: number) => String(value).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}

function defaultFilters(): ReportFilters {
  const end = new Date()
  const start = new Date(end)
  start.setDate(start.getDate() - 29)
  return { start: localDate(start), end: localDate(end), serviceId: '' }
}

function minutes(value: number | null) {
  return value === null ? '–' : formatMinutes(value)
}

function dateTime(value: string | null) {
  if (!value) return '–'
  const date = new Date(value)
  return `${formatDate(date)}, ${formatTime(date)}`
}

function hourRange(hour: number | null) {
  if (hour === null) return '–'
  const start = new Date(2000, 0, 1, hour)
  const end = new Date(2000, 0, 1, hour + 1)
  return `${formatTime(start)} – ${formatTime(end)}`
}

// Admin reporting module: queue usage statistics, service activity and each patient's
// participation, filtered by date range and service, exportable as CSV or PDF.
export function ReportsPage() {
  const { user, token, signOut } = useAuth()
  const navigate = useNavigate()
  const [services, setServices] = useState<Service[]>([])
  const [filters, setFilters] = useState<ReportFilters>(defaultFilters)
  // The latest response and which filters it answers. The previous report stays on screen
  // (dimmed) while a new one loads.
  const [loaded, setLoaded] = useState<{ key: string; report: Report | null; error: string | null } | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [exporting, setExporting] = useState<ExportFormat | null>(null)
  const [showAllPatients, setShowAllPatients] = useState(false)
  const [showAllVisits, setShowAllVisits] = useState(false)

  const rangeError =
    filters.start && filters.end && filters.start > filters.end
      ? 'The start date must be on or before the end date.'
      : undefined
  const filtersKey = JSON.stringify(filters)
  const isLoading = !rangeError && loaded?.key !== filtersKey
  const report = loaded?.report ?? null
  const error = exportError ?? (loaded?.key === filtersKey ? loaded.error : null)

  useEffect(() => {
    fetchServices(token)
      .then(setServices)
      .catch(() => setServices([]))
  }, [token])

  useEffect(() => {
    if (rangeError) return
    let cancelled = false
    fetchReport(filters, token)
      .then((data) => {
        if (!cancelled) setLoaded({ key: filtersKey, report: data, error: null })
      })
      .catch((caught) => {
        if (cancelled) return
        const message = errorMessage(caught, 'Could not load the report. Try again.')
        setLoaded((previous) => ({ key: filtersKey, report: previous?.report ?? null, error: message }))
      })
    return () => {
      cancelled = true
    }
  }, [filters, filtersKey, token, rangeError])

  const update = (changes: Partial<ReportFilters>) => {
    setFilters((current) => ({ ...current, ...changes }))
    setExportError(null)
    setShowAllPatients(false)
    setShowAllVisits(false)
  }

  const handleExport = async (format: ExportFormat) => {
    setExporting(format)
    setExportError(null)
    try {
      await downloadReport(filters, format, token)
    } catch (caught) {
      setExportError(errorMessage(caught, `Could not download the ${format.toUpperCase()} report. Try again.`))
    } finally {
      setExporting(null)
    }
  }

  const handleSignOut = () => {
    signOut()
    navigate('/login', { replace: true })
  }

  // RequireAdmin guarantees a signed-in admin.
  if (!user) return null

  const summary = report?.summary
  const patients = report ? (showAllPatients ? report.patients : report.patients.slice(0, PREVIEW_ROWS)) : []
  const visits = report ? (showAllVisits ? report.visits : report.visits.slice(0, PREVIEW_ROWS)) : []
  const canExport = !rangeError && !exporting

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
        <section className="admin-intro glass" aria-labelledby="reports-title">
          <div className="admin-intro__row">
            <div>
              <p className="admin-intro__eyebrow">Admin dashboard</p>
              <h1 id="reports-title">Reports</h1>
              <p className="admin-intro__note">
                Queue usage, service activity and patient visit history. Visits count by the day the patient joined.
              </p>
            </div>
            <div className="report-export" role="group" aria-label="Download report">
              <button type="button" className="btn btn-ghost" onClick={() => handleExport('csv')} disabled={!canExport}>
                {exporting === 'csv' ? 'Preparing…' : 'Download CSV'}
              </button>
              <button
                type="button"
                className="btn btn-primary"
                onClick={() => handleExport('pdf')}
                disabled={!canExport}
              >
                {exporting === 'pdf' ? 'Preparing…' : 'Download PDF'}
              </button>
            </div>
          </div>

          <form className="report-filters" aria-label="Report filters" onSubmit={(event) => event.preventDefault()}>
            <TextField
              label="From"
              type="date"
              value={filters.start}
              max={filters.end || undefined}
              onChange={(event) => update({ start: event.target.value })}
            />
            <TextField
              label="To"
              type="date"
              value={filters.end}
              min={filters.start || undefined}
              onChange={(event) => update({ end: event.target.value })}
              error={rangeError}
            />
            <SelectField
              label="Service"
              value={filters.serviceId}
              onChange={(event) => update({ serviceId: event.target.value })}
              options={[
                { value: '', label: 'All services' },
                ...services.map((service) => ({ value: service.id, label: service.name })),
              ]}
            />
            <button type="button" className="btn btn-ghost report-filters__reset" onClick={() => update(defaultFilters())}>
              Last 30 days
            </button>
            <button
              type="button"
              className="btn btn-ghost report-filters__reset"
              onClick={() => update({ start: '', end: '' })}
            >
              All time
            </button>
          </form>
        </section>

        {error && (
          <div className="alert alert-error" role="alert">
            {error}
          </div>
        )}

        {report === null && isLoading && <p className="service-list__loading">Loading report…</p>}

        {summary && (
          <div className={`report-body${isLoading ? ' report-body--stale' : ''}`} aria-busy={isLoading}>
            <section className="report-stats" aria-label="Queue usage statistics">
              <Stat label="Patients served" value={String(summary.served)} note={`of ${summary.totalVisits} visits`} />
              <Stat
                label="Average wait"
                value={minutes(summary.averageWaitMinutes)}
                note={summary.longestWaitMinutes === null ? 'served visits' : `longest ${minutes(summary.longestWaitMinutes)}`}
              />
              <Stat
                label="Served rate"
                value={summary.servedRate === null ? '–' : `${summary.servedRate}%`}
                note={`${summary.left} left the queue`}
              />
              <Stat label="Unique patients" value={String(summary.uniquePatients)} note="joined a queue" />
              <Stat label="Busiest hour" value={hourRange(summary.busiestHour)} note="most patients joined" />
              <Stat label="Waiting now" value={String(summary.waitingNow)} note="across these services" />
            </section>

            <section className="report-panel glass" aria-labelledby="report-services">
              <h2 id="report-services">Services</h2>
              <div className="report-table-wrap">
                <table className="report-table">
                  <thead>
                    <tr>
                      <th scope="col">Service</th>
                      <th scope="col">Status</th>
                      <th scope="col" className="num">Expected</th>
                      <th scope="col" className="num">Waiting now</th>
                      <th scope="col" className="num">Visits</th>
                      <th scope="col" className="num">Served</th>
                      <th scope="col" className="num">Left</th>
                      <th scope="col" className="num">Avg wait</th>
                      <th scope="col" className="num">Longest</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.services.map((service) => (
                      <tr key={service.serviceId}>
                        <th scope="row">
                          <span className="report-table__name">{service.name}</span>
                          {service.priority && <span className="report-table__sub report-table__sub--caps">{service.priority} priority</span>}
                        </th>
                        <td>
                          <span
                            className={`status-badge status-badge--${service.archived ? 'closed' : service.status}`}
                          >
                            {service.archived ? 'Archived' : service.status === 'open' ? 'Open' : 'Closed'}
                          </span>
                        </td>
                        <td className="num">{minutes(service.expectedDurationMinutes)}</td>
                        <td className="num">{service.waitingNow}</td>
                        <td className="num">{service.visits}</td>
                        <td className="num">{service.served}</td>
                        <td className="num">{service.left}</td>
                        <td className="num">{minutes(service.averageWaitMinutes)}</td>
                        <td className="num">{minutes(service.longestWaitMinutes)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="report-panel glass" aria-labelledby="report-patients">
              <h2 id="report-patients">Patients</h2>
              {report.patients.length === 0 ? (
                <p className="report-panel__empty">No patients joined a queue in this range.</p>
              ) : (
                <>
                  <div className="report-table-wrap">
                    <table className="report-table">
                      <thead>
                        <tr>
                          <th scope="col">Patient</th>
                          <th scope="col" className="num">Visits</th>
                          <th scope="col" className="num">Served</th>
                          <th scope="col" className="num">Left</th>
                          <th scope="col" className="num">Avg wait</th>
                          <th scope="col">Last visit</th>
                          <th scope="col">Services used</th>
                        </tr>
                      </thead>
                      <tbody>
                        {patients.map((patient) => (
                          <tr key={patient.userId}>
                            <th scope="row">
                              <span className="report-table__name">{patient.name}</span>
                              <span className="report-table__sub">{patient.email}</span>
                            </th>
                            <td className="num">{patient.visits}</td>
                            <td className="num">{patient.served}</td>
                            <td className="num">{patient.left}</td>
                            <td className="num">{minutes(patient.averageWaitMinutes)}</td>
                            <td>{dateTime(patient.lastVisitAt)}</td>
                            <td>{patient.services.join(', ')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <ShowMore
                    shown={patients.length}
                    total={report.patients.length}
                    expanded={showAllPatients}
                    onToggle={() => setShowAllPatients((shown) => !shown)}
                    noun="patients"
                  />
                </>
              )}
            </section>

            <section className="report-panel glass" aria-labelledby="report-visits">
              <h2 id="report-visits">Visit history</h2>
              {report.visits.length === 0 ? (
                <p className="report-panel__empty">No finished visits in this range.</p>
              ) : (
                <>
                  <div className="report-table-wrap">
                    <table className="report-table">
                      <thead>
                        <tr>
                          <th scope="col">Ticket</th>
                          <th scope="col">Patient</th>
                          <th scope="col">Service</th>
                          <th scope="col">Joined</th>
                          <th scope="col">Outcome</th>
                          <th scope="col" className="num">Waited</th>
                        </tr>
                      </thead>
                      <tbody>
                        {visits.map((visit) => (
                          <tr key={visit.id}>
                            <th scope="row">{visit.ticket}</th>
                            <td>
                              <span className="report-table__name">{visit.patientName}</span>
                              <span className="report-table__sub">{visit.email}</span>
                            </td>
                            <td>{visit.serviceName}</td>
                            <td>{dateTime(visit.joinedAt)}</td>
                            <td>
                              <span
                                className={`status-badge status-badge--${visit.outcome === 'served' ? 'open' : 'closed'}`}
                              >
                                {visit.outcome === 'served' ? 'Served' : 'Left'}
                              </span>
                            </td>
                            <td className="num">{minutes(visit.waitedMinutes)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <ShowMore
                    shown={visits.length}
                    total={report.visits.length}
                    expanded={showAllVisits}
                    onToggle={() => setShowAllVisits((shown) => !shown)}
                    noun="visits"
                  />
                </>
              )}
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="report-stat glass">
      <p className="report-stat__label">{label}</p>
      <p className="report-stat__value">{value}</p>
      <p className="report-stat__note">{note}</p>
    </div>
  )
}

type ShowMoreProps = { shown: number; total: number; expanded: boolean; onToggle: () => void; noun: string }

function ShowMore({ shown, total, expanded, onToggle, noun }: ShowMoreProps) {
  if (total <= PREVIEW_ROWS) return null
  return (
    <div className="report-panel__more">
      <span>
        Showing {shown} of {total} {noun}
      </span>
      <button type="button" className="btn btn-ghost" onClick={onToggle}>
        {expanded ? 'Show fewer' : `Show all ${total}`}
      </button>
    </div>
  )
}
