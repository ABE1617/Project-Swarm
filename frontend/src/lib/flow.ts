import { MarkerType, type Edge, type Node } from '@xyflow/react'
import type { SwarmNodeData, WorkflowDefinition } from '../types'

export type FlowNode = Node<SwarmNodeData>

export const defaultEdgeOptions = {
  type: 'smoothstep' as const,
  markerEnd: { type: MarkerType.ArrowClosed, width: 18, height: 18 },
}

/** Branch handles ("true"/"false") get a visible label; the default handle does not. */
export function edgeLabel(sourceHandle?: string | null): string | undefined {
  return sourceHandle && sourceHandle !== 'out' ? sourceHandle : undefined
}

export function serializeFlow(nodes: FlowNode[], edges: Edge[]): WorkflowDefinition {
  return {
    nodes: nodes.map((n) => ({
      id: n.id,
      type: n.data.kind,
      label: n.data.label,
      position: n.position,
      config: n.data.config ?? {},
    })),
    edges: edges.map((e) => ({
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: e.sourceHandle ?? undefined,
      targetHandle: e.targetHandle ?? undefined,
    })),
  }
}

export function deserializeFlow(definition: WorkflowDefinition): {
  nodes: FlowNode[]
  edges: Edge[]
} {
  const nodes: FlowNode[] = (definition.nodes ?? []).map((n) => ({
    id: n.id,
    type: 'swarm',
    position: n.position ?? { x: 100, y: 100 },
    data: { kind: n.type, label: n.label, config: n.config ?? {} },
  }))
  const edges: Edge[] = (definition.edges ?? []).map((e, i) => ({
    id: e.id ?? `e_${i}_${e.source}_${e.target}`,
    source: e.source,
    target: e.target,
    sourceHandle: e.sourceHandle,
    targetHandle: e.targetHandle,
    label: edgeLabel(e.sourceHandle),
    ...defaultEdgeOptions,
  }))
  return { nodes, edges }
}
