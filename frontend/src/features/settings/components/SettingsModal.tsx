import { XIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface SettingsModalProps {
  open: boolean
  onClose: () => void
  sourcesPanelEnabled: boolean
  onSourcesPanelEnabledChange: (value: boolean) => void
  artifactPanelEnabled: boolean
  onArtifactPanelEnabledChange: (value: boolean) => void
}

interface ToggleRowProps {
  label: string
  description: string
  checked: boolean
  onChange: (value: boolean) => void
}

function ToggleRow({ label, description, checked, onChange }: ToggleRowProps) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <div>
        <div className="text-sm font-medium text-foreground">{label}</div>
        <div className="text-xs text-muted-foreground">{description}</div>
      </div>
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        aria-label={label}
        onClick={() => onChange(!checked)}
        className={`relative h-6 w-11 shrink-0 rounded-full transition ${checked ? 'bg-primary' : 'bg-accent'}`}
      >
        <span
          className={`absolute top-0.5 h-5 w-5 rounded-full bg-white shadow-sm transition ${
            checked ? 'left-5' : 'left-0.5'
          }`}
        />
      </button>
    </div>
  )
}

export function SettingsModal({
  open,
  onClose,
  sourcesPanelEnabled,
  onSourcesPanelEnabledChange,
  artifactPanelEnabled,
  onArtifactPanelEnabledChange,
}: SettingsModalProps) {
  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#2A2A28]/40 px-4">
      <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-foreground">Settings</h2>
          <Button type="button" variant="ghost" size="icon-sm" onClick={onClose} aria-label="Close settings">
            <XIcon />
          </Button>
        </div>

        <p className="mt-4 text-xs text-muted-foreground">
          The side panel shows one of these at a time — turning one on turns the other off. Turn both off to keep
          the panel hidden.
        </p>
        <div className="mt-2 divide-y divide-border">
          <ToggleRow
            label="Show sources panel"
            description="Auto-show citations for grounded answers in the side panel."
            checked={sourcesPanelEnabled}
            onChange={onSourcesPanelEnabledChange}
          />
          <ToggleRow
            label="Show artifact panel"
            description="Allow opening generated Markdown/HTML artifacts in the side panel."
            checked={artifactPanelEnabled}
            onChange={onArtifactPanelEnabledChange}
          />
        </div>
      </div>
    </div>
  )
}
