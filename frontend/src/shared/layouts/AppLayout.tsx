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
  // Which artifact the panel currently shows — not just open/closed, since a
  // session can produce several artifacts and any of their inline
  // ArtifactCards (see ChatBubble.tsx) can be clicked to swap the panel to
  // that one, including older messages further up the scroll.
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [settingsOpen, setSettingsOpen] = useState(false)
  const {
    sessions,
    activeSessionId,
    loading: sessionsLoading,
    error: sessionsError,
    selectSession,
    createSession,
    deleteSession,
    renameSession,
    refreshSessions,
  } = useSessions()

  // Feature 4 (auto-naming) runs as a server-side background task, so the
  // frontend can't know exactly when it lands. A single fixed delay isn't
  // reliable — Anthropic's title call typically lands in a couple seconds,
  // but a local Ollama model can easily take 10s+ for the same small
  // completion (confirmed live: a 1.5s-only refresh consistently raced
  // ahead of it). A few staggered attempts covers both without polling
  // indefinitely or wiring a websocket for one field.
  function scheduleSessionsRefresh() {
    for (const delayMs of [2000, 6000, 12000]) {
      window.setTimeout(() => void refreshSessions(), delayMs)
    }
  }

  const {
    messages,
    loading: messagesLoading,
    sending,
    error: chatError,
    errorKind: chatErrorKind,
    sendMessage,
  } = useChatSession(activeSessionId, scheduleSessionsRefresh)

  // No auto-open (Claude.ai-style, chosen over "auto-open once per session"):
  // the panel only opens when a user clicks an ArtifactCard or the TopBar
  // toggle. A prior version auto-opened the panel on every new artifact-
  // bearing message, which — despite a comment claiming otherwise — reopened
  // over a manually-collapsed panel and made older artifacts unreachable once
  // a newer message's auto-open took over. No-auto-open removes that whole
  // class of "did it respect my manual collapse" ambiguity by construction.
  function openArtifact(artifactId: string) {
    setSelectedArtifactId(artifactId)
    setPanelCollapsed(false)
  }

  // Switching sessions clears the panel rather than continuing to show an
  // artifact from the chat the user just left.
  useEffect(() => {
    setSelectedArtifactId(null)
    setPanelCollapsed(true)
  }, [activeSessionId])

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
        onRenameSession={renameSession}
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
            onOpenArtifact={openArtifact}
          />
        </div>
      </div>

      <Panel collapsed={panelCollapsed}>
        <ArtifactViewer artifactId={selectedArtifactId} />
      </Panel>

      <SettingsModal open={settingsOpen} onClose={() => setSettingsOpen(false)} />
    </div>
  )
}
