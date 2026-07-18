import { FormEvent, useState } from 'react'
import { api, ApiError } from '../api'
import AppShell from '../components/AppShell'
import CredentialsSection from '../components/CredentialsSection'
import { useStore } from '../store'

function ProfileSection() {
  const user = useStore((s) => s.user)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)

  async function changePassword(e: FormEvent) {
    e.preventDefault()
    setMessage(null)
    setBusy(true)
    try {
      await api.post('/api/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      })
      setCurrentPassword('')
      setNewPassword('')
      setMessage({ ok: true, text: 'Password changed' })
    } catch (err) {
      setMessage({
        ok: false,
        text: err instanceof ApiError ? err.message : 'Could not change the password',
      })
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="settings-section">
      <div className="settings-section-header">
        <h2>Profile</h2>
      </div>
      <div className="profile-row">
        <span>Username</span>
        <span className="profile-value">{user?.username}</span>
      </div>
      <div className="profile-row">
        <span>Email</span>
        <span className="profile-value">{user?.email}</span>
      </div>

      <form className="credential-form" onSubmit={changePassword}>
        <label>
          Current password
          <input
            type="password"
            value={currentPassword}
            onChange={(e) => setCurrentPassword(e.target.value)}
            required
            autoComplete="current-password"
          />
        </label>
        <label>
          New password
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
            minLength={6}
            autoComplete="new-password"
          />
        </label>
        {message && (
          <div className={message.ok ? 'settings-ok' : 'auth-error'}>{message.text}</div>
        )}
        <div className="credential-form-actions">
          <button type="submit" className="btn btn-primary" disabled={busy}>
            {busy ? 'Saving…' : 'Change password'}
          </button>
        </div>
      </form>
    </section>
  )
}

export default function SettingsPage() {
  return (
    <AppShell>
      <div className="settings">
        <h1>Settings</h1>
        <ProfileSection />
        <CredentialsSection />
      </div>
    </AppShell>
  )
}
