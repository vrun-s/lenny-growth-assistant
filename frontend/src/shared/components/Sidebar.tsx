import { MessagesSquare, PanelLeftClose, PanelLeftOpen, Pencil, Plus, Settings as SettingsIcon } from 'lucide-react'
import { useRef, useState, type KeyboardEvent } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import type { SessionSummary } from '../../features/sessions/types'
import { useResizableWidth } from '../hooks/useResizableWidth'
import { ResizeHandle } from './ResizeHandle'

export const SIDEBAR_MIN_WIDTH = 200
export const SIDEBAR_MAX_WIDTH = 420
export const SIDEBAR_DEFAULT_WIDTH = 240

interface SidebarProps {
  collapsed: boolean
  onToggleCollapse: () => void
  width: number
  onResizeWidth: (width: number) => void
  sessions: SessionSummary[]
  activeSessionId: string | null
  sessionsLoading: boolean
  sessionsError: string | null
  onSelectSession: (id: string) => void
  onCreateSession: () => void
  onDeleteSession: (id: string) => void
  onRenameSession: (id: string, title: string) => Promise<boolean>
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
  collapsed,
  onToggleCollapse,
  width,
  onResizeWidth,
  sessions,
  activeSessionId,
  sessionsLoading,
  sessionsError,
  onSelectSession,
  onCreateSession,
  onDeleteSession,
  onRenameSession,
  onOpenSettings,
}: SidebarProps) {
  const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')
  // Escape clears editingId/editValue, but the input's onBlur can still fire
  // afterward as it unmounts — without this flag that blur would "commit"
  // the already-cleared editValue and rename the session to "Untitled chat".
  const skipNextCommitRef = useRef(false)
  const pendingDeleteTitle = sessions.find((s) => s.id === pendingDeleteId)?.title

  // Handle sits on the sidebar's right edge; dragging right (away from the
  // sidebar, which is left-aligned) grows it — direction +1, the mirror of
  // the side panel's handle on its own left edge. Called unconditionally
  // (Rules of Hooks) even though only the expanded branch below renders it —
  // the collapsed rail is a fixed width, not resizable.
  const handleResizeStart = useResizableWidth({
    width,
    min: SIDEBAR_MIN_WIDTH,
    max: SIDEBAR_MAX_WIDTH,
    direction: 1,
    onResize: onResizeWidth,
  })

  function startEditing(session: SessionSummary) {
    skipNextCommitRef.current = false
    setEditingId(session.id)
    setEditValue(session.title)
  }

  function cancelEditing() {
    skipNextCommitRef.current = true
    setEditingId(null)
    setEditValue('')
  }

  async function commitEditing(session: SessionSummary) {
    if (skipNextCommitRef.current) {
      skipNextCommitRef.current = false
      return
    }
    const title = editValue.trim() || 'Untitled chat'
    setEditingId(null)
    if (title !== session.title) {
      await onRenameSession(session.id, title)
    }
  }

  // Enter blurs the input, which commits via onBlur below. Escape cancels
  // via skipNextCommitRef instead, so a blur triggered by the input
  // unmounting right after doesn't re-commit the just-cleared value.
  function handleEditKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'Enter') {
      event.preventDefault()
      event.currentTarget.blur()
    } else if (event.key === 'Escape') {
      event.preventDefault()
      cancelEditing()
    }
  }

  // Collapsed state is a slim icon-only rail (Claude.ai's own left-nav
  // pattern), not a fully hidden sidebar — "Chats" re-expands it,
  // functionally the same trigger as the toggle button above it, just
  // framed for what it does rather than what it toggles.
  if (collapsed) {
    return (
      <aside className="flex w-14 shrink-0 flex-col items-center border-r border-zinc-200 bg-white py-3">
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Show chat history"
          title="Show chat history"
          className="rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-900"
        >
          <PanelLeftOpen className="h-5 w-5" />
        </button>

        <button
          type="button"
          onClick={onCreateSession}
          aria-label="New chat"
          title="New chat"
          className="mt-3 rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-900"
        >
          <Plus className="h-5 w-5" />
        </button>

        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Show all chats"
          title="Chats"
          className="mt-1 rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-900"
        >
          <MessagesSquare className="h-5 w-5" />
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={onOpenSettings}
          aria-label="Settings"
          title="Settings"
          className="rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-100 hover:text-zinc-900"
        >
          <SettingsIcon className="h-5 w-5" />
        </button>
      </aside>
    )
  }

  return (
    <aside
      className="relative flex h-full shrink-0 flex-col border-r border-zinc-200 bg-white"
      style={{ width }}
    >
      <ResizeHandle edge="right" onMouseDown={handleResizeStart} />

      <div className="flex items-center justify-between px-4 py-4">
        <h1 className="text-sm font-semibold text-zinc-900">Lenny Growth Assistant</h1>
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Hide chat history"
          title="Hide chat history"
          className="shrink-0 rounded-lg p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
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
            const isEditing = editingId === session.id
            return (
              <div
                key={session.id}
                className={`group flex w-full items-center gap-1 rounded-lg pr-1 transition ${
                  isActive ? 'bg-indigo-50' : 'hover:bg-zinc-100'
                }`}
              >
                {isEditing ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(event) => setEditValue(event.target.value)}
                    onKeyDown={handleEditKeyDown}
                    onBlur={() => void commitEditing(session)}
                    className="min-w-0 flex-1 rounded-md border border-indigo-300 bg-white px-2 py-1.5 mx-1 my-1 text-sm text-zinc-900 focus:outline-none focus:ring-2 focus:ring-indigo-500/30"
                  />
                ) : (
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
                )}
                {!isEditing && (
                  <button
                    type="button"
                    aria-label={`Rename "${session.title}"`}
                    onClick={(event) => {
                      event.stopPropagation()
                      startEditing(session)
                    }}
                    className="shrink-0 rounded-md p-1.5 text-zinc-400 opacity-0 transition hover:bg-zinc-200 hover:text-zinc-700 group-hover:opacity-100"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>
                )}
                {!isEditing && (
                  <button
                    type="button"
                    aria-label={`Delete "${session.title}"`}
                    onClick={(event) => {
                      event.stopPropagation()
                      setPendingDeleteId(session.id)
                    }}
                    className="shrink-0 rounded-md p-1.5 text-zinc-400 opacity-0 transition hover:bg-zinc-200 hover:text-zinc-700 group-hover:opacity-100"
                  >
                    🗑
                  </button>
                )}
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
          <SettingsIcon className="h-4 w-4" aria-hidden /> Settings
        </button>
      </div>

      <AlertDialog
        open={pendingDeleteId !== null}
        onOpenChange={(open) => {
          if (!open) setPendingDeleteId(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this session?</AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDeleteTitle ? `"${pendingDeleteTitle}"` : 'This chat'} and its messages will be
              permanently deleted. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (pendingDeleteId) onDeleteSession(pendingDeleteId)
                setPendingDeleteId(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </aside>
  )
}
