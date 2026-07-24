import { AnimatePresence, motion } from 'framer-motion'
import {
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  ExternalLink,
  Loader2,
  Mail,
  ShieldCheck,
  TriangleAlert,
} from 'lucide-react'
import type { DraftPublic, SequenceView, TargetDetail } from '../types'
import { EVIDENCE_LABEL, checkRange, hostname, longDate, relativeTime, wordCount } from '../lib/format'

interface Props {
  target: TargetDetail | null
  draft: DraftPublic | null
  sequence: SequenceView | null
  body: string
  loading: boolean
  approving: boolean
  onBodyChange: (value: string) => void
  onApprove: () => void
}

export function DetailPanel({
  target,
  draft,
  sequence,
  body,
  loading,
  approving,
  onBodyChange,
  onApprove,
}: Props) {
  if (!target) {
    return (
      <aside className="hidden w-[340px] shrink-0 flex-col items-center justify-center gap-3 border-l border-line bg-panel px-8 text-center lg:flex xl:w-[420px]">
        <span className="flex h-9 w-9 items-center justify-center rounded-md border border-line bg-surface">
          <Mail size={16} className="text-mute" aria-hidden />
        </span>
        <p className="font-display text-[14px] font-semibold text-bright">Select an investor</p>
        <p className="max-w-[240px] text-[12px] leading-relaxed text-mute">
          Every row opens into the dated evidence that qualified it and the draft built from that same evidence.
        </p>
      </aside>
    )
  }

  const queued = draft?.approved_at != null
  const words = wordCount(body)
  const dirty = draft ? body !== draft.body : false

  return (
    <aside className="flex w-[340px] shrink-0 flex-col overflow-hidden border-l border-line bg-panel xl:w-[420px]">
      <div className="shrink-0 border-b border-line px-4 py-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate font-display text-[16px] font-bold tracking-tight text-bright">
              {target.investor_person ?? target.investor_firm}
            </h2>
            <p className="truncate font-mono text-[10px] text-mute">
              {target.role ? `${target.role} · ` : ''}
              {target.investor_firm} · {target.location ?? '—'}
            </p>
          </div>
          <span
            className={`shrink-0 rounded px-1.5 py-0.5 font-mono text-[11px] font-bold ${
              target.score >= 0.9 ? 'bg-lime/15 text-lime' : 'bg-raised text-body'
            }`}
          >
            {Math.round(target.score * 100)}
          </span>
        </div>

        <div className="mt-2 flex flex-wrap items-center gap-2 label-mono text-mute">
          <span>{checkRange(target.check_min, target.check_max)}</span>
          <span className="text-line">|</span>
          <span>{target.evidence.length} dated records</span>
          {queued && (
            <>
              <span className="text-line">|</span>
              <span className="flex items-center gap-1 text-lime">
                <CheckCircle2 size={11} aria-hidden /> queued
              </span>
            </>
          )}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        <section className="border-b border-line px-4 py-3" aria-label="Evidence">
          <h3 className="label-mono mb-2 text-mute">Evidence — verified at request time</h3>
          <ul className="space-y-2">
            {target.evidence.map((record) => {
              const isLead = record.id === target.lead_evidence.id
              return (
              <li
                key={record.id}
                className={`rounded-md border p-2.5 transition-colors ${
                  isLead ? 'border-lime/45 bg-lime/[0.07]' : 'border-line bg-surface'
                }`}
              >
                {isLead && (
                  <p className="mb-1.5 flex items-center gap-1 label-mono text-lime">
                    <ArrowDownRight size={11} aria-hidden /> Used in draft — opens the email
                  </p>
                )}
                <div className="mb-1 flex items-center gap-2">
                  <span className="rounded bg-raised px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wide text-body">
                    {EVIDENCE_LABEL[record.kind] ?? record.kind}
                  </span>
                  <span className="label-mono text-mute">{longDate(record.event_date)}</span>
                  {record.stale ? (
                    <span className="ml-auto flex items-center gap-1 label-mono text-amber">
                      <TriangleAlert size={10} aria-hidden /> stale
                    </span>
                  ) : (
                    <span className="ml-auto flex items-center gap-1 label-mono text-lime">
                      <ShieldCheck size={10} aria-hidden /> verified
                    </span>
                  )}
                </div>
                <p className="text-[12px] leading-snug text-bright">{record.claim}</p>
                <p className="mt-1 text-[11px] leading-relaxed text-mute">{record.detail}</p>
                <div className="mt-1.5 flex items-center justify-between gap-2">
                  <a
                    href={record.source_url}
                    target="_blank"
                    rel="noreferrer noopener"
                    className="flex items-center gap-1 truncate font-mono text-[10px] text-cyan hover:underline"
                  >
                    <ExternalLink size={10} aria-hidden />
                    {record.source_name || hostname(record.source_url)}
                  </a>
                  {record.verified_at && (
                    <span className="label-mono shrink-0 text-mute">re-checked {relativeTime(record.verified_at)}</span>
                  )}
                </div>
              </li>
              )
            })}
          </ul>
        </section>

        <section className="border-b border-line px-4 py-3" aria-label="Draft email">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="label-mono text-mute">Draft — built from the lead fact</h3>
            <span className={`label-mono ${words >= 80 && words <= 120 ? 'text-mute' : 'text-amber'}`}>
              {words} words
            </span>
          </div>

          {loading && !draft && (
            <div className="flex h-32 items-center justify-center gap-2 rounded-md border border-line bg-surface">
              <Loader2 size={14} className="animate-spin text-lime" aria-hidden />
              <span className="font-mono text-[11px] text-mute">Drafting from evidence…</span>
            </div>
          )}

          {draft && (
            <>
              <p className="mb-2 rounded-md border border-line bg-surface px-2.5 py-2 font-mono text-[11px] text-bright">
                <span className="text-mute">Subject: </span>
                {draft.subject}
              </p>
              <p className="mb-1.5 flex items-start gap-1.5 rounded-md border border-lime/30 bg-lime/[0.07] px-2.5 py-2 text-[12px] leading-snug text-bright">
                <ArrowUpRight size={12} className="mt-0.5 shrink-0 text-lime" aria-hidden />
                <span>
                  <span className="label-mono mb-0.5 block text-lime">Opening line, from the evidence above</span>
                  {body.split('\n\n')[1] ?? ''}
                </span>
              </p>
              <label className="sr-only" htmlFor="draft-body">
                Email body
              </label>
              <textarea
                id="draft-body"
                value={body}
                onChange={(event) => onBodyChange(event.target.value)}
                spellCheck={false}
                className="h-64 w-full resize-none rounded-md border border-line bg-surface p-2.5 text-[12px] leading-relaxed text-bright focus:border-lime/40 focus:outline-none"
              />
              {draft.prior_contact.found && (
                <p className="mt-2 flex items-start gap-1.5 rounded border border-amber/25 bg-amber/[0.07] px-2 py-1.5 text-[11px] leading-snug text-amber">
                  <TriangleAlert size={11} className="mt-0.5 shrink-0" aria-hidden />
                  {draft.prior_contact.summary ?? 'Prior thread found — this is a follow-up, not cold outreach.'}
                </p>
              )}
            </>
          )}
        </section>

        <section className="px-4 py-3" aria-label="Follow-up sequence">
          <h3 className="label-mono mb-2 text-mute">Follow-up sequence</h3>
          <ol className="relative space-y-2 border-l border-line pl-4">
            {(sequence?.steps ?? []).map((step) => (
              <li key={step.n} className="relative">
                <span
                  className={`absolute -left-[21px] top-1 h-2 w-2 rounded-full border ${
                    step.status === 'delivered'
                      ? 'border-lime bg-lime'
                      : step.status === 'scheduled'
                        ? 'border-lime/50 bg-panel'
                        : 'border-line bg-panel'
                  }`}
                  aria-hidden
                />
                <p className="flex items-center gap-2 text-[12px] text-bright">
                  {step.n === 1 ? 'Initial send' : `Day ${step.offset_days}`}
                  <span className="label-mono text-mute">{step.status}</span>
                </p>
                <p className="text-[11px] leading-snug text-mute">{step.preview}</p>
              </li>
            ))}
            {!sequence && <li className="text-[11px] text-mute">Sequence starts once the message is approved.</li>}
          </ol>
          {sequence?.state === 'active' && (
            <p className="mt-2 label-mono text-mute">Follow-ups stop automatically on reply.</p>
          )}
        </section>
      </div>

      <div className="shrink-0 border-t border-line bg-ink px-4 py-3">
        <AnimatePresence mode="wait">
          {queued && !dirty ? (
            <motion.p
              key="queued"
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center justify-center gap-2 rounded-md border border-lime/30 bg-lime/10 py-2 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-lime"
            >
              <CheckCircle2 size={13} aria-hidden /> Approved &amp; queued — initial, day 4, day 10
            </motion.p>
          ) : (
            <motion.button
              key="approve"
              type="button"
              onClick={onApprove}
              disabled={!draft || approving}
              whileTap={{ scale: 0.985 }}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex w-full items-center justify-center gap-2 rounded-md bg-lime py-2 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e6ff3d] disabled:cursor-not-allowed disabled:bg-lime/40"
            >
              {approving ? <Loader2 size={13} className="animate-spin" aria-hidden /> : <CheckCircle2 size={13} aria-hidden />}
              {dirty && queued ? 'Re-approve edited message' : 'Approve & queue'}
            </motion.button>
          )}
        </AnimatePresence>
        <p className="mt-1.5 text-center label-mono text-mute">Nothing sends without this click</p>
      </div>
    </aside>
  )
}
