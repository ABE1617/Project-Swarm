import type { Node } from '@xyflow/react'
import { Trash2 } from 'lucide-react'
import { useStore } from '../store'
import type { ConfigField } from '../types'
import type { SwarmNodeData } from './SwarmNode'

interface Props {
  node: Node<SwarmNodeData> | null
  onConfigChange: (nodeId: string, patch: Record<string, unknown>) => void
  onLabelChange: (nodeId: string, label: string) => void
  onDelete: (nodeId: string) => void
}

function fieldVisible(field: ConfigField, config: Record<string, unknown>): boolean {
  if (!field.showIf) return true
  return Object.entries(field.showIf).every(([key, expected]) => {
    const actual = config[key] ?? defaultFor(key, field)
    if (Array.isArray(expected)) return expected.includes(String(actual))
    return String(actual) === String(expected)
  })
}

function defaultFor(_key: string, _field: ConfigField): unknown {
  return undefined
}

function jsonHint(value: unknown): string | null {
  if (typeof value !== 'string' || !value.trim()) return null
  if (value.includes('{{')) return null // templates resolve at run time
  try {
    JSON.parse(value)
    return null
  } catch {
    return 'Not valid JSON (ok if it becomes valid after {{ }} templates resolve)'
  }
}

function FieldInput({
  field,
  value,
  onChange,
}: {
  field: ConfigField
  value: unknown
  onChange: (value: unknown) => void
}) {
  const current = value ?? field.default ?? ''
  switch (field.type) {
    case 'select':
      return (
        <select value={String(current)} onChange={(e) => onChange(e.target.value)}>
          {(field.options ?? []).map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      )
    case 'boolean':
      return (
        <label className="toggle-row">
          <input
            type="checkbox"
            checked={Boolean(value ?? field.default ?? false)}
            onChange={(e) => onChange(e.target.checked)}
          />
          <span>{field.help ?? 'Enabled'}</span>
        </label>
      )
    case 'number':
      return (
        <input
          type="number"
          step="any"
          value={String(current)}
          placeholder={field.placeholder}
          onChange={(e) => onChange(e.target.value === '' ? '' : Number(e.target.value))}
        />
      )
    case 'text':
    case 'json': {
      const hint = field.type === 'json' ? jsonHint(current) : null
      return (
        <>
          <textarea
            className={field.type === 'json' ? 'mono' : ''}
            rows={field.type === 'json' ? 4 : 3}
            value={String(current)}
            placeholder={field.placeholder}
            onChange={(e) => onChange(e.target.value)}
          />
          {hint && <div className="field-warning">{hint}</div>}
        </>
      )
    }
    case 'secret':
      return (
        <input
          type="password"
          value={String(current)}
          placeholder={field.placeholder ?? '••••••'}
          onChange={(e) => onChange(e.target.value)}
          autoComplete="off"
        />
      )
    default:
      return (
        <input
          value={String(current)}
          placeholder={field.placeholder}
          onChange={(e) => onChange(e.target.value)}
        />
      )
  }
}

export default function ConfigPanel({ node, onConfigChange, onLabelChange, onDelete }: Props) {
  const spec = useStore((s) => (node ? s.specsByType[node.data.kind] : undefined))
  const runState = useStore((s) => (node ? s.run.nodeStates[node.id] : undefined))

  if (!node || !spec) {
    return (
      <aside className="config-panel empty">
        <div className="config-empty">
          <p>Select a node to configure it.</p>
          <p className="hint">
            Reference upstream data with templates: <code>{'{{ input.field }}'}</code> or{' '}
            <code>{'{{ node_id.field }}'}</code>
          </p>
        </div>
      </aside>
    )
  }

  const config = node.data.config ?? {}

  return (
    <aside className="config-panel">
      <div className="config-header">
        <div className="config-title">
          <span className="node-icon" style={{ background: spec.color }} />
          {spec.name}
        </div>
        <button className="btn btn-icon danger" title="Delete node" onClick={() => onDelete(node.id)}>
          <Trash2 size={15} />
        </button>
      </div>
      <div className="config-id">
        id: <code>{node.id}</code>
      </div>
      <p className="config-desc">{spec.description}</p>

      <label className="config-field">
        <span>Label</span>
        <input
          value={node.data.label ?? ''}
          placeholder={spec.name}
          onChange={(e) => onLabelChange(node.id, e.target.value)}
        />
      </label>

      {spec.config_fields.filter((f) => fieldVisible(f, config)).map((field) => (
        <label key={field.key} className="config-field">
          <span>
            {field.label}
            {field.required && <em className="required">*</em>}
          </span>
          <FieldInput
            field={field}
            value={config[field.key]}
            onChange={(value) => onConfigChange(node.id, { [field.key]: value })}
          />
          {field.help && field.type !== 'boolean' && <div className="field-help">{field.help}</div>}
        </label>
      ))}

      {runState && runState.status !== 'pending' && (
        <div className={`config-run-result ${runState.status}`}>
          <div className="config-run-header">
            Last run: {runState.status}
            {runState.elapsed_ms !== undefined && <span> · {runState.elapsed_ms}ms</span>}
          </div>
          {runState.error && <pre className="run-error-text">{runState.error}</pre>}
          {runState.reason && <div className="field-help">{runState.reason}</div>}
          {runState.output !== undefined && (
            <pre className="run-output">{JSON.stringify(runState.output, null, 2)}</pre>
          )}
        </div>
      )}
    </aside>
  )
}
