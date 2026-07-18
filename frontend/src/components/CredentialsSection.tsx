import { ExternalLink, Plus, RefreshCw, Trash2 } from 'lucide-react'
import { FormEvent, useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { useStore } from '../store'

const SERVICES = [
  { key: 'gmail', label: 'Gmail' },
  { key: 'sheets', label: 'Sheets' },
  { key: 'calendar', label: 'Calendar' },
  { key: 'drive', label: 'Drive' },
  { key: 'docs', label: 'Docs' },
]

export default function CredentialsSection() {
  const credentials = useStore((s) => s.credentials)
  const loadCredentials = useStore((s) => s.loadCredentials)
  const [creating, setCreating] = useState(false)
  const [name, setName] = useState('')
  const [clientId, setClientId] = useState('')
  const [clientSecret, setClientSecret] = useState('')
  const [services, setServices] = useState<string[]>(['gmail', 'sheets', 'calendar', 'drive', 'docs'])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const redirectUri = `${location.origin}/api/oauth/google/callback`

  useEffect(() => {
    void loadCredentials()
  }, [loadCredentials])

  function toggleService(key: string) {
    setServices((current) =>
      current.includes(key) ? current.filter((s) => s !== key) : [...current, key],
    )
  }

  async function connect(credentialId: number) {
    const { url } = await api.get<{ url: string }>(`/api/credentials/${credentialId}/oauth/start`)
    window.open(url, '_blank', 'noopener')
  }

  async function handleCreate(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const { credential } = await api.post<{ credential: { id: number } }>('/api/credentials', {
        name,
        client_id: clientId,
        client_secret: clientSecret,
        services,
      })
      await loadCredentials()
      setCreating(false)
      setName('')
      setClientId('')
      setClientSecret('')
      await connect(credential.id)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not create the credential')
    } finally {
      setBusy(false)
    }
  }

  async function handleDelete(credentialId: number, credentialName: string) {
    if (!window.confirm(`Delete credential "${credentialName}"? Nodes using it will fail.`)) return
    await api.delete(`/api/credentials/${credentialId}`)
    await loadCredentials()
  }

  return (
    <section className="settings-section">
      <div className="settings-section-header">
        <h2>Credentials</h2>
        <button
          className="btn btn-icon"
          title="Refresh connection status"
          onClick={() => void loadCredentials()}
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {credentials.length === 0 && !creating && <p className="modal-empty">No credentials yet</p>}

      {credentials.map((cred) => (
        <div key={cred.id} className="credential-row">
          <div className="credential-info">
            <div className="credential-name">{cred.name}</div>
            <div className="credential-meta">
              {cred.connected ? (
                <span className="credential-ok">{cred.account_email || 'Connected'}</span>
              ) : (
                <span className="credential-pending">Not connected</span>
              )}
              {' · '}
              {cred.services.join(', ')}
            </div>
          </div>
          <button className="btn btn-small" onClick={() => void connect(cred.id)}>
            <ExternalLink size={12} /> {cred.connected ? 'Reconnect' : 'Connect'}
          </button>
          <button
            className="btn btn-icon danger"
            title="Delete credential"
            onClick={() => void handleDelete(cred.id, cred.name)}
          >
            <Trash2 size={14} />
          </button>
        </div>
      ))}

      {creating ? (
        <form className="credential-form" onSubmit={handleCreate}>
          <label>
            Name
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Google account"
              required
              autoFocus
            />
          </label>
          <label>
            OAuth client ID
            <input
              value={clientId}
              onChange={(e) => setClientId(e.target.value)}
              placeholder="xxxx.apps.googleusercontent.com"
              required
              minLength={10}
            />
          </label>
          <label>
            OAuth client secret
            <input
              type="password"
              value={clientSecret}
              onChange={(e) => setClientSecret(e.target.value)}
              required
              minLength={5}
              autoComplete="off"
            />
          </label>
          <div className="credential-services">
            <span>Services</span>
            <div className="service-checks">
              {SERVICES.map((service) => (
                <label key={service.key} className="service-check">
                  <input
                    type="checkbox"
                    checked={services.includes(service.key)}
                    onChange={() => toggleService(service.key)}
                  />
                  {service.label}
                </label>
              ))}
            </div>
          </div>

          <div className="credential-hint">
            In the{' '}
            <a
              href="https://console.cloud.google.com/apis/credentials"
              target="_blank"
              rel="noreferrer"
            >
              Google Cloud Console
            </a>
            , create an OAuth client (Web application) with this redirect URI, and enable the APIs
            for the selected services:
            <code>{redirectUri}</code>
          </div>

          {error && <div className="auth-error">{error}</div>}
          <div className="credential-form-actions">
            <button type="button" className="btn" onClick={() => setCreating(false)}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={busy || services.length === 0}
            >
              {busy ? 'Creating…' : 'Create and connect'}
            </button>
          </div>
        </form>
      ) : (
        <button className="btn credential-add" onClick={() => setCreating(true)}>
          <Plus size={15} /> Add Google credential
        </button>
      )}
    </section>
  )
}
