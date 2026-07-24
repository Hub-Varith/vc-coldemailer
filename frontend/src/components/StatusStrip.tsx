import { AnimatePresence, motion } from 'framer-motion'
import type { RunStatus } from '../types'

export function StatusStrip({ run, running }: { run: RunStatus | null; running: boolean }) {
  const stats = run?.retrieval_stats
  const items = [
    { label: 'sources searched', value: run?.sources_searched ?? 0 },
    { label: 'investors verified', value: run?.progress.investors ?? 0 },
    { label: 'stale records rejected', value: run?.rejected_count ?? 0 },
    { label: 'queries fanned out', value: stats?.queries_issued ?? 0 },
  ]

  return (
    <div className="flex h-9 shrink-0 items-center gap-4 overflow-x-auto border-b border-line bg-panel px-4">
      <span className="flex shrink-0 items-center gap-2">
        <motion.span
          animate={running ? { opacity: [1, 0.25, 1] } : { opacity: 1 }}
          transition={{ duration: 1.1, repeat: running ? Infinity : 0 }}
          className={`h-1.5 w-1.5 rounded-full ${running ? 'bg-lime' : 'bg-lime/60'}`}
        />
        <AnimatePresence mode="wait">
          <motion.span
            key={run?.stage ?? 'idle'}
            initial={{ opacity: 0, y: -3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 3 }}
            className="label-mono text-lime"
          >
            {run?.stage ?? 'idle'}
          </motion.span>
        </AnimatePresence>
      </span>

      {items.map((item) => (
        <span key={item.label} className="flex shrink-0 items-center gap-1.5 label-mono text-mute">
          <motion.span
            key={item.value}
            initial={{ opacity: 0.4 }}
            animate={{ opacity: 1 }}
            className="font-mono text-[11px] font-bold normal-case tracking-normal text-bright"
          >
            {item.value.toLocaleString()}
          </motion.span>
          {item.label}
        </span>
      ))}

      {stats && stats.wall_time_ms > 0 && (
        <span className="ml-auto hidden shrink-0 label-mono text-mute lg:block">
          {stats.queries_issued} queries · {stats.wall_time_ms}ms wall
          {stats.cache_hits > 0
            ? ` · ${stats.cache_hits} served from cache`
            : ` · p50 ${stats.p50_latency_ms}ms · concurrency ${stats.max_concurrency}`}
        </span>
      )}
    </div>
  )
}
