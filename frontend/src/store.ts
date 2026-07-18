import { create } from 'zustand'
import { api, runEventsUrl } from './api'
import type {
  Credential,
  NodeLoadError,
  NodeSpec,
  RunState,
  User,
  WorkflowDefinition,
} from './types'

interface SwarmStore {
  user: User | null
  authChecked: boolean
  specs: NodeSpec[]
  specsByType: Record<string, NodeSpec>
  nodeLoadErrors: NodeLoadError[]
  workflowId: number | null
  workflowName: string
  run: RunState
  ws: WebSocket | null
  notice: string | null
  credentials: Credential[]

  loadCredentials: () => Promise<void>
  setNotice: (message: string) => void
  setUser: (user: User | null) => void
  checkAuth: () => Promise<void>
  loadSpecs: () => Promise<void>
  reloadSpecs: () => Promise<void>
  setWorkflow: (id: number | null, name: string) => void
  startRun: (
    definition: WorkflowDefinition,
    workflowId: number | null,
    workflowName: string,
    targetNodeId?: string,
    excludeTarget?: boolean,
  ) => Promise<void>
  cancelRun: () => Promise<void>
  resetRun: () => void
}

const idleRun: RunState = { runId: null, status: 'idle', nodeStates: {}, logs: [] }

export const useStore = create<SwarmStore>((set, get) => ({
  user: null,
  authChecked: false,
  specs: [],
  specsByType: {},
  nodeLoadErrors: [],
  workflowId: null,
  workflowName: 'Untitled workflow',
  run: idleRun,
  ws: null,
  notice: null,
  credentials: [],

  loadCredentials: async () => {
    const { credentials } = await api.get<{ credentials: Credential[] }>('/api/credentials')
    set({ credentials })
  },

  setNotice: (message) => {
    set({ notice: message })
    window.setTimeout(() => {
      if (get().notice === message) set({ notice: null })
    }, 2800)
  },

  setUser: (user) => set({ user, authChecked: true }),

  checkAuth: async () => {
    try {
      const { user } = await api.get<{ user: User }>('/api/auth/me')
      set({ user, authChecked: true })
    } catch {
      set({ user: null, authChecked: true })
    }
  },

  loadSpecs: async () => {
    const data = await api.get<{ nodes: NodeSpec[]; load_errors: NodeLoadError[] }>('/api/nodes')
    const byType: Record<string, NodeSpec> = {}
    for (const spec of data.nodes) byType[spec.type] = spec
    set({ specs: data.nodes, specsByType: byType, nodeLoadErrors: data.load_errors ?? [] })
  },

  reloadSpecs: async () => {
    const data = await api.post<{ nodes: NodeSpec[]; load_errors: NodeLoadError[] }>(
      '/api/nodes/reload',
    )
    const byType: Record<string, NodeSpec> = {}
    for (const spec of data.nodes) byType[spec.type] = spec
    set({ specs: data.nodes, specsByType: byType, nodeLoadErrors: data.load_errors ?? [] })
  },

  setWorkflow: (id, name) => set({ workflowId: id, workflowName: name }),

  startRun: async (definition, workflowId, workflowName, targetNodeId, excludeTarget) => {
    get().ws?.close()
    set({ run: { ...idleRun, status: 'running', runId: null } })

    let run_id: string
    try {
      ;({ run_id } = await api.post<{ run_id: string }>('/api/run', {
        definition,
        workflow_id: workflowId,
        workflow_name: workflowName,
        target_node_id: targetNodeId ?? null,
        exclude_target: excludeTarget ?? false,
      }))
    } catch (e) {
      set({
        run: {
          ...idleRun,
          status: 'error',
          error: e instanceof Error ? e.message : 'Could not start the run',
        },
      })
      return
    }

    const ws = new WebSocket(runEventsUrl(run_id))
    set({ ws, run: { ...idleRun, status: 'running', runId: run_id } })

    ws.onmessage = (msg) => {
      const event = JSON.parse(msg.data)
      set((state) => {
        const run = { ...state.run, nodeStates: { ...state.run.nodeStates }, logs: [...state.run.logs] }
        switch (event.type) {
          case 'node_state':
            run.nodeStates[event.node_id] = {
              status: event.status,
              output: event.output,
              error: event.error,
              reason: event.reason,
              elapsed_ms: event.elapsed_ms,
            }
            if (event.error) {
              run.logs.push({ level: 'error', node_id: event.node_id, message: event.error, ts: event.ts })
            }
            break
          case 'log':
            run.logs.push({ level: event.level, node_id: event.node_id, message: event.message, ts: event.ts })
            break
          case 'run_error':
            run.error = event.message
            run.logs.push({ level: 'error', message: event.message, ts: event.ts })
            break
          case 'run_finished':
            run.status = event.status
            break
        }
        return { run }
      })
    }
    ws.onerror = () => {
      set((state) => ({
        run: { ...state.run, error: state.run.error ?? 'Lost connection to the run event stream' },
      }))
    }
    ws.onclose = () => {
      set((state) => {
        if (state.run.status === 'running' && state.run.runId === run_id) {
          // Socket closed without a run_finished: fall back to polling the snapshot.
          api
            .get<{ run: { status: string } }>(`/api/runs/${run_id}`)
            .then(({ run }) =>
              set((s) =>
                s.run.runId === run_id
                  ? { run: { ...s.run, status: run.status as RunState['status'] } }
                  : s,
              ),
            )
            .catch(() => undefined)
        }
        return { ws: null }
      })
    }
  },

  cancelRun: async () => {
    const { run } = get()
    if (run.runId && run.status === 'running') {
      await api.post(`/api/runs/${run.runId}/cancel`)
    }
  },

  resetRun: () => {
    get().ws?.close()
    set({ run: idleRun, ws: null })
  },
}))
