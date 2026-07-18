from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.engine.registry import get_registry
from app.models import User

router = APIRouter(prefix="/api/nodes", tags=["nodes"])


@router.get("")
def list_node_types(user: User = Depends(get_current_user)):
    return {"nodes": get_registry().to_api()}
