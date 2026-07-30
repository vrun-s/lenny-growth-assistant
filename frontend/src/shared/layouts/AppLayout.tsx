import { NavLink, Outlet } from 'react-router-dom'

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `px-3 py-1.5 rounded-md text-sm font-medium ${
    isActive ? 'bg-neutral-900 text-white' : 'text-neutral-600 hover:bg-neutral-100'
  }`

export function AppLayout() {
  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center gap-2 border-b border-neutral-200 px-4 py-3">
        <span className="mr-4 text-sm font-semibold">Lenny Growth Assistant</span>
        <nav className="flex gap-1">
          <NavLink to="/" end className={navLinkClass}>
            Chat
          </NavLink>
          <NavLink to="/settings" className={navLinkClass}>
            Settings
          </NavLink>
        </nav>
      </header>
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
