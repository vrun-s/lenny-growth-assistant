import { useState } from 'react'

const PANEL_TYPE_KEY = 'lenny.enabledPanelType'
// Superseded by PANEL_TYPE_KEY (two independent booleans let both render ON
// with no single source of truth) — read once for a one-time migration so
// anyone with the old keys already in localStorage doesn't see their
// preference silently reset.
const LEGACY_SOURCES_KEY = 'lenny.sourcesPanelEnabled'
const LEGACY_ARTIFACT_KEY = 'lenny.artifactPanelEnabled'

type PanelType = 'sources' | 'artifact' | null

function readInitialPanelType(): PanelType {
  const stored = localStorage.getItem(PANEL_TYPE_KEY)
  if (stored === 'sources' || stored === 'artifact' || stored === 'none') {
    return stored === 'none' ? null : stored
  }

  // No new-format value yet — migrate from the old independent-toggle keys
  // if present, then persist under the new key so this only ever runs once.
  const legacyArtifact = localStorage.getItem(LEGACY_ARTIFACT_KEY)
  const legacySources = localStorage.getItem(LEGACY_SOURCES_KEY)
  let migrated: PanelType = 'sources' // explicit default: sources on, artifact off
  if (legacyArtifact === 'true' && legacySources !== 'true') {
    migrated = 'artifact'
  } else if (legacySources === 'false' && legacyArtifact !== 'true') {
    migrated = null
  }
  localStorage.setItem(PANEL_TYPE_KEY, migrated ?? 'none')
  return migrated
}

/** Client-side display preference only (PRD scope: no backend/DB change) —
 * gates whether the side panel is allowed to show sources/artifact content
 * at all. Sources and artifact are mutually exclusive: at most one is ever
 * "on". Modeled as a single nullable value, not two independent booleans —
 * two booleans meant "turn one on" and "turn the other off" were separate
 * writes that could disagree, which is what let both render checked
 * regardless of real state. A single value makes that combination
 * unrepresentable instead of just avoided by convention. */
export function useSettings() {
  const [activePanelType, setActivePanelType] = useState<PanelType>(readInitialPanelType)

  function persist(next: PanelType) {
    localStorage.setItem(PANEL_TYPE_KEY, next ?? 'none')
    return next
  }

  // Functional updater form throughout — never reads activePanelType from
  // closure — so two toggles firing in quick succession (or a re-render
  // landing between a click and its handler running) can't act on a stale
  // "current" value.
  function setSourcesPanelEnabled(value: boolean) {
    setActivePanelType((prev) => persist(value ? 'sources' : prev === 'sources' ? null : prev))
  }

  function setArtifactPanelEnabled(value: boolean) {
    setActivePanelType((prev) => persist(value ? 'artifact' : prev === 'artifact' ? null : prev))
  }

  return {
    sourcesPanelEnabled: activePanelType === 'sources',
    artifactPanelEnabled: activePanelType === 'artifact',
    setSourcesPanelEnabled,
    setArtifactPanelEnabled,
  }
}
