"""Node discovery.

Two sources are scanned, in order:

1. Built-in nodes: every module in the ``app.nodes`` package.
2. User drop-in nodes: every ``*.py`` file in the ``nodes/`` directory at the
   project root (``config.NODES_DIR``). Drop a file in, hit the reload
   endpoint (or restart), and it appears in the palette — no other wiring.

A module counts as a node when it defines ``NODE_TYPE`` and a callable
``run``. User nodes with the same ``NODE_TYPE`` as a built-in override it.
Files that fail to load are reported via ``load_errors`` instead of being
silently ignored.
"""

import asyncio
import importlib
import importlib.util
import inspect
import logging
import pkgutil
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any

from app import config

logger = logging.getLogger(__name__)

CATEGORY_ORDER = {"Triggers": 0, "Logic": 1, "Data": 2, "AI": 3, "Actions": 4, "Files": 5}


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
    source: str  # "builtin" | "custom"
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
            "source": self.source,
        }


def _wrap_sync_run(sync_run: Callable) -> Callable:
    async def async_run(ctx):
        return await asyncio.to_thread(sync_run, ctx)

    return async_run


def _spec_from_module(module: ModuleType, source: str) -> NodeSpec | None:
    node_type = getattr(module, "NODE_TYPE", None)
    run = getattr(module, "run", None)
    if not node_type or not callable(run):
        return None

    if not inspect.iscoroutinefunction(run):
        run = _wrap_sync_run(run)

    try:
        timeout = float(getattr(module, "NODE_TIMEOUT", config.DEFAULT_NODE_TIMEOUT))
    except (TypeError, ValueError):
        timeout = config.DEFAULT_NODE_TIMEOUT

    return NodeSpec(
        type=str(node_type),
        name=str(getattr(module, "NODE_NAME", node_type)),
        description=str(getattr(module, "NODE_DESCRIPTION", "")),
        category=str(getattr(module, "NODE_CATEGORY", "Other")),
        color=str(getattr(module, "NODE_COLOR", "#64748b")),
        icon=str(getattr(module, "NODE_ICON", "box")),
        inputs=list(getattr(module, "NODE_INPUTS", ["in"])),
        outputs=list(getattr(module, "NODE_OUTPUTS", ["out"])),
        config_fields=list(getattr(module, "CONFIG_FIELDS", [])),
        timeout=timeout,
        source=source,
        run=run,
    )


def _load_user_module(path: Path) -> ModuleType:
    module_name = f"swarm_user_node_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot create import spec for {path.name}")
    module = importlib.util.module_from_spec(spec)
    # Replace any previous version so edits to the file take effect on reload.
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class NodeRegistry:
    def __init__(self):
        self._specs: dict[str, NodeSpec] = {}
        self.load_errors: list[dict[str, str]] = []

    def load(self) -> None:
        self._specs.clear()
        self.load_errors.clear()
        self._load_builtins()
        self._load_user_nodes()
        logger.info(
            "Loaded %d node types (%d custom): %s",
            len(self._specs),
            sum(1 for s in self._specs.values() if s.source == "custom"),
            ", ".join(sorted(self._specs)),
        )

    def _load_builtins(self) -> None:
        import app.nodes as nodes_pkg

        for modinfo in pkgutil.iter_modules(nodes_pkg.__path__):
            if modinfo.name.startswith("_"):
                continue
            qualified = f"app.nodes.{modinfo.name}"
            try:
                module = importlib.import_module(qualified)
                spec = _spec_from_module(module, source="builtin")
            except Exception as e:
                logger.exception("Failed to load builtin node module %s", qualified)
                self.load_errors.append({"file": f"{modinfo.name}.py", "error": str(e)})
                continue
            if spec is not None:
                self._specs[spec.type] = spec

    def _load_user_nodes(self) -> None:
        nodes_dir = Path(config.NODES_DIR)
        if not nodes_dir.is_dir():
            return
        for path in sorted(nodes_dir.glob("*.py")):
            if path.name.startswith("_"):
                continue
            try:
                module = _load_user_module(path)
                spec = _spec_from_module(module, source="custom")
            except Exception as e:
                logger.exception("Failed to load user node file %s", path)
                self.load_errors.append({"file": path.name, "error": str(e)})
                continue
            if spec is None:
                self.load_errors.append(
                    {
                        "file": path.name,
                        "error": "Not a node: define NODE_TYPE and a run(ctx) function",
                    }
                )
                continue
            if spec.type in self._specs and self._specs[spec.type].source == "builtin":
                logger.warning(
                    "User node %s overrides builtin node type '%s'", path.name, spec.type
                )
            self._specs[spec.type] = spec

    def get(self, node_type: str) -> NodeSpec | None:
        return self._specs.get(node_type)

    @property
    def types(self) -> list[str]:
        return list(self._specs)

    def to_api(self) -> list[dict[str, Any]]:
        specs = sorted(
            self._specs.values(), key=lambda s: (CATEGORY_ORDER.get(s.category, 99), s.name)
        )
        return [s.to_api() for s in specs]


_registry: NodeRegistry | None = None


def get_registry() -> NodeRegistry:
    global _registry
    if _registry is None:
        _registry = NodeRegistry()
        _registry.load()
    return _registry
