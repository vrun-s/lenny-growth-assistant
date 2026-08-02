import { Clock, Mic } from 'lucide-react'

interface SourcesViewProps {
  citations: string[]
}

interface ParsedCitation {
  episode: string
  speaker: string | null
  timestamp: string | null
}

// Backend's rag_skill._citation() builds citations as exactly
// "{episode}" + " — {speaker}" + " [{timestamp_range}]" (either suffix
// optional). Parsing on those same literal separators — rather than a loose
// regex — means episode+meta always reconstructs the original string
// character-for-character, which is what e2e tests assert is on the page.
function parseCitation(raw: string): ParsedCitation {
  let rest = raw
  let timestamp: string | null = null
  if (rest.endsWith(']')) {
    const bracketStart = rest.lastIndexOf(' [')
    if (bracketStart !== -1) {
      timestamp = rest.slice(bracketStart + 2, -1)
      rest = rest.slice(0, bracketStart)
    }
  }
  let speaker: string | null = null
  const dashIndex = rest.indexOf(' — ')
  let episode = rest
  if (dashIndex !== -1) {
    episode = rest.slice(0, dashIndex)
    speaker = rest.slice(dashIndex + 3)
  }
  return { episode, speaker, timestamp }
}

// Loose polaroid-stack rotation, deterministic per card so re-renders don't
// jitter — alternating tilt reads as "tossed down", not a tidy aligned list.
const ROTATIONS = [-4, 3, -2.5, 4, -3, 2.5]

/** Body content for the side panel's 'sources' mode — citations belonging to
 * the most recent grounded assistant message in the session (see AppLayout
 * for the reactivity rule). Panel-level header/close/fullscreen controls
 * live in SidePanel, not here. Signature element: a loose stacked-card
 * cluster instead of a flat list, each card showing episode/speaker/
 * timestamp in place of a photo. */
export function SourcesView({ citations }: SourcesViewProps) {
  if (citations.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
        No sources yet — citations from a grounded answer will appear here.
      </div>
    )
  }

  return (
    <div className="flex flex-col px-6 py-8">
      {citations.map((citation, index) => {
        const { episode, speaker, timestamp } = parseCitation(citation)
        const rotation = ROTATIONS[index % ROTATIONS.length]
        return (
          <div
            key={`${citation}-${index}`}
            className={`relative rounded-xl border border-black/8 bg-white px-4 py-4 shadow-[0_10px_24px_-12px_rgba(42,42,40,0.4)] transition hover:z-10 hover:-translate-y-1 hover:rotate-0 hover:shadow-[0_18px_36px_-14px_rgba(42,42,40,0.45)] ${
              index > 0 ? '-mt-3' : ''
            }`}
            style={{ transform: `rotate(${rotation}deg)`, zIndex: index }}
          >
            <div className="text-sm font-semibold text-foreground">{episode}</div>
            {(speaker || timestamp) && (
              <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                {speaker && (
                  <span className="inline-flex items-center gap-1">
                    <Mic className="h-3 w-3" aria-hidden />
                    {speaker}
                  </span>
                )}
                {timestamp && (
                  <span className="inline-flex items-center gap-1">
                    <Clock className="h-3 w-3" aria-hidden />
                    {timestamp}
                  </span>
                )}
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}
