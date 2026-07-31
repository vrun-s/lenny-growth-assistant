import type { MessageRole } from '../types'

interface ChatBubbleProps {
  role: MessageRole
  content: string
}

export function ChatBubble({ role, content }: ChatBubbleProps) {
  const isUser = role === 'user'

  return (
    <div
      className={`max-w-[75%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm shadow-sm ${
        isUser ? 'self-end bg-indigo-600 text-white' : 'self-start bg-white text-zinc-900'
      }`}
    >
      {content}
    </div>
  )
}
