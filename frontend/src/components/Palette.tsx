import { DragEvent } from 'react'
import { useStore } from '../store'
import type { NodeSpec } from '../types'
import NodeIcon from './NodeIcon'

function PaletteItem({ spec }: { spec: NodeSpec }) {
  function onDragStart(e: DragEvent) {
    e.dataTransfer.setData('application/swarm-node', spec.type)
    e.dataTransfer.effectAllowed = 'move'
  }
  return (
    <div className="palette-item" draggable onDragStart={onDragStart} title={spec.description}>
      <div className="node-icon" style={{ background: spec.color }}>
        <NodeIcon name={spec.icon} size={14} />
      </div>
      <div>
        <div className="palette-item-name">{spec.name}</div>
        <div className="palette-item-desc">{spec.description}</div>
      </div>
    </div>
  )
}

export default function Palette() {
  const specs = useStore((s) => s.specs)
  const categories: Record<string, NodeSpec[]> = {}
  for (const spec of specs) {
    ;(categories[spec.category] ??= []).push(spec)
  }

  return (
    <aside className="palette">
      <div className="palette-hint">Drag nodes onto the canvas</div>
      {Object.entries(categories).map(([category, items]) => (
        <div key={category} className="palette-group">
          <div className="palette-category">{category}</div>
          {items.map((spec) => (
            <PaletteItem key={spec.type} spec={spec} />
          ))}
        </div>
      ))}
    </aside>
  )
}
