import ReactMarkdown from 'react-markdown'
import rehypeSanitize from 'rehype-sanitize'
import { useArtifact } from '../hooks/useArtifact'

interface ArtifactViewerProps {
  artifactId: string | null
}

export function ArtifactViewer({ artifactId }: ArtifactViewerProps) {
  const { artifact, loading, error } = useArtifact(artifactId)

  return (
    <div className="flex h-full flex-col">
      <div className="min-h-0 flex-1 overflow-auto">
        {!artifactId ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-zinc-400">
            No artifact yet — generated Markdown or HTML will appear here.
          </div>
        ) : loading ? (
          <div className="flex h-full items-center justify-center text-sm text-zinc-400">Loading artifact…</div>
        ) : error ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-red-600">
            {error}
          </div>
        ) : artifact?.type === 'html' ? (
          <iframe
            title="Generated HTML artifact"
            sandbox=""
            srcDoc={artifact.content}
            className="h-full w-full border-0"
          />
        ) : artifact ? (
          <div className="px-4 py-4 text-sm leading-relaxed text-zinc-800 [&_code]:rounded [&_code]:bg-zinc-100 [&_code]:px-1 [&_code]:py-0.5 [&_code]:text-xs [&_h1]:mt-4 [&_h1]:text-lg [&_h1]:font-semibold [&_h1]:first:mt-0 [&_h2]:mt-4 [&_h2]:text-base [&_h2]:font-semibold [&_h2]:first:mt-0 [&_li]:my-1 [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5">
            <ReactMarkdown rehypePlugins={[rehypeSanitize]}>{artifact.content}</ReactMarkdown>
          </div>
        ) : null}
      </div>
    </div>
  )
}
