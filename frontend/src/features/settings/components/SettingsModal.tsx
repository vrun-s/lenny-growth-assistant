import { XIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

export function SettingsModal({ open, onClose }: SettingsModalProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-zinc-900">Settings</h2>
          <Button type="button" variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close settings">
            <XIcon />
          </Button>
        </div>
        <p className="mt-4 text-sm text-zinc-500">
          Settings aren't built yet — provider selection, model, and session management are coming in a later
          phase.
        </p>
      </div>
    </div>
  )
}
