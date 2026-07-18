import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import AppShell from '../components/AppShell'
import type { WorkflowMeta } from '../types'
import { timeAgo } from '../lib/time'

export default function LobbyPage() {
  const [workflows, setWorkflows] = useState<WorkflowMeta[] | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    void api
      .get<{ workflows: WorkflowMeta[] }>('/api/workflows')
      .then((data) => setWorkflows(data.workflows))
      .catch(() => setWorkflows([]))
  }, [])

  async function handleDelete(id: number, name: string) {
    if (!window.confirm(`Delete "${name}"?`)) return
    await api.delete(`/api/workflows/${id}`)
    setWorkflows((current) => current?.filter((w) => w.id !== id) ?? null)
  }

  return (
    <AppShell>
      <div className="lobby">
        <div className="lobby-header">
          <h1>Workflows</h1>
          <button className="btn btn-primary" onClick={() => navigate('/editor')}>
            <Plus size={15} /> New workflow
          </button>
        </div>

        {workflows === null ? (
          <div className="lobby-loading">
            <div className="spinner" />
          </div>
        ) : workflows.length === 0 ? (
          <div className="lobby-empty">
            <p>No workflows yet</p>
            <button className="btn btn-primary" onClick={() => navigate('/editor')}>
              <Plus size={15} /> Create your first workflow
            </button>
          </div>
        ) : (
          <div className="lobby-grid">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                className="workflow-card"
                onClick={() => navigate(`/editor/${workflow.id}`)}
              >
                <div className="workflow-card-name">{workflow.name}</div>
                <div className="workflow-card-meta">Updated {timeAgo(workflow.updated_at)}</div>
                <button
                  className="btn btn-icon danger workflow-card-delete"
                  title="Delete workflow"
                  onClick={(e) => {
                    e.stopPropagation()
                    void handleDelete(workflow.id, workflow.name)
                  }}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  )
}
