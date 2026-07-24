export interface ChoreographyStage {
  key: string
  label: string
  /** Milliseconds from sequence start when this stage begins. */
  at: number
  duration: number
}

export const SEARCH_STAGES: ChoreographyStage[] = [
  { key: 'planning', label: 'Planning search', at: 0, duration: 900 },
  { key: 'searching', label: 'Searching sources', at: 700, duration: 2400 },
  { key: 'extracting', label: 'Extracting evidence', at: 2600, duration: 1600 },
  { key: 'deduping', label: 'Deduplicating investors', at: 3900, duration: 1000 },
  { key: 'verifying', label: 'Verifying freshness', at: 4700, duration: 1400 },
  { key: 'ranking', label: 'Ranking matches', at: 5900, duration: 900 },
  { key: 'drafting', label: 'Drafting outreach', at: 6600, duration: 1100 },
]

export const SEARCH_INTENTS = [
  { key: 'adjacent', label: 'Adjacent portfolio companies', detail: 'Funds already backing companies like ours' },
  { key: 'closes', label: 'Recent fund closes', detail: 'Fresh capital, visibly deploying' },
  { key: 'thesis', label: 'Partner thesis signals', detail: 'Essays, podcasts, conference transcripts' },
  { key: 'gaps', label: 'Portfolio gaps', detail: 'Relevant portfolio, visible hole where we sit' },
  { key: 'geo', label: 'Geography-crossing funds', detail: 'Funds that cross into our region' },
] as const

export const SEQUENCE_MS = 7800

/** Eased 0→1 progress for a stage at time `t`. */
export function stageProgress(stage: ChoreographyStage, t: number): number {
  if (t <= stage.at) return 0
  const raw = Math.min(1, (t - stage.at) / stage.duration)
  return 1 - Math.pow(1 - raw, 3)
}

export function overallProgress(t: number): number {
  return Math.max(0, Math.min(1, t / SEQUENCE_MS))
}

/** Counters ramp smoothly and deterministically off the same clock. */
export function counterAt(target: number, t: number, startMs: number, spanMs: number): number {
  if (t <= startMs) return 0
  const raw = Math.min(1, (t - startMs) / spanMs)
  return Math.round(target * (1 - Math.pow(1 - raw, 2)))
}
