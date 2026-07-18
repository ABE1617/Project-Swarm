import { FormEvent, useState } from 'react'
import { api, ApiError } from '../api'
import { useStore } from '../store'
import type { User } from '../types'

export default function AuthPage() {
  const setUser = useStore((s) => s.setUser)
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const body = mode === 'login' ? { username, password } : { username, email, password }
      const { user } = await api.post<{ user: User }>(`/api/auth/${mode}`, body)
      setUser(user)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Something went wrong')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="fullscreen-center auth-bg">
      <form className="auth-card" onSubmit={submit}>
        <div className="auth-logo">🐝</div>
        <h1>Swarm</h1>
        <p className="auth-tagline">Local-first workflow automation</p>

        <label>
          Username
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            minLength={3}
            autoFocus
          />
        </label>
        {mode === 'register' && (
          <label>
            Email
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </label>
        )}
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
          />
        </label>

        {error && <div className="auth-error">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? '...' : mode === 'login' ? 'Log in' : 'Create account'}
        </button>

        <button
          type="button"
          className="auth-switch"
          onClick={() => {
            setMode(mode === 'login' ? 'register' : 'login')
            setError(null)
          }}
        >
          {mode === 'login' ? 'No account? Register' : 'Have an account? Log in'}
        </button>
      </form>
    </div>
  )
}
