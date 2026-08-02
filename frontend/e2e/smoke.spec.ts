import { expect, test } from '@playwright/test'

// PRD §8's "1-2 Playwright smoke tests": send a message → response renders;
// click an artifact card → viewer opens. Every /api/* call is mocked via
// page.route() so these run standalone against `npm run dev`, with no
// backend, database, or LLM required — a frontend rendering check, not an
// LLM-behavior check (see build-log.md for why real-backend E2E was done
// separately, driven manually through Playwright MCP).

const SESSION = {
  id: '11111111-1111-1111-1111-111111111111',
  title: 'Smoke test session',
  created_at: '2026-08-01T00:00:00Z',
  updated_at: '2026-08-01T00:00:00Z',
}

// The panel's default setting is sources-on/artifact-off (Fix 1) — tests
// that exercise the artifact-click flow need it seeded before the app's
// first render, not toggled through the UI mid-test.
async function enableArtifactPanel(page: import('@playwright/test').Page) {
  await page.addInitScript(() => localStorage.setItem('lenny.enabledPanelType', 'artifact'))
}

async function mockSessionList(page: import('@playwright/test').Page) {
  await page.route('**/api/sessions', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ json: [SESSION] })
    } else {
      await route.continue()
    }
  })
  await page.route(`**/api/sessions/${SESSION.id}`, async (route) => {
    await route.fulfill({ json: { session: SESSION, messages: [] } })
  })
}

test('sending a message renders the reply as a new chat bubble', async ({ page }) => {
  await mockSessionList(page)
  await page.route('**/api/chat', async (route) => {
    await route.fulfill({
      json: {
        session_id: SESSION.id,
        assistant_message: 'Here is a grounded answer from the transcripts.',
        citations: ['Some Episode'],
        artifact_id: null,
      },
    })
  })

  await page.goto('/')

  const input = page.getByPlaceholder('Ask about growth, retention, pricing…')
  await input.fill('What makes a good decision maker?')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('What makes a good decision maker?')).toBeVisible()
  await expect(page.getByText('Here is a grounded answer from the transcripts.')).toBeVisible()

  // Citations no longer render inline — a grounded reply auto-shows them in
  // the side panel instead (Feature: unified sources/artifact panel).
  await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible()
  await expect(page.getByText('Some Episode')).toBeVisible()
})

test('a successful SSE stream renders text deltas and finalizes with citations', async ({ page }) => {
  await mockSessionList(page)

  const sseBody =
    `data: ${JSON.stringify({ kind: 'text', text: 'Good ' })}\n\n` +
    `data: ${JSON.stringify({ kind: 'tool_call', tool_name: 'rag_query' })}\n\n` +
    `data: ${JSON.stringify({ kind: 'text', text: 'decision makers ' })}\n\n` +
    `data: ${JSON.stringify({ kind: 'text', text: 'think in bets.' })}\n\n` +
    `data: ${JSON.stringify({
      kind: 'final',
      assistant_message: 'Good decision makers think in bets.',
      citations: ['Annie Duke — Decision Making'],
      artifact_id: null,
    })}\n\n`

  await page.route('**/api/chat/stream', async (route) => {
    await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody })
  })

  await page.goto('/')

  const input = page.getByPlaceholder('Ask about growth, retention, pricing…')
  await input.fill('What makes a good decision maker?')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('Good decision makers think in bets.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sources' })).toBeVisible()
  // The sources panel renders each citation as a card with the episode and
  // speaker as separate fields (not a flat "Episode — Speaker" string) — see
  // SourcesView's parseCitation.
  await expect(page.getByText('Annie Duke', { exact: true })).toBeVisible()
  await expect(page.getByText('Decision Making', { exact: true })).toBeVisible()
})

test('a stream that fails after producing text is shown as interrupted, not resent', async ({ page }) => {
  await mockSessionList(page)
  let chatCalls = 0

  const sseBody = `data: ${JSON.stringify({ kind: 'text', text: 'Partial answer before it broke.' })}\n\n`

  await page.route('**/api/chat/stream', async (route) => {
    // Truncated body with no "final"/"error" frame and a connection-close
    // simulates a real mid-stream drop, not a clean server-sent error.
    await route.fulfill({ status: 200, contentType: 'text/event-stream', body: sseBody })
  })
  await page.route('**/api/chat', async (route) => {
    chatCalls += 1
    await route.fulfill({
      json: { session_id: SESSION.id, assistant_message: 'should not be sent', citations: [], artifact_id: null },
    })
  })

  await page.goto('/')

  const input = page.getByPlaceholder('Ask about growth, retention, pricing…')
  await input.fill('What makes a good decision maker?')
  await page.getByRole('button', { name: 'Send' }).click()

  await expect(page.getByText('Partial answer before it broke.')).toBeVisible()
  await expect(page.getByText('Response was interrupted')).toBeVisible()
  expect(chatCalls).toBe(0)
})

