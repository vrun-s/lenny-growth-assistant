import { useEffect, useState } from 'react'
import { ArtifactViewer } from '../../features/artifacts/components/ArtifactViewer'
import { ChatWindow } from '../../features/chat/components/ChatWindow'
import { useChatSession } from '../../features/chat/hooks/useChatSession'
import { SettingsModal } from '../../features/settings/components/SettingsModal'
import { useSessions } from '../../features/sessions/hooks/useSessions'
import { Panel } from '../components/Panel'
import { Sidebar } from '../components/Sidebar'
import { TopBar } from '../components/TopBar'

export function AppLayout() {
  const [panelCollapsed, setPanelCollapsed] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const {
    sessions,
    activeSessionId,
    loading: sessionsLoading,
    error: sessionsError,
    selectSession,
    createSession,
    deleteSession,
  } = useSessions()

  const {
    messages,
    loading: messagesLoading,
    sending,
    error: chatError,
    errorKind: chatErrorKind,
    sendMessage,
  } = useChatSession(activeSessionId)

  // Auto-open only governs the first appearance of a given artifact — the
  // effect only re-fires when this value actually changes, so a user who
  // manually re-collapses the panel while looking at the same trailing
  // artifact message isn't fought by this effect re-opening it.
  const lastMessage = messages[messages.length - 1]
  const latestArtifactId = lastMessage?.role === 'assistant' ? lastMessage.artifact_id : null

  useEffect(() => {
    if (latestArtifactId) {
      setPanelCollapsed(false)
    }
  }, [latestArtifactId])

  return (
    <div className="flex h-screen bg-zinc-50 text-zinc-900">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        sessionsLoading={sessionsLoading}
        sessionsError={sessionsError}
        onSelectSession={selectSession}
        onCreateSession={() => void createSession()}
        onDeleteSession={(id) => void deleteSession(id)}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar panelCollapsed={panelCollapsed} onTogglePanel={() => setPanelCollapsed((c) => !c)} />
        <div className="min-h-0 flex-1">
          <ChatWindow
            sessionId={activeSessionId}
            messages={messages}
            loading={messagesLoading}
            sending={sending}
            error={chatError}
            errorKind={chatErrorKind}
            onSend={(text) => void sendMessage(text)}
          />
        </div>
      </div>

      <Panel collapsed={panelCollapsed}>
        <ArtifactViewer artifactId={latestArtifactId} />
      </Panel>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
