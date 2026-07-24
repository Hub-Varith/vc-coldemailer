import { AnimatePresence, motion } from 'framer-motion'
import { Check, X } from 'lucide-react'
import { SEARCH_INTENTS, SEARCH_STAGES, stageProgress } from '../lib/choreography'

export interface SearchCounters {
  sources: number
  candidates: number
  rejected: number
  verified: number
  coverage: number
}

interface Props {
  open: boolean
  running: boolean
  elapsed: number
  counters: SearchCounters
  onSkip: () => void
  onCancel: () => void
  onClose: () => void
}

export function SearchTray({ open, running, elapsed, counters, onSkip, onCancel, onClose }: Props) {
  return (
    <AnimatePresence>
      {open && (
        <motion.section
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
          className="shrink-0 border-b border-line bg-ink"
          aria-live="polite"
        >
          <div className="flex items-center gap-3 border-b border-line-soft px-4 py-2">
            <span className="flex items-center gap-2 label-mono text-lime">
              <span className={`h-1.5 w-1.5 rounded-full bg-lime ${running ? 'animate-pulse' : ''}`} />
              {running ? 'Live search running' : 'Live search complete'}
            </span>

            <div className="ml-auto flex items-center gap-3">
              <span className="hidden label-mono text-mute sm:block">
                {counters.sources} sources · {counters.candidates} candidates · {counters.rejected} rejected ·{' '}
                {counters.verified} verified · {Math.round(counters.coverage * 100)}% evidence coverage
              </span>
              {running ? (
                <>
                  <button
                    type="button"
                    onClick={onSkip}
                    className="h-6 rounded border border-line px-2 font-mono text-[10px] text-body transition-colors hover:border-lime/40 hover:text-lime"
                  >
                    Skip
                  </button>
                  <button
                    type="button"
                    onClick={onCancel}
                    className="h-6 rounded border border-line px-2 font-mono text-[10px] text-mute transition-colors hover:border-danger/40 hover:text-danger"
                  >
                    Cancel
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  onClick={onClose}
                  aria-label="Hide live search activity"
                  className="flex h-6 w-6 items-center justify-center rounded text-mute transition-colors hover:bg-raised hover:text-bright"
                >
                  <X size={13} aria-hidden />
                </button>
              )}
            </div>
          </div>

          <div className="grid gap-3 px-4 py-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
            <div>
              <p className="label-mono mb-1.5 text-mute">Intents — running concurrently</p>
              <ul className="space-y-1">
                {SEARCH_INTENTS.map((intent, index) => {
                  const start = 500 + index * 120
                  const done = elapsed > start + 2600
                  const active = elapsed > start && !done
                  const width = Math.min(100, Math.max(0, ((elapsed - start) / 2600) * 100))
                  return (
                    <li key={intent.key} className="flex items-center gap-2.5">
                      <span
                        className={`flex h-3.5 w-3.5 shrink-0 items-center justify-center rounded-sm border ${
                          done ? 'border-lime bg-lime/20 text-lime' : active ? 'border-lime/40' : 'border-line'
                        }`}
                      >
                        {done && <Check size={9} strokeWidth={3} aria-hidden />}
                      </span>
                      <span className="w-[190px] shrink-0 truncate font-mono text-[11px] text-bright">
                        {intent.label}
                      </span>
                      <span className="hidden flex-1 truncate font-mono text-[10px] text-mute xl:block">
                        {intent.detail}
                      </span>
                      <span className="h-[3px] w-24 shrink-0 overflow-hidden rounded-full bg-raised">
                        <motion.span
                          animate={{ width: `${done ? 100 : Math.max(0, width)}%` }}
                          transition={{ duration: 0.25, ease: 'easeOut' }}
                          className="block h-full bg-lime"
                        />
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>

            <div>
              <p className="label-mono mb-1.5 text-mute">Pipeline</p>
              <ul className="grid gap-1 sm:grid-cols-2">
                {SEARCH_STAGES.map((stage) => {
                  const progress = stageProgress(stage, elapsed)
                  const state = progress >= 1 ? 'done' : progress > 0 ? 'running' : 'queued'
                  return (
                    <li
                      key={stage.key}
                      className={`rounded border px-2 py-1.5 transition-colors ${
                        state === 'running' ? 'border-lime/25 bg-lime/[0.06]' : 'border-line bg-surface'
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span
                          className={`truncate font-mono text-[10px] ${
                            state === 'queued' ? 'text-mute' : 'text-bright'
                          }`}
                        >
                          {stage.label}
                        </span>
                        <span
                          className={`shrink-0 label-mono ${
                            state === 'done' ? 'text-body' : state === 'running' ? 'text-lime' : 'text-mute'
                          }`}
                        >
                          {state === 'done' ? 'done' : state === 'running' ? `${Math.round(progress * 100)}%` : '—'}
                        </span>
                      </div>
                      <span className="mt-1 block h-[2px] overflow-hidden rounded-full bg-raised">
                        <motion.span
                          animate={{ width: `${progress * 100}%` }}
                          transition={{ duration: 0.2, ease: 'linear' }}
                          className={`block h-full ${state === 'done' ? 'bg-lime/40' : 'bg-lime'}`}
                        />
                      </span>
                    </li>
                  )
                })}
              </ul>
            </div>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  )
}
