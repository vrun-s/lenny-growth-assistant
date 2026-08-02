import { Maximize2, Minimize2, XIcon } from 'lucide-react'
import { useEffect, useLayoutEffect, useRef, useState, type ReactNode } from 'react'
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

// Kept in sync with the transition-[width]/opacity durations below — the
// unmount timer just needs to run at least as long as the CSS animation.
const CLOSE_ANIMATION_MS = 300

/** The single side panel — mutually exclusive sources/artifact content, per
 * AppLayout's priority rule (artifact beats sources, only one renders at a
 * time). Owns its own header (title/close/fullscreen) so ArtifactViewer and
 * SourcesView only need to render body content, not duplicate chrome. */
export function Panel({ content, width, isFullscreen, onClose, onToggleFullscreen, onResizeWidth, children }: PanelProps) {
  // Handle sits on the panel's left edge; dragging left (away from the
  // panel, which is right-aligned) grows it — direction -1.
  const { handleResizeStart, isDragging } = useResizableWidth({
    width,
    min: PANEL_MIN_WIDTH,
    max: PANEL_MAX_WIDTH,
    direction: -1,
    onResize: onResizeWidth,
  })

  // Slides in/out like Claude.ai's artifact panel instead of popping in and
  // out instantly: stays mounted for CLOSE_ANIMATION_MS after content goes
  // 'hidden' so the width/opacity transition below has time to play before
  // unmounting for real.
  const asideRef = useRef<HTMLElement>(null)
  const [mounted, setMounted] = useState(content !== 'hidden')
  const [open, setOpen] = useState(false)
  // Kept stable through the close animation so the title (and TITLES lookup)
  // don't flip to a default the instant `content` goes 'hidden', while the
  // panel is still visibly fading out.
  const [displayedContent, setDisplayedContent] = useState<Exclude<PanelContent, 'hidden'>>(
    content === 'hidden' ? 'sources' : content,
  )

  useEffect(() => {
    if (content !== 'hidden') {
      setDisplayedContent(content)
      setMounted(true)
      return
    }
    setOpen(false)
    const timeout = window.setTimeout(() => setMounted(false), CLOSE_ANIMATION_MS)
    return () => window.clearTimeout(timeout)
  }, [content])

  // Runs synchronously right after `mounted` flips true and the width:0 DOM
  // commit lands, but before the browser paints. requestAnimationFrame alone
  // (even two nested calls) turned out not to be reliable here — this
  // browser can fire consecutive rAF callbacks with no paint in between, so
  // `open` was flipping to true before width:0 was ever actually committed
  // to the render tree, and the panel snapped straight to full width
  // (confirmed empirically by tracing style mutations on open). Reading
  // offsetWidth forces a synchronous layout of the width:0 state — locking
  // it in as the browser's last computed style — before flipping open on
  // the next tick, which the CSS transition can then reliably animate from.
  //
  // Keyed on `content` as well as `mounted`, not `mounted` alone: when the
  // panel is re-shown while the close animation is still in flight, `mounted`
  // is still true (its unmount timer hasn't fired), so a `[mounted]`-only
  // effect never re-runs — `open` stays false and the panel sticks at width 0
  // permanently. That is the normal send-a-message path, where the session
  // refresh flips content hidden -> sources inside the 300ms window.
  useLayoutEffect(() => {
    if (content === 'hidden') return
    if (asideRef.current) void asideRef.current.offsetWidth
    const raf = requestAnimationFrame(() => setOpen(true))
    return () => cancelAnimationFrame(raf)
  }, [mounted, content])

  if (!mounted) return null

  const targetWidth = isFullscreen ? '100%' : width
  const currentWidth = open ? targetWidth : 0

  return (
    <aside
      ref={asideRef}
      className={`relative flex h-full shrink-0 flex-col border-l border-border bg-card ${
        isDragging ? '' : 'transition-[width] duration-300 ease-in-out'
      }`}
      style={{ width: currentWidth }}
    >
      {/* Resize is horizontal-only, and disabled in fullscreen (width there
          is dictated by the viewport, not the drag handle). Rendered as a
          sibling of the clipping wrapper below, not inside it — it straddles
          the panel's left edge on purpose (half in, half out), and
          overflow-hidden here would clip its own hit region. */}
      {!isFullscreen && open && <ResizeHandle edge="left" onMouseDown={handleResizeStart} />}

      <div className="h-full w-full overflow-hidden">
        {/* Fixed at the real target width regardless of the wrapper's animated
            width, so text reflows once (at the end state) instead of wrapping
            progressively as the wrapper narrows — same technique as Sidebar. */}
        <div
          className={`flex h-full min-w-0 flex-col transition-opacity duration-200 ${
            open ? 'opacity-100 delay-100' : 'opacity-0'
          }`}
          style={{ width: targetWidth }}
        >
          <div className="flex h-14 shrink-0 items-center justify-between border-b border-border px-4">
            <h2 className="text-sm font-semibold text-foreground">{TITLES[displayedContent]}</h2>
            <div className="flex items-center gap-1">
              <button
                type="button"
                onClick={onToggleFullscreen}
                aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
                className="rounded-full p-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
              >
                {isFullscreen ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
              </button>
              <button
                type="button"
                onClick={onClose}
                aria-label="Close panel"
                className="rounded-full p-1.5 text-muted-foreground transition hover:bg-accent hover:text-foreground"
              >
                <XIcon className="h-4 w-4" />
              </button>
            </div>
          </div>

          <div className="min-h-0 flex-1 overflow-auto">{children}</div>
        </div>
      </div>
    </aside>
  )
}
