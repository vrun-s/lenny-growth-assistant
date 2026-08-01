import type { SessionSummary } from '../sessions/types'

export type MessageRole = 'user' | 'assistant'

/** 'streaming'/'interrupted' only ever apply to the one in-progress assistant
 * message a turn produces — persisted history loaded from the backend never
 * carries this field, which is equivalent to 'done'. */
export type ChatMessageStatus = 'streaming' | 'interrupted' | 'done'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
  artifact_id: string | null
  citations: string[]
  status?: ChatMessageStatus
  toolInProgress?: string | null
}

export interface PersistedMessage {
  id: string
  session_id: string
  role: MessageRole
  content: string
  created_at: string
  artifact_id: string | null
  citations: string[]
}

export interface SessionWithMessages {
  session: SessionSummary
  messages: PersistedMessage[]
}

export interface ChatResponse {
  session_id: string
  assistant_message: string
  citations: string[]
  artifact_id: string | null
}
