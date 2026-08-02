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

// Loose polaroid tilt, deterministic per card so re-renders don't jitter —
// alternating lean reads as "tossed down", not a tidy aligned list.
//
// Deliberately small (<=1.5deg) and expressed as static Tailwind classes
// rather than an inline `transform`, for two reasons the first version got
// wrong:
//   1. Rotation displaces a card's corners by roughly width/2 * sin(angle).
//      On a ~430px-wide panel card the original 4deg threw each corner ~15px
//      out of line, which overflowed the panel horizontally (titles were
//      visibly sliced off at the right edge) and drove cards into each
//      other vertically.
//   2. An inline `style={{transform}}` outranks Tailwind's `hover:` utilities,
//      so the intended straighten-on-hover silently never fired. Same-
//      specificity utility classes let the hover variant win by cascade
//      order, which is what makes the interaction work at all.
// Class strings must stay literal — Tailwind only generates what it can see.
const ROTATIONS = [
  '-rotate-[1.5deg]',
  'rotate-[1deg]',
  '-rotate-[0.75deg]',
  'rotate-[1.25deg]',
  '-rotate-[1deg]',
  'rotate-[0.75deg]',
]

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
    // px-5 (not px-6) leaves room for the tilt to swing without clipping;
    // gap-5 replaces the old -mt-3 overlap, which stacked opaque white cards
    // directly over the previous card's title and timestamp. The tilt alone
    // carries the "loose pile" look — the overlap was only ever costing
    // legibility.
    //
    // max-w-md matters for more than typography: a tilted card's corners rise
    // and fall by about (width / 2) * sin(angle), so the swing grows with the
    // card. Unbounded, a card in a 900px-wide panel threw its corners ~11px
    // out and started clipping its neighbours again. Capping the width caps
    // the swing at ~6px no matter how wide the user drags the panel — and
    // keeps citation lines at a readable measure instead of stretching them
    // across the full panel.
    <div className="mx-auto flex w-full max-w-md flex-col gap-5 px-5 py-6">
      {citations.map((citation, index) => {
        const { episode, speaker, timestamp } = parseCitation(citation)
        const rotation = ROTATIONS[index % ROTATIONS.length]
        return (
          <div
            key={`${citation}-${index}`}
            className={`relative rounded-xl border border-black/8 bg-white px-4 py-3.5 shadow-[0_10px_24px_-12px_rgba(42,42,40,0.4)] transition hover:z-10 hover:-translate-y-0.5 hover:rotate-0 hover:shadow-[0_18px_36px_-14px_rgba(42,42,40,0.45)] ${rotation}`}
          >
            {/* Real episode titles run long ("Pricing your AI product: Lessons
                from 400+ companies and 50 unicorns | Madhavan Ramanujam"), so
                they must wrap rather than run off the card. */}
            <div className="text-sm leading-snug font-semibold break-words text-foreground">{episode}</div>
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
