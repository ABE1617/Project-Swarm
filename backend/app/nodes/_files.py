"""Shared path sandboxing for file nodes (underscore prefix = not a node)."""

from pathlib import Path

from app.config import ALLOW_ANY_PATH, FILES_DIR
from app.engine.types import NodeExecutionError


def resolve_sandboxed(path_str: str) -> Path:
    if not path_str or not str(path_str).strip():
        raise NodeExecutionError("A file path is required")
    p = Path(str(path_str))
    if not p.is_absolute():
        p = FILES_DIR / p
    p = p.resolve()
    if not ALLOW_ANY_PATH and not p.is_relative_to(FILES_DIR):
        raise NodeExecutionError(
            f"Path '{p}' is outside the sandbox directory '{FILES_DIR}'. "
            "Use a relative path, or set SWARM_ALLOW_ANY_PATH=1 to disable the sandbox."
        )
    return p
