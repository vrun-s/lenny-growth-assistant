import { useEffect, useRef, useState } from 'react'
import { apiClient, ApiError } from '../../../core/api_client'
import { ACTIVE_SESSION_STORAGE_KEY } from '../../../core/constants'
import type { ChatMessage, ChatResponse, SessionSummary, SessionWithMessages } from '../types'

async function loadOrCreateSession(): Promise<SessionWithMessages> {
  const storedId = localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY)

  if (storedId) {
    try {
      return await apiClient.get<SessionWithMessages>(`/sessions/${storedId}`)
    } catch (err) {
      if (!(err instanceof ApiError && err.status === 404)) {
        throw err
      }
      // Stored session no longer exists (e.g. deleted) — fall through and create a new one.
      localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY)
    }
  }

  const session = await apiClient.post<SessionSummary>('/sessions', {})
  localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, session.id)
  return { session, messages: [] }
}

export function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadOrCreateSession()
      .then(({ session, messages }) => {
        setSessionId(session.id)
        setMessages(messages.map((m) => ({ id: m.id, role: m.role, content: m.content })))
      })
      .catch(() => setError('Could not load the conversation.'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSend() {
    const text = input.trim()
    if (!text || !sessionId || sending) return

    setSending(true)
    setError(null)
    setInput('')
    setMessages((prev) => [...prev, { id: crypto.randomUUID(), role: 'user', content: text }])

    try {
      const response = await apiClient.post<ChatResponse>('/chat', {
        session_id: sessionId,
        message: text,
      })
      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), role: 'assistant', content: response.assistant_message },
      ])
    } catch {
      setError('Failed to send message.')
    } finally {
      setSending(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-neutral-400">Loading conversation…</div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-auto px-4 py-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-neutral-400">
            Send a message to start the conversation.
          </div>
        ) : (
          <div className="mx-auto flex max-w-2xl flex-col gap-3">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                  message.role === 'user'
                    ? 'self-end bg-neutral-900 text-white'
                    : 'self-start bg-neutral-100 text-neutral-900'
                }`}
              >
                {message.content}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {error && <div className="px-4 py-1 text-center text-sm text-red-600">{error}</div>}

      <form
        className="mx-auto flex w-full max-w-2xl gap-2 border-t border-neutral-200 p-4"
        onSubmit={(e) => {
          e.preventDefault()
          void handleSend()
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={sending}
          className="flex-1 rounded-md border border-neutral-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-900"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Send
        </button>
      </form>
    </div>
  )
}
