"""In-memory run manager: starts workflow executions as background asyncio tasks,
buffers events for WebSocket replay/streaming, and persists results to the DB."""

import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from app.db import SessionLocal
from app.engine.executor import execute_workflow
from app.engine.registry import NodeRegistry
from app.engine.types import WorkflowError
from app.models import Execution

MAX_KEPT_RUNS = 50
SUMMARY_CHAR_LIMIT = 500_000


class Run:
    def __init__(self, run_id: str, user_id: int, workflow_id: int | None, workflow_name: str):
        self.id = run_id
        self.user_id = user_id
        self.workflow_id = workflow_id
        self.workflow_name = workflow_name
        self.status = "running"
        self.events: list[dict] = []
        self.subscribers: set[asyncio.Queue] = set()
        self.result: dict | None = None
        self.task: asyncio.Task | None = None
        self.started_at = datetime.now(timezone.utc)
        self.finished_at: datetime | None = None

    def emit(self, event: dict) -> None:
        event.setdefault("ts", datetime.now(timezone.utc).isoformat())
        event["seq"] = len(self.events)
        self.events.append(event)
        for q in list(self.subscribers):
            q.put_nowait(event)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self.subscribers.discard(q)

    def snapshot(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "result": self.result,
        }


class RunManager:
    def __init__(self):
        self.runs: dict[str, Run] = {}

    def start(
        self,
        definition: dict,
        registry: NodeRegistry,
        user_id: int,
        workflow_id: int | None = None,
        workflow_name: str = "",
        run_input: Any = None,
    ) -> Run:
        run = Run(str(uuid.uuid4()), user_id, workflow_id, workflow_name)
        self.runs[run.id] = run
        self._prune()

        db = SessionLocal()
        try:
            db.add(
                Execution(
                    id=run.id,
                    workflow_id=workflow_id,
                    workflow_name=workflow_name or "",
                    user_id=user_id,
                    status="running",
                    started_at=run.started_at,
                )
            )
            db.commit()
        finally:
            db.close()

        run.task = asyncio.create_task(self._execute(run, definition, registry, run_input))
        return run

    async def _execute(self, run: Run, definition: dict, registry: NodeRegistry, run_input: Any):
        try:
            result = await execute_workflow(
                definition, registry, run_input=run_input, emit=run.emit
            )
            run.status = result["status"]
            run.result = result
        except WorkflowError as e:
            run.status = "error"
            run.result = {"status": "error", "error": str(e)}
            run.emit({"type": "run_error", "message": str(e)})
        except asyncio.CancelledError:
            run.status = "cancelled"
            run.result = {"status": "cancelled"}
        except Exception as e:
            run.status = "error"
            run.result = {"status": "error", "error": f"{type(e).__name__}: {e}"}
            run.emit({"type": "run_error", "message": run.result["error"]})
        finally:
            run.finished_at = datetime.now(timezone.utc)
            run.emit({"type": "run_finished", "status": run.status})
            self._persist(run)

    def _persist(self, run: Run) -> None:
        db = SessionLocal()
        try:
            row = db.get(Execution, run.id)
            if row is not None:
                row.status = run.status
                row.finished_at = run.finished_at
                summary = json.dumps(run.result or {}, ensure_ascii=False, default=str)
                row.summary = summary[:SUMMARY_CHAR_LIMIT]
                db.commit()
        finally:
            db.close()

    def _prune(self) -> None:
        finished = [r for r in self.runs.values() if r.finished_at is not None]
        if len(finished) > MAX_KEPT_RUNS:
            finished.sort(key=lambda r: r.finished_at)
            for r in finished[: len(finished) - MAX_KEPT_RUNS]:
                self.runs.pop(r.id, None)

    def get(self, run_id: str) -> Run | None:
        return self.runs.get(run_id)

    def cancel(self, run_id: str) -> bool:
        run = self.runs.get(run_id)
        if run and run.task and not run.task.done():
            run.task.cancel()
            return True
        return False


manager = RunManager()
