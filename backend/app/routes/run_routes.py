import json

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.auth import get_current_user, get_user_from_token
from app.config import SESSION_COOKIE
from app.db import SessionLocal, get_db
from app.engine.registry import get_registry
from app.engine.runs import manager
from app.models import Execution, User
from app.schemas import RunRequest

router = APIRouter(tags=["runs"])


@router.post("/api/run")
async def start_run(body: RunRequest, user: User = Depends(get_current_user)):
    run = manager.start(
        definition=body.definition,
        registry=get_registry(),
        user_id=user.id,
        workflow_id=body.workflow_id,
        workflow_name=body.workflow_name,
        run_input=body.input,
    )
    return {"run_id": run.id}


@router.get("/api/runs/{run_id}")
def get_run(run_id: str, user: User = Depends(get_current_user)):
    run = manager.get(run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"run": run.snapshot()}


@router.post("/api/runs/{run_id}/cancel")
async def cancel_run(run_id: str, user: User = Depends(get_current_user)):
    run = manager.get(run_id)
    if run is None or run.user_id != user.id:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"cancelled": manager.cancel(run_id)}


@router.get("/api/executions")
def list_executions(
    limit: int = 25, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    rows = (
        db.query(Execution)
        .filter(Execution.user_id == user.id)
        .order_by(Execution.started_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return {
        "executions": [
            {
                "id": r.id,
                "workflow_id": r.workflow_id,
                "workflow_name": r.workflow_name,
                "status": r.status,
                "started_at": r.started_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in rows
        ]
    }


@router.get("/api/executions/{execution_id}")
def get_execution(
    execution_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    row = (
        db.query(Execution)
        .filter(Execution.id == execution_id, Execution.user_id == user.id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Execution not found")
    try:
        summary = json.loads(row.summary or "{}")
    except json.JSONDecodeError:
        summary = {}
    return {
        "execution": {
            "id": row.id,
            "workflow_id": row.workflow_id,
            "workflow_name": row.workflow_name,
            "status": row.status,
            "started_at": row.started_at.isoformat(),
            "finished_at": row.finished_at.isoformat() if row.finished_at else None,
            "summary": summary,
        }
    }


@router.websocket("/api/runs/{run_id}/ws")
async def run_events(websocket: WebSocket, run_id: str):
    db = SessionLocal()
    try:
        user = get_user_from_token(websocket.cookies.get(SESSION_COOKIE), db)
    finally:
        db.close()
    if user is None:
        await websocket.close(code=4401)
        return

    run = manager.get(run_id)
    if run is None or run.user_id != user.id:
        await websocket.close(code=4404)
        return

    await websocket.accept()
    queue = run.subscribe()
    try:
        replay = list(run.events)
        last_seq = replay[-1]["seq"] if replay else -1
        for event in replay:
            await websocket.send_json(event)
        if any(e.get("type") == "run_finished" for e in replay):
            return
        while True:
            event = await queue.get()
            if event.get("seq", 0) <= last_seq:
                continue
            await websocket.send_json(event)
            if event.get("type") == "run_finished":
                return
    except WebSocketDisconnect:
        pass
    finally:
        run.unsubscribe(queue)
        try:
            await websocket.close()
        except RuntimeError:
            pass
