export type MessageRole = 'user' | 'assistant'

export interface ChatMessage {
  id: string
  role: MessageRole
  content: string
}

export interface SessionSummary {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface PersistedMessage {
  id: string
  session_id: string
  role: MessageRole
  content: string
  created_at: string
  artifact_id: string | null
}

export interface SessionWithMessages {
  session: SessionSummary
  messages: PersistedMessage[]
}

export interface ChatResponse {
  session_id: string
  assistant_message: string
}
