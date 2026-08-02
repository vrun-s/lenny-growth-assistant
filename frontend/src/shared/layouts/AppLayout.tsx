import { useEffect, useRef, useState } from 'react'
import { ArtifactViewer } from '../../features/artifacts/components/ArtifactViewer'
import { ChatWindow } from '../../features/chat/components/ChatWindow'
import { useChatSession } from '../../features/chat/hooks/useChatSession'
import { SourcesView } from '../../features/chat/components/SourcesView'
import { useSettings } from '../../features/settings/hooks/useSettings'
import { SettingsModal } from '../../features/settings/components/SettingsModal'
import { useSessions } from '../../features/sessions/hooks/useSessions'
import { Panel, PANEL_DEFAULT_WIDTH, PANEL_MAX_WIDTH, PANEL_MIN_WIDTH, type PanelContent } from '../components/Panel'
import { Sidebar, SIDEBAR_DEFAULT_WIDTH, SIDEBAR_MAX_WIDTH, SIDEBAR_MIN_WIDTH } from '../components/Sidebar'
import { TopBar } from '../components/TopBar'

const PANEL_WIDTH_STORAGE_KEY = 'lenny.panelWidth'
const SIDEBAR_WIDTH_STORAGE_KEY = 'lenny.sidebarWidth'

function readStoredWidth(key: string, min: number, max: number, fallback: number): number {
  const stored = Number(localStorage.getItem(key))
  return stored >= min && stored <= max ? stored : fallback
}

interface FullscreenSnapshot {
  width: number
  sidebarCollapsed: boolean
}

