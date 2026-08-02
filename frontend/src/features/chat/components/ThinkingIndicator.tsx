import { useEffect, useState } from 'react'

interface ThinkingIndicatorProps {
  /** e.g. "Searching Lenny's transcripts" for a tool-call-in-progress chunk,
   * or omitted for the generic pre-first-token / non-streaming-fallback
   * wait. Either way this is the one indicator both cases share. */
  label?: string
}

const STILL_WORKING_AFTER_SECONDS = 12

export function ThinkingIndicator({ label = 'Thinking' }: ThinkingIndicatorProps) {
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const start = Date.now()
    const id = window.setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div className="flex items-center gap-2 self-start rounded-2xl bg-card px-4 py-2.5 text-sm text-muted-foreground shadow-sm">
      <span className="flex gap-1">
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.3s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60 [animation-delay:-0.15s]" />
        <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-muted-foreground/60" />
      </span>
      <span>
        {label}
        {elapsed >= STILL_WORKING_AFTER_SECONDS ? ` — still working (${elapsed}s)…` : '…'}
      </span>
    </div>
  )
}
