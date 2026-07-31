import { useEffect, useState } from 'react'
import { toast } from 'sonner'
import { apiClient } from '../../../core/api_client'
import type { ArtifactSummary } from '../types'

/** Fetches one artifact by id. Content/type always come from this fetched
 * object — never parsed or sniffed from chat message text (PRD §6.6). */
export function useArtifact(artifactId: string | null) {
  const [artifact, setArtifact] = useState<ArtifactSummary | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!artifactId) {
      setArtifact(null)
      setError(null)
      setLoading(false)
      return
    }

    setLoading(true)
    setError(null)
    apiClient
      .get<ArtifactSummary>(`/artifacts/${artifactId}`)
      .then(setArtifact)
      .catch(() => {
        setError('Could not load this artifact.')
        toast.error('Could not load this artifact.')
      })
      .finally(() => setLoading(false))
  }, [artifactId])

  return { artifact, loading, error }
}
