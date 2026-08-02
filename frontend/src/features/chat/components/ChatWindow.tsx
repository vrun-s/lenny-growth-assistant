import { useEffect, useRef } from 'react'
import type { ChatErrorKind } from '../hooks/useChatSession'
import type { ChatMessage } from '../types'
import { ChatBubble } from './ChatBubble'
import { MessageInput } from './MessageInput'

interface ChatWindowProps {
  sessionId: string | null
  messages: ChatMessage[]
  loading: boolean
  sending: boolean
  error: string | null
  errorKind: ChatErrorKind | null
  onSend: (text: string) => void
  onOpenArtifact: (artifactId: string) => void
  artifactPanelEnabled: boolean
  /** True while the artifact panel is open — its resize handle sits right
   * at the chat area's right edge, where a visible native scrollbar makes it
   * hard to grab reliably. Scrolling itself still works either way. */
  hideScrollbar?: boolean
}

export function ChatWindow({
  sessionId,
  messages,
  loading,
  sending,
  error,
  errorKind,
  onSend,
  onOpenArtifact,
  artifactPanelEnabled,
  hideScrollbar,
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!sessionId) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
        Start a new chat to begin.
      </div>
    )
  }

  if (loading) {
    return <div className="flex h-full items-center justify-center text-muted-foreground">Loading conversation…</div>
  }

  // DB failures are whole-app scoped (PRD §7.1: "frontend shows a banner,
  // not a blank chat") — surfaced as a persistent top banner rather than the
  // inline per-message error text used for harness/generic failures below.
  const isDbDown = errorKind === 'db'

  return (
    <div className="flex h-full flex-col">
      {isDbDown && (
        <div className="mx-4 mb-2 rounded-2xl bg-red-50 px-4 py-2 text-center text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      <div className={`flex-1 overflow-auto px-6 py-6 ${hideScrollbar ? 'scrollbar-none' : ''}`}>
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-muted-foreground">
            {isDbDown ? 'Waiting for the database to come back.' : 'Send a message to start the conversation.'}
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-3">
            {messages.map((message) => (
              <ChatBubble
                key={message.id}
                role={message.role}
                content={message.content}
                artifactId={message.artifact_id}
                onOpenArtifact={onOpenArtifact}
                artifactPanelEnabled={artifactPanelEnabled}
                status={message.status}
                toolInProgress={message.toolInProgress}
                createdAt={message.created_at}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && !isDbDown && <div className="px-4 py-1 text-center text-sm text-red-600">{error}</div>}

      <div className="mx-auto w-full max-w-2xl px-4 pb-4">
        <MessageInput disabled={sending} onSend={onSend} />
      </div>
    </div>
  )
}
