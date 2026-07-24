import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import type { RunEvent, RunStatus } from '../types'

const STAGES = ['planning', 'retrieving', 'extracting', 'verifying', 'scoring'] as const

interface Props {
  run: RunStatus | null
  events: RunEvent[]
  open: boolean
  onClose: () => void
}

export function LiveSearchPanel({ run, events, open, onClose }: Props) {
  const finished = run?.status === 'complete'
  const stageIndex = finished ? STAGES.length : run ? STAGES.indexOf(run.stage as (typeof STAGES)[number]) : -1
  const queryProgress = run?.progress.queries_total
    ? run.progress.queries_done / run.progress.queries_total
    : 0

  return (
    <AnimatePresence>
      {open && (
        <motion.section
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
          className="max-h-[42vh] shrink-0 overflow-y-auto border-b border-line bg-ink"
          aria-live="polite"
        >
          <div className="flex items-center justify-between border-b border-line-soft px-4 py-2">
            <span className="flex items-center gap-2 label-mono text-lime">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-lime" />
              Live search activity
            </span>
            <span className="flex items-center gap-3">
              <span className="label-mono text-mute">
                {run?.progress.queries_done ?? 0}/{run?.progress.queries_total ?? 0} queries
              </span>
              <button
                type="button"
                onClick={onClose}
                aria-label="Hide live search activity"
                className="flex h-6 w-6 items-center justify-center rounded text-mute transition-colors hover:bg-raised hover:text-bright"
              >
                <X size={13} aria-hidden />
              </button>
            </span>
          </div>

          <div className="grid gap-1.5 p-3 md:grid-cols-2">
            {STAGES.map((stage, index) => {
              const state =
                stageIndex < 0 ? 'queued' : index < stageIndex ? 'done' : index === stageIndex ? 'running' : 'queued'
              const progress = state === 'done' ? 1 : state === 'running' ? Math.max(queryProgress, 0.12) : 0
              const latest = [...events].reverse().find((e) => e.stage === stage)
              return (
                <div
                  key={stage}
                  className={`rounded-md border px-3 py-2 transition-colors ${
                    state === 'running' ? 'border-lime/25 bg-lime/[0.06]' : 'border-line bg-surface'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <p className="truncate font-mono text-[11px] text-bright">{stage}</p>
                    <span
                      className={`label-mono shrink-0 ${
                        state === 'running' ? 'text-lime' : state === 'done' ? 'text-body' : 'text-mute'
                      }`}
                    >
                      {state === 'done' ? 'completed' : state === 'running' ? 'running' : 'queued'}
                    </span>
                  </div>
                  <p className="mt-0.5 truncate font-mono text-[10px] text-mute">
                    {latest?.message ?? (state === 'done' ? 'Completed' : state === 'running' ? 'Working' : 'Awaiting dependency')}
                  </p>
                  <div className="mt-1.5 h-[3px] overflow-hidden rounded-full bg-raised">
                    <motion.div
                      animate={{ width: `${progress * 100}%` }}
                      transition={{ duration: 0.4, ease: 'easeOut' }}
                      className={state === 'done' ? 'h-full bg-lime/40' : 'h-full bg-lime'}
                    />
                  </div>
                </div>
              )
            })}

            <div className="rounded-md border border-line bg-surface px-3 py-2 md:col-span-2">
              <p className="label-mono mb-1.5 text-mute">Event log</p>
              <ul className="max-h-24 space-y-0.5 overflow-y-auto font-mono text-[10px] leading-relaxed">
                {events.slice(-40).reverse().map((event, index) => (
                  <li
                    key={`${event.at}-${index}`}
                    className={
                      event.type === 'record_rejected'
                        ? 'text-danger'
                        : event.type === 'investor_found'
                          ? 'text-lime'
                          : 'text-mute'
                    }
                  >
                    <span className="text-mute/60">[{new Date(event.at).toLocaleTimeString('en-GB')}]</span>{' '}
                    {event.message}
                  </li>
                ))}
                {events.length === 0 && <li className="text-mute">No events yet — start a live search.</li>}
              </ul>
            </div>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  )
}
