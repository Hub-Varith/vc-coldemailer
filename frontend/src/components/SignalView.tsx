import type { PipelineCounts, RunStatus, UsageView } from '../types'
import { relativeTime } from '../lib/format'

interface Props {
  runs: RunStatus[]
  counts: PipelineCounts | null
  usage: UsageView | null
  onOpenRun: (runId: string) => void
}

function Stat({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="rounded-md border border-line bg-surface px-3 py-2.5">
      <p className="label-mono text-mute">{label}</p>
      <p className="mt-1 font-display text-[20px] font-bold leading-none text-bright">{value}</p>
      {hint && <p className="mt-1 font-mono text-[10px] text-mute">{hint}</p>}
    </div>
  )
}

export function SignalView({ runs, counts, usage, onOpenRun }: Props) {
  const latest = runs[0]
  const replyRate = counts && counts.sent > 0 ? `${Math.round((counts.replied / counts.sent) * 100)}%` : '—'

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-y-auto" aria-label="Reply signal">
      <div className="px-5 pb-3 pt-4">
        <h2 className="font-display text-[22px] font-bold leading-tight tracking-tight text-bright">Reply signal</h2>
        <p className="mt-0.5 text-[12px] text-mute">
          Reply rate per run is the number that says whether this works. Nothing here counts a message as sent
          without an approval behind it.
        </p>
      </div>

      <div className="grid gap-2 px-5 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Approved & sent" value={String(counts?.sent ?? 0)} hint="own domain only" />
        <Stat label="Replies" value={String(counts?.replied ?? 0)} hint={`reply rate ${replyRate}`} />
        <Stat
          label="Queries consumed"
          value={(usage?.queries_consumed ?? 0).toLocaleString()}
          hint={`${usage?.runs_used ?? 0} runs`}
        />
        <Stat
          label="Token spend"
          value={usage ? `$${usage.estimated_cost_usd.toFixed(2)}` : '$0.00'}
          hint={`${(usage?.prompt_tokens ?? 0).toLocaleString()} prompt tokens`}
        />
      </div>

      <div className="px-5 py-4">
        <h3 className="label-mono mb-2 text-mute">Run history</h3>
        <ul className="space-y-1.5">
          {runs.map((run) => (
            <li key={run.run_id}>
              <button
                type="button"
                onClick={() => onOpenRun(run.run_id)}
                className="flex w-full flex-wrap items-center gap-3 rounded-md border border-line bg-surface px-3 py-2 text-left transition-colors hover:border-lime/30 hover:bg-raised"
              >
                <span className="font-mono text-[11px] text-bright">{run.run_id.slice(0, 8)}</span>
                <span
                  className={`label-mono ${
                    run.status === 'complete' ? 'text-lime' : run.status === 'failed' ? 'text-danger' : 'text-amber'
                  }`}
                >
                  {run.status}
                </span>
                <span className="label-mono text-mute">{run.progress.investors} verified</span>
                <span className="label-mono text-mute">{run.rejected_count} rejected</span>
                <span className="label-mono text-mute">
                  {run.retrieval_stats.queries_issued} queries · {run.retrieval_stats.wall_time_ms}ms
                </span>
                <span className="ml-auto label-mono text-mute">{relativeTime(run.started_at)}</span>
              </button>
            </li>
          ))}
          {runs.length === 0 && <li className="font-mono text-[11px] text-mute">No runs yet.</li>}
        </ul>

        {latest?.warnings.length ? (
          <p className="mt-3 rounded border border-amber/25 bg-amber/[0.06] px-3 py-2 font-mono text-[10px] text-amber">
            Latest run warnings: {latest.warnings.join(', ')}
          </p>
        ) : null}
      </div>
    </section>
  )
}
