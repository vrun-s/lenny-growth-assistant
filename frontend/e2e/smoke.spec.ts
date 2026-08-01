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
  await expect(page.getByText('Sources: Some Episode')).toBeVisible()
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
  await expect(page.getByText('Sources: Annie Duke — Decision Making')).toBeVisible()
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
