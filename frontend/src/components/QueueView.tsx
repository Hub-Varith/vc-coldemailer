import { motion } from 'framer-motion'
import { CheckCircle2, Clock, TriangleAlert } from 'lucide-react'
import type { DraftPublic, TargetSummary } from '../types'
import { relativeTime } from '../lib/format'

interface Props {
  drafts: DraftPublic[]
  rows: TargetSummary[]
  loading: boolean
  onOpen: (targetId: string) => void
}

const BLOCKER_COPY: Record<string, string> = {
  stale_lead_evidence: 'Lead fact is stale — needs manual review',
  no_contact_email: 'No contact address resolved',
  prior_contact_exists: 'Prior thread exists — treat as follow-up',
  domain_unverified: 'Sending domain not verified',
}

export function QueueView({ drafts, rows, loading, onOpen }: Props) {
  const nameFor = (targetId: string) => {
    const row = rows.find((r) => r.target_id === targetId)
    return row ? `${row.investor_person ?? row.investor_firm} · ${row.investor_firm}` : 'Unknown target'
  }
  const approved = drafts.filter((d) => d.approved_at)
  const pending = drafts.filter((d) => !d.approved_at)

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden" aria-label="Approval queue">
      <div className="px-5 pb-3 pt-4">
        <h2 className="font-display text-[22px] font-bold leading-tight tracking-tight text-bright">
          Approval queue
        </h2>
        <p className="mt-0.5 text-[12px] text-mute">
          {approved.length} approved · {pending.length} awaiting review. Approval is per message — there is no
          approve-all.
        </p>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-5">
        {loading && <p className="font-mono text-[11px] text-mute">Loading queue…</p>}

        {!loading && drafts.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-center">
            <p className="font-display text-[15px] font-semibold text-bright">Nothing drafted yet</p>
            <p className="max-w-sm text-[12px] leading-relaxed text-mute">
              Open an investor to generate a draft from its strongest dated fact. Drafts land here for review.
            </p>
          </div>
        )}

        <ul className="space-y-2">
          {drafts.map((draft, index) => (
            <motion.li
              key={draft.draft_id}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.2, delay: Math.min(index * 0.02, 0.2) }}
            >
              <button
                type="button"
                onClick={() => onOpen(draft.target_id)}
                className="w-full rounded-md border border-line bg-surface p-3 text-left transition-colors hover:border-lime/30 hover:bg-raised"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate font-display text-[13px] font-semibold text-bright">
                      {nameFor(draft.target_id)}
                    </p>
                    <p className="mt-0.5 truncate font-mono text-[11px] text-body">{draft.subject}</p>
                  </div>
                  <span
                    className={`flex shrink-0 items-center gap-1 rounded px-1.5 py-0.5 label-mono ${
                      draft.approved_at ? 'bg-lime/15 text-lime' : 'bg-raised text-mute'
                    }`}
                  >
                    {draft.approved_at ? <CheckCircle2 size={10} aria-hidden /> : <Clock size={10} aria-hidden />}
                    {draft.approved_at ? 'queued' : 'awaiting'}
                  </span>
                </div>

                <p className="mt-1.5 line-clamp-2 text-[11px] leading-relaxed text-mute">
                  {draft.body.split('\n\n')[1] ?? draft.body}
                </p>

                <div className="mt-2 flex flex-wrap items-center gap-2 label-mono text-mute">
                  <span>{draft.word_count} words</span>
                  <span className="text-line">|</span>
                  <span>v{draft.version}</span>
                  <span className="text-line">|</span>
                  <span>edited {relativeTime(draft.updated_at)}</span>
                  {draft.blockers.map((blocker) => (
                    <span key={blocker} className="flex items-center gap-1 text-amber">
                      <TriangleAlert size={10} aria-hidden />
                      {BLOCKER_COPY[blocker] ?? blocker}
                    </span>
                  ))}
                </div>
              </button>
            </motion.li>
          ))}
        </ul>
      </div>
    </section>
  )
}
