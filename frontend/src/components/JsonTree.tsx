import { useState } from 'react'
import { buildTemplate } from '../lib/mapping'

interface TreeProps {
  data: unknown
  root: string
  onPick: (template: string) => void
}

function preview(value: unknown): string {
  if (value === null) return 'null'
  if (typeof value === 'string') return value.length > 40 ? `"${value.slice(0, 40)}…"` : `"${value}"`
  if (Array.isArray(value)) return `[${value.length}]`
  if (typeof value === 'object') return `{${Object.keys(value as object).length}}`
  return String(value)
}

function Entry({
  name,
  value,
  root,
  path,
  onPick,
  depth,
}: {
  name: string | number
  value: unknown
  root: string
  path: Array<string | number>
  onPick: (template: string) => void
  depth: number
}) {
  const [open, setOpen] = useState(depth < 2)
  const isBranch = value !== null && typeof value === 'object'

  const label = (
    <button
      className="jt-key"
      title={`Insert ${buildTemplate(root, path)}`}
      onClick={() => onPick(buildTemplate(root, path))}
    >
      {String(name)}
    </button>
  )

  if (!isBranch) {
    return (
      <div className="jt-row" style={{ paddingLeft: depth * 14 }}>
        {label}
        <span className="jt-value">{preview(value)}</span>
      </div>
    )
  }

  const entries: Array<[string | number, unknown]> = Array.isArray(value)
    ? value.map((v, i) => [i, v] as [number, unknown])
    : Object.entries(value as Record<string, unknown>)

  return (
    <div>
      <div className="jt-row" style={{ paddingLeft: depth * 14 }}>
        <button className="jt-toggle" onClick={() => setOpen(!open)}>
          {open ? '▾' : '▸'}
        </button>
        {label}
        <span className="jt-value jt-muted">{preview(value)}</span>
      </div>
      {open &&
        entries.map(([key, child]) => (
          <Entry
            key={String(key)}
            name={key}
            value={child}
            root={root}
            path={[...path, key]}
            onPick={onPick}
            depth={depth + 1}
          />
        ))}
    </div>
  )
}

export default function JsonTree({ data, root, onPick }: TreeProps) {
  if (data === null || typeof data !== 'object') {
    return (
      <div className="jt-row">
        <button
          className="jt-key"
          title={`Insert ${buildTemplate(root, [])}`}
          onClick={() => onPick(buildTemplate(root, []))}
        >
          value
        </button>
        <span className="jt-value">{preview(data)}</span>
      </div>
    )
  }
  const entries: Array<[string | number, unknown]> = Array.isArray(data)
    ? data.map((v, i) => [i, v] as [number, unknown])
    : Object.entries(data as Record<string, unknown>)
  return (
    <div className="json-tree">
      {entries.map(([key, child]) => (
        <Entry
          key={String(key)}
          name={key}
          value={child}
          root={root}
          path={[key]}
          onPick={onPick}
          depth={0}
        />
      ))}
    </div>
  )
}
