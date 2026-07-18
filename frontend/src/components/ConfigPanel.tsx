import type { Edge, Node } from '@xyflow/react'
import { FlaskConical, Play, Trash2 } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { fieldDefaults, fieldVisible } from '../lib/fields'
import { ancestorsOf, directSources, insertAtCursor } from '../lib/mapping'
import { useStore } from '../store'
import type { ConfigField, SwarmNodeData } from '../types'
import JsonTree from './JsonTree'

interface Props {
  node: Node<SwarmNodeData> | null
  edges: Edge[]
  allNodes: Node<SwarmNodeData>[]
  onConfigChange: (nodeId: string, patch: Record<string, unknown>) => void
  onLabelChange: (nodeId: string, label: string) => void
  onDelete: (nodeId: string) => void
  onTestNode: (nodeId: string) => void
  onRunPrevious: (nodeId: string) => void
}

interface FocusedField {
  key: string
  element: HTMLInputElement | HTMLTextAreaElement
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

function CredentialSelect({
  value,
  onChange,
}: {
  value: unknown
  onChange: (value: unknown) => void
}) {
  const credentials = useStore((s) => s.credentials)
  const loadCredentials = useStore((s) => s.loadCredentials)

  useEffect(() => {
    if (credentials.length === 0) void loadCredentials()
  }, [credentials.length, loadCredentials])

  if (credentials.length === 0) {
    return (
      <div className="field-help">
        No Google credential yet - create one via the Credentials button in the toolbar.
      </div>
    )
  }
  return (
    <select value={String(value ?? '')} onChange={(e) => onChange(Number(e.target.value) || '')}>
      <option value="">Select a credential…</option>
      {credentials.map((cred) => (
        <option key={cred.id} value={cred.id}>
          {cred.name}
          {cred.account_email ? ` (${cred.account_email})` : ''}
          {cred.connected ? '' : ' - not connected'}
        </option>
      ))}
    </select>
  )
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
    case 'credential':
      return <CredentialSelect value={value} onChange={onChange} />
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
          step={field.step ?? 'any'}
          min={field.min}
          max={field.max}
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

function InputDataPanel({
  node,
  edges,
  allNodes,
  onPick,
  onRunPrevious,
}: {
  node: Node<SwarmNodeData>
  edges: Edge[]
  allNodes: Node<SwarmNodeData>[]
  onPick: (template: string) => void
  onRunPrevious: (nodeId: string) => void
}) {
  const nodeStates = useStore((s) => s.run.nodeStates)
  const specsByType = useStore((s) => s.specsByType)
  const runStatus = useStore((s) => s.run.status)

  const directs = directSources(edges, node.id)
  const ancestors = ancestorsOf(edges, node.id)
  const withData = ancestors.filter((id) => nodeStates[id]?.output !== undefined)

  if (ancestors.length === 0) return null

  const nameOf = (id: string) => {
    const n = allNodes.find((candidate) => candidate.id === id)
    if (!n) return id
    return n.data.label || specsByType[n.data.kind]?.name || id
  }

  return (
    <div className="input-data">
      <div className="input-data-header">
        <span>Input data</span>
        {withData.length > 0 && (
          <button
            className="btn btn-small"
            title="Run everything before this node again to refresh its input data"
            disabled={runStatus === 'running'}
            onClick={() => onRunPrevious(node.id)}
          >
            <Play size={11} /> Execute previous nodes
          </button>
        )}
      </div>
      {withData.length === 0 ? (
        <div className="input-data-cta">
          <p className="input-data-empty">
            No input data yet. Execute the previous nodes to see what data arrives here - then
            click any field to map it into a parameter.
          </p>
          <button
            className="btn btn-primary btn-small"
            disabled={runStatus === 'running'}
            onClick={() => onRunPrevious(node.id)}
          >
            <Play size={12} /> Execute previous nodes
          </button>
        </div>
      ) : (
        <>
          <p className="input-data-hint">
            Click a field to insert its {'{{ }}'} reference into the focused parameter.
          </p>
          {withData.map((id) => (
            <div key={id} className="input-source">
              <div className="input-source-name">
                {nameOf(id)} <code>{id}</code>
              </div>
              <JsonTree
                data={nodeStates[id].output}
                root={directs.length === 1 && id === directs[0] ? 'input' : id}
                onPick={onPick}
              />
            </div>
          ))}
        </>
      )}
    </div>
  )
}

export default function ConfigPanel({
  node,
  edges,
  allNodes,
  onConfigChange,
  onLabelChange,
  onDelete,
  onTestNode,
  onRunPrevious,
}: Props) {
  const runStatus = useStore((s) => s.run.status)
  const spec = useStore((s) => (node ? s.specsByType[node.data.kind] : undefined))
  const runState = useStore((s) => (node ? s.run.nodeStates[node.id] : undefined))
  const setNotice = useStore((s) => s.setNotice)
  const focusedField = useRef<FocusedField | null>(null)
  const [, forceRender] = useState(0)

  useEffect(() => {
    focusedField.current = null
  }, [node?.id])

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

  function rememberFocus(event: React.FocusEvent) {
    const target = event.target as HTMLElement
    if (target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement) {
      if (target.type === 'checkbox' || target.type === 'password') return
      const holder = target.closest('[data-field-key]')
      const key = holder?.getAttribute('data-field-key')
      if (key) focusedField.current = { key, element: target }
    }
  }

  function handlePick(template: string) {
    const focused = focusedField.current
    if (focused && node) {
      const current = String(config[focused.key] ?? '')
      const next = insertAtCursor(focused.element, current, template)
      onConfigChange(node.id, { [focused.key]: next })
      forceRender((n) => n + 1)
    } else {
      void navigator.clipboard.writeText(template)
      setNotice('Reference copied - click into a field first to insert it directly')
    }
  }

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

      <InputDataPanel
        node={node}
        edges={edges}
        allNodes={allNodes}
        onPick={handlePick}
        onRunPrevious={onRunPrevious}
      />

      <div onFocusCapture={rememberFocus}>
        <label className="config-field">
          <span>Label</span>
          <input
            value={node.data.label ?? ''}
            placeholder={spec.name}
            onChange={(e) => onLabelChange(node.id, e.target.value)}
          />
        </label>

        {spec.config_fields
          .filter((f) => fieldVisible(f, config, fieldDefaults(spec)))
          .map((field) => (
            <label key={field.key} className="config-field" data-field-key={field.key}>
              <span>
                {field.label}
                {field.required && <em className="required">*</em>}
              </span>
              <FieldInput
                field={field}
                value={config[field.key]}
                onChange={(value) => onConfigChange(node.id, { [field.key]: value })}
              />
              {field.help && field.type !== 'boolean' && (
                <div className="field-help">{field.help}</div>
              )}
            </label>
          ))}
      </div>

      <div className={`config-run-result ${runState?.status ?? ''}`}>
        <div className="output-header">
          <span className="config-run-header">
            {runState && runState.status !== 'pending' ? (
              <>
                Output: {runState.status}
                {runState.elapsed_ms !== undefined && <span> · {runState.elapsed_ms}ms</span>}
              </>
            ) : (
              'Output'
            )}
          </span>
          <button
            className="btn btn-small"
            title="Run this node (and everything before it) to see its output"
            disabled={runStatus === 'running'}
            onClick={() => onTestNode(node.id)}
          >
            <FlaskConical size={12} /> Execute step
          </button>
        </div>
        {runState && runState.status !== 'pending' ? (
          <>
            {runState.error && <pre className="run-error-text">{runState.error}</pre>}
            {runState.reason && <div className="field-help">{runState.reason}</div>}
            {runState.output !== undefined && (
              <pre className="run-output">{JSON.stringify(runState.output, null, 2)}</pre>
            )}
          </>
        ) : (
          <p className="input-data-empty">
            Not executed yet. Execute step runs this node with fresh data from the previous nodes.
          </p>
        )}
      </div>
    </aside>
  )
}
