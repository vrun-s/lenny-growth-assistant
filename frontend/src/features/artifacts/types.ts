export type ArtifactType = 'markdown' | 'html'

export interface ArtifactSummary {
  id: string
  session_id: string
  type: ArtifactType
  content: string
  created_at: string
}
