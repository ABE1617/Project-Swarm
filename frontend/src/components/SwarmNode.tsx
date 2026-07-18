import { Handle, Position, type NodeProps } from '@xyflow/react'
import { AlertCircle, Check, Minus } from 'lucide-react'
import { missingRequired } from '../lib/fields'
import { useStore } from '../store'
import type { SwarmNodeData } from '../types'
import NodeIcon from './NodeIcon'

function StatusBadge({ nodeId }: { nodeId: string }) {
  const state = useStore((s) => s.run.nodeStates[nodeId])
  if (!state) return null
  switch (state.status) {
    case 'running':
      return <span className="node-status running"><span className="spinner spinner-sm" /></span>
    case 'success':
      return <span className="node-status success"><Check size={11} strokeWidth={3} /></span>
    case 'error':
      return <span className="node-status error"><AlertCircle size={11} strokeWidth={3} /></span>
    case 'skipped':
      return <span className="node-status skipped"><Minus size={11} strokeWidth={3} /></span>
    default:
      return null
  }
}

export default function SwarmNode({ id, data, selected }: NodeProps) {
  const nodeData = data as SwarmNodeData
  const spec = useStore((s) => s.specsByType[nodeData.kind])
  const status = useStore((s) => s.run.nodeStates[id]?.status)

  if (!spec) {
    return <div className="swarm-node unknown">Unknown node: {nodeData.kind}</div>
  }

  const outputs = spec.outputs
  const inputs = spec.inputs
  const missing = missingRequired(spec, nodeData.config ?? {})

  return (
    <div
      className={[
        'swarm-node',
        selected ? 'selected' : '',
        status ? `run-${status}` : '',
        inputs.length === 0 ? 'is-trigger' : '',
      ].join(' ')}
    >
      {inputs.map((handle, i) => (
        <Handle
          key={handle}
          id={handle}
          type="target"
          position={Position.Left}
          style={{ top: `${((i + 1) * 100) / (inputs.length + 1)}%` }}
        />
      ))}

      <div
        className="node-icon"
        style={{
          background: `color-mix(in srgb, ${spec.color} 16%, transparent)`,
          color: spec.color,
        }}
      >
        <NodeIcon name={spec.icon} size={15} />
      </div>
      <div className="node-body">
        <div className="node-title">{nodeData.label || spec.name}</div>
        <div className="node-subtitle">{nodeData.label ? spec.name : id}</div>
      </div>
      <StatusBadge nodeId={id} />
      {missing.length > 0 && !status && (
        <span className="node-warning" title={`Missing: ${missing.join(', ')}`}>
          !
        </span>
      )}

      {outputs.map((handle, i) => (
        <Handle
          key={handle}
          id={handle}
          type="source"
          position={Position.Right}
          className={`handle-${handle}`}
          style={{ top: `${((i + 1) * 100) / (outputs.length + 1)}%` }}
        >
          {outputs.length > 1 && <span className="handle-label">{handle}</span>}
        </Handle>
      ))}
    </div>
  )
}
