import { Square } from 'lucide-react'
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
  const [open, setOpen] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (open) logsEndRef.current?.scrollIntoView({ block: 'end' })
  }, [run.logs.length, open])

  const counts = Object.values(run.nodeStates).reduce(
    (acc, s) => {
      acc[s.status] = (acc[s.status] ?? 0) + 1
      return acc
    },
    {} as Record<string, number>,
  )

  const summary =
    run.status === 'idle'
      ? ''
      : [
          counts.success ? `${counts.success} ok` : '',
          counts.error ? `${counts.error} failed` : '',
          counts.skipped ? `${counts.skipped} skipped` : '',
        ]
          .filter(Boolean)
          .join(' · ')

  return (
    <div
      className="run-menu"
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <span className={`run-chip ${run.status}`}>{STATUS_LABEL[run.status]}</span>

      {open && (
        <div className="run-dropdown">
          <div className="run-dropdown-header">
            <span className={`run-chip ${run.status}`}>{STATUS_LABEL[run.status]}</span>
            {summary && <span className="run-counts">{summary}</span>}
            {run.error && <span className="run-error-inline">{run.error}</span>}
            <span className="flex-spacer" />
            {run.status === 'running' && (
              <button className="btn btn-small danger" onClick={() => void cancelRun()}>
                <Square size={12} /> Stop
              </button>
            )}
          </div>
          <div className="run-logs">
            {run.logs.length === 0 && <div className="log-line muted">No logs</div>}
            {run.logs.map((log, i) => (
              <div key={i} className={`log-line ${log.level}`}>
                <span className="log-node">{log.node_id ?? '—'}</span>
                <span>{log.message}</span>
              </div>
            ))}
            <div ref={logsEndRef} />
          </div>
        </div>
      )}
    </div>
  )
}
