import {
  addEdge,
  Background,
  BackgroundVariant,
  Controls,
  MiniMap,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
  useReactFlow,
  type Connection,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import { DragEvent, useCallback, useEffect, useMemo, useRef } from 'react'
import { api } from '../api'
import ConfigPanel from '../components/ConfigPanel'
import Palette from '../components/Palette'
import SwarmNode from '../components/SwarmNode'
import Toolbar from '../components/Toolbar'
import {
  defaultEdgeOptions,
  deserializeFlow,
  edgeLabel,
  serializeFlow,
  wouldCreateCycle,
  type FlowNode,
} from '../lib/flow'
import { useStore } from '../store'
import type { WorkflowDefinition } from '../types'

const nodeTypes = { swarm: SwarmNode }

const initialNodes: FlowNode[] = [
  {
    id: 'manual_trigger_1',
    type: 'swarm',
    position: { x: 140, y: 220 },
    data: { kind: 'manual_trigger', config: {} },
  },
]

function EditorInner() {
  const loadSpecs = useStore((s) => s.loadSpecs)
  const specsByType = useStore((s) => s.specsByType)
  const workflowId = useStore((s) => s.workflowId)
  const workflowName = useStore((s) => s.workflowName)
  const setWorkflow = useStore((s) => s.setWorkflow)
  const startRun = useStore((s) => s.startRun)
  const resetRun = useStore((s) => s.resetRun)
  const runStatus = useStore((s) => s.run.status)
  const notice = useStore((s) => s.notice)
  const setNotice = useStore((s) => s.setNotice)

  const [nodes, setNodes, onNodesChange] = useNodesState<FlowNode>(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const { screenToFlowPosition, fitView } = useReactFlow()
  const idCounter = useRef(2)

  useEffect(() => {
    void loadSpecs()
  }, [loadSpecs])

  const selectedNode = useMemo(() => nodes.find((n) => n.selected) ?? null, [nodes])
  const hasTrigger = useMemo(
    () => nodes.some((n) => specsByType[n.data.kind]?.inputs.length === 0),
    [nodes, specsByType],
  )

  const isValidConnection = useCallback(
    (connection: Edge | Connection) => {
      if (!connection.source || !connection.target) return false
      return !wouldCreateCycle(edges, connection.source, connection.target)
    },
    [edges],
  )

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge({ ...connection, label: edgeLabel(connection.sourceHandle) }, eds),
      )
    },
    [setEdges],
  )

  const onDragOver = useCallback((e: DragEvent) => {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
  }, [])

  const onDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault()
      const kind = e.dataTransfer.getData('application/swarm-node')
      if (!kind) return
      const spec = specsByType[kind]
      if (!spec) return
      if (spec.inputs.length === 0 && hasTrigger) {
        setNotice('Only one trigger per workflow')
        return
      }

      const position = screenToFlowPosition({ x: e.clientX, y: e.clientY })
      let id = `${kind}_${idCounter.current++}`
      while (nodes.some((n) => n.id === id)) id = `${kind}_${idCounter.current++}`

      const config: Record<string, unknown> = {}
      for (const field of spec.config_fields) {
        if (field.default !== undefined) config[field.key] = field.default
      }
      setNodes((nds) => [
        ...nds,
        { id, type: 'swarm', position, data: { kind, config } },
      ])
    },
    [specsByType, screenToFlowPosition, nodes, setNodes, hasTrigger, setNotice],
  )

  const updateNodeConfig = useCallback(
    (nodeId: string, patch: Record<string, unknown>) => {
      setNodes((nds) =>
        nds.map((n) =>
          n.id === nodeId
            ? { ...n, data: { ...n.data, config: { ...n.data.config, ...patch } } }
            : n,
        ),
      )
    },
    [setNodes],
  )

  const updateNodeLabel = useCallback(
    (nodeId: string, label: string) => {
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, label } } : n)),
      )
    },
    [setNodes],
  )

  const deleteNode = useCallback(
    (nodeId: string) => {
      setNodes((nds) => nds.filter((n) => n.id !== nodeId))
      setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId))
    },
    [setNodes, setEdges],
  )

  const serialize = useCallback((): WorkflowDefinition => serializeFlow(nodes, edges), [nodes, edges])

  const loadDefinition = useCallback(
    (definition: WorkflowDefinition) => {
      resetRun()
      const { nodes: flowNodes, edges: flowEdges } = deserializeFlow(definition)
      setNodes(flowNodes)
      setEdges(flowEdges)
      window.setTimeout(() => void fitView({ padding: 0.3, maxZoom: 0.9 }), 50)
    },
    [resetRun, setNodes, setEdges, fitView],
  )

  const handleSave = useCallback(async () => {
    const body = { name: workflowName || 'Untitled workflow', definition: serialize() }
    if (workflowId != null) {
      await api.put(`/api/workflows/${workflowId}`, body)
    } else {
      const { workflow } = await api.post<{ workflow: { id: number } }>('/api/workflows', body)
      setWorkflow(workflow.id, body.name)
    }
  }, [workflowId, workflowName, serialize, setWorkflow])

  const handleLoad = useCallback(
    async (id: number) => {
      const { workflow } = await api.get<{
        workflow: { id: number; name: string; definition: WorkflowDefinition }
      }>(`/api/workflows/${id}`)
      setWorkflow(workflow.id, workflow.name)
      loadDefinition(workflow.definition)
    },
    [setWorkflow, loadDefinition],
  )

  const handleNew = useCallback(() => {
    resetRun()
    setWorkflow(null, 'Untitled workflow')
    setNodes(initialNodes)
    setEdges([])
  }, [resetRun, setWorkflow, setNodes, setEdges])

  const handleRun = useCallback(async () => {
    await startRun(serialize(), workflowId, workflowName)
  }, [startRun, serialize, workflowId, workflowName])

  const handleTestNode = useCallback(
    (nodeId: string) => {
      void startRun(serialize(), workflowId, workflowName, nodeId)
    },
    [startRun, serialize, workflowId, workflowName],
  )

  const handleExport = useCallback(() => {
    const payload = { name: workflowName, definition: serialize() }
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${workflowName.replace(/[^\w-]+/g, '_') || 'workflow'}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [workflowName, serialize])

  const handleImport = useCallback(
    (file: File) => {
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const parsed = JSON.parse(String(reader.result))
          const definition: WorkflowDefinition = parsed.definition ?? parsed
          if (!Array.isArray(definition.nodes)) throw new Error('no nodes array')
          setWorkflow(null, parsed.name ?? 'Imported workflow')
          loadDefinition(definition)
        } catch (e) {
          window.alert(`Could not import: ${e instanceof Error ? e.message : 'invalid file'}`)
        }
      }
      reader.readAsText(file)
    },
    [setWorkflow, loadDefinition],
  )

  return (
    <div className="editor-layout">
      <Toolbar
        onSave={handleSave}
        onRun={handleRun}
        onNew={handleNew}
        onLoad={handleLoad}
        onExport={handleExport}
        onImport={handleImport}
      />
      <div className="editor-main">
        <Palette hasTrigger={hasTrigger} />
        <div className="canvas-wrap" data-running={runStatus === 'running'}>
          {notice && <div className="canvas-notice">{notice}</div>}
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={nodeTypes}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            isValidConnection={isValidConnection}
            onDrop={onDrop}
            onDragOver={onDragOver}
            defaultEdgeOptions={defaultEdgeOptions}
            deleteKeyCode={['Backspace', 'Delete']}
            fitView
            fitViewOptions={{ padding: 0.3, maxZoom: 0.9 }}
            proOptions={{ hideAttribution: true }}
          >
            <Background variant={BackgroundVariant.Dots} gap={26} size={1.1} color="#2b251c" />
            <Controls position="bottom-left" />
            <MiniMap
              pannable
              zoomable
              maskColor="rgba(20, 17, 13, 0.78)"
              nodeColor="#3a332a"
              nodeStrokeColor="#55492f"
            />
          </ReactFlow>
        </div>
        <ConfigPanel
          node={selectedNode}
          edges={edges}
          allNodes={nodes}
          onConfigChange={updateNodeConfig}
          onLabelChange={updateNodeLabel}
          onDelete={deleteNode}
          onTestNode={handleTestNode}
        />
      </div>
    </div>
  )
}

export default function Editor() {
  return (
    <ReactFlowProvider>
      <EditorInner />
    </ReactFlowProvider>
  )
}
