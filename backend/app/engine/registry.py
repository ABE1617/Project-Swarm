"""Node discovery: every .py file in app/nodes that defines NODE_TYPE and run() is a node."""

import importlib
import inspect
import logging
import pkgutil
from dataclasses import dataclass, field
from typing import Any, Callable

from app.config import DEFAULT_NODE_TIMEOUT

logger = logging.getLogger(__name__)


@dataclass
class NodeSpec:
    type: str
    name: str
    description: str
    category: str
    color: str
    icon: str
    inputs: list[str]
    outputs: list[str]
    config_fields: list[dict[str, Any]]
    timeout: float
    run: Callable = field(repr=False, default=None)

    def to_api(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "color": self.color,
            "icon": self.icon,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "config_fields": self.config_fields,
        }


class NodeRegistry:
    def __init__(self):
        self._specs: dict[str, NodeSpec] = {}

    def load(self) -> None:
        import app.nodes as nodes_pkg

        self._specs.clear()
        for modinfo in pkgutil.iter_modules(nodes_pkg.__path__):
            if modinfo.name.startswith("_"):
                continue
            try:
                module = importlib.import_module(f"app.nodes.{modinfo.name}")
            except Exception:
                logger.exception("Failed to import node module %s", modinfo.name)
                continue

            node_type = getattr(module, "NODE_TYPE", None)
            run = getattr(module, "run", None)
            if not node_type or not callable(run):
                continue

            wrapped = run
            if not inspect.iscoroutinefunction(run):
                # Allow plain sync nodes: run them in a worker thread.
                import asyncio

                def make_async(sync_run):
                    async def async_run(ctx):
                        return await asyncio.to_thread(sync_run, ctx)

                    return async_run

                wrapped = make_async(run)

            self._specs[node_type] = NodeSpec(
                type=node_type,
                name=getattr(module, "NODE_NAME", node_type),
                description=getattr(module, "NODE_DESCRIPTION", ""),
                category=getattr(module, "NODE_CATEGORY", "Other"),
                color=getattr(module, "NODE_COLOR", "#64748b"),
                icon=getattr(module, "NODE_ICON", "box"),
                inputs=list(getattr(module, "NODE_INPUTS", ["in"])),
                outputs=list(getattr(module, "NODE_OUTPUTS", ["out"])),
                config_fields=list(getattr(module, "CONFIG_FIELDS", [])),
                timeout=float(getattr(module, "NODE_TIMEOUT", DEFAULT_NODE_TIMEOUT)),
                run=wrapped,
            )
        logger.info("Loaded %d node types: %s", len(self._specs), ", ".join(sorted(self._specs)))

    def get(self, node_type: str) -> NodeSpec | None:
        return self._specs.get(node_type)

    @property
    def types(self) -> list[str]:
        return list(self._specs)

    def to_api(self) -> list[dict[str, Any]]:
        order = {"Triggers": 0, "Logic": 1, "Data": 2, "AI": 3, "Actions": 4, "Files": 5}
        specs = sorted(self._specs.values(), key=lambda s: (order.get(s.category, 99), s.name))
        return [s.to_api() for s in specs]


_registry: NodeRegistry | None = None


def get_registry() -> NodeRegistry:
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
        _registry.load()
    return _registry
