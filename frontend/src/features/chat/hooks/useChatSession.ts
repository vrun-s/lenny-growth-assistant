import { useEffect, useState } from 'react'
import { ApiError, apiClient } from '../../../core/api_client'
import type { ChatMessage, ChatResponse, SessionWithMessages } from '../types'

/** Which chat-visible surface an error should render on (PRD §7.1): 'db'
 * failures are whole-app scoped and get a banner; 'harness' (Ollama
 * unreachable/timeout) and 'generic' failures are tied to the current
 * message/action and render inline. */
export type ChatErrorKind = 'db' | 'harness' | 'generic'

function classifyError(err: unknown, fallback: string): { message: string; kind: ChatErrorKind } {
  if (err instanceof ApiError) {
    if (err.status === 503) return { message: err.message, kind: 'db' }
    if (err.status === 502) return { message: err.message, kind: 'harness' }
  }
  return { message: fallback, kind: 'generic' }
}

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
  const [errorKind, setErrorKind] = useState<ChatErrorKind | null>(null)

  useEffect(() => {
    if (!sessionId) {
      setMessages([])
      setError(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    setErrorKind(null)
    apiClient
      .get<SessionWithMessages>(`/sessions/${sessionId}`)
      .then(({ messages }) => {
        setMessages(
          messages.map((m) => ({ id: m.id, role: m.role, content: m.content, artifact_id: m.artifact_id })),
        )
      })
      .catch((err) => {
        const { message, kind } = classifyError(err, 'Could not load the conversation.')
        setError(message)
        setErrorKind(kind)
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  async function sendMessage(text: string) {
    if (!text || !sessionId || sending) return

    setSending(true)
    setError(null)
    setErrorKind(null)
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: text, artifact_id: null },
    ])

    try {
      const response = await apiClient.post<ChatResponse>('/chat', {
        session_id: sessionId,
        message: text,
      })
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: 'assistant',
          content: response.assistant_message,
          artifact_id: response.artifact_id,
        },
      ])
    } catch (err) {
      const { message, kind } = classifyError(err, 'Failed to send message.')
      setError(message)
      setErrorKind(kind)
    } finally {
      setSending(false)
    }
  }

  return { messages, loading, sending, error, errorKind, sendMessage }
}
