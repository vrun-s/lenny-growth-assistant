import { ArtifactCard } from '../../artifacts/components/ArtifactCard'
import type { ChatMessageStatus, MessageRole } from '../types'
import { ThinkingIndicator } from './ThinkingIndicator'

interface ChatBubbleProps {
  role: MessageRole
  content: string
  artifactId: string | null
  onOpenArtifact: (artifactId: string) => void
  artifactPanelEnabled: boolean
  status?: ChatMessageStatus
  toolInProgress?: string | null
  createdAt?: string
}

function formatTimestamp(iso: string): string {
  return new Date(iso).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' })
}

const TOOL_LABELS: Record<string, string> = {
  rag_query: "Searching Lenny's transcripts",
  write_ship30_essay: 'Writing your essay',
  generate_artifact: 'Writing your artifact',
}

function toolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] ?? `Using ${toolName}`
}

export function ChatBubble({
  role,
  content,
  artifactId,
  onOpenArtifact,
  artifactPanelEnabled,
  status = 'done',
  toolInProgress,
  createdAt,
}: ChatBubbleProps) {
  const isUser = role === 'user'

  // A tool is running and no text has arrived since (a fresh "text" event
  // clears toolInProgress in useChatSession) — show what's happening
  // instead of an empty bubble. Also covers the pre-first-token gap and the
  // non-streaming fallback wait, both of which look identical: streaming,
  // no content yet, no tool named.
  if (status === 'streaming' && !content) {
    return <ThinkingIndicator label={toolInProgress ? toolLabel(toolInProgress) : undefined} />
  }

  return (
    <div className={`flex max-w-[75%] flex-col gap-1 ${isUser ? 'self-end items-end' : 'self-start items-start'}`}>
      <div
        className={`whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground'
        }`}
      >
        {content}
        {status === 'streaming' && (
          <span className="ml-0.5 inline-block h-3.5 w-1.5 animate-pulse bg-current align-middle opacity-40" />
        )}
      </div>
      {status !== 'streaming' && createdAt && (
        <span className="px-1 text-[11px] text-muted-foreground">{formatTimestamp(createdAt)}</span>
      )}
      {status === 'interrupted' && (
        <div className="px-1 text-xs text-amber-600">Response was interrupted</div>
      )}
      {status === 'done' && artifactId && (
        <ArtifactCard artifactId={artifactId} onOpen={onOpenArtifact} enabled={artifactPanelEnabled} />
      )}
    </div>
  )
}
