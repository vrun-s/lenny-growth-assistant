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
}: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  if (!sessionId) {
    return (
      <div className="flex h-full items-center justify-center text-center text-sm text-zinc-400">
        Start a new chat to begin.
      </div>
    )
  }

  if (loading) {
    return <div className="flex h-full items-center justify-center text-zinc-400">Loading conversation…</div>
  }

  // DB failures are whole-app scoped (PRD §7.1: "frontend shows a banner,
  // not a blank chat") — surfaced as a persistent top banner rather than the
  // inline per-message error text used for harness/generic failures below.
  const isDbDown = errorKind === 'db'

  return (
    <div className="flex h-full flex-col">
      {isDbDown && (
        <div className="border-b border-red-200 bg-red-50 px-4 py-2 text-center text-sm font-medium text-red-700">
          {error}
        </div>
      )}

      <div className="flex-1 overflow-auto px-6 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-zinc-400">
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
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && !isDbDown && <div className="px-4 py-1 text-center text-sm text-red-600">{error}</div>}

      <div className="mx-auto w-full max-w-2xl">
        <MessageInput disabled={sending} onSend={onSend} />
      </div>
    </div>
  )
}
