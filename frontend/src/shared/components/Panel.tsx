import { Maximize2, Minimize2, XIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { useResizableWidth } from '../hooks/useResizableWidth'
import { ResizeHandle } from './ResizeHandle'

export const PANEL_MIN_WIDTH = 320
export const PANEL_MAX_WIDTH = 900
export const PANEL_DEFAULT_WIDTH = 480

export type PanelContent = 'sources' | 'artifact' | 'hidden'

interface PanelProps {
  content: PanelContent
  width: number
  isFullscreen: boolean
  onClose: () => void
  onToggleFullscreen: () => void
  onResizeWidth: (width: number) => void
  children: ReactNode
}

const TITLES: Record<Exclude<PanelContent, 'hidden'>, string> = {
  sources: 'Sources',
  artifact: 'Artifact',
}

/** The single side panel — mutually exclusive sources/artifact content, per
 * AppLayout's priority rule (artifact beats sources, only one renders at a
 * time). Owns its own header (title/close/fullscreen) so ArtifactViewer and
 * SourcesView only need to render body content, not duplicate chrome. */
export function Panel({ content, width, isFullscreen, onClose, onToggleFullscreen, onResizeWidth, children }: PanelProps) {
  // Handle sits on the panel's left edge; dragging left (away from the
  // panel, which is right-aligned) grows it — direction -1.
  const handleResizeStart = useResizableWidth({
    width,
    min: PANEL_MIN_WIDTH,
    max: PANEL_MAX_WIDTH,
    direction: -1,
    onResize: onResizeWidth,
  })

  if (content === 'hidden') return null

  return (
    <aside
      className="relative flex h-full shrink-0 flex-col border-l border-zinc-200 bg-white shadow-sm"
      style={{ width: isFullscreen ? '100%' : width }}
    >
      {/* Resize is horizontal-only, and disabled in fullscreen (width there
          is dictated by the viewport, not the drag handle). */}
      {!isFullscreen && <ResizeHandle edge="left" onMouseDown={handleResizeStart} />}

      <div className="flex h-14 shrink-0 items-center justify-between border-b border-zinc-200 px-4">
        <h2 className="text-sm font-semibold text-zinc-900">{TITLES[content]}</h2>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onToggleFullscreen}
            aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
            className="rounded-md p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
          >
            {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close panel"
            className="rounded-md p-1.5 text-zinc-400 transition hover:bg-zinc-100 hover:text-zinc-700"
          >
            <XIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">{children}</div>
    </aside>
  )
}
