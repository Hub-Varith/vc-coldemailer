import { AnimatePresence, motion } from 'framer-motion'
import { CheckCircle2, TriangleAlert } from 'lucide-react'

export interface ToastMessage {
  id: number
  title: string
  detail: string
  tone: 'success' | 'warning'
}

export function ToastStack({ toasts, onDismiss }: { toasts: ToastMessage[]; onDismiss: (id: number) => void }) {
  return (
    <div className="pointer-events-none fixed bottom-5 right-5 z-50 flex w-[320px] flex-col gap-2" role="status" aria-live="polite">
      <AnimatePresence initial={false}>
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            layout
            initial={{ opacity: 0, y: 14, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 380, damping: 30 }}
            onClick={() => onDismiss(toast.id)}
            className={`pointer-events-auto cursor-pointer rounded-md border px-3 py-2.5 shadow-[0_16px_40px_-12px_rgba(0,0,0,0.9)] ${
              toast.tone === 'success' ? 'border-lime/30 bg-[#141a05]' : 'border-amber/30 bg-[#1a1405]'
            }`}
          >
            <p
              className={`flex items-center gap-1.5 font-mono text-[11px] font-bold uppercase tracking-[0.08em] ${
                toast.tone === 'success' ? 'text-lime' : 'text-amber'
              }`}
            >
              {toast.tone === 'success' ? (
                <CheckCircle2 size={12} aria-hidden />
              ) : (
                <TriangleAlert size={12} aria-hidden />
              )}
              {toast.title}
            </p>
            <p className="mt-1 text-[11px] leading-snug text-body">{toast.detail}</p>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}
