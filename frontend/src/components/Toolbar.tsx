import {
  Download,
  FilePlus2,
  FolderOpen,
  KeyRound,
  LogOut,
  Play,
  Save,
  Trash2,
  Upload,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import { useStore } from '../store'
import type { WorkflowMeta } from '../types'
import CredentialsModal from './CredentialsModal'
import Logo from './Logo'
import RunPanel from './RunPanel'

interface Props {
  onSave: () => Promise<void>
  onRun: () => Promise<void>
  onNew: () => void
  onLoad: (id: number) => Promise<void>
  onExport: () => void
  onImport: (file: File) => void
}

export default function Toolbar({ onSave, onRun, onNew, onLoad, onExport, onImport }: Props) {
  const user = useStore((s) => s.user)
  const setUser = useStore((s) => s.setUser)
  const workflowName = useStore((s) => s.workflowName)
  const workflowId = useStore((s) => s.workflowId)
  const setWorkflow = useStore((s) => s.setWorkflow)
  const runStatus = useStore((s) => s.run.status)

  const [menuOpen, setMenuOpen] = useState(false)
  const [credentialsOpen, setCredentialsOpen] = useState(false)
  const [workflows, setWorkflows] = useState<WorkflowMeta[]>([])
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const menuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function onClickOutside(e: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(e.target as globalThis.Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onClickOutside)
    return () => document.removeEventListener('mousedown', onClickOutside)
  }, [])

  function showToast(message: string) {
    setToast(message)
    window.setTimeout(() => setToast(null), 2500)
  }

  async function openMenu() {
    if (!menuOpen) {
      const { workflows } = await api.get<{ workflows: WorkflowMeta[] }>('/api/workflows')
      setWorkflows(workflows)
    }
    setMenuOpen(!menuOpen)
  }

  async function handleSave() {
    setSaving(true)
    try {
      await onSave()
      showToast('Workflow saved')
    } catch (e) {
      showToast(`Save failed: ${e instanceof Error ? e.message : 'unknown error'}`)
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete(id: number, name: string) {
    if (!window.confirm(`Delete workflow "${name}"?`)) return
    await api.delete(`/api/workflows/${id}`)
    setWorkflows(workflows.filter((w) => w.id !== id))
    if (workflowId === id) setWorkflow(null, workflowName)
  }

  async function logout() {
    await api.post('/api/auth/logout')
    setUser(null)
  }

  return (
    <header className="toolbar">
      <div className="toolbar-brand">
        <Logo size={21} />
        <span>Swarm</span>
      </div>
      <div className="toolbar-divider" />

      <input
        className="workflow-name"
        value={workflowName}
        onChange={(e) => setWorkflow(workflowId, e.target.value)}
        placeholder="Workflow name"
      />

      <button className="btn" onClick={handleSave} disabled={saving} title="Save workflow">
        <Save size={15} /> {saving ? 'Saving…' : 'Save'}
      </button>

      <div className="menu-anchor" ref={menuRef}>
        <button className="btn" onClick={openMenu} title="Open workflow">
          <FolderOpen size={15} /> Open
        </button>
        {menuOpen && (
          <div className="dropdown">
            {workflows.length === 0 && <div className="dropdown-empty">No saved workflows</div>}
            {workflows.map((w) => (
              <div key={w.id} className="dropdown-item">
                <button
                  className="dropdown-load"
                  onClick={async () => {
                    await onLoad(w.id)
                    setMenuOpen(false)
                  }}
                >
                  {w.name}
                </button>
                <button className="btn btn-icon danger" onClick={() => handleDelete(w.id, w.name)}>
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn" onClick={onNew} title="New workflow">
        <FilePlus2 size={15} /> New
      </button>
      <button className="btn" onClick={onExport} title="Export as JSON">
        <Download size={15} />
      </button>
      <button className="btn" onClick={() => fileInputRef.current?.click()} title="Import JSON">
        <Upload size={15} />
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json"
        hidden
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onImport(file)
          e.target.value = ''
        }}
      />

      <button className="btn" onClick={() => setCredentialsOpen(true)} title="Manage credentials">
        <KeyRound size={15} /> Credentials
      </button>

      <span className="flex-spacer" />

      <RunPanel />

      <button
        className="btn btn-primary"
        onClick={() => void onRun()}
        disabled={runStatus === 'running'}
      >
        <Play size={15} /> {runStatus === 'running' ? 'Running…' : 'Run'}
      </button>

      <div className="toolbar-user">
        <span>{user?.username}</span>
        <button className="btn btn-icon" onClick={() => void logout()} title="Log out">
          <LogOut size={15} />
        </button>
      </div>

      {toast && <div className="toast">{toast}</div>}
      {credentialsOpen && <CredentialsModal onClose={() => setCredentialsOpen(false)} />}
    </header>
  )
}
