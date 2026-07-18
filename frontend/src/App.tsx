import { useEffect } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import AuthPage from './pages/AuthPage'
import Editor from './pages/Editor'
import LobbyPage from './pages/LobbyPage'
import SettingsPage from './pages/SettingsPage'
import { useStore } from './store'

export default function App() {
  const user = useStore((s) => s.user)
  const authChecked = useStore((s) => s.authChecked)
  const checkAuth = useStore((s) => s.checkAuth)

  useEffect(() => {
    void checkAuth()
  }, [checkAuth])

  if (!authChecked) {
    return (
      <div className="fullscreen-center">
        <div className="spinner" />
      </div>
    )
  }
  if (!user) return <AuthPage />

  return (
    <Routes>
      <Route path="/" element={<LobbyPage />} />
      <Route path="/editor" element={<Editor />} />
      <Route path="/editor/:workflowId" element={<Editor />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
