import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { X } from 'lucide-react'
import type { WorkspaceProfile } from '../types'

export interface RaiseBriefDraft {
  company: string
  one_liner: string
  round: string
  raise_target: string
  sectors: string
  geographies: string
  check_target_min: number
  check_target_max: number
}

interface Props {
  open: boolean
  profile: WorkspaceProfile | null
  saving: boolean
  onClose: () => void
  onSave: (draft: RaiseBriefDraft) => void
}

const FIELD =
  'h-8 w-full rounded-md border border-line bg-surface px-2.5 font-mono text-[11px] text-bright placeholder:text-mute focus:border-lime/40 focus:outline-none'

export function RaiseBriefModal({ open, profile, saving, onClose, onSave }: Props) {
  const [draft, setDraft] = useState<RaiseBriefDraft | null>(null)

  useEffect(() => {
    if (!open || !profile) return
    setDraft({
      company: profile.company,
      one_liner: profile.one_liner,
      round: profile.round,
      raise_target: profile.raise_target,
      sectors: profile.sectors?.join(', ') ?? '',
      geographies: profile.geographies?.join(', ') ?? '',
      check_target_min: profile.check_target_min ?? 250000,
      check_target_max: profile.check_target_max ?? 2000000,
    })
  }, [open, profile])

  return (
    <AnimatePresence>
      {open && draft && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4"
          onClick={onClose}
          role="presentation"
        >
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.99 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.99 }}
            transition={{ type: 'spring', stiffness: 420, damping: 34 }}
            onClick={(event) => event.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Edit raise brief"
            className="w-full max-w-[520px] rounded-lg border border-line bg-panel shadow-[0_32px_80px_-24px_rgba(0,0,0,0.95)]"
          >
            <div className="flex items-center justify-between border-b border-line px-4 py-2.5">
              <h2 className="font-display text-[14px] font-bold tracking-tight text-bright">Raise brief</h2>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close"
                className="flex h-6 w-6 items-center justify-center rounded text-mute transition-colors hover:bg-raised hover:text-bright"
              >
                <X size={13} aria-hidden />
              </button>
            </div>

            <form
              className="space-y-2.5 px-4 py-3.5"
              onSubmit={(event) => {
                event.preventDefault()
                onSave(draft)
              }}
            >
              <label className="block">
                <span className="label-mono mb-1 block text-mute">Company</span>
                <input
                  className={FIELD}
                  value={draft.company}
                  onChange={(e) => setDraft({ ...draft, company: e.target.value })}
                />
              </label>

              <label className="block">
                <span className="label-mono mb-1 block text-mute">What you build</span>
                <textarea
                  className="h-14 w-full resize-none rounded-md border border-line bg-surface p-2.5 text-[12px] leading-relaxed text-bright focus:border-lime/40 focus:outline-none"
                  value={draft.one_liner}
                  onChange={(e) => setDraft({ ...draft, one_liner: e.target.value })}
                />
              </label>

              <div className="grid grid-cols-2 gap-2.5">
                <label className="block">
                  <span className="label-mono mb-1 block text-mute">Stage</span>
                  <input
                    className={FIELD}
                    value={draft.round}
                    onChange={(e) => setDraft({ ...draft, round: e.target.value })}
                  />
                </label>
                <label className="block">
                  <span className="label-mono mb-1 block text-mute">Raise target</span>
                  <input
                    className={FIELD}
                    value={draft.raise_target}
                    onChange={(e) => setDraft({ ...draft, raise_target: e.target.value })}
                  />
                </label>
              </div>

              <label className="block">
                <span className="label-mono mb-1 block text-mute">Sectors</span>
                <input
                  className={FIELD}
                  value={draft.sectors}
                  onChange={(e) => setDraft({ ...draft, sectors: e.target.value })}
                  placeholder="hearing, audio hardware, accessibility"
                />
              </label>

              <div className="grid grid-cols-3 gap-2.5">
                <label className="block">
                  <span className="label-mono mb-1 block text-mute">Geography</span>
                  <input
                    className={FIELD}
                    value={draft.geographies}
                    onChange={(e) => setDraft({ ...draft, geographies: e.target.value })}
                    placeholder="US, EU"
                  />
                </label>
                <label className="block">
                  <span className="label-mono mb-1 block text-mute">Check min</span>
                  <input
                    className={FIELD}
                    type="number"
                    step={50000}
                    value={draft.check_target_min}
                    onChange={(e) => setDraft({ ...draft, check_target_min: Number(e.target.value) })}
                  />
                </label>
                <label className="block">
                  <span className="label-mono mb-1 block text-mute">Check max</span>
                  <input
                    className={FIELD}
                    type="number"
                    step={50000}
                    value={draft.check_target_max}
                    onChange={(e) => setDraft({ ...draft, check_target_max: Number(e.target.value) })}
                  />
                </label>
              </div>

              <div className="flex items-center justify-between pt-1">
                <p className="label-mono text-mute">Saved to the run profile</p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={onClose}
                    className="h-8 rounded-md border border-line px-3 font-mono text-[11px] text-body transition-colors hover:bg-raised"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={saving}
                    className="h-8 rounded-md bg-lime px-3 font-mono text-[11px] font-bold uppercase tracking-[0.08em] text-black transition-colors hover:bg-[#e6ff3d] disabled:bg-lime/40"
                  >
                    {saving ? 'Saving' : 'Save brief'}
                  </button>
                </div>
              </div>
            </form>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
