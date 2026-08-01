import { useRef } from 'react'

interface UseResizableWidthOptions {
  width: number
  min: number
  max: number
  /** 1 when dragging right should grow the width (a handle on the
   * container's right edge, e.g. the sidebar); -1 when dragging left should
   * grow it (a handle on the left edge, e.g. the side panel). */
  direction: 1 | -1
  onResize: (width: number) => void
}

/** Drag-to-resize math shared by the side panel and the sidebar — mousedown
 * on the handle, track movement against the starting width, clamp to
 * [min, max], clean up on mouseup. Visual affordance is ResizeHandle.tsx;
 * this hook only owns the numbers. */
export function useResizableWidth({ width, min, max, direction, onResize }: UseResizableWidthOptions) {
  const dragStateRef = useRef<{ startX: number; startWidth: number } | null>(null)

  function handleResizeStart(event: React.MouseEvent) {
    event.preventDefault()
    dragStateRef.current = { startX: event.clientX, startWidth: width }

    function onMouseMove(moveEvent: MouseEvent) {
      if (!dragStateRef.current) return
      const delta = (moveEvent.clientX - dragStateRef.current.startX) * direction
      const next = Math.min(max, Math.max(min, dragStateRef.current.startWidth + delta))
      onResize(next)
    }

    function onMouseUp() {
      dragStateRef.current = null
      window.removeEventListener('mousemove', onMouseMove)
      window.removeEventListener('mouseup', onMouseUp)
    }

    window.addEventListener('mousemove', onMouseMove)
    window.addEventListener('mouseup', onMouseUp)
  }

  return handleResizeStart
}
