import { useEffect, useRef } from 'react'
import { useChatSession } from '../hooks/useChatSession'
import { ChatBubble } from './ChatBubble'
import { MessageInput } from './MessageInput'

interface ChatWindowProps {
  sessionId: string | null
}

export function ChatWindow({ sessionId }: ChatWindowProps) {
  const { messages, loading, sending, error, sendMessage } = useChatSession(sessionId)
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

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-auto px-6 py-6">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center text-sm text-zinc-400">
            Send a message to start the conversation.
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-3">
            {messages.map((message) => (
              <ChatBubble key={message.id} role={message.role} content={message.content} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && <div className="px-4 py-1 text-center text-sm text-red-600">{error}</div>}

      <div className="mx-auto w-full max-w-2xl">
        <MessageInput disabled={sending} onSend={(text) => void sendMessage(text)} />
      </div>
    </div>
  )
}
