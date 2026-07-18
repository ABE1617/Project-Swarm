from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.engine.registry import get_registry
from app.models import User

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.get("")
def list_node_types(user: User = Depends(get_current_user)):
    registry = get_registry()
    return {"nodes": registry.to_api(), "load_errors": registry.load_errors}


@router.post("/reload")
def reload_node_types(user: User = Depends(get_current_user)):
    """Re-scan builtin and drop-in node files without restarting the server."""
    registry = get_registry()
    registry.load()
    return {"nodes": registry.to_api(), "load_errors": registry.load_errors}