test('clicking an artifact card opens the artifact panel with content', async ({ page }) => {
  await enableArtifactPanel(page)
  await mockSessionList(page)
  const artifactId = '22222222-2222-2222-2222-222222222222'

  await page.route('**/api/chat', async (route) => {
    await route.fulfill({
      json: {
        session_id: SESSION.id,
        assistant_message: "I've generated the markdown cheat sheet.",
        citations: [],
        artifact_id: artifactId,
      },
    })
  })
  await page.route(`**/api/artifacts/${artifactId}`, async (route) => {
    await route.fulfill({
      json: {
        id: artifactId,
        session_id: SESSION.id,
        type: 'markdown',
        content: '# Top 3 Growth Lessons\n\n- **Lesson one**\n- **Lesson two**\n- **Lesson three**',
        created_at: '2026-08-01T00:00:00Z',
      },
    })
  })

  await page.goto('/')

  const input = page.getByPlaceholder('Ask about growth, retention, pricing…')
  await input.fill('generate a markdown cheat sheet of the top 3 growth lessons')
  await page.getByRole('button', { name: 'Send' }).click()

  // No auto-open (AppLayout.tsx, Feature 2 — Claude.ai-style click-to-open):
  // the panel only opens when the inline ArtifactCard is clicked.
  await expect(page.getByRole('heading', { name: 'Artifact' })).not.toBeVisible()
  await page.getByRole('button', { name: 'Markdown artifact' }).click()

  await expect(page.getByRole('heading', { name: 'Artifact' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Top 3 Growth Lessons' })).toBeVisible()
  await expect(page.getByText('Lesson one')).toBeVisible()
})

test('an open artifact is not stolen by an incoming grounded reply, and the panel closes via its own hide control', async ({
  page,
}) => {
  await enableArtifactPanel(page)
  await mockSessionList(page)
  const artifactId = '33333333-3333-3333-3333-333333333333'
  let chatCalls = 0

  await page.route('**/api/chat', async (route) => {
    chatCalls += 1
    if (chatCalls === 1) {
      await route.fulfill({
        json: {
          session_id: SESSION.id,
          assistant_message: "I've generated the markdown cheat sheet.",
          citations: [],
          artifact_id: artifactId,
        },
      })
    } else {
      await route.fulfill({
        json: {
          session_id: SESSION.id,
          assistant_message: 'Here is a grounded follow-up answer.',
          citations: ['Some Episode'],
          artifact_id: null,
        },
      })
    }
  })
  await page.route(`**/api/artifacts/${artifactId}`, async (route) => {
    await route.fulfill({
      json: {
        id: artifactId,
        session_id: SESSION.id,
        type: 'markdown',
        content: '# Top 3 Growth Lessons',
        created_at: '2026-08-01T00:00:00Z',
      },
    })
  })

  await page.goto('/')
  const input = page.getByPlaceholder('Ask about growth, retention, pricing…')

  await input.fill('generate a markdown cheat sheet')
  await page.getByRole('button', { name: 'Send' }).click()
  await page.getByRole('button', { name: 'Markdown artifact' }).click()
  await expect(page.getByRole('heading', { name: 'Top 3 Growth Lessons' })).toBeVisible()

  // A new grounded reply arrives while the artifact is open. With the
  // sources/artifact toggles mutually exclusive (Fix 1), artifact-enabled
  // implies sources-disabled, so the settings gate alone already stops the
  // reply from claiming the panel — the panel's own artifact-beats-sources
  // priority check is still in place underneath as a second guard, just
  // rarely the one doing the work now that both can't be enabled at once.
  await input.fill('what makes a good decision maker?')
  await page.getByRole('button', { name: 'Send' }).click()
  await expect(page.getByText('Here is a grounded follow-up answer.')).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Artifact' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Sources' })).not.toBeVisible()

  // The panel's own hide control closes it regardless of current content.
  await page.getByRole('button', { name: 'Close panel' }).click()
  await expect(page.getByRole('heading', { name: 'Artifact' })).not.toBeVisible()
})

test('closing the panel while fullscreen returns to the normal chat view, not a blank screen', async ({ page }) => {
  await enableArtifactPanel(page)
  await mockSessionList(page)
  const artifactId = '44444444-4444-4444-4444-444444444444'

  await page.route('**/api/chat', async (route) => {
    await route.fulfill({
      json: {
        session_id: SESSION.id,
        assistant_message: "I've generated the markdown cheat sheet.",
        citations: [],
        artifact_id: artifactId,
      },
    })
  })
  await page.route(`**/api/artifacts/${artifactId}`, async (route) => {
    await route.fulfill({
      json: {
        id: artifactId,
        session_id: SESSION.id,
        type: 'markdown',
        content: '# Fullscreen Close Bug',
        created_at: '2026-08-01T00:00:00Z',
      },
    })
  })

  await page.goto('/')
  const input = page.getByPlaceholder('Ask about growth, retention, pricing…')
  await input.fill('generate a markdown cheat sheet')
  await page.getByRole('button', { name: 'Send' }).click()
  await page.getByRole('button', { name: 'Markdown artifact' }).click()

  await page.getByRole('button', { name: 'Enter fullscreen' }).click()
  await expect(page.getByRole('heading', { name: 'Fullscreen Close Bug' })).toBeVisible()

  // Regression: closePanel() used to only hide the panel content, leaving
  // isFullscreen on — since the sidebar/chat column only render when
  // !isFullscreen, that left nothing rendered at all (a blank white screen)
  // instead of returning to the chat.
  await page.getByRole('button', { name: 'Close panel' }).click()
  await expect(page.getByRole('heading', { name: 'Artifact' })).not.toBeVisible()
  await expect(page.getByText('generate a markdown cheat sheet')).toBeVisible()
  await expect(page.getByPlaceholder('Ask about growth, retention, pricing…')).toBeVisible()
})

