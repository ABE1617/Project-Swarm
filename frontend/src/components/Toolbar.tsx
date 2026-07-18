import { Check, Download, Play, RefreshCw, Settings, Upload } from 'lucide-react'
import { useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useStore } from '../store'
import Logo from './Logo'
import RunPanel from './RunPanel'

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

interface Props {
  saveStatus: SaveStatus
  onRun: () => Promise<void>
  onExport: () => void
  onImport: (file: File) => void
}

export default function Toolbar({ saveStatus, onRun, onExport, onImport }: Props) {
  const workflowName = useStore((s) => s.workflowName)
  const workflowId = useStore((s) => s.workflowId)
  const setWorkflow = useStore((s) => s.setWorkflow)
  const runStatus = useStore((s) => s.run.status)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  return (
    <header className="toolbar">
      <button className="toolbar-brand as-button" onClick={() => navigate('/')} title="All workflows">
        <Logo size={21} />
        <span>Swarm</span>
      </button>
      <div className="toolbar-divider" />

      <input
        className="workflow-name"
        value={workflowName}
        onChange={(e) => setWorkflow(workflowId, e.target.value)}
        placeholder="Workflow name"
      />

      <span className={`save-status ${saveStatus}`}>
        {saveStatus === 'saving' && <RefreshCw size={11} className="spin" />}
        {saveStatus === 'saved' && <Check size={12} />}
        {saveStatus === 'saving' ? 'Saving' : saveStatus === 'saved' ? 'Saved' : ''}
        {saveStatus === 'error' && 'Save failed'}
      </span>

      <button className="btn btn-icon" onClick={onExport} title="Export as JSON">
        <Download size={15} />
      </button>
      <button
        className="btn btn-icon"
        onClick={() => fileInputRef.current?.click()}
        title="Import JSON"
      >
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

      <span className="flex-spacer" />

      <RunPanel />

      <button
        className="btn btn-primary"
        onClick={() => void onRun()}
        disabled={runStatus === 'running'}
      >
        <Play size={15} /> {runStatus === 'running' ? 'Running…' : 'Run'}
      </button>

      <button
        className="btn btn-icon"
        onClick={() => navigate('/settings')}
        title="Settings and credentials"
      >
        <Settings size={15} />
      </button>
    </header>
  )
}
