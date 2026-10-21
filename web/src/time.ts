export function clock(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

export function hourLabel(ts: number): string {
  return new Date(ts * 1000).toLocaleTimeString([], { hour: 'numeric' })
}

export function ago(ts: number, now = Date.now() / 1000): string {
  const s = Math.max(0, Math.round(now - ts))
  if (s < 45) return 'just now'
  if (s < 90) return 'about a minute ago'
  const m = Math.round(s / 60)
  if (m < 60) return `${m} minutes ago`
  const h = Math.round(s / 3600)
  return h === 1 ? 'about an hour ago' : `about ${h} hours ago`
}
