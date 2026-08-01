interface ResizeHandleProps {
  /** Which edge of the parent container this handle sits on — controls only
   * which side it's anchored to, not the drag math (that's the caller's
   * onMouseDown, via useResizableWidth). */
  edge: 'left' | 'right'
  onMouseDown: (event: React.MouseEvent) => void
}

/** The visible drag-to-resize affordance shared by the side panel and the
 * chat history sidebar: a faint pill centered on the border, growing and
 * darkening on hover so the border reads as draggable rather than as an
 * invisible hit-zone. Purely presentational — drag math lives in
 * useResizableWidth, not here. */
export function ResizeHandle({ edge, onMouseDown }: ResizeHandleProps) {
  const edgeClass = edge === 'left' ? 'left-0 -translate-x-1/2' : 'right-0 translate-x-1/2'

  return (
    <div
      onMouseDown={onMouseDown}
      className={`group absolute inset-y-0 ${edgeClass} z-10 w-2.5 cursor-col-resize select-none`}
    >
      <div className="pointer-events-none absolute top-1/2 left-1/2 h-10 w-1 -translate-x-1/2 -translate-y-1/2 rounded-full bg-zinc-300 opacity-70 transition-all group-hover:h-14 group-hover:w-1.5 group-hover:bg-indigo-400 group-hover:opacity-100" />
    </div>
  )
}
