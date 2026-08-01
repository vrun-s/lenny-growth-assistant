import { API_BASE_URL } from '../../core/constants'

export type StreamEvent =
  | { kind: 'text'; text: string }
  | { kind: 'tool_call'; tool_name: string }
  | { kind: 'final'; assistant_message: string; citations: string[]; artifact_id: string | null }
  | { kind: 'error'; error: string }

interface StreamChatParams {
  sessionId: string
  message: string
  onEvent: (event: StreamEvent) => void
  signal?: AbortSignal
}

/** Opens POST /api/chat/stream and parses "data: {...}\n\n" SSE frames off
 * the response body as they arrive. Native EventSource only supports GET —
 * fetch + a ReadableStream reader is the standard approach for SSE-over-POST,
 * so that's what this does instead of fighting EventSource into working here.
 *
 * Throws if the connection can't even be established (network error, or a
 * non-2xx/no-body response) — useChatSession falls back to the non-streaming
 * POST /api/chat in that case. A failure *after* some events have already
 * been delivered (mid-stream disconnect) also throws, but the caller tells
 * these apart by whether onEvent ever fired, not by anything in this module.
 */
export async function streamChat({ sessionId, message, onEvent, signal }: StreamChatParams): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
    signal,
  })

  if (!response.ok || !response.body) {
    const body = await response.text().catch(() => '')
    let detail = body || response.statusText
    try {
      const parsed = JSON.parse(body) as { detail?: string }
      if (parsed.detail) detail = parsed.detail
    } catch {
      // body wasn't JSON — fall back to the raw text/statusText set above
    }
    throw new Error(detail)
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let separatorIndex = buffer.indexOf('\n\n')
    while (separatorIndex !== -1) {
      const rawEvent = buffer.slice(0, separatorIndex)
      buffer = buffer.slice(separatorIndex + 2)
      const dataLine = rawEvent.split('\n').find((line) => line.startsWith('data: '))
      if (dataLine) {
        onEvent(JSON.parse(dataLine.slice('data: '.length)) as StreamEvent)
      }
      separatorIndex = buffer.indexOf('\n\n')
    }
  }
}
