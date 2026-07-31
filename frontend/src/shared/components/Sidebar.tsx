import type { SessionSummary } from '../../features/sessions/types'

interface SidebarProps {
  sessions: SessionSummary[]
  activeSessionId: string | null
  sessionsLoading: boolean
  sessionsError: string | null
  onSelectSession: (id: string) => void
  onCreateSession: () => void
  onDeleteSession: (id: string) => void
  onOpenSettings: () => void
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function Sidebar({
  sessions,
  activeSessionId,
  sessionsLoading,
  sessionsError,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onOpenSettings,
}: SidebarProps) {
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-zinc-200 bg-white">
      <div className="px-4 py-4">
        <h1 className="text-sm font-semibold text-zinc-900">Lenny Growth Assistant</h1>
      </div>

      <div className="px-3">
        <button
          type="button"
          onClick={onCreateSession}
          className="w-full rounded-xl bg-indigo-600 px-3 py-2 text-sm font-medium text-white shadow-sm transition hover:bg-indigo-500"
        >
          + New Chat
        </button>
      </div>

      <nav className="mt-4 flex-1 space-y-1 overflow-auto px-2">
        {sessionsLoading ? (
          <div className="px-3 py-2 text-sm text-zinc-400">Loading conversations…</div>
        ) : sessionsError ? (
          <div className="px-3 py-2 text-sm text-red-600">{sessionsError}</div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-2 text-sm text-zinc-400">
            No conversations yet — start one above.
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId
            return (
              <div
                key={session.id}
                className={`group flex w-full items-center gap-1 rounded-lg pr-1 transition ${
                  isActive ? 'bg-indigo-50' : 'hover:bg-zinc-100'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectSession(session.id)}
                  className="min-w-0 flex-1 truncate px-3 py-2 text-left"
                >
                  <div className={`truncate text-sm ${isActive ? 'font-medium text-indigo-700' : 'text-zinc-700'}`}>
                    {session.title}
                  </div>
                  <div className="truncate text-xs text-zinc-400">{formatTimestamp(session.created_at)}</div>
                </button>
                <button
                  type="button"
                  aria-label={`Delete "${session.title}"`}
                  onClick={(event) => {
                    event.stopPropagation()
                    if (window.confirm('Delete this chat? This cannot be undone.')) {
                      onDeleteSession(session.id)
                    }
                  }}
                  className="shrink-0 rounded-md p-1.5 text-zinc-400 opacity-0 transition hover:bg-zinc-200 hover:text-zinc-700 group-hover:opacity-100"
                >
                  🗑
                </button>
              </div>
            )
          })
        )}
      </nav>

      <div className="border-t border-zinc-200 px-2 py-3">
        <button
          type="button"
          onClick={onOpenSettings}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-zinc-600 transition hover:bg-zinc-100 hover:text-zinc-900"
        >
          <span aria-hidden>⚙</span> Settings
        </button>
      </div>
    </aside>
  )
}
