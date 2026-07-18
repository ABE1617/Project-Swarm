export interface ConfigField {
  key: string
  label: string
  type: 'string' | 'text' | 'number' | 'boolean' | 'select' | 'json' | 'secret' | 'credential'
  options?: string[]
  default?: unknown
  required?: boolean
  placeholder?: string
  help?: string
  showIf?: Record<string, string | string[]>
  min?: number
  max?: number
  step?: number
  credential_type?: string
}

export interface Credential {
  id: number
  name: string
  type: string
  services: string[]
  account_email: string
  connected: boolean
  created_at: string
}

export interface NodeSpec {
  type: string
  name: string
  description: string
  category: string
  color: string
  icon: string
  inputs: string[]
  outputs: string[]
  config_fields: ConfigField[]
  source?: 'builtin' | 'custom'
}

export interface NodeLoadError {
  file: string
  error: string
}

export interface SwarmNodeData {
  kind: string
  label?: string
  config: Record<string, unknown>
  [key: string]: unknown
}

export interface User {
  id: number
  username: string
  email: string
}

export interface WorkflowMeta {
  id: number
  name: string
  created_at: string
  updated_at: string
}

export type NodeRunStatus = 'pending' | 'queued' | 'running' | 'success' | 'error' | 'skipped'

export interface NodeRunState {
  status: NodeRunStatus
  output?: unknown
  error?: string
  reason?: string
  elapsed_ms?: number
}

export interface LogEntry {
  level: string
  node_id?: string | null
  message: string
  ts?: string
}

export interface RunState {
  runId: string | null
  status: 'idle' | 'running' | 'success' | 'error' | 'cancelled'
  nodeStates: Record<string, NodeRunState>
  logs: LogEntry[]
  error?: string
  elapsedMs?: number
}

export interface WorkflowDefinition {
  nodes: Array<{
    id: string
    type: string
    label?: string
    position: { x: number; y: number }
    config: Record<string, unknown>
  }>
  edges: Array<{
    id?: string
    source: string
    target: string
    sourceHandle?: string
    targetHandle?: string
  }>
}
