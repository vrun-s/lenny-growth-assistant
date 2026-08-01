// The sidebar collapse/expand toggle lives inside Sidebar.tsx itself
// (Claude.ai's own left-nav pattern) — TopBar no longer owns it.
export function TopBar() {
  return (
    <header className="flex h-14 shrink-0 items-center border-b border-zinc-200 bg-white px-6">
      <span className="text-sm font-medium text-zinc-700">Conversation</span>
    </header>
  )
}
