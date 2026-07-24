export function relativeTime(iso: string): string {
  const then = new Date(iso).getTime()
  const diff = Date.now() - then
  if (Number.isNaN(then)) return '—'
  const minutes = Math.round(diff / 60_000)
  if (minutes < 1) return 'just now'
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.round(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.round(hours / 24)}d ago`
}

export function longDate(iso: string | null): string {
  if (!iso) return 'undated'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return 'undated'
  return date.toLocaleDateString('en-US', { month: 'short', day: '2-digit', year: 'numeric' })
}

export function checkRange(min: number | null, max: number | null): string {
  if (!min && !max) return '—'
  const money = (value: number) =>
    value >= 1_000_000 ? `$${(value / 1_000_000).toFixed(value % 1_000_000 === 0 ? 0 : 1)}M` : `$${Math.round(value / 1000)}K`
  return `${money(min ?? 0)}–${money(max ?? 0)}`
}

export function wordCount(text: string): number {
  return text.split(/\s+/).filter(Boolean).length
}

export function hostname(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export const EVIDENCE_LABEL: Record<string, string> = {
  portfolio_investment: 'Portfolio',
  thesis_publication: 'Thesis',
  fund_close: 'Fund',
  portfolio_gap: 'Gap',
  exit: 'Exit',
  personnel: 'Personnel',
  other: 'Signal',
}
