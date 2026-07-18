"""Shared types for the execution engine and control nodes."""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


class WorkflowError(Exception):
    """Raised when a workflow definition is invalid (cycle, no trigger, unknown type)."""


class NodeExecutionError(Exception):
    """Raised by a node to signal a clean, user-facing failure."""


class TemplateError(Exception):
    """Raised when a {{ }} template reference cannot be resolved."""


@dataclass
class NodeOutput:
    """Return this from a node's run() to route output to a specific handle.

    handle=None means the output goes out on all of the node's output handles.
    """

    data: Any
    handle: str | None = None


@dataclass
class NodeContext:
    """Everything a node's run() receives."""

    node_id: str
    config: dict[str, Any]
    inputs: list[Any] = field(default_factory=list)
    log: Callable[[str, str], None] = lambda level, message: None

    @property
    def input(self) -> Any:
        """Primary input: the first active upstream output (None for triggers)."""
        return self.inputs[0] if self.inputs else None
