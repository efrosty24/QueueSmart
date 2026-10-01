const timeFormat = new Intl.DateTimeFormat(undefined, { hour: 'numeric', minute: '2-digit' })
const dateFormat = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

export function formatTime(date: Date | number) {
  return timeFormat.format(date)
}

export function formatDate(date: Date | number) {
  return dateFormat.format(date)
}

// "About 1 hr 5 min" style durations for wait estimates.
export function formatMinutes(minutes: number) {
  if (minutes < 1) return 'Less than a minute'
  const hours = Math.floor(minutes / 60)
  const rest = Math.round(minutes % 60)
  if (hours === 0) return `${rest} min`
  return rest === 0 ? `${hours} hr` : `${hours} hr ${rest} min`
}
