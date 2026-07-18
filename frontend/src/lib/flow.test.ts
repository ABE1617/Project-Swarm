import { describe, expect, it } from 'vitest'
import type { WorkflowDefinition } from '../types'
import { deserializeFlow, edgeLabel, serializeFlow, wouldCreateCycle } from './flow'

const definition: WorkflowDefinition = {
  nodes: [
    {
      id: 'manual_trigger_1',
      type: 'manual_trigger',
      label: 'Start',
      position: { x: 12, y: 34 },
      config: { payload: '{"a": 1}' },
    },
    {
      id: 'if_condition_1',
      type: 'if_condition',
      position: { x: 200, y: 34 },
      config: { mode: 'simple', value1: '{{ input.a }}', operator: '==', value2: '1' },
    },
  ],
  edges: [
    {
      id: 'e1',
      source: 'manual_trigger_1',
      target: 'if_condition_1',
      sourceHandle: 'out',
      targetHandle: 'in',
    },
    { source: 'if_condition_1', target: 'manual_trigger_1', sourceHandle: 'true' },
  ],
}

describe('edgeLabel', () => {
  it('labels branch handles but not the default handle', () => {
    expect(edgeLabel('true')).toBe('true')
    expect(edgeLabel('false')).toBe('false')
    expect(edgeLabel('out')).toBeUndefined()
    expect(edgeLabel(null)).toBeUndefined()
    expect(edgeLabel(undefined)).toBeUndefined()
  })
})

describe('serialize/deserialize round trip', () => {
  it('preserves ids, kinds, labels, positions, config, and handles', () => {
    const { nodes, edges } = deserializeFlow(definition)
    const roundTripped = serializeFlow(nodes, edges)

    expect(roundTripped.nodes).toHaveLength(2)
    expect(roundTripped.nodes[0]).toMatchObject({
      id: 'manual_trigger_1',
      type: 'manual_trigger',
      label: 'Start',
      position: { x: 12, y: 34 },
      config: { payload: '{"a": 1}' },
    })
    expect(roundTripped.nodes[1].config).toEqual(definition.nodes[1].config)
    expect(roundTripped.edges[0]).toMatchObject({
      source: 'manual_trigger_1',
      target: 'if_condition_1',
      sourceHandle: 'out',
      targetHandle: 'in',
    })
    expect(roundTripped.edges[1].sourceHandle).toBe('true')
  })

  it('drops nothing when serializing', () => {
    const { nodes, edges } = deserializeFlow(definition)
    expect(serializeFlow(nodes, edges).nodes).toHaveLength(definition.nodes.length)
    expect(serializeFlow(nodes, edges).edges).toHaveLength(definition.edges.length)
  })
})

describe('deserializeFlow defaults', () => {
  it('fills in position and edge ids when missing', () => {
    const sparse: WorkflowDefinition = {
      nodes: [{ id: 'a', type: 'manual_trigger', position: undefined as never, config: {} }],
      edges: [{ source: 'a', target: 'a' }],
    }
    const { nodes, edges } = deserializeFlow(sparse)
    expect(nodes[0].position).toEqual({ x: 100, y: 100 })
    expect(edges[0].id).toBeTruthy()
  })

  it('labels branch edges on load', () => {
    const { edges } = deserializeFlow(definition)
    expect(edges[0].label).toBeUndefined()
    expect(edges[1].label).toBe('true')
  })
})

describe('wouldCreateCycle', () => {
  const edges = [
    { source: 'a', target: 'b' },
    { source: 'b', target: 'c' },
  ]

  it('rejects self-connections', () => {
    expect(wouldCreateCycle(edges, 'a', 'a')).toBe(true)
  })

  it('rejects edges that close a loop', () => {
    expect(wouldCreateCycle(edges, 'c', 'a')).toBe(true)
    expect(wouldCreateCycle(edges, 'b', 'a')).toBe(true)
  })

  it('allows forward and parallel edges', () => {
    expect(wouldCreateCycle(edges, 'a', 'c')).toBe(false)
    expect(wouldCreateCycle(edges, 'c', 'd')).toBe(false)
  })
})
