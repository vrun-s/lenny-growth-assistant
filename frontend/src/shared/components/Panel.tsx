import type { ReactNode } from 'react'

interface PanelProps {
  collapsed: boolean
  children: ReactNode
}

export function Panel({ collapsed, children }: PanelProps) {
  if (collapsed) return null

  return (
    <aside className="w-[480px] shrink-0 overflow-auto border-l border-zinc-200 bg-white shadow-sm">
      {children}
    </aside>
  )
}
