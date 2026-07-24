import { motion } from 'framer-motion'
import { CheckCircle2, Search, SlidersHorizontal } from 'lucide-react'
import type { TargetSummary } from '../types'
import { checkRange, longDate } from '../lib/format'

export type SortKey = 'score' | 'recency' | 'firm'

interface Props {
  rows: TargetSummary[]
  total: number
  loading: boolean
  selectedId: string | null
  query: string
  sort: SortKey
  activeChips: string[]
  chips: string[]
  onQuery: (value: string) => void
  onSort: (value: SortKey) => void
  onToggleChip: (chip: string) => void
  onSelect: (row: TargetSummary) => void
  hasRun: boolean
  onRunSearch: () => void
}

function initials(row: TargetSummary): string {
  const source = row.investor_person ?? row.investor_firm
  return source
    .split(' ')
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase()
}

export function InvestorList({
  rows,
  total,
  loading,
  selectedId,
  query,
  sort,
  activeChips,
  chips,
  onQuery,
  onSort,
  onToggleChip,
  onSelect,
  hasRun,
  onRunSearch,
}: Props) {
  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden" aria-label="Ranked investors">
      <div className="flex flex-wrap items-end justify-between gap-3 px-5 pb-3 pt-4">
        <div>
          <h2 className="font-display text-[22px] font-bold leading-tight tracking-tight text-bright">
            {total} verified investor{total === 1 ? '' : 's'}
          </h2>
          <p className="mt-0.5 text-[12px] text-mute">Ranked by evidence strength and freshness</p>
        </div>

        <div className="flex items-center gap-2">
          <div className="relative">
            <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-mute" aria-hidden />
            <input
              type="search"
              value={query}
              onChange={(event) => onQuery(event.target.value)}
              placeholder="Filter name, firm, evidence…"
              aria-label="Filter investors"
              className="h-8 w-44 rounded-md xl:w-56 border border-line bg-surface pl-8 pr-3 font-mono text-[11px] text-bright placeholder:text-mute focus:border-lime/40 focus:outline-none"
            />
          </div>
          <label className="flex h-8 items-center gap-1.5 rounded-md border border-line bg-surface px-2.5">
            <SlidersHorizontal size={12} className="text-mute" aria-hidden />
            <span className="sr-only">Sort investors by</span>
            <select
              value={sort}
              onChange={(event) => onSort(event.target.value as SortKey)}
              className="bg-transparent font-mono text-[11px] text-body focus:outline-none"
            >
              <option value="score">Fit score</option>
              <option value="recency">Evidence recency</option>
              <option value="firm">Firm A–Z</option>
            </select>
          </label>
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5 px-5 pb-3">
        {chips.map((chip) => {
          const active = activeChips.includes(chip)
          return (
            <button
              key={chip}
              type="button"
              aria-pressed={active}
              onClick={() => onToggleChip(chip)}
              className={`rounded border px-2 py-1 font-mono text-[10px] transition-colors ${
                active
                  ? 'border-lime/40 bg-lime/15 text-lime'
                  : 'border-line bg-surface text-mute hover:border-line hover:text-body'
              }`}
            >
              {chip}
            </button>
          )
        })}
      </div>

      <div className="grid shrink-0 grid-cols-[minmax(150px,200px)_40px_1fr] gap-3 border-y border-line bg-panel px-4 py-2 label-mono text-mute lg:grid-cols-[minmax(160px,200px)_40px_100px_1fr] xl:grid-cols-[220px_44px_112px_150px_1fr] xl:px-5">
        <span>Investor &amp; firm</span>
        <span>Fit</span>
        <span className="hidden lg:block">Check size</span>
        <span className="hidden xl:block">Tags</span>
        <span>Primary evidence</span>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {loading && (
          <ul className="divide-y divide-line-soft">
            {Array.from({ length: 6 }).map((_, index) => (
              <li key={index} className="flex animate-pulse items-center gap-3 px-5 py-3.5">
                <span className="h-7 w-7 rounded bg-raised" />
                <span className="h-3 w-40 rounded bg-raised" />
                <span className="ml-auto h-3 w-64 rounded bg-raised" />
              </li>
            ))}
          </ul>
        )}

        {!loading && rows.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-8 text-center">
            <p className="font-display text-[15px] font-semibold text-bright">
              {hasRun ? 'No investor matches that filter' : 'No search has been run yet'}
            </p>
            <p className="max-w-sm text-[12px] leading-relaxed text-mute">
              {hasRun
                ? 'Every listed name carries at least one dated, retrievable fact. Clear the filters, or run a fresh search to pull new evidence.'
                : 'One run expands your profile into several hundred narrow queries, then keeps only the investors backed by a dated, retrievable fact.'}
            </p>
            {!hasRun && (
              <button
                type="button"
                onClick={onRunSearch}
                className="mt-1 rounded-md bg-lime px-3 py-1.5 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e6ff3d]"
              >
                Run live search
              </button>
            )}
          </div>
        )}

        {!loading && rows.length > 0 && (
          <ul className="divide-y divide-line-soft">
            {rows.map((row, index) => {
              const selected = row.target_id === selectedId
              const queued = row.status === 'approved' || row.status === 'sent'
              return (
                <motion.li
                  key={row.target_id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.22, delay: Math.min(index * 0.018, 0.25) }}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(row)}
                    aria-current={selected ? 'true' : undefined}
                    className={`relative grid w-full grid-cols-[minmax(150px,200px)_40px_1fr] items-start gap-3 px-4 py-3.5 text-left transition-colors lg:grid-cols-[minmax(160px,200px)_40px_100px_1fr] xl:grid-cols-[220px_44px_112px_150px_1fr] xl:px-5 ${
                      selected ? 'bg-lime/[0.07]' : 'hover:bg-surface'
                    }`}
                  >
                    {selected && <span className="absolute inset-y-0 left-0 w-[2px] bg-lime" aria-hidden />}

                    <span className="flex min-w-0 items-center gap-2.5">
                      <span
                        className={`flex h-7 w-7 shrink-0 items-center justify-center rounded font-mono text-[10px] font-bold ${
                          selected ? 'bg-lime text-black' : 'bg-raised text-body'
                        }`}
                        aria-hidden
                      >
                        {initials(row)}
                      </span>
                      <span className="min-w-0">
                        <span className="flex items-center gap-1.5">
                          <span className="truncate font-display text-[13px] font-semibold text-bright">
                            {row.investor_person ?? row.investor_firm}
                          </span>
                          {queued && <CheckCircle2 size={12} className="shrink-0 text-lime" aria-label="Queued" />}
                        </span>
                        <span className="block truncate font-mono text-[10px] text-mute">{row.investor_firm}</span>
                      </span>
                    </span>

                    <span
                      className={`rounded px-1.5 py-0.5 text-center font-mono text-[11px] font-bold ${
                        row.score >= 0.9 ? 'bg-lime/15 text-lime' : 'bg-raised text-body'
                      }`}
                    >
                      {Math.round(row.score * 100)}
                    </span>

                    <span className="hidden font-mono text-[11px] text-body lg:block">
                      {checkRange(row.check_min, row.check_max)}
                    </span>

                    <span className="hidden flex-wrap gap-1 xl:flex">
                      {[...row.stage, ...row.sectors].slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="rounded border border-line bg-surface px-1.5 py-0.5 font-mono text-[9px] text-body"
                        >
                          {tag}
                        </span>
                      ))}
                    </span>

                    <span className="min-w-0">
                      <span className="line-clamp-2 text-[12px] leading-snug text-body">
                        “{row.lead_evidence.claim}”
                      </span>
                      <span className="mt-1 flex items-center gap-2 label-mono text-mute">
                        {longDate(row.lead_evidence.event_date)}
                        {row.has_stale_evidence && <span className="text-amber">contains stale records</span>}
                      </span>
                    </span>
                  </button>
                </motion.li>
              )
            })}
          </ul>
        )}
      </div>
    </section>
  )
}