test('settings toggles are mutually exclusive, reflect real persisted state on load, and the ON path genuinely works', async ({
  page,
}) => {
  await mockSessionList(page)
  await page.goto('/')

  await page.getByRole('button', { name: 'Settings' }).click()

  // Initial render must match the real default (sources on, artifact off),
  // not a hardcoded checked-by-default value on both switches.
  const sourcesSwitch = page.getByRole('switch', { name: 'Show sources panel' })
  const artifactSwitch = page.getByRole('switch', { name: 'Show artifact panel' })
  await expect(sourcesSwitch).toHaveAttribute('aria-checked', 'true')
  await expect(artifactSwitch).toHaveAttribute('aria-checked', 'false')

  // Turning artifact ON must actually take — not just visually, but as the
  // real state the rest of the app reads — and must turn sources off since
  // only one can be enabled at a time.
  await artifactSwitch.click()
  await expect(artifactSwitch).toHaveAttribute('aria-checked', 'true')
  await expect(sourcesSwitch).toHaveAttribute('aria-checked', 'false')
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('lenny.enabledPanelType')))
    .toBe('artifact')

  // Turning sources back ON must flip artifact back off, and this is the
  // exact ON path the earlier bug report described as broken.
  await sourcesSwitch.click()
  await expect(sourcesSwitch).toHaveAttribute('aria-checked', 'true')
  await expect(artifactSwitch).toHaveAttribute('aria-checked', 'false')

  // Both off simultaneously is allowed — turning the currently-on one off
  // must not force the other back on.
  await sourcesSwitch.click()
  await expect(sourcesSwitch).toHaveAttribute('aria-checked', 'false')
  await expect(artifactSwitch).toHaveAttribute('aria-checked', 'false')
})

test('sidebar collapses to an icon rail (not fully hidden) and expands back via either rail action', async ({
  page,
}) => {
  await mockSessionList(page)
  await page.goto('/')

  await expect(page.getByRole('heading', { name: 'Lenny Growth Assistant' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Smoke test session Aug 1' })).toBeVisible()

  // Collapse via the toggle inside the sidebar itself (Fix 2 — no longer in
  // TopBar). The rail keeps New chat/Chats/Settings as icon buttons instead
  // of disappearing entirely.
  await page.getByRole('button', { name: 'Hide chat history' }).click()
  await expect(page.getByRole('heading', { name: 'Lenny Growth Assistant' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'Smoke test session' })).not.toBeVisible()
  await expect(page.getByRole('button', { name: 'New chat' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Show all chats' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Settings' })).toBeVisible()

  // "Chats" is the other way to re-expand — functionally identical to the
  // toggle, framed as "show my chats" per the brief.
  await page.getByRole('button', { name: 'Show all chats' }).click()
  await expect(page.getByRole('heading', { name: 'Lenny Growth Assistant' })).toBeVisible()

  // And the plain toggle round-trips too, from the expanded side this time.
  await page.getByRole('button', { name: 'Hide chat history' }).click()
  await page.getByRole('button', { name: 'Show chat history' }).click()
  await expect(page.getByRole('heading', { name: 'Lenny Growth Assistant' })).toBeVisible()
})

test('sidebar is horizontally resizable via a drag handle, and the collapsed rail has none', async ({ page }) => {
  await mockSessionList(page)
  await page.goto('/')

  const sidebar = page.locator('aside').first()
  const handle = sidebar.locator('.cursor-col-resize')
  await expect(handle).toBeVisible()

  const startWidth = (await sidebar.boundingBox())!.width
  const handleBox = (await handle.boundingBox())!
  const startX = handleBox.x + handleBox.width / 2
  const y = handleBox.y + handleBox.height / 2

  await page.mouse.move(startX, y)
  await page.mouse.down()
  await page.mouse.move(startX + 80, y, { steps: 5 })
  await page.mouse.up()

  await expect
    .poll(async () => (await sidebar.boundingBox())!.width)
    .toBeGreaterThan(startWidth + 60)
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem('lenny.sidebarWidth')))
    .not.toBeNull()

  // The collapsed rail is a fixed width, not resizable — no handle at all.
  await page.getByRole('button', { name: 'Hide chat history' }).click()
  await expect(page.locator('aside').first().locator('.cursor-col-resize')).toHaveCount(0)
})
