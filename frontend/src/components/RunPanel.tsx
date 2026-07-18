import { ChevronDown, ChevronUp, Square } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { useStore } from '../store'

const STATUS_LABEL: Record<string, string> = {
  idle: 'Ready',
  running: 'Running…',
  success: 'Success',
  error: 'Failed',
  cancelled: 'Cancelled',
}

export default function RunPanel() {
  const run = useStore((s) => s.run)
  const cancelRun = useStore((s) => s.cancelRun)
  const [expanded, setExpanded] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (run.status === 'running' && run.logs.length > 0) setExpanded(true)
  }, [run.status])

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [run.logs.length])

  const counts = Object.values(run.nodeStates).reduce(
    (acc, s) => {
      acc[s.status] = (acc[s.status] ?? 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

  return (
    <div className={`run-panel ${expanded ? 'expanded' : ''}`}>
      <div className="run-panel-bar" onClick={() => setExpanded(!expanded)}>
        <span className={`run-chip ${run.status}`}>{STATUS_LABEL[run.status]}</span>
        {run.status !== 'idle' && (
          <span className="run-counts">
            {counts.success ? `${counts.success} ok` : ''}
            {counts.error ? ` · ${counts.error} failed` : ''}
            {counts.skipped ? ` · ${counts.skipped} skipped` : ''}
          </span>
        )}
        {run.error && <span className="run-error-inline">{run.error}</span>}
        <span className="flex-spacer" />
        {run.status === 'running' && (
          <button
            className="btn btn-small danger"
            onClick={(e) => {
              e.stopPropagation()
              void cancelRun()
            }}
          >
            <Square size={12} /> Stop
          </button>
        )}
        <button className="btn btn-icon">{expanded ? <ChevronDown size={16} /> : <ChevronUp size={16} />}</button>
      </div>
      {expanded && (
        <div className="run-logs">
          {run.logs.length === 0 && <div className="log-line muted">No logs yet.</div>}
          {run.logs.map((log, i) => (
            <div key={i} className={`log-line ${log.level}`}>
              <span className="log-node">{log.node_id ?? '—'}</span>
              <span>{log.message}</span>
            </div>
          ))}
          <div ref={logsEndRef} />
        </div>
      )}
    </div>
  )
}
