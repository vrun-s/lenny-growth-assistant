import { useEffect, useRef, useState } from 'react'
import { ApiError, apiClient } from '../../../core/api_client'
import { streamChat } from '../streamChat'
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
 *
 * `onExchangeComplete` fires once a turn genuinely succeeds (streamed or
 * fallback) — AppLayout uses it to refresh the session list shortly after,
 * to pick up Feature 4's auto-generated title without polling constantly.
 */
export function useChatSession(sessionId: string | null, onExchangeComplete?: () => void) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [errorKind, setErrorKind] = useState<ChatErrorKind | null>(null)
  const onExchangeCompleteRef = useRef(onExchangeComplete)
  onExchangeCompleteRef.current = onExchangeComplete

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
          messages.map((m) => ({
            id: m.id,
            role: m.role,
            content: m.content,
            artifact_id: m.artifact_id,
            citations: m.citations,
          })),
        )
      })
      .catch((err) => {
        const { message, kind } = classifyError(err, 'Could not load the conversation.')
        setError(message)
        setErrorKind(kind)
      })
      .finally(() => setLoading(false))
  }, [sessionId])

  function updateMessage(id: string, patch: Partial<ChatMessage>) {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)))
  }

  async function sendMessage(text: string) {
    if (!text || !sessionId || sending) return

    setSending(true)
    setError(null)
    setErrorKind(null)
    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: 'user', content: text, artifact_id: null, citations: [] },
    ])

    const assistantId = crypto.randomUUID()
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: 'assistant',
        content: '',
        artifact_id: null,
        citations: [],
        status: 'streaming',
        toolInProgress: null,
      },
    ])

    let receivedAnyEvent = false
    let gotFinal = false
    let gotAnyTerminalEvent = false
    try {
      await streamChat({
        sessionId,
        message: text,
        onEvent: (event) => {
          receivedAnyEvent = true
          if (event.kind === 'text') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId ? { ...m, content: m.content + event.text, toolInProgress: null } : m,
              ),
            )
          } else if (event.kind === 'tool_call') {
            updateMessage(assistantId, { toolInProgress: event.tool_name })
          } else if (event.kind === 'final') {
            gotFinal = true
            gotAnyTerminalEvent = true
            updateMessage(assistantId, {
              content: event.assistant_message,
              citations: event.citations,
              artifact_id: event.artifact_id,
              status: 'done',
              toolInProgress: null,
            })
          } else if (event.kind === 'error') {
            gotAnyTerminalEvent = true
            updateMessage(assistantId, { status: 'interrupted', toolInProgress: null })
            const { message, kind } = classifyError(new Error(event.error), event.error)
            setError(message)
            setErrorKind(kind)
          }
        },
      })
      if (gotFinal) {
        onExchangeCompleteRef.current?.()
      } else if (!gotAnyTerminalEvent) {
        // The connection closed cleanly (no throw) but without ever
        // sending a "final" or "error" frame — the bubble would otherwise
        // be stuck showing the streaming cursor/indicator forever.
        updateMessage(assistantId, { status: 'interrupted', toolInProgress: null })
      }
    } catch (err) {
      if (receivedAnyEvent) {
        // The stream opened and produced real content but then the
        // connection itself dropped mid-turn — don't resend (that would
        // duplicate the user's message); the backend's own interrupted-
        // response persistence already covers this server-side.
        updateMessage(assistantId, { status: 'interrupted', toolInProgress: null })
      } else {
        // Never got a first byte (network error, stream endpoint
        // unreachable) — fall back to the non-streaming path entirely,
        // reusing the same in-progress bubble so the "thinking" indicator
        // already showing doesn't flicker away and back.
        try {
          const response = await apiClient.post<ChatResponse>('/chat', { session_id: sessionId, message: text })
          updateMessage(assistantId, {
            content: response.assistant_message,
            citations: response.citations,
            artifact_id: response.artifact_id,
            status: 'done',
          })
          onExchangeCompleteRef.current?.()
        } catch (fallbackErr) {
          setMessages((prev) => prev.filter((m) => m.id !== assistantId))
          const { message, kind } = classifyError(fallbackErr, 'Failed to send message.')
          setError(message)
          setErrorKind(kind)
        }
      }
    } finally {
      setSending(false)
    }
  }

  return { messages, loading, sending, error, errorKind, sendMessage }
}
