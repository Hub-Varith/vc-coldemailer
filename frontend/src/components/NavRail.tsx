import { motion } from 'framer-motion'
import { Archive, BarChart3, Building2, Search, Settings, SquarePen } from 'lucide-react'

const ITEMS = [
  { id: 'search', label: 'Live search', icon: Search },
  { id: 'investors', label: 'Investor list', icon: Building2 },
  { id: 'drafts', label: 'Approval queue', icon: SquarePen },
  { id: 'signal', label: 'Reply signal', icon: BarChart3 },
] as const

type NavId = (typeof ITEMS)[number]['id']

export function NavRail({ active, onSelect }: { active: NavId; onSelect: (id: NavId) => void }) {
  return (
    <nav
      aria-label="Workspace sections"
      className="flex h-full w-14 shrink-0 flex-col items-center gap-1 border-r border-line bg-ink py-3"
    >
      <div className="mb-4 flex h-8 w-8 items-center justify-center font-display text-[15px] font-bold tracking-tight text-bright">
        P<span className="text-lime">/</span>
      </div>

      {ITEMS.map(({ id, label, icon: Icon }) => {
        const isActive = active === id
        return (
          <button
            key={id}
            type="button"
            title={label}
            aria-label={label}
            aria-current={isActive ? 'page' : undefined}
            onClick={() => onSelect(id)}
            className="group relative flex h-9 w-9 items-center justify-center rounded-md text-mute transition-colors hover:bg-raised hover:text-bright"
          >
            {isActive && (
              <motion.span
                layoutId="nav-active"
                transition={{ type: 'spring', stiffness: 420, damping: 34 }}
                className="absolute inset-0 rounded-md border border-lime/25 bg-lime/10"
              />
            )}
            <Icon
              size={16}
              strokeWidth={1.75}
              className={`relative ${isActive ? 'text-lime' : ''}`}
              aria-hidden
            />
          </button>
        )
      })}

      <div className="mt-auto flex flex-col items-center gap-1">
        <button
          type="button"
          title="Settings"
          aria-label="Settings"
          className="flex h-9 w-9 items-center justify-center rounded-md text-mute transition-colors hover:bg-raised hover:text-bright"
        >
          <Settings size={16} strokeWidth={1.75} aria-hidden />
        </button>
        <button
          type="button"
          title="Run archive"
          aria-label="Run archive"
          className="flex h-9 w-9 items-center justify-center rounded-md text-mute transition-colors hover:bg-raised hover:text-bright"
        >
          <Archive size={16} strokeWidth={1.75} aria-hidden />
        </button>
      </div>
    </nav>
  )
}

export type { NavId }
