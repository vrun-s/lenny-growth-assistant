import { ArrowUp, Plus } from 'lucide-react'
import { useState, type KeyboardEvent } from 'react'

interface MessageInputProps {
  disabled?: boolean
  onSend: (text: string) => void
}

export function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [value, setValue] = useState('')

  function submit() {
    const text = value.trim()
    if (!text || disabled) return
    onSend(text)
    setValue('')
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline (default textarea behavior).
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit()
    }
  }

  return (
    <form
      className="flex items-center gap-2 rounded-full bg-white py-2 pr-2 pl-4 shadow-md"
      onSubmit={(event) => {
        event.preventDefault()
        submit()
      }}
    >
      <Plus className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Ask about growth, retention, pricing…"
        rows={1}
        disabled={disabled}
        className="max-h-40 flex-1 resize-none bg-transparent py-1.5 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none disabled:opacity-60"
      />
      <button
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Send"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-sm transition hover:bg-primary/90 disabled:cursor-not-allowed disabled:opacity-40"
      >
        <ArrowUp className="h-4 w-4" aria-hidden />
      </button>
    </form>
  )
}