export function AppLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  const [sidebarWidth, setSidebarWidth] = useState<number>(() =>
    readStoredWidth(SIDEBAR_WIDTH_STORAGE_KEY, SIDEBAR_MIN_WIDTH, SIDEBAR_MAX_WIDTH, SIDEBAR_DEFAULT_WIDTH),
  )
  // Disarmed permanently (for the current session) the first time the user
  // manually reopens a sidebar that got auto-collapsed for an artifact — see
  // toggleSidebar. Re-armed on session switch (the rule is session-scoped).
  const sidebarAutoCollapseArmedRef = useRef(true)

  // Single side panel, mutually exclusive content — see Panel.tsx. Artifact
  // beats sources: an incoming grounded reply only claims the panel when
  // it's hidden or already showing sources, never stealing it from an open
  // artifact (see the sources auto-show effect below).
  const [panelContent, setPanelContent] = useState<PanelContent>('hidden')
  const prevPanelContentRef = useRef<PanelContent>('hidden')
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null)
  const [sourceCitations, setSourceCitations] = useState<string[]>([])
  const lastAutoShownMessageIdRef = useRef<string | null>(null)

  const [panelWidth, setPanelWidth] = useState<number>(() =>
    readStoredWidth(PANEL_WIDTH_STORAGE_KEY, PANEL_MIN_WIDTH, PANEL_MAX_WIDTH, PANEL_DEFAULT_WIDTH),
  )
  const [isFullscreen, setIsFullscreen] = useState(false)
  const preFullscreenRef = useRef<FullscreenSnapshot | null>(null)

  const [settingsOpen, setSettingsOpen] = useState(false)
  const { sourcesPanelEnabled, setSourcesPanelEnabled, artifactPanelEnabled, setArtifactPanelEnabled } =
    useSettings()

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

  function openArtifact(artifactId: string) {
    if (!artifactPanelEnabled) return
    setSelectedArtifactId(artifactId)
    setPanelContent('artifact')
  }

  // Shared by the fullscreen toggle's exit path and closePanel() below —
  // both need to undo the fullscreen layout override the same way, restoring
  // whatever width/sidebar state was captured right before entering it.
  function exitFullscreen() {
    const snapshot = preFullscreenRef.current
    setIsFullscreen(false)
    if (snapshot) {
      setPanelWidth(snapshot.width)
      setSidebarCollapsed(snapshot.sidebarCollapsed)
    }
  }

  function closePanel() {
    // Closing while fullscreen must also exit fullscreen — the three-column
    // layout (sidebar + chat) only renders when !isFullscreen, so leaving
    // isFullscreen on with the panel hidden rendered nothing at all (a blank
    // white screen) instead of returning to the normal chat view.
    if (isFullscreen) exitFullscreen()
    setPanelContent('hidden')
  }

  function toggleSidebar() {
    setSidebarCollapsed((collapsed) => {
      const opening = collapsed
      if (opening) {
        // A manual reopen — whether or not the collapse that preceded it was
        // auto-triggered — permanently disarms auto-collapse for the rest of
        // this session. Don't fight this action on the next artifact.
        sidebarAutoCollapseArmedRef.current = false
      }
      return !collapsed
    })
  }

  function toggleFullscreen() {
    if (isFullscreen) {
      exitFullscreen()
    } else {
      preFullscreenRef.current = { width: panelWidth, sidebarCollapsed }
      setIsFullscreen(true)
    }
  }

  function resizePanelWidth(width: number) {
    setPanelWidth(width)
    localStorage.setItem(PANEL_WIDTH_STORAGE_KEY, String(width))
  }

  function resizeSidebarWidth(width: number) {
    setSidebarWidth(width)
    localStorage.setItem(SIDEBAR_WIDTH_STORAGE_KEY, String(width))
  }

  // Auto-collapse the chat history sidebar the first time the panel shows an
  // artifact in this session (not for sources — artifacts get priority
  // treatment throughout this feature set). Re-collapsing on a later
  // artifact while still armed is a harmless no-op if it's already
  // collapsed; if the user has since manually reopened it, armed is false
  // and this does nothing, honoring that manual choice.
  useEffect(() => {
    if (
      panelContent === 'artifact' &&
      prevPanelContentRef.current !== 'artifact' &&
      sidebarAutoCollapseArmedRef.current
    ) {
      setSidebarCollapsed(true)
    }
    prevPanelContentRef.current = panelContent
  }, [panelContent])

  // Sources auto-show: track the most recent grounded (non-empty-citations)
  // assistant message, and once per new such message, claim the panel for
  // sources — but only if enabled and the panel isn't currently showing an
  // artifact the user is actively looking at.
  useEffect(() => {
    const lastGrounded = [...messages]
      .reverse()
      .find((m) => m.role === 'assistant' && m.citations.length > 0 && (m.status === undefined || m.status === 'done'))
    if (!lastGrounded || lastGrounded.id === lastAutoShownMessageIdRef.current) return
    lastAutoShownMessageIdRef.current = lastGrounded.id
    setSourceCitations(lastGrounded.citations)
    if (sourcesPanelEnabled && panelContent !== 'artifact') {
      setPanelContent('sources')
    }
  }, [messages, sourcesPanelEnabled, panelContent])

  // Settings gate content, not just future auto-show — flipping a toggle off
  // must immediately stop showing that content type, not just prevent it
  // from being triggered again later.
  useEffect(() => {
    if (!sourcesPanelEnabled && panelContent === 'sources') setPanelContent('hidden')
  }, [sourcesPanelEnabled, panelContent])
  useEffect(() => {
    if (!artifactPanelEnabled && panelContent === 'artifact') setPanelContent('hidden')
  }, [artifactPanelEnabled, panelContent])

  // Switching sessions clears the panel and re-arms per-session state rather
  // than continuing to show an artifact/sources from the chat just left.
  useEffect(() => {
    setSelectedArtifactId(null)
    setPanelContent('hidden')
    setSourceCitations([])
    lastAutoShownMessageIdRef.current = null
    sidebarAutoCollapseArmedRef.current = true
  }, [activeSessionId])

  const showThreeColumnLayout = !isFullscreen

  return (
    <div className="flex h-screen items-stretch bg-background p-3 text-foreground sm:p-6">
      <div className="flex h-full min-h-0 w-full overflow-hidden rounded-[24px] bg-surface shadow-[0_30px_60px_-25px_rgba(42,42,40,0.35)]">
        {showThreeColumnLayout && (
          <Sidebar
            collapsed={sidebarCollapsed}
            onToggleCollapse={toggleSidebar}
            width={sidebarWidth}
            onResizeWidth={resizeSidebarWidth}
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
        )}

        {showThreeColumnLayout && (
          <div className="flex min-w-0 flex-1 flex-col">
            <TopBar />
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
                artifactPanelEnabled={artifactPanelEnabled}
              />
            </div>
          </div>
        )}

        <Panel
          content={panelContent}
          width={panelWidth}
          isFullscreen={isFullscreen}
          onClose={closePanel}
          onToggleFullscreen={toggleFullscreen}
          onResizeWidth={resizePanelWidth}
        >
          {panelContent === 'artifact' ? (
            <ArtifactViewer artifactId={selectedArtifactId} />
          ) : (
            <SourcesView citations={sourceCitations} />
          )}
        </Panel>

        <SettingsModal
          open={settingsOpen}
          onClose={() => setSettingsOpen(false)}
          sourcesPanelEnabled={sourcesPanelEnabled}
          onSourcesPanelEnabledChange={setSourcesPanelEnabled}
          artifactPanelEnabled={artifactPanelEnabled}
          onArtifactPanelEnabledChange={setArtifactPanelEnabled}
        />
      </div>
    </div>
  )
}
