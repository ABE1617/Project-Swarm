import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.models import User, Workflow
from app.schemas import WorkflowSave

router = APIRouter(prefix="/api/workflows", tags=["workflows"])


def _workflow_meta(w: Workflow) -> dict:
    return {
        "id": w.id,
        "name": w.name,
        "created_at": w.created_at.isoformat(),
        "updated_at": w.updated_at.isoformat(),
    }


@router.get("")
def list_workflows(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(Workflow)
        .filter(Workflow.user_id == user.id)
        .order_by(Workflow.updated_at.desc())
        .all()
    )
    return {"workflows": [_workflow_meta(w) for w in rows]}


@router.post("")
def create_workflow(
    body: WorkflowSave, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    w = Workflow(name=body.name, data=json.dumps(body.definition), user_id=user.id)
    db.add(w)
    db.commit()
    return {"workflow": _workflow_meta(w)}


@router.get("/{workflow_id}")
def get_workflow(
    workflow_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if w is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"workflow": {**_workflow_meta(w), "definition": json.loads(w.data)}}


@router.put("/{workflow_id}")
def update_workflow(
    workflow_id: int,
    body: WorkflowSave,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if w is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    w.name = body.name
    w.data = json.dumps(body.definition)
    db.commit()
    return {"workflow": _workflow_meta(w)}


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    w = db.query(Workflow).filter(Workflow.id == workflow_id, Workflow.user_id == user.id).first()
    if w is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(w)
    db.commit()
    return {"ok": True}
