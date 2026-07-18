import { RefreshCw } from 'lucide-react'
import { DragEvent, useState } from 'react'
import { useStore } from '../store'
import type { NodeSpec } from '../types'
import NodeIcon from './NodeIcon'

function PaletteItem({ spec, disabled }: { spec: NodeSpec; disabled: boolean }) {
  function onDragStart(e: DragEvent) {
    if (disabled) {
      e.preventDefault()
      return
    }
    e.dataTransfer.setData('application/swarm-node', spec.type)
    e.dataTransfer.effectAllowed = 'move'
  }
  return (
    <div
      className={`palette-item ${disabled ? 'disabled' : ''}`}
      draggable={!disabled}
      onDragStart={onDragStart}
      title={disabled ? 'Only one trigger per workflow' : spec.description}
    >
      <div
        className="node-icon"
        style={{
          background: `color-mix(in srgb, ${spec.color} 16%, transparent)`,
          color: spec.color,
        }}
      >
        <NodeIcon name={spec.icon} size={14} />
      </div>
      <div className="palette-item-text">
        <div className="palette-item-name">
          {spec.name}
          {spec.source === 'custom' && <span className="badge-custom">custom</span>}
        </div>
        <div className="palette-item-desc">
          {disabled ? 'Only one trigger per workflow' : spec.description}
        </div>
      </div>
    </div>
  )
}

export default function Palette({ hasTrigger }: { hasTrigger: boolean }) {
  const specs = useStore((s) => s.specs)
  const loadErrors = useStore((s) => s.nodeLoadErrors)
  const reloadSpecs = useStore((s) => s.reloadSpecs)
  const [reloading, setReloading] = useState(false)

  async function handleReload() {
    setReloading(true)
    try {
      await reloadSpecs()
    } finally {
      setReloading(false)
    }
  }

  const categories: Record<string, NodeSpec[]> = {}
  for (const spec of specs) {
    ;(categories[spec.category] ??= []).push(spec)
  }

  return (
    <aside className="palette">
      <div className="palette-header">
        <span className="palette-hint">Drag nodes onto the canvas</span>
        <button
          className="btn btn-icon"
          title="Re-scan the nodes/ folder for drop-in node files"
          onClick={() => void handleReload()}
          disabled={reloading}
        >
          <RefreshCw size={14} className={reloading ? 'spin' : ''} />
        </button>
      </div>

      {loadErrors.length > 0 && (
        <div className="palette-errors">
          {loadErrors.map((e) => (
            <div key={e.file} className="palette-error">
              <strong>{e.file}</strong> {e.error}
            </div>
          ))}
        </div>
      )}

      {Object.entries(categories).map(([category, items]) => (
        <div key={category} className="palette-group">
          <div className="palette-category">{category}</div>
          {items.map((spec) => (
            <PaletteItem
              key={spec.type}
              spec={spec}
              disabled={spec.inputs.length === 0 && hasTrigger}
            />
          ))}
        </div>
      ))}
    </aside>
  )
}
