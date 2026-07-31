import { useEffect, useState } from 'react'
import { apiClient } from '../../../core/api_client'
import type { ChatMessage, ChatResponse, SessionWithMessages } from '../types'

/** Loads and sends messages for a given, externally-controlled session id.
 * Which session is active — and creating/deleting sessions — is
 * features/sessions/hooks/useSessions.ts's job; this hook only knows how to
 * load one session's history and post new messages to it.
 */
export function useChatSession(sessionId: string | null) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!sessionId) {
      setMessages([])
      setError(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    apiClient
      .get<SessionWithMessages>(`/sessions/${sessionId}`)
      .then(({ messages }) => {
        setMessages(messages.map((m) => ({ id: m.id, role: m.role, content: m.content })))
      })
      .catch(() => setError('Could not load the conversation.'))
      .finally(() => setLoading(false))
  }, [sessionId])

  async function sendMessage(text: string) {
    if (!text || !sessionId || sending) return

    setSending(true)
    setError(null)
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

  return { messages, loading, sending, error, sendMessage }
}
