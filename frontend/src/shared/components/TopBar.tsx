interface TopBarProps {
  panelCollapsed: boolean
  onTogglePanel: () => void
}

export function TopBar({ panelCollapsed, onTogglePanel }: TopBarProps) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 bg-white px-6">
      <span className="text-sm font-medium text-zinc-700">Conversation</span>
      <button
        type="button"
        onClick={onTogglePanel}
        className="rounded-lg border border-zinc-300 px-3 py-1.5 text-xs font-medium text-zinc-600 transition hover:bg-zinc-100"
      >
        {panelCollapsed ? 'Show Artifact Panel' : 'Hide Artifact Panel'}
      </button>
    </header>
  )
}
