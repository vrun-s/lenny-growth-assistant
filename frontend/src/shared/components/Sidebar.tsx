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
// Matches the old collapsed rail's fixed `w-14`.
const SIDEBAR_COLLAPSED_WIDTH = 56

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

// Cross-fades the collapsed rail and expanded nav. Opacity alone isn't
// enough — an opacity-0 element is still in the accessibility tree and still
// hit-testable, so the inactive variant's buttons (e.g. both rails have their
// own "Settings" button) stay focusable and collide with getByRole lookups.
// `visibility` fixes that, but must be *delayed* on the way out (only after
// the fade finishes) and applied *immediately* on the way in — otherwise the
// content pops in/out instead of fading.
function overlayTransitionStyle(active: boolean): React.CSSProperties {
  return {
    opacity: active ? 1 : 0,
    visibility: active ? 'visible' : 'hidden',
    pointerEvents: active ? 'auto' : 'none',
    transitionProperty: 'opacity, visibility',
    transitionDuration: '200ms',
    transitionDelay: active ? '100ms, 0ms' : '0ms, 200ms',
    transitionTimingFunction: 'ease-in-out',
  }
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
  const { handleResizeStart, isDragging } = useResizableWidth({
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
  //
  // Both variants stay mounted at all times, stacked via absolute inset-0
  // inside an inner clipping wrapper, and cross-fade via opacity — mirrors
  // Claude.ai's own sidebar collapse (width + fade, no content reflow mid
  // transition since the expanded content keeps its full target width the
  // whole time and is simply clipped by the inner wrapper's overflow-hidden).
  // That clipping wrapper is *inner*, not on the <aside> itself, because the
  // resize handle below straddles the aside's right edge on purpose (half
  // in, half out) — overflow-hidden on the aside would clip its hit region
  // and silently break dragging. The width transition is suppressed during
  // an active drag-resize so the handle tracks the cursor 1:1 instead of
  // lagging behind it.
  return (
    <aside
      className={`relative flex h-full shrink-0 flex-col bg-background ${
        isDragging ? '' : 'transition-[width] duration-300 ease-in-out'
      }`}
      style={{ width: collapsed ? SIDEBAR_COLLAPSED_WIDTH : width }}
    >
      {!collapsed && <ResizeHandle edge="right" onMouseDown={handleResizeStart} />}

      <div className="relative h-full w-full overflow-hidden">
      <div
        className="absolute inset-0 flex w-14 shrink-0 flex-col items-center bg-background py-3"
        style={overlayTransitionStyle(collapsed)}
      >
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Show chat history"
          title="Show chat history"
          className="rounded-full p-2.5 text-muted-foreground transition hover:bg-white hover:text-foreground hover:shadow-sm"
        >
          <PanelLeftOpen className="h-5 w-5" />
        </button>

        <button
          type="button"
          onClick={onCreateSession}
          aria-label="New chat"
          title="New chat"
          className="mt-3 rounded-full bg-primary p-2.5 text-primary-foreground shadow-sm transition hover:bg-primary/90"
        >
          <Plus className="h-5 w-5" />
        </button>

        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Show all chats"
          title="Chats"
          className="mt-1 rounded-full p-2.5 text-muted-foreground transition hover:bg-white hover:text-foreground hover:shadow-sm"
        >
          <MessagesSquare className="h-5 w-5" />
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={onOpenSettings}
          aria-label="Settings"
          title="Settings"
          className="rounded-full p-2.5 text-muted-foreground transition hover:bg-white hover:text-foreground hover:shadow-sm"
        >
          <SettingsIcon className="h-5 w-5" />
        </button>
      </div>

      <div
        className="absolute inset-0 flex flex-col bg-background"
        style={{ width, ...overlayTransitionStyle(!collapsed) }}
      >
      <div className="flex items-center justify-between px-4 py-4">
        <h1 className="text-sm font-semibold tracking-tight text-foreground">Lenny Growth Assistant</h1>
        <button
          type="button"
          onClick={onToggleCollapse}
          aria-label="Hide chat history"
          title="Hide chat history"
          className="shrink-0 rounded-full p-1.5 text-muted-foreground transition hover:bg-white hover:text-foreground"
        >
          <PanelLeftClose className="h-4 w-4" />
        </button>
      </div>

      <div className="px-3">
        <button
          type="button"
          onClick={onCreateSession}
          className="flex w-full items-center gap-2 rounded-full bg-primary px-4 py-2.5 text-left text-sm font-medium text-primary-foreground shadow-sm transition hover:bg-primary/90"
        >
          <Plus className="h-4 w-4 shrink-0" aria-hidden />
          New Chat
        </button>
      </div>

      <nav className="mt-4 flex-1 space-y-1.5 overflow-auto px-3">
        {sessionsLoading ? (
          <div className="px-3 py-2 text-sm text-muted-foreground">Loading conversations…</div>
        ) : sessionsError ? (
          <div className="px-3 py-2 text-sm text-red-600">{sessionsError}</div>
        ) : sessions.length === 0 ? (
          <div className="px-3 py-2 text-sm text-muted-foreground">
            No conversations yet — start one above.
          </div>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId
            const isEditing = editingId === session.id
            return (
              <div
                key={session.id}
                className={`group flex w-full items-center gap-1 rounded-full pr-1 shadow-sm transition ${
                  isActive ? 'bg-primary shadow-md' : 'bg-white hover:shadow-md'
                }`}
              >
                {isEditing ? (
                  <input
                    autoFocus
                    value={editValue}
                    onChange={(event) => setEditValue(event.target.value)}
                    onKeyDown={handleEditKeyDown}
                    onBlur={() => void commitEditing(session)}
                    className="min-w-0 flex-1 rounded-full border border-border bg-white px-3 py-1.5 mx-1 my-1 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring/30"
                  />
                ) : (
                  <button
                    type="button"
                    onClick={() => onSelectSession(session.id)}
                    className="flex min-w-0 flex-1 items-center gap-2.5 px-4 py-2.5 text-left"
                  >
                    <MessagesSquare
                      className={`h-4 w-4 shrink-0 ${isActive ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}
                      aria-hidden
                    />
                    <span className="min-w-0 flex-1">
                      <div className={`truncate text-sm font-medium ${isActive ? 'text-primary-foreground' : 'text-foreground'}`}>
                        {session.title}
                      </div>
                      <div className={`truncate text-[11px] ${isActive ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                        {formatTimestamp(session.created_at)}
                      </div>
                    </span>
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
                    className={`shrink-0 rounded-full p-1.5 opacity-0 transition group-hover:opacity-100 ${
                      isActive
                        ? 'text-primary-foreground/70 hover:bg-white/15 hover:text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                    }`}
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
                    className={`mr-1 shrink-0 rounded-full p-1.5 opacity-0 transition group-hover:opacity-100 ${
                      isActive
                        ? 'text-primary-foreground/70 hover:bg-white/15 hover:text-primary-foreground'
                        : 'text-muted-foreground hover:bg-accent hover:text-foreground'
                    }`}
                  >
                    🗑
                  </button>
                )}
              </div>
            )
          })
        )}
      </nav>

      <div className="px-3 py-3">
        <button
          type="button"
          onClick={onOpenSettings}
          className="flex w-full items-center gap-2 rounded-full bg-white px-4 py-2.5 text-left text-sm font-medium text-foreground shadow-sm transition hover:shadow-md"
        >
          <SettingsIcon className="h-4 w-4" aria-hidden /> Settings
        </button>
      </div>
      </div>
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
