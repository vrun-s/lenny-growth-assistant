export function ArtifactViewer() {
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-zinc-200 px-4 py-3">
        <h2 className="text-sm font-semibold text-zinc-900">Artifact</h2>
      </div>
      <div className="flex flex-1 items-center justify-center px-6 text-center text-sm text-zinc-400">
        No artifact yet — generated Markdown or HTML will appear here.
      </div>
    </div>
  )
}
