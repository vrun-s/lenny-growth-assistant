import { useState } from 'react'
import { ArtifactViewer } from '../../features/artifacts/components/ArtifactViewer'
import { ChatWindow } from '../../features/chat/components/ChatWindow'
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
          <ChatWindow sessionId={activeSessionId} />
        </div>
      </div>

      <Panel collapsed={panelCollapsed}>
        <ArtifactViewer />
      </Panel>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
