import { Route, Routes } from 'react-router-dom'
import { AppLayout } from './shared/layouts/AppLayout'
import { ChatPage } from './features/chat/components/ChatPage'
import { SettingsPage } from './features/settings/components/SettingsPage'

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<ChatPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
