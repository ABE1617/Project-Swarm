import { LogOut } from 'lucide-react'
import { ReactNode } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useStore } from '../store'
import Logo from './Logo'

export default function AppShell({ children }: { children: ReactNode }) {
  const user = useStore((s) => s.user)
  const setUser = useStore((s) => s.setUser)
  const navigate = useNavigate()

  async function logout() {
    await api.post('/api/auth/logout')
    setUser(null)
    navigate('/')
  }

  return (
    <div className="shell">
      <header className="toolbar">
        <button className="toolbar-brand as-button" onClick={() => navigate('/')}>
          <Logo size={21} />
          <span>Swarm</span>
        </button>
        <nav className="shell-nav">
          <NavLink to="/" end>
            Workflows
          </NavLink>
          <NavLink to="/settings">Settings</NavLink>
        </nav>
        <span className="flex-spacer" />
        <div className="toolbar-user">
          <span>{user?.username}</span>
          <button className="btn btn-icon" onClick={() => void logout()} title="Log out">
            <LogOut size={15} />
          </button>
        </div>
      </header>
      <main className="shell-main">{children}</main>
    </div>
  )
}
