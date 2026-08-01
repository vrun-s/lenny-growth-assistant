import { Code2, FileText } from 'lucide-react'
import { useArtifact } from '../hooks/useArtifact'

interface ArtifactCardProps {
  artifactId: string
  onOpen: (artifactId: string) => void
  enabled: boolean
}

/** Inline, clickable affordance rendered inside a ChatBubble for any
 * assistant message carrying an artifact_id (Claude.ai-style click-to-open —
 * see AppLayout.tsx for why there's no auto-open). Fetches via the same
 * useArtifact hook the panel itself uses, just to know markdown vs. html for
 * the icon/label — a second, independent fetch when the panel later opens is
 * expected and cheap, not treated as something to dedupe/cache here.
 *
 * When the artifact panel is turned off in Settings, the card renders
 * visibly inert (muted, no hover affordance, disabled) rather than silently
 * no-opping on click — a disabled control reads as "this is turned off"
 * where a live-looking button that does nothing would just look broken. */
export function ArtifactCard({ artifactId, onOpen, enabled }: ArtifactCardProps) {
  const { artifact } = useArtifact(artifactId)
  const isHtml = artifact?.type === 'html'
  const Icon = isHtml ? Code2 : FileText
  const label = artifact ? (isHtml ? 'HTML artifact' : 'Markdown artifact') : 'Artifact'

  return (
    <button
      type="button"
      disabled={!enabled}
      title={enabled ? undefined : 'Artifact panel is turned off in Settings'}
      onClick={() => onOpen(artifactId)}
      className="flex items-center gap-2 rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-left text-xs font-medium text-zinc-700 shadow-sm transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:border-zinc-200 disabled:hover:bg-zinc-50 disabled:hover:text-zinc-700"
    >
      <Icon className="h-4 w-4 shrink-0" />
      {label}
    </button>
  )
}
