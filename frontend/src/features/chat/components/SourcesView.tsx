interface SourcesViewProps {
  citations: string[]
}

/** Body content for the side panel's 'sources' mode — citations belonging to
 * the most recent grounded assistant message in the session (see AppLayout
 * for the reactivity rule). Panel-level header/close/fullscreen controls
 * live in SidePanel, not here. */
export function SourcesView({ citations }: SourcesViewProps) {
  if (citations.length === 0) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-zinc-400">
        No sources yet — citations from a grounded answer will appear here.
      </div>
    )
  }

  return (
    <ul className="divide-y divide-zinc-100">
      {citations.map((citation, index) => (
        <li key={`${citation}-${index}`} className="px-4 py-3 text-sm text-zinc-700">
          {citation}
        </li>
      ))}
    </ul>
  )
}
