import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
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
        className={`rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
          isUser
            ? 'whitespace-pre-wrap bg-primary text-primary-foreground'
            : 'bg-card text-foreground'
        }`}
      >
        {/* User text stays literal — it's what they typed, and rendering it as
            Markdown would reformat their own message back at them. Assistant
            replies are Markdown (the model emits ## headings and **bold**, and
            the Ship30 structure *is* the bolded lessons), sanitized with the
            same rehype-sanitize pass ArtifactViewer uses. */}
        {isUser ? (
          content
        ) : (
          <div className="[&>*:first-child]:mt-0 [&>*:last-child]:mb-0 [&_a]:underline [&_code]:rounded [&_code]:bg-accent [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs [&_em]:italic [&_h1]:mt-3 [&_h1]:mb-1 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-3 [&_h2]:mb-1 [&_h2]:text-sm [&_h2]:font-semibold [&_h3]:mt-3 [&_h3]:mb-1 [&_h3]:text-sm [&_h3]:font-semibold [&_li]:my-0.5 [&_ol]:my-1.5 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-1.5 [&_pre]:overflow-x-auto [&_pre]:rounded [&_pre]:bg-accent [&_pre]:p-2 [&_strong]:font-semibold [&_ul]:my-1.5 [&_ul]:list-disc [&_ul]:pl-5">
            <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{content}</ReactMarkdown>
          </div>
        )}
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
