import { useEffect } from 'react'
import AuthPage from './pages/AuthPage'
import Editor from './pages/Editor'
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
  return user ? <Editor /> : <AuthPage />
}
