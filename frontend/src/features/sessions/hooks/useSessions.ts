import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { apiClient } from '../../../core/api_client'
import { ACTIVE_SESSION_STORAGE_KEY } from '../../../core/constants'
import type { SessionSummary } from '../types'

export function useSessions() {
  const [sessions, setSessions] = useState<SessionSummary[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    apiClient
      .get<SessionSummary[]>('/sessions')
      .then((list) => {
        setSessions(list)
        const storedId = localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY)
        const initialId = list.find((s) => s.id === storedId)?.id ?? list[0]?.id ?? null
        setActiveSessionId(initialId)
        if (initialId) {
          localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, initialId)
        } else {
          localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY)
        }
      })
      .catch(() => setError('Could not load sessions.'))
      .finally(() => setLoading(false))
  }, [])

  const selectSession = useCallback((id: string) => {
    setActiveSessionId(id)
    localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, id)
  }, [])

  const createSession = useCallback(async () => {
    try {
      const session = await apiClient.post<SessionSummary>('/sessions', {})
      setSessions((prev) => [session, ...prev])
      setActiveSessionId(session.id)
      localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, session.id)
      return session
    } catch {
      toast.error('Could not start a new chat. Please try again.')
      return undefined
    }
  }, [])

  const deleteSession = useCallback(
    async (id: string) => {
      try {
        await apiClient.delete<void>(`/sessions/${id}`)
      } catch {
        toast.error('Could not delete this chat. Please try again.')
        return
      }

      const next = sessions.filter((s) => s.id !== id)
      setSessions(next)

      if (activeSessionId === id) {
        const fallbackId = next[0]?.id ?? null
        setActiveSessionId(fallbackId)
        if (fallbackId) {
          localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, fallbackId)
        } else {
          localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY)
        }
      }
    },
    [sessions, activeSessionId],
  )

  return { sessions, activeSessionId, loading, error, selectSession, createSession, deleteSession }
}
