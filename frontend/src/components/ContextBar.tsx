import { motion } from 'framer-motion'
import { Bell, CircleHelp, Loader2, Play } from 'lucide-react'
import type { RunStatus, WorkspaceProfile } from '../types'
import { relativeTime } from '../lib/format'

interface Props {
  profile: WorkspaceProfile | null
  run: RunStatus | null
  running: boolean
  offline: boolean
  onRunSearch: () => void
  onEditBrief: () => void
  onReset: () => void
  resetting: boolean
}

export function ContextBar({ profile, run, running, offline, onRunSearch, onEditBrief, onReset, resetting }: Props) {
  const verifiedAt = run?.completed_at ?? run?.started_at ?? null

  return (
    <header className="flex h-[52px] shrink-0 items-center gap-4 border-b border-line bg-ink px-4">
      <h1 className="flex items-baseline gap-2 font-display text-[17px] font-bold tracking-tight text-bright">
        {profile?.company ?? 'Novi Audio'}
        <span className="text-mute">—</span>
        <span className="text-body">{profile?.round ?? 'Seed'}</span>
      </h1>

      <button
        type="button"
        onClick={onEditBrief}
        className="hidden max-w-[320px] truncate rounded border border-line bg-surface px-2 py-1 text-left font-mono text-[10px] text-body transition-colors hover:border-lime/40 hover:text-bright lg:block"
        title="Edit raise brief"
      >
        {profile?.raise_target ?? '$3.5M'} · {profile?.one_liner ?? ''}
      </button>

      <p className="label-mono hidden text-mute md:block">
        {offline ? 'Offline snapshot' : verifiedAt ? `Last verified: ${relativeTime(verifiedAt)}` : 'No run yet'}
      </p>

      <div className="ml-auto flex items-center gap-1">
        <button
          type="button"
          aria-label="Notifications"
          className="flex h-8 w-8 items-center justify-center rounded-md text-mute transition-colors hover:bg-raised hover:text-bright"
        >
          <Bell size={15} strokeWidth={1.75} aria-hidden />
        </button>
        <button
          type="button"
          aria-label="Help"
          className="flex h-8 w-8 items-center justify-center rounded-md text-mute transition-colors hover:bg-raised hover:text-bright"
        >
          <CircleHelp size={15} strokeWidth={1.75} aria-hidden />
        </button>

        <button
          type="button"
          onClick={onReset}
          disabled={resetting}
          className="mr-1 h-8 rounded-md border border-line px-2.5 font-mono text-[10px] uppercase tracking-[0.08em] text-mute transition-colors hover:border-lime/40 hover:text-lime disabled:opacity-50"
        >
          {resetting ? 'Resetting' : 'Reset demo'}
        </button>

        <motion.button
          type="button"
          onClick={onRunSearch}
          disabled={running}
          whileTap={{ scale: 0.98 }}
          className="ml-2 flex h-8 items-center gap-1.5 rounded-md bg-lime px-3 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e6ff3d] disabled:cursor-not-allowed disabled:bg-lime/40"
        >
          {running ? (
            <Loader2 size={12} className="animate-spin" aria-hidden />
          ) : (
            <Play size={11} fill="currentColor" aria-hidden />
          )}
          {running ? 'Searching' : 'Run live search'}
        </motion.button>
      </div>
    </header>
  )
}
